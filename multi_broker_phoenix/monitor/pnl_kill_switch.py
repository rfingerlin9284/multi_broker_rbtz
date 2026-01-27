"""P&L kill switch: continuously monitor account-level P&L and flatten + freeze when threshold exceeded.

Design:
- Expose resolve_pnl_config() to read ~/.rbotzilla/features.yaml (read-only) or fall back to defaults
- Expose run_pnl_once(oanda_connector) to perform single deterministic check (useful for unit tests)
- Expose start_pnl_loop(oanda_connector) to run in background thread
- On trigger: call OANDA connector flatten_positions(), set watchdog freeze, log events to JSONL/audit and sqlite ledger

FIXED PATHS:
- All log paths are now repo-root relative (not package-relative)
- Directories are created with proper mkdir(parents=True, exist_ok=True)
- SQLite failures degrade gracefully without crashing
"""
from __future__ import annotations
import os
import threading
import time
import json
import sqlite3
import logging
from pathlib import Path
from typing import Dict, Any, Optional

try:
    import yaml
except Exception:
    yaml = None

logger = logging.getLogger(__name__)

# Allow tests to monkeypatch OandaPracticeClient by exposing it at module scope
try:
    from execution.oanda_practice_client import OandaPracticeClient
except Exception:
    OandaPracticeClient = None

DEFAULT_CONFIG = {
    'pnl_kill_switch': {
        'enabled': True,
        'session_max_loss_usd': 220.0,
        'daily_max_loss_usd': 220.0,
        'action': 'FLATTEN_AND_FREEZE',
        'check_interval_sec': 5,
        'include_unrealized': True,
        'include_realized': True
    },
    'margin_emergency': {
        'enabled': True,
        'min_margin_available_usd': 500.0,
        'max_margin_used_pct': 0.5,
        'flatten_worst_first': True
    }
}

# FIXED: Determine repo root properly
REPO_ROOT = Path(__file__).resolve().parents[3]  # multi_broker_phoenix/monitor/pnl_kill_switch.py -> 3 levels up
LOG_DIR = REPO_ROOT / 'logs'
RUN_DIR = LOG_DIR / 'runs'
OPS_DIR = REPO_ROOT / 'ops' / 'state'

# Ensure directories exist
LOG_DIR.mkdir(parents=True, exist_ok=True)
RUN_DIR.mkdir(parents=True, exist_ok=True)
OPS_DIR.mkdir(parents=True, exist_ok=True)

EVENTS_PATH = RUN_DIR / 'pnl_kill_events.jsonl'
AUDIT_LOG = LOG_DIR / 'audit.log'
SQLITE_DB = LOG_DIR / 'trade_ledger.sqlite'

# Ensure DB table exists (graceful degradation if fails)
def _ensure_db():
    try:
        # Ensure parent directory exists
        SQLITE_DB.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(str(SQLITE_DB))
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT,
                    event_type TEXT,
                    details TEXT
                )
                """
            )
            conn.commit()
        finally:
            conn.close()
    except Exception as e:
        logger.warning(f'Failed to initialize sqlite ledger (will degrade to JSONL only): {e}')

_ensure_db()


def _log_event(event_type: str, details: Dict[str, Any]):
    """
    Log event to durable storage.
    
    Writes to:
    1. JSONL events file (primary)
    2. Audit log (human-readable)
    3. SQLite ledger (queryable, degrades gracefully if unavailable)
    """
    ts = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    record = {'ts': ts, 'event': event_type, 'details': details}
    
    # JSONL (primary)
    try:
        EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(EVENTS_PATH, 'a') as f:
            f.write(json.dumps(record) + '\n')
    except Exception as e:
        logger.error(f'Failed to write events.jsonl: {e}')

    # Audit log (human-readable)
    try:
        AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(AUDIT_LOG, 'a') as f:
            f.write(f"{ts} {event_type} {json.dumps(details)}\n")
    except Exception as e:
        logger.error(f'Failed to write audit log: {e}')

    # SQLite ledger (graceful degradation)
    try:
        SQLITE_DB.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(SQLITE_DB))
        conn.execute('INSERT INTO events (ts, event_type, details) VALUES (?, ?, ?)', (ts, event_type, json.dumps(details)))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning(f'Failed to write sqlite ledger (non-fatal): {e}')


def resolve_pnl_config() -> Dict[str, Any]:
    """
    Resolve PnL configuration from features.yaml or defaults.
    
    Returns:
        Config dictionary with pnl_kill_switch and margin_emergency settings
    """
    cfg_path = Path.home() / '.rbotzilla' / 'features.yaml'
    if yaml and cfg_path.exists():
        try:
            with open(cfg_path, 'r') as f:
                obj = yaml.safe_load(f)
                risk = obj.get('risk', {}) if isinstance(obj, dict) else {}
                return {
                    'pnl_kill_switch': risk.get('pnl_kill_switch', DEFAULT_CONFIG['pnl_kill_switch'])
                }
        except Exception:
            logger.exception('Failed to parse features.yaml; falling back to defaults')
    return DEFAULT_CONFIG


def _compute_account_pnl(client) -> Dict[str, float]:
    """
    Compute account P&L from broker client.
    
    Args:
        client: Broker client with get_account_summary() and list_open_trades()
    
    Returns:
        {'realized': float, 'unrealized': float, 'total': float}
    """
    realized = 0.0
    unrealized = 0.0
    try:
        acct = client.get_account_summary().get('account', {})
        # Some API variations may include 'unrealizedPL'
        unrealized = float(acct.get('unrealizedPL', 0.0) or 0.0)
        # Realized not always present; attempt best-effort
        realized = float(acct.get('realizedPL', 0.0) or 0.0)
    except Exception:
        # Fallback: sum unrealized from open trades
        try:
            trades = client.list_open_trades().get('trades', [])
            unrealized = sum(float(t.get('unrealizedPL', 0.0) or 0.0) for t in trades)
        except Exception:
            unrealized = 0.0
    return {'realized': realized, 'unrealized': unrealized, 'total': realized + unrealized}


def _connector_ready(oanda_connector) -> bool:
    """Check if OANDA connector is ready to use."""
    try:
        return bool(
            oanda_connector
            and getattr(oanda_connector, 'token', None)
            and getattr(oanda_connector, 'account_id', None)
            and getattr(oanda_connector, 'base_url', None)
            and getattr(oanda_connector, 'http', None)
        )
    except Exception:
        return False


def run_pnl_once(oanda_connector) -> Dict[str, Any]:
    """Perform one P&L check. If threshold exceeded, flatten positions and freeze.

    Returns a snapshot dict with keys: triggered(bool), total_loss(float), details(dict)
    """
    cfg = resolve_pnl_config()['pnl_kill_switch']
    if not cfg.get('enabled', True):
        return {'triggered': False, 'reason': 'disabled'}

    if not _connector_ready(oanda_connector):
        _log_event('PNL_KILL_CONNECTOR_MISSING', {'reason': 'connector_missing'})
        try:
            from multi_broker_phoenix.monitor.watchdog import _set_trading_allowed as _wd_set
            _wd_set(False)
        except Exception:
            logger.exception('PNL_KILL: failed to set watchdog freeze')
        return {'triggered': True, 'reason': 'connector_missing'}

    # Prefer module-level OandaPracticeClient (testable); fallback to import if not set
    ClientClass = globals().get('OandaPracticeClient')
    if ClientClass is None:
        try:
            from execution.oanda_practice_client import OandaPracticeClient as ClientClass
        except Exception as e:
            logger.exception('PNL_KILL: failed to create practice client: %s', e)
            return {'triggered': False, 'reason': 'client_init_failed'}

    try:
        # RBOTZILLA_TOKEN_COMPAT: Resilient token access with fallback
        token = getattr(oanda_connector, 'token', '') or ''
        if not token:
            logger.warning('PNL_KILL: token unavailable (skipping check)')
            return {'triggered': False, 'reason': 'token_unavailable'}
        
        client = ClientClass(
            token=token,
            account_id=getattr(oanda_connector, 'account_id', None),
            base_url=getattr(oanda_connector, 'base_url', None),
            http_client=getattr(oanda_connector, 'http', None)
        )
        # Support test factories that return the actual client when the instance is callable
        if callable(client) and not hasattr(client, 'get_account_summary'):
            try:
                client = client()
            except Exception:
                pass
    except Exception as e:
        logger.exception('PNL_KILL: failed to instantiate practice client: %s', e)
        return {'triggered': False, 'reason': 'client_init_failed'}

    pnl = _compute_account_pnl(client)
    include_unrealized = cfg.get('include_unrealized', True)
    include_realized = cfg.get('include_realized', True)

    total_loss = 0.0
    if include_realized:
        total_loss += pnl.get('realized', 0.0)
    if include_unrealized:
        total_loss += pnl.get('unrealized', 0.0)

    snapshot = {'realized': pnl.get('realized', 0.0), 'unrealized': pnl.get('unrealized', 0.0), 'total': total_loss}

    # Trigger if loss <= -session_max_loss_usd (note: losses are negative numbers)
    thresh = -abs(float(cfg.get('session_max_loss_usd', 220.0)))
    if total_loss <= thresh:
        # Execute flatten + freeze
        _log_event('PNL_KILL_SWITCH_TRIGGERED', {'snapshot': snapshot, 'threshold': thresh})
        # Attempt flatten
        try:
            res = client.close_all_positions()
            _log_event('FLATTEN_ATTEMPT', {'result': res})
        except Exception as e:
            _log_event('FLATTEN_FAIL', {'error': str(e)})
            # Keep trying and mark triggered
            try:
                from multi_broker_phoenix.monitor.watchdog import _set_trading_allowed as _wd_set
                _wd_set(False)
            except Exception:
                logger.exception('PNL_KILL: failed to set watchdog freeze')
            return {'triggered': True, 'total_loss': total_loss, 'details': snapshot}

        # Verify closure
        try:
            remaining = client.list_open_trades().get('trades', [])
            if remaining:
                _log_event('FLATTEN_PARTIAL', {'remaining': len(remaining)})
                # Keep freezing and log
                try:
                    from multi_broker_phoenix.monitor.watchdog import _set_trading_allowed as _wd_set
                    _wd_set(False)
                except Exception:
                    logger.exception('PNL_KILL: failed to set watchdog freeze')
                return {'triggered': True, 'total_loss': total_loss, 'details': snapshot}
        except Exception:
            _log_event('FLATTEN_VERIFY_FAIL', {'error': 'verify_failed'})
            try:
                from multi_broker_phoenix.monitor.watchdog import _set_trading_allowed as _wd_set
                _wd_set(False)
            except Exception:
                logger.exception('PNL_KILL: failed to set watchdog freeze')
            return {'triggered': True, 'total_loss': total_loss, 'details': snapshot}

        # Success: frozen and flattened
        try:
            from multi_broker_phoenix.monitor.watchdog import _set_trading_allowed as _wd_set
            _wd_set(False)
        except Exception:
            logger.exception('PNL_KILL: failed to set watchdog freeze')

        _log_event('FLATTEN_SUCCESS', {'snapshot': snapshot})
        return {'triggered': True, 'total_loss': total_loss, 'details': snapshot}

    return {'triggered': False, 'total_loss': total_loss, 'details': snapshot}


def start_pnl_loop(oanda_connector):
    """Start background P&L monitoring loop."""
    cfg = resolve_pnl_config()['pnl_kill_switch']
    interval = int(cfg.get('check_interval_sec', 5))

    def _run():
        while True:
            try:
                run_pnl_once(oanda_connector)
            except Exception:
                logger.exception('PNL_KILL loop failed')
            try:
                # margin emergency: check and act if necessary
                try:
                    cfg = resolve_pnl_config().get('margin_emergency', {})
                    if cfg.get('enabled', True):
                        run_margin_once(oanda_connector, cfg)
                except Exception:
                    logger.exception('MARGIN_EMERGENCY check failed')
            except Exception:
                logger.exception('MARGIN_EMERGENCY loop failed')
            time.sleep(interval)

    t = threading.Thread(target=_run, daemon=True, name='pnl_kill')
    t.start()
    return t


def run_margin_once(oanda_connector, cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Check margin levels and flatten if thresholds exceeded."""
    cfg = cfg or resolve_pnl_config().get('margin_emergency', {})
    if not cfg.get('enabled', True):
        return {'triggered': False, 'reason': 'disabled'}
    if not _connector_ready(oanda_connector):
        _log_event('MARGIN_EMERGENCY_CONNECTOR_MISSING', {'reason': 'connector_missing'})
        try:
            from multi_broker_phoenix.monitor.watchdog import _set_trading_allowed as _wd_set
            _wd_set(False)
        except Exception:
            logger.exception('MARGIN_EMERGENCY: failed to set watchdog freeze')
        return {'triggered': True, 'reason': 'connector_missing'}
    
    # Instantiate practice client like run_pnl_once
    ClientClass = globals().get('OandaPracticeClient')
    if ClientClass is None:
        try:
            from execution.oanda_practice_client import OandaPracticeClient as ClientClass
        except Exception as e:
            logger.exception('MARGIN_EMERGENCY: failed to create practice client: %s', e)
            return {'triggered': False, 'reason': 'client_init_failed'}

    try:
        # RBOTZILLA_TOKEN_COMPAT: Resilient token access with fallback
        token = getattr(oanda_connector, 'token', '') or ''
        if not token:
            logger.warning('MARGIN_EMERGENCY: token unavailable (skipping check)')
            return {'triggered': False, 'reason': 'token_unavailable'}
        
        client = ClientClass(
            token=token,
            account_id=getattr(oanda_connector, 'account_id', None),
            base_url=getattr(oanda_connector, 'base_url', None),
            http_client=getattr(oanda_connector, 'http', None)
        )
        if callable(client) and not hasattr(client, 'get_account_summary'):
            try:
                client = client()
            except Exception:
                pass
    except Exception as e:
        logger.exception('MARGIN_EMERGENCY: failed to instantiate practice client: %s', e)
        return {'triggered': False, 'reason': 'client_init_failed'}

    try:
        acct = client.get_account_summary().get('account', {})
        margin_avail = float(acct.get('marginAvailable', acct.get('marginAvailable', 0.0) or 0.0) or 0.0)
        margin_used = float(acct.get('marginUsed', 0.0) or 0.0)
        balance = float(acct.get('balance', 0.0) or 0.0)
        margin_used_pct = (margin_used / balance) if balance > 0 else 1.0
    except Exception:
        logger.exception('MARGIN_EMERGENCY: failed to read account summary')
        return {'triggered': False, 'reason': 'account_read_failed'}

    min_margin = float(cfg.get('min_margin_available_usd', 500.0))
    max_used_pct = float(cfg.get('max_margin_used_pct', 0.5))

    if margin_avail < min_margin or margin_used_pct > max_used_pct:
        _log_event('MARGIN_EMERGENCY_TRIGGERED', {'margin_available': margin_avail, 'margin_used': margin_used, 'margin_used_pct': margin_used_pct})
        # Attempt flatten (prioritize worst positions if configured otherwise flatten all)
        try:
            if cfg.get('flatten_worst_first', True):
                # Best-effort: close trades with largest notional exposure first
                trades = client.list_open_trades().get('trades', [])
                if not trades:
                    logger.info('MARGIN_EMERGENCY: No open trades to close')
                    _log_event('MARGIN_FLATTEN_ATTEMPT', {'closed': [], 'note': 'no_open_trades'})
                else:
                    trades_sorted = sorted(trades, key=lambda t: abs(float(t.get('currentUnits', 0)) * float(t.get('price', acct.get('price', 0) or 1.0))), reverse=True)
                    closed = []
                    for t in trades_sorted:
                        inst = t.get('instrument')
                        try:
                            result = client.close_position(inst)
                            closed.append(inst)
                            if result.get('status') == 'already_closed':
                                logger.info('MARGIN_EMERGENCY: %s already closed', inst)
                        except Exception:
                            logger.exception('MARGIN_EMERGENCY: failed to close instrument: %s', inst)
                    _log_event('MARGIN_FLATTEN_ATTEMPT', {'closed': closed})
            else:
                res = client.close_all_positions()
                _log_event('MARGIN_FLATTEN_ATTEMPT', {'result': res})
        except Exception as e:
            _log_event('MARGIN_FLATTEN_FAIL', {'error': str(e)})
        try:
            from multi_broker_phoenix.monitor.watchdog import _set_trading_allowed as _wd_set
            _wd_set(False)
        except Exception:
            logger.exception('MARGIN_EMERGENCY: failed to set watchdog freeze')
        return {'triggered': True, 'margin_available': margin_avail, 'margin_used_pct': margin_used_pct}

    return {'triggered': False, 'margin_available': margin_avail, 'margin_used_pct': margin_used_pct}
