"""Protect Loop - Unified protection cycle for autonomous trading.

This module provides a single entry point that runs all protection
checks in one cycle:
1. OCO reconciliation (verify/repair SL/TP)
2. Exit manager check (profit lock, trailing, time stop)
3. Broker health verification

Events emitted:
- PROTECT_LOOP_TICK: Each cycle completion (proves loop is running)
- Plus all events from OCO reconciler and exit manager

Usage:
    from multi_broker_phoenix.risk.protect_loop import run_protect_once, start_protect_loop
    
    # One-shot check
    result = run_protect_once(connector)
    
    # Background loop
    start_protect_loop(connector)  # Runs every 30s
"""
from __future__ import annotations
import os
import time
import logging
import threading
import json
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# State file for observability
STATE_FILE = os.getenv('PROTECT_STATE_FILE', 'ops/state/protect_loop.json')


def _ensure_state_dir():
    """Ensure state directory exists."""
    import pathlib
    pathlib.Path(STATE_FILE).parent.mkdir(parents=True, exist_ok=True)


def _write_state(state: Dict[str, Any]) -> None:
    """Write state to JSON file."""
    try:
        _ensure_state_dir()
        state['updated_at'] = datetime.utcnow().isoformat() + 'Z'
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2, default=str)
    except Exception as e:
        logger.warning(f'Failed to write protect loop state: {e}')


def _log_event(event_type: str, details: Dict[str, Any]) -> None:
    """Log event to durable narration stream."""
    try:
        from multi_broker_phoenix.monitor.pnl_kill_switch import _log_event as durable_log
        durable_log(event_type, details)
    except Exception:
        logger.info(f'PROTECT_EVENT: {event_type} {details}')


def run_protect_once(connector, account_id: str = None) -> Dict[str, Any]:
    """Run a single protection cycle.
    
    This is the unified "protect loop" that:
    1. Runs OCO reconciliation
    2. Runs exit manager checks
    3. Verifies broker health
    
    Args:
        connector: OANDA connector
        account_id: OANDA account ID (optional)
    
    Returns:
        Dict with results from all subsystems
    """
    ts = time.time()
    results = {
        'timestamp': ts,
        'oco': None,
        'exit_manager': None,
        'broker_health': None,
        'errors': [],
    }
    
    # 1. OCO Reconciliation
    try:
        from multi_broker_phoenix.risk.oco_reconcile import run_oco_reconcile_once
        from execution.oanda_practice_client import OandaPracticeClient
        
        oco_client = OandaPracticeClient(
            token=connector.token,
            account_id=account_id or connector.account_id,
            base_url=connector.base_url,
            http_client=getattr(connector, 'http', None)
        )
        results['oco'] = run_oco_reconcile_once(oco_client)
    except Exception as e:
        results['errors'].append(f'OCO reconcile error: {e}')
        logger.error(f'Protect loop OCO error: {e}')
    
    # 2. Exit Manager Check
    try:
        from multi_broker_phoenix.risk.exit_manager import get_exit_manager
        em = get_exit_manager()
        if em:
            results['exit_manager'] = em.check_all_positions()
        else:
            results['exit_manager'] = {'skipped': True, 'reason': 'not_initialized'}
    except Exception as e:
        results['errors'].append(f'Exit manager error: {e}')
        logger.error(f'Protect loop exit manager error: {e}')
    
    # 3. Broker Health
    try:
        from multi_broker_phoenix.risk.broker_health import get_health_state
        results['broker_health'] = get_health_state()
    except ImportError:
        results['broker_health'] = {'skipped': True, 'reason': 'module_not_available'}
    except Exception as e:
        results['errors'].append(f'Broker health error: {e}')
        logger.error(f'Protect loop broker health error: {e}')
    
    # Emit PROTECT_LOOP_TICK event (proves loop is running)
    _log_event('PROTECT_LOOP_TICK', {
        'timestamp': ts,
        'oco_ok': results.get('oco', {}).get('ok', 0) if results.get('oco') else 0,
        'oco_missing': results.get('oco', {}).get('missing', 0) if results.get('oco') else 0,
        'oco_repaired': results.get('oco', {}).get('repaired', 0) if results.get('oco') else 0,
        'exit_profit_locks': results.get('exit_manager', {}).get('profit_locks', 0) if results.get('exit_manager') else 0,
        'broker_healthy': results.get('broker_health', {}).get('healthy', False) if results.get('broker_health') else False,
        'errors': len(results['errors']),
    })
    
    # Write state for observability
    _write_state(results)
    
    return results


# Global loop control
_protect_thread: Optional[threading.Thread] = None
_stop_event = threading.Event()


def start_protect_loop(connector, interval_sec: int = None, account_id: str = None) -> threading.Thread:
    """Start the background protection loop.
    
    Args:
        connector: OANDA connector
        interval_sec: Check interval (default: 30s or from env PROTECT_LOOP_INTERVAL)
        account_id: OANDA account ID
    
    Returns:
        The protection loop thread
    """
    global _protect_thread, _stop_event
    
    interval = interval_sec or int(os.getenv('PROTECT_LOOP_INTERVAL', '30'))
    
    _stop_event.clear()
    
    def _run():
        logger.info(f'Protect loop started (interval={interval}s)')
        while not _stop_event.is_set():
            try:
                run_protect_once(connector, account_id)
            except Exception as e:
                logger.exception(f'Protect loop error: {e}')
            _stop_event.wait(interval)
        logger.info('Protect loop stopped')
    
    _protect_thread = threading.Thread(target=_run, daemon=True, name='protect_loop')
    _protect_thread.start()
    return _protect_thread


def stop_protect_loop() -> None:
    """Stop the background protection loop."""
    global _stop_event
    _stop_event.set()
    if _protect_thread and _protect_thread.is_alive():
        _protect_thread.join(timeout=5)


def get_protect_state() -> Dict[str, Any]:
    """Get current protection loop state from state file."""
    try:
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return {}


if __name__ == '__main__':
    # Quick self-test
    print("Protect Loop module loaded successfully")
    print(f"State file: {STATE_FILE}")
