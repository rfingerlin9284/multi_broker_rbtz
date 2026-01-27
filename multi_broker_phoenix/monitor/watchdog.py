"""Always-on connection watchdog for brokers and AI services.

Improvements:
- Resolve AI health endpoints when API keys exist (xAI/Grok, DeepSeek) and prefer lightweight authenticated checks (/v1/models).
- Expose testable helpers: resolve_ai_health_urls and run_watchdog_once for deterministic unit tests.
- Treat 401/403 as AUTH FAIL; treat network errors as DISCONNECTED.
- Log freeze/unfreeze with timestamps and reasons.
"""
from __future__ import annotations
import threading
import time
import requests
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

try:
    from multi_broker_phoenix.hive.brain_seat_router import BrainSeatRouter
except Exception:
    BrainSeatRouter = None

logger = logging.getLogger(__name__)

# Public state
WATCHDOG_STATE: Dict[str, Any] = {
    'ok': True,
    'last_check': None,
    'details': {}
}

_TRADING_ALLOWED = True

# Optional reconnect callbacks: each is a callable that takes (oanda_connector)
_RECONNECT_CALLBACKS: list = []

# Durable audit helper (resolved at call-time to support monkeypatching in tests)
def _log_event(event_type: str, details: Dict[str, Any]):
    try:
        from multi_broker_phoenix.monitor import pnl_kill_switch as pk
        pk._log_event(event_type, details)
    except Exception:
        # Best-effort noop if durable logging not available
        try:
            logger.info('EVENT: %s %s', event_type, details)
        except Exception:
            pass


def register_reconnect_callback(cb):
    """Register a callable to be invoked (in background) when watchdog observes
    a transition from DISCONNECTED -> OK. The callback will receive the
    oanda_connector as its single argument."""
    try:
        if callable(cb):
            _RECONNECT_CALLBACKS.append(cb)
            return True
    except Exception:
        pass
    return False


def unregister_reconnect_callback(cb):
    """Unregister a previously registered reconnect callback."""
    try:
        if cb in _RECONNECT_CALLBACKS:
            _RECONNECT_CALLBACKS.remove(cb)
            return True
    except Exception:
        pass
    return False


def trading_allowed() -> bool:
    return _TRADING_ALLOWED


def _set_trading_allowed(val: bool):
    global _TRADING_ALLOWED
    _TRADING_ALLOWED = bool(val)


def _check_oanda(oanda_connector) -> bool:
    try:
        r = oanda_connector.verify_credentials()
        return r.get('success', False)
    except Exception:
        return False


def _check_endpoint(url: str, timeout: float = 5.0, headers: Optional[Dict[str, str]] = None) -> Tuple[bool, Optional[int], Optional[str]]:
    """Perform a health GET to url with optional headers.
    Returns (ok: bool, status_code, reason_text)
    """
    try:
        r = requests.get(url, timeout=timeout, headers=headers)
        code = getattr(r, 'status_code', None)
        if code == 200:
            return True, code, 'OK'
        if code in (401, 403):
            return False, code, 'AUTH_FAIL'
        # Any other non-200 considered a failure (DISCONNECTED/ERROR)
        return False, code, f'HTTP_{code}'
    except Exception as e:
        return False, None, f'EXCEPTION_{str(e)}'


def resolve_ai_health_urls() -> Tuple[Optional[str], Optional[str]]:
    """Return (grok_url, deepseek_url) for watchdog health checks.

    Logic:
    - If explicit GROK_HEALTH_URL or XAI_API_URL set, use that (prefer explicit).
    - Else if XAI/API key present (XAI_API_KEY or GROK_API_KEY), use XAI_BASE_URL + '/v1/models'.
    - For DeepSeek: if DEEPSEEK_HEALTH_URL set use it; else if DEEPSEEK_API_KEY present use 'https://api.deepseek.com/v1/models'.
    """
    grok_health_env = os.getenv('GROK_HEALTH_URL') or os.getenv('XAI_API_URL')
    xai_key = os.getenv('XAI_API_KEY') or os.getenv('GROK_API_KEY')
    xai_base = os.getenv('XAI_BASE_URL', 'https://api.x.ai').rstrip('/')

    if grok_health_env:
        grok_url = grok_health_env
    elif xai_key:
        base = xai_base.rstrip('/')
        if base.endswith('/v1'):
            grok_url = f"{base}/models"
        else:
            grok_url = f"{base}/v1/models"
    else:
        grok_url = None

    deepseek_health_env = os.getenv('DEEPSEEK_HEALTH_URL')
    deepseek_key = os.getenv('DEEPSEEK_API_KEY')
    if deepseek_health_env:
        deepseek_url = deepseek_health_env
    elif deepseek_key:
        deepseek_url = 'https://api.deepseek.com/v1/models'
    else:
        deepseek_url = None

    return grok_url, deepseek_url


def _log_freeze_change(ok: bool, details: Dict[str, Any]):
    ts = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    if not ok:
        logger.critical('WATCHDOG FREEZE %s - details=%s', ts, details)
    else:
        logger.info('WATCHDOG UNFREEZE %s - details=%s', ts, details)


def run_watchdog_once(oanda_connector, grok_url: Optional[str], deepseek_url: Optional[str], invoke_callbacks_async: bool = True) -> Dict[str, Any]:
    """Single iteration health check; sets WATCHDOG_STATE and trading_allowed.

    Args:
      invoke_callbacks_async: when False, invoke reconnect callbacks synchronously (useful for tests)

    Returns a snapshot dict of the new state for testing.
    """
    details: Dict[str, Any] = {}
    ok = True

    # OANDA check
    try:
        o_ok = _check_oanda(oanda_connector)
        details['oanda'] = {'ok': bool(o_ok)}
        if not o_ok:
            ok = False
    except Exception as e:
        details['oanda'] = {'ok': False, 'reason': str(e)}
        ok = False
        logger.exception('Watchdog OANDA check failed: %s', e)

    # AI health check (freeze only if NO brain seats healthy)
    if os.getenv('WATCHDOG_AI_HEALTH', '1').lower() in ('1', 'true', 'yes'):
        try:
            if BrainSeatRouter is None:
                raise RuntimeError('BrainSeatRouter unavailable')
            router = BrainSeatRouter()
            ok_any, snap, chosen = router.any_brain_ok()
            details['ai_seats'] = {
                'ok_any': ok_any,
                'chosen': chosen,
                'snapshot': snap
            }
            if not ok_any:
                ok = False
        except Exception as e:
            details['ai_seats'] = {'ok': False, 'reason': str(e)}
            ok = False

    prev_ok = WATCHDOG_STATE.get('ok', True)
    WATCHDOG_STATE['ok'] = ok
    WATCHDOG_STATE['last_check'] = time.time()
    WATCHDOG_STATE['details'] = details

    # Heartbeat monitoring (exit/protect/watchdog ticks)
    hb = heartbeat_status()
    details['heartbeat'] = hb
    if not hb.get('ok', True):
        ok = False
        if os.getenv('HEARTBEAT_FAILSAFE_FLATTEN', '1').lower() in ('1', 'true', 'yes'):
            try:
                _failsafe_flatten(oanda_connector, 'HEARTBEAT_STALE', hb)
            except Exception:
                pass

    if not ok:
        _set_trading_allowed(False)
    else:
        _set_trading_allowed(True)

    _write_watchdog_state()

    # If we just recovered from a disconnect, invoke any registered reconnect callbacks
    if not prev_ok and ok:
        # Emit durable narration event
        try:
            _log_event('WATCHDOG_UNFREEZE', {'details': details, 'timestamp': WATCHDOG_STATE.get('last_check')})
        except Exception:
            logger.exception('Watchdog: failed to record WATCHDOG_UNFREEZE event')

        try:
            for cb in list(_RECONNECT_CALLBACKS):
                try:
                    # Allow tests and callers to request synchronous callback invocation
                    if invoke_callbacks_async:
                        threading.Thread(target=lambda c=cb: c(oanda_connector), daemon=True).start()
                    else:
                        c = cb
                        c(oanda_connector)
                except Exception:
                    logger.exception('Watchdog: failed to start/invoke reconnect callback')
        except Exception:
            logger.exception('Watchdog: failed to invoke reconnect callbacks')
    elif not ok and prev_ok:
        # Transitioned to a frozen state
        try:
            _log_event('WATCHDOG_FREEZE', {'details': details, 'timestamp': WATCHDOG_STATE.get('last_check')})
        except Exception:
            logger.exception('Watchdog: failed to record WATCHDOG_FREEZE event')

    # Log with timestamp and reason
    _log_event('WATCHDOG_TICK', {'details': details, 'timestamp': WATCHDOG_STATE.get('last_check')})
    _log_freeze_change(ok, details)

    return dict(WATCHDOG_STATE)


def _state_age_seconds(path: str) -> Optional[float]:
    try:
        p = Path(path)
        if not p.exists():
            return None
        return time.time() - p.stat().st_mtime
    except Exception:
        return None


def heartbeat_status() -> Dict[str, Any]:
    max_skew = int(os.getenv('HEARTBEAT_MAX_SKEW_SEC', '180'))
    enforce_missing = os.getenv('HEARTBEAT_ENFORCE_MISSING', '0').lower() in ('1', 'true', 'yes')
    exit_state = os.getenv('HEARTBEAT_EXIT_STATE_FILE', 'ops/state/exit_manager.json')
    protect_state = os.getenv('HEARTBEAT_PROTECT_STATE_FILE', 'ops/state/protect_loop.json')
    watchdog_state = os.getenv('HEARTBEAT_WATCHDOG_STATE_FILE', 'ops/state/watchdog.json')

    ages = {
        'exit_manager': _state_age_seconds(exit_state),
        'protect_loop': _state_age_seconds(protect_state),
        'watchdog': _state_age_seconds(watchdog_state),
    }

    stale = []
    for k, age in ages.items():
        if age is None and not enforce_missing:
            continue
        if age is None or age > max_skew:
            stale.append(k)

    return {
        'ok': len(stale) == 0,
        'max_skew_sec': max_skew,
        'enforce_missing': enforce_missing,
        'ages_sec': ages,
        'stale': stale,
    }


def _write_watchdog_state() -> None:
    path = os.getenv('HEARTBEAT_WATCHDOG_STATE_FILE', 'ops/state/watchdog.json')
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, 'w') as f:
            f.write(str(int(time.time())))
    except Exception:
        pass


def _failsafe_flatten(oanda_connector, reason: str, details: Dict[str, Any]) -> bool:
    try:
        from execution.oanda_practice_client import OandaPracticeClient
        
        # RBOTZILLA_TOKEN_COMPAT: Resilient token access with fallback
        token = getattr(oanda_connector, 'token', '') or ''
        if not token:
            logger.warning('watchdog failsafe flatten: token unavailable (cannot execute)')
            _log_event('HEARTBEAT_FAILSAFE_ERROR', {'reason': reason, 'error': 'token_unavailable'})
            _set_trading_allowed(False)
            return False
        
        client = OandaPracticeClient(
            token=token,
            account_id=getattr(oanda_connector, 'account_id', None),
            base_url=getattr(oanda_connector, 'base_url', None),
            http_client=getattr(oanda_connector, 'http', None)
        )
        res = client.close_all_positions()
        _log_event('HEARTBEAT_FAILSAFE_FLATTEN', {'reason': reason, 'details': details, 'result': res})
        _set_trading_allowed(False)
        return True
    except Exception as e:
        _log_event('HEARTBEAT_FAILSAFE_ERROR', {'reason': reason, 'error': str(e)})
        try:
            _set_trading_allowed(False)
        except Exception:
            pass
        return False


def _run_watchdog(oanda_connector, grok_url: str | None, deepseek_url: str | None, interval: int = 15):
    while True:
        try:
            run_watchdog_once(oanda_connector, grok_url, deepseek_url)
        except Exception:
            logger.exception('Watchdog iteration failed')
        time.sleep(interval)


def start_watchdog(oanda_connector, grok_url: str | None = None, deepseek_url: str | None = None, interval: int = 15):
    t = threading.Thread(target=_run_watchdog, args=(oanda_connector, grok_url, deepseek_url, interval), daemon=True, name='watchdog')
    t.start()
    return t
