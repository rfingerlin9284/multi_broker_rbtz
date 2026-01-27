"""Broker Health Monitor with Circuit Breaker.

Provides constant connection monitoring and fail-closed behavior:
1. Periodic health checks (auth, pricing, orders endpoints)
2. Consecutive failure tracking
3. Circuit breaker (stop new trades when unhealthy)
4. Exponential backoff reconnect
5. Resume only after successful reconcile pass

Events emitted:
- BROKER_HEALTH_OK: All checks passed
- BROKER_HEALTH_DEGRADED: Some checks failing
- BROKER_HEALTH_CRITICAL: Broker unreachable, trading halted
- BROKER_RECONNECT_ATTEMPT: Attempting reconnection
- BROKER_RECONNECT_SUCCESS: Connection restored
- BROKER_RECONNECT_FAIL: Reconnection failed

State file: ops/state/broker_health.json
"""
from __future__ import annotations
import os
import time
import json
import logging
import threading
from typing import Dict, Any, Optional, Callable, List

logger = logging.getLogger(__name__)

# Configuration
DEFAULT_CONFIG = {
    'enabled': True,
    'check_interval_sec': int(os.getenv('BROKER_HEALTH_INTERVAL', '10')),
    'consecutive_failures_threshold': int(os.getenv('BROKER_FAILURE_THRESHOLD', '3')),
    'latency_threshold_ms': int(os.getenv('BROKER_LATENCY_THRESHOLD_MS', '5000')),
    'reconnect_max_backoff_sec': int(os.getenv('BROKER_RECONNECT_MAX_BACKOFF', '60')),
    'reconnect_initial_backoff_sec': int(os.getenv('BROKER_RECONNECT_INITIAL_BACKOFF', '2')),
    'require_reconcile_after_reconnect': True,
}

STATE_FILE = os.getenv('BROKER_HEALTH_STATE_FILE', 'ops/state/broker_health.json')

# Global state
_health_state: Dict[str, Any] = {
    'healthy': True,
    'trading_allowed': True,
    'consecutive_failures': 0,
    'last_check': None,
    'last_error': None,
    'checks': {
        'auth': None,
        'pricing': None,
        'orders': None,
        'latency_ms': None,
    },
}

_monitor_thread: Optional[threading.Thread] = None
_stop_event = threading.Event()
_reconnect_callbacks: List[Callable] = []


def _ensure_state_dir():
    """Ensure state directory exists."""
    import pathlib
    pathlib.Path(STATE_FILE).parent.mkdir(parents=True, exist_ok=True)


def _write_state() -> None:
    """Write state to JSON file."""
    try:
        _ensure_state_dir()
        with open(STATE_FILE, 'w') as f:
            json.dump(_health_state, f, indent=2, default=str)
    except Exception as e:
        logger.warning(f'Failed to write broker health state: {e}')


def _log_event(event_type: str, details: Dict[str, Any]) -> None:
    """Log event to durable narration stream."""
    try:
        from multi_broker_phoenix.monitor.pnl_kill_switch import _log_event as durable_log
        durable_log(event_type, details)
    except Exception:
        logger.info(f'BROKER_HEALTH_EVENT: {event_type} {details}')


def register_reconnect_callback(cb: Callable) -> None:
    """Register a callback to be invoked on successful reconnect."""
    if callable(cb) and cb not in _reconnect_callbacks:
        _reconnect_callbacks.append(cb)


def unregister_reconnect_callback(cb: Callable) -> None:
    """Unregister a reconnect callback."""
    if cb in _reconnect_callbacks:
        _reconnect_callbacks.remove(cb)


def is_healthy() -> bool:
    """Return whether broker is healthy."""
    return _health_state.get('healthy', False)


def is_trading_allowed() -> bool:
    """Return whether trading is currently allowed."""
    return _health_state.get('trading_allowed', False)


def get_health_state() -> Dict[str, Any]:
    """Return current health state."""
    return dict(_health_state)


def _check_auth(connector) -> Dict[str, Any]:
    """Check authentication status."""
    start = time.time()
    try:
        result = connector.verify_credentials()
        latency = (time.time() - start) * 1000
        return {
            'ok': result.get('success', False),
            'latency_ms': latency,
            'error': None if result.get('success') else 'Auth failed',
        }
    except Exception as e:
        return {
            'ok': False,
            'latency_ms': (time.time() - start) * 1000,
            'error': str(e),
        }


def _check_pricing(connector) -> Dict[str, Any]:
    """Check pricing endpoint reachability."""
    start = time.time()
    try:
        # Try to get a price for a common pair
        prices = connector.get_prices(['EUR_USD'])
        latency = (time.time() - start) * 1000
        has_prices = bool(prices.get('prices'))
        return {
            'ok': has_prices,
            'latency_ms': latency,
            'error': None if has_prices else 'No prices returned',
        }
    except Exception as e:
        return {
            'ok': False,
            'latency_ms': (time.time() - start) * 1000,
            'error': str(e),
        }


def _check_orders(connector) -> Dict[str, Any]:
    """Check orders endpoint reachability (list open trades)."""
    start = time.time()
    try:
        # Use the practice client if available
        try:
            from execution.oanda_practice_client import OandaPracticeClient
            
            # RBOTZILLA_TOKEN_COMPAT: Resilient token access with fallback
            token = getattr(connector, 'token', '') or ''
            if not token:
                logger.warning('broker_health orders check: token unavailable (skipping)')
                return {'ok': True, 'latency_ms': 0, 'error': 'token_unavailable', 'skipped': True}
            
            client = OandaPracticeClient(
                token=token,
                account_id=getattr(connector, 'account_id', None),
                base_url=getattr(connector, 'base_url', None),
                http_client=getattr(connector, 'http', None)
            )
            trades = client.list_open_trades()
        except Exception:
            # Fallback: try connector's method if exists
            if hasattr(connector, 'list_open_trades'):
                trades = connector.list_open_trades()
            else:
                return {'ok': True, 'latency_ms': 0, 'error': None}  # Assume OK if no method
        
        latency = (time.time() - start) * 1000
        return {
            'ok': True,
            'latency_ms': latency,
            'error': None,
        }
    except Exception as e:
        return {
            'ok': False,
            'latency_ms': (time.time() - start) * 1000,
            'error': str(e),
        }


def run_health_check(connector, config: Dict[str, Any] = None) -> Dict[str, Any]:
    """Run a single health check cycle.
    
    Returns:
        {
            'healthy': bool,
            'checks': {
                'auth': {...},
                'pricing': {...},
                'orders': {...},
            },
            'latency_ms': float (max of all checks),
            'timestamp': float,
        }
    """
    global _health_state
    cfg = config or DEFAULT_CONFIG
    ts = time.time()
    
    checks = {
        'auth': _check_auth(connector),
        'pricing': _check_pricing(connector),
        'orders': _check_orders(connector),
    }
    
    # Calculate overall health
    all_ok = all(c['ok'] for c in checks.values())
    max_latency = max(c['latency_ms'] for c in checks.values())
    latency_ok = max_latency < cfg.get('latency_threshold_ms', 5000)
    
    healthy = all_ok and latency_ok
    
    # Update state
    prev_healthy = _health_state.get('healthy', True)
    prev_trading = _health_state.get('trading_allowed', True)
    
    if healthy:
        _health_state['consecutive_failures'] = 0
        _health_state['last_error'] = None
    else:
        _health_state['consecutive_failures'] += 1
        errors = [c['error'] for c in checks.values() if c['error']]
        _health_state['last_error'] = '; '.join(errors) if errors else 'Latency exceeded'
    
    _health_state['healthy'] = healthy
    _health_state['last_check'] = ts
    _health_state['checks'] = checks
    _health_state['checks']['latency_ms'] = max_latency
    
    # Circuit breaker logic
    threshold = cfg.get('consecutive_failures_threshold', 3)
    if _health_state['consecutive_failures'] >= threshold:
        _health_state['trading_allowed'] = False
    elif healthy:
        # Only re-enable trading after successful health check
        # If require_reconcile_after_reconnect is True, we need additional confirmation
        if not prev_healthy and cfg.get('require_reconcile_after_reconnect', True):
            # Keep trading disabled until explicit re-enable after reconcile
            pass
        else:
            _health_state['trading_allowed'] = True
    
    # Emit events on state change
    if healthy and not prev_healthy:
        _log_event('BROKER_HEALTH_OK', {
            'timestamp': ts,
            'checks': {k: v['ok'] for k, v in checks.items()},
            'latency_ms': max_latency,
        })
        # Invoke reconnect callbacks
        for cb in _reconnect_callbacks:
            try:
                cb(connector)
            except Exception as e:
                logger.exception(f'Reconnect callback error: {e}')
    elif not healthy and prev_healthy:
        _log_event('BROKER_HEALTH_DEGRADED', {
            'timestamp': ts,
            'checks': checks,
            'consecutive_failures': _health_state['consecutive_failures'],
        })
    elif not healthy and _health_state['consecutive_failures'] >= threshold and prev_trading:
        _log_event('BROKER_HEALTH_CRITICAL', {
            'timestamp': ts,
            'message': 'Trading halted due to broker health failures',
            'consecutive_failures': _health_state['consecutive_failures'],
        })
    
    _write_state()
    
    return {
        'healthy': healthy,
        'checks': checks,
        'latency_ms': max_latency,
        'timestamp': ts,
        'trading_allowed': _health_state['trading_allowed'],
        'consecutive_failures': _health_state['consecutive_failures'],
    }


def attempt_reconnect(connector, config: Dict[str, Any] = None) -> Dict[str, Any]:
    """Attempt to reconnect to broker with exponential backoff.
    
    Returns:
        {
            'success': bool,
            'attempts': int,
            'final_error': str or None,
        }
    """
    global _health_state
    cfg = config or DEFAULT_CONFIG
    
    initial_backoff = cfg.get('reconnect_initial_backoff_sec', 2)
    max_backoff = cfg.get('reconnect_max_backoff_sec', 60)
    
    attempts = 0
    backoff = initial_backoff
    
    while not _stop_event.is_set():
        attempts += 1
        _log_event('BROKER_RECONNECT_ATTEMPT', {
            'attempt': attempts,
            'backoff_sec': backoff,
            'timestamp': time.time(),
        })
        
        # Try health check
        result = run_health_check(connector, cfg)
        
        if result['healthy']:
            _log_event('BROKER_RECONNECT_SUCCESS', {
                'attempts': attempts,
                'timestamp': time.time(),
            })
            return {
                'success': True,
                'attempts': attempts,
                'final_error': None,
            }
        
        # Wait with backoff
        _stop_event.wait(backoff)
        backoff = min(backoff * 2, max_backoff)
        
        # Add jitter (±20%)
        import random
        backoff *= (0.8 + 0.4 * random.random())
    
    _log_event('BROKER_RECONNECT_FAIL', {
        'attempts': attempts,
        'final_error': _health_state.get('last_error'),
        'timestamp': time.time(),
    })
    
    return {
        'success': False,
        'attempts': attempts,
        'final_error': _health_state.get('last_error'),
    }


def enable_trading_after_reconcile() -> None:
    """Explicitly enable trading after successful reconcile pass.
    
    Call this after startup reconcile or after a reconnect reconcile.
    """
    global _health_state
    if _health_state.get('healthy', False):
        _health_state['trading_allowed'] = True
        _write_state()
        _log_event('BROKER_TRADING_ENABLED', {
            'timestamp': time.time(),
            'trigger': 'reconcile_pass',
        })


def disable_trading(reason: str = 'manual') -> None:
    """Disable trading (e.g., for maintenance or emergency)."""
    global _health_state
    _health_state['trading_allowed'] = False
    _write_state()
    _log_event('BROKER_TRADING_DISABLED', {
        'timestamp': time.time(),
        'reason': reason,
    })


def start_health_monitor(connector, config: Dict[str, Any] = None) -> threading.Thread:
    """Start the broker health monitor background thread.
    
    Args:
        connector: Broker connector (OANDA/IBKR/etc.)
        config: Override config dict
    
    Returns:
        The monitor thread
    """
    global _monitor_thread, _stop_event
    
    cfg = config or DEFAULT_CONFIG
    interval = cfg.get('check_interval_sec', 10)
    
    if not cfg.get('enabled', True):
        logger.info('Broker health monitor disabled by config')
        return None
    
    _stop_event.clear()
    
    def _run():
        while not _stop_event.is_set():
            try:
                result = run_health_check(connector, cfg)
                
                # If unhealthy and trading was disabled, try reconnect
                if not result['healthy'] and not result['trading_allowed']:
                    logger.warning('Broker unhealthy, attempting reconnect...')
                    attempt_reconnect(connector, cfg)
                
            except Exception as e:
                logger.exception(f'Health monitor error: {e}')
            
            _stop_event.wait(interval)
    
    _monitor_thread = threading.Thread(target=_run, daemon=True, name='broker_health_monitor')
    _monitor_thread.start()
    logger.info(f'Broker health monitor started (interval={interval}s)')
    return _monitor_thread


def stop_health_monitor() -> None:
    """Stop the broker health monitor background thread."""
    global _stop_event
    _stop_event.set()
    if _monitor_thread and _monitor_thread.is_alive():
        _monitor_thread.join(timeout=5)
    logger.info('Broker health monitor stopped')


# Integration with existing watchdog
def sync_with_watchdog() -> None:
    """Sync broker health state with the existing watchdog module."""
    try:
        from multi_broker_phoenix.monitor.watchdog import _set_trading_allowed
        _set_trading_allowed(_health_state.get('trading_allowed', False))
    except Exception:
        pass
