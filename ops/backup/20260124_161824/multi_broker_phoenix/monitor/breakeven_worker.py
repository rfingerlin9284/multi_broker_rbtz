"""Breakeven worker: move stop-loss to breakeven when safe.

This worker is broker-authoritative: it queries open trades, checks profit,
and calls the practice client to set a stop loss at the entry price +/- offset.
"""
from __future__ import annotations
import time
import threading
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Import _log_event for durable logging
try:
    from multi_broker_phoenix.monitor.pnl_kill_switch import _log_event
except Exception:
    def _log_event(*a, **k):
        logger.info('LOG_EVENT: %s %s', a, k)

# Allow tests to monkeypatch OandaPracticeClient
try:
    from execution.oanda_practice_client import OandaPracticeClient
except Exception:
    OandaPracticeClient = None

DEFAULT_BREAKEVEN_CFG = {
    'enabled': True,
    'interval_sec': 10,
    'trigger_pips': 8.0,
    'sl_offset_pips': 0.2,
    'verify_after_modify': True,
}


def _pip_size_for(instrument: str) -> float:
    """Get pip size using centralized pip_math module."""
    try:
        from multi_broker_phoenix.risk.pip_math import pip_size
        return pip_size(instrument)
    except ImportError:
        # Fallback: JPY vs non-JPY heuristic
        inst = (instrument or '').upper()
        if 'JPY' in inst or inst.endswith('_JPY'):
            return float(0.01)
        return float(0.0001)


def run_breakeven_once(oanda_connector, cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    cfg = cfg or DEFAULT_BREAKEVEN_CFG
    if not cfg.get('enabled', True):
        return {'handled': False, 'reason': 'disabled'}

    ClientClass = globals().get('OandaPracticeClient')
    if ClientClass is None:
        try:
            from execution.oanda_practice_client import OandaPracticeClient as ClientClass
        except Exception:
            logger.exception('BREAKEVEN: failed to import practice client')
            return {'handled': False, 'reason': 'client_import_failed'}

    try:
        client = ClientClass(token=oanda_connector.token, account_id=oanda_connector.account_id, base_url=oanda_connector.base_url, http_client=oanda_connector.http)
        if callable(client) and not hasattr(client, 'list_open_trades'):
            try:
                client = client()
            except Exception:
                pass
    except Exception:
        logger.exception('BREAKEVEN: failed to instantiate client')
        return {'handled': False, 'reason': 'client_init_failed'}

    results = {'processed': 0, 'breakeven_set': 0, 'skipped': 0, 'errors': [], 'pips_by_trade': {}}
    try:
        trades = client.list_open_trades().get('trades', [])
    except Exception:
        logger.exception('BREAKEVEN: failed to list open trades')
        return {'handled': False, 'reason': 'list_failed'}

    trigger_pips = float(cfg.get('trigger_pips', 8.0))
    sl_offset = float(cfg.get('sl_offset_pips', 0.2))

    for t in trades:
        results['processed'] += 1
        try:
            tid = t.get('tradeID') or t.get('id')
            inst = t.get('instrument')
            entry_price = float(t.get('price') or t.get('initialPrice') or t.get('openPrice') or 0.0)
            # Some brokers provide 'currentPrice' or we can compute mid from prices
            current_price = float(t.get('currentPrice') or t.get('price') or t.get('markPrice') or 0.0)
            if current_price == 0.0:
                # try pricing lookup
                try:
                    p = client.get_prices([inst]).get('prices', [])
                    if p:
                        current_price = float(p[0].get('closeoutAsk') or p[0].get('closeoutBid') or p[0].get('closeoutAsk') or 0.0)
                except Exception:
                    pass

            if not entry_price or not current_price:
                results['skipped'] += 1
                continue

            pip_size = _pip_size_for(inst)
            # Determine direction from units
            units = float(t.get('currentUnits', t.get('units', 0)) or 0)
            direction = 1 if units > 0 else -1 if units < 0 else 0
            if direction == 0:
                results['skipped'] += 1
                continue

            move_in_pips = (current_price - entry_price) * (1.0 / pip_size) * direction
            results['pips_by_trade'][str(tid)] = move_in_pips
            if move_in_pips >= trigger_pips:
                # Candidate breakeven price
                if direction > 0:
                    be_price = entry_price + sl_offset * pip_size
                else:
                    be_price = entry_price - sl_offset * pip_size

                # Extra guard: re-check threshold before attempting any modification
                if not (move_in_pips >= trigger_pips):
                    results['skipped'] += 1
                    continue

                # Do not loosen existing SL: check existing stop
                has_stop = bool(t.get('stopLoss') or t.get('stopLossOrder') or t.get('stopLossOnFill'))
                if has_stop:
                    # ensure the current SL is not higher (i.e., not loosening) before setting
                    curr_sl = float(t.get('stopLoss') or t.get('sl') or 0.0)
                    if curr_sl:
                        # For longs, curr_sl should be <= be_price; for shorts, curr_sl >= be_price
                        if (direction > 0 and curr_sl >= be_price) or (direction < 0 and curr_sl <= be_price):
                            results['skipped'] += 1
                            continue

                # Attempt to set stop to breakeven
                try:
                    resp = client.create_stop_loss(tid, be_price)
                    set_ok = False
                    if cfg.get('verify_after_modify', True):
                        # re-query trades
                        updated = client.list_open_trades().get('trades', [])
                        for ut in updated:
                            if ut.get('tradeID') == tid or ut.get('id') == tid:
                                if ut.get('stopLoss') or ut.get('stopLossOrder'):
                                    set_ok = True
                                    break
                    else:
                        set_ok = True

                    if set_ok:
                        _log_event('BREAKEVEN_SET_PASS', {'tradeID': tid, 'instrument': inst, 'breakeven_price': be_price})
                        results['breakeven_set'] += 1
                    else:
                        _log_event('BREAKEVEN_SET_FAIL', {'tradeID': tid, 'instrument': inst, 'attempted_price': be_price})
                        results['errors'].append(f"breakeven_verify_failed:{tid}")
                except Exception as e:
                    logger.exception('BREAKEVEN: failed to set stop for %s: %s', tid, e)
                    results['errors'].append(str(e))
            else:
                results['skipped'] += 1
        except Exception as e:
            logger.exception('BREAKEVEN: error processing trade: %s', e)
            results['errors'].append(str(e))

    return results


def start_breakeven_worker(oanda_connector, cfg: Optional[Dict[str, Any]] = None):
    cfg = cfg or DEFAULT_BREAKEVEN_CFG
    if not cfg.get('enabled', True):
        return None
    interval = int(cfg.get('interval_sec', 10))

    def _run():
        while True:
            try:
                run_breakeven_once(oanda_connector, cfg)
            except Exception:
                logger.exception('BREAKEVEN worker failed')
            time.sleep(interval)

    t = threading.Thread(target=_run, daemon=True, name='breakeven')
    t.start()
    return t
