"""Protect-or-Exit Reconciler

Continuously verifies open trades for SL/TP/OCO/trailing presence. Attempts
repair up to 3 times with exponential backoff. If repair still fails the trade
is closed (autonomous stop-out) and the global watchdog is frozen.
"""
from __future__ import annotations
import time
import threading
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Expose OandaPracticeClient symbol for tests to monkeypatch
try:
    from execution.oanda_practice_client import OandaPracticeClient
except Exception:
    OandaPracticeClient = None

DEFAULT_RECONCILE_CONFIG = {
    'interval_sec': 15,
    'repair_attempts': 3,
    'initial_backoff_sec': 1.0,
    'enabled': True,
}


def _sleep(seconds: float) -> None:
    # single abstraction so tests can monkeypatch
    time.sleep(seconds)


def _repair_trade(client, trade, candidate_hint=None) -> bool:
    """Attempt to repair protections (trailing stop or SL/TP) for a single trade.
    Return True if repaired, False otherwise.
    """
    tid = trade.get('tradeID') or trade.get('id')
    instrument = trade.get('instrument')
    # Prefer create_trailing_stop when trade supports it
    try:
        # Use candidate_hint to suggest distance if provided
        distance = None
        if candidate_hint:
            distance = getattr(candidate_hint, 'trailing_distance', getattr(candidate_hint, 'trailing', None))
        # If client supports create_trailing_stop, attempt
        if hasattr(client, 'create_trailing_stop') and tid:
            # distance fallback
            dist = float(distance or 10.0)
            client.create_trailing_stop(instrument, tid, dist)
            return True
    except Exception:
        logger.exception('PROTECT_REPAIR: trailing creation failed for %s', tid)
    try:
        # Fallback: try to attach stop via close position helper (some APIs may support modify)
        if hasattr(client, 'create_order_market') and instrument and hasattr(candidate_hint, 'stop_loss') and hasattr(candidate_hint, 'take_profit'):
            # As a destructive fallback no-op here; real implementation may need modify endpoints
            return False
    except Exception:
        logger.exception('PROTECT_REPAIR: fallback modify failed for %s', tid)
    return False


def run_reconcile_once(oanda_connector, cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    cfg = cfg or DEFAULT_RECONCILE_CONFIG
    if not cfg.get('enabled', True):
        return {'handled': False, 'reason': 'disabled'}

    # instantiate client
    ClientClass = globals().get('OandaPracticeClient')
    if ClientClass is None:
        try:
            from execution.oanda_practice_client import OandaPracticeClient as ClientClass
        except Exception:
            logger.exception('PROTECT: failed to import practice client')
            return {'handled': False, 'reason': 'client_import_failed'}

    try:
        client = ClientClass(token=oanda_connector.token, account_id=oanda_connector.account_id, base_url=oanda_connector.base_url, http_client=oanda_connector.http)
        if callable(client) and not hasattr(client, 'list_open_trades'):
            try:
                client = client()
            except Exception:
                pass
    except Exception:
        logger.exception('PROTECT: failed to instantiate client')
        return {'handled': False, 'reason': 'client_init_failed'}

    trades = []
    try:
        trades = client.list_open_trades().get('trades', [])
    except Exception:
        logger.exception('PROTECT: failed to list open trades')
        return {'handled': False, 'reason': 'list_failed'}

    results = {'processed': 0, 'repaired': 0, 'closed': 0, 'errors': []}

    for trade in trades:
        results['processed'] += 1
        # Detect presence of protections
        has_stop = bool(trade.get('stopLoss') or trade.get('stopLossOrder') or trade.get('stopLossOnFill'))
        has_tp = bool(trade.get('takeProfit') or trade.get('takeProfitOrder') or trade.get('takeProfitOnFill'))
        has_trailing = bool(trade.get('trailingStopLoss') or trade.get('trailingStopLossOnFill'))

        if has_stop and has_tp:
            # fully protected
            continue

        repaired = False
        # attempt repairs with backoff
        attempts = int(cfg.get('repair_attempts', 3))
        backoff = float(cfg.get('initial_backoff_sec', 1.0))
        for attempt in range(attempts):
            try:
                ok = _repair_trade(client, trade)
                if ok:
                    repaired = True
                    results['repaired'] += 1
                    break
            except Exception as e:
                logger.exception('PROTECT: repair attempt failed: %s', e)
            # backoff
            _sleep(backoff * (2 ** attempt))

        if not repaired:
            # Close this trade and freeze trading
            try:
                inst = trade.get('instrument')
                client.close_position(inst)
                results['closed'] += 1
                _log = getattr(logger, 'warning')
                _log('PROTECT: closed unprotected trade %s (%s)', trade.get('tradeID'), inst)
            except Exception as e:
                results['errors'].append(str(e))
                logger.exception('PROTECT: failed to close trade: %s', e)
            try:
                from multi_broker_phoenix.monitor.watchdog import _set_trading_allowed as _wd_set
                _wd_set(False)
            except Exception:
                logger.exception('PROTECT: failed to set watchdog freeze')

    return results


def start_reconciler(oanda_connector, cfg: Optional[Dict[str, Any]] = None):
    cfg = cfg or DEFAULT_RECONCILE_CONFIG
    interval = int(cfg.get('interval_sec', 15))

    def _run():
        while True:
            try:
                run_reconcile_once(oanda_connector, cfg)
            except Exception:
                logger.exception('PROTECT reconciler failed')
            time.sleep(interval)

    t = threading.Thread(target=_run, daemon=True, name='protect_reconciler')
    t.start()
    return t


def start_up_reconcile(oanda_connector, cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Perform a one-shot startup reconcile sequence.

    Steps (atomic-ish):
    - Freeze new entries
    - Run protect reconcile once (repair/close unprotected trades)
    - Run P&L kill check once
    - Run margin emergency once
    - Run breakeven worker once

    Returns {'passed': bool, 'details': {...}}
    """
    cfg = cfg or DEFAULT_RECONCILE_CONFIG
    results: Dict[str, Any] = {'passed': False, 'details': {}}

    # Freeze trading while reconciling
    try:
        from multi_broker_phoenix.monitor.watchdog import _set_trading_allowed as _wd_set
        _wd_set(False)
    except Exception:
        logger.exception('STARTUP_RECONCILE: failed to freeze trading')

    # Durable banner
    try:
        from multi_broker_phoenix.monitor.pnl_kill_switch import _log_event
    except Exception:
        def _log_event(et, d):
            logger.info('STARTUP_LOG: %s %s', et, d)

    _log_event('STARTUP_RECONCILE_BEGIN', {'timestamp': time.time()})

    passed = True
    details: Dict[str, Any] = {}

    # Protect reconcile
    try:
        pr = run_reconcile_once(oanda_connector, cfg)
        details['protect'] = pr
        if pr.get('errors'):
            passed = False
    except Exception as e:
        logger.exception('STARTUP_RECONCILE: protect reconcile failed')
        details['protect_error'] = str(e)
        passed = False

    # P&L kill switch run once
    try:
        from multi_broker_phoenix.monitor.pnl_kill_switch import run_pnl_once
        pnl = run_pnl_once(oanda_connector)
        details['pnl'] = pnl
        if pnl.get('triggered'):
            # If kill switch triggered, treat as FAIL (system should remain frozen)
            passed = False
    except Exception as e:
        logger.exception('STARTUP_RECONCILE: pnl check failed')
        details['pnl_error'] = str(e)
        passed = False

    # Margin emergency run once
    try:
        from multi_broker_phoenix.monitor.pnl_kill_switch import run_margin_once
        me = run_margin_once(oanda_connector)
        details['margin'] = me
        if me.get('triggered'):
            passed = False
    except Exception as e:
        logger.exception('STARTUP_RECONCILE: margin check failed')
        details['margin_error'] = str(e)
        passed = False

    # Breakeven pass
    try:
        from multi_broker_phoenix.monitor.breakeven_worker import run_breakeven_once
        be = run_breakeven_once(oanda_connector, {})
        details['breakeven'] = be
        # breakeven errors are non-fatal; just note
        if be.get('errors'):
            details['breakeven_errors'] = be.get('errors')
    except Exception as e:
        logger.exception('STARTUP_RECONCILE: breakeven check failed')
        details['breakeven_error'] = str(e)

    if passed:
        try:
            _log_event('STARTUP_RECONCILE_END', {'result': 'PASS', 'details': details})
        except Exception:
            logger.info('STARTUP_RECONCILE_END PASS %s', details)
        try:
            from multi_broker_phoenix.monitor.watchdog import _set_trading_allowed as _wd_set
            _wd_set(True)
        except Exception:
            logger.exception('STARTUP_RECONCILE: failed to unfreeze trading')
        results['passed'] = True
    else:
        try:
            _log_event('STARTUP_RECONCILE_END', {'result': 'FAIL', 'details': details})
        except Exception:
            logger.info('STARTUP_RECONCILE_END FAIL %s', details)
        # Keep trading frozen; caller should retry
        results['passed'] = False

    results['details'] = details
    return results
