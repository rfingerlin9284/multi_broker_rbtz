"""OCO Reconciliation + Auto-Repair + Emergency Flatten.

This module provides always-on verification of open trades:
1. Every N seconds, fetch all open trades from broker
2. Verify each has valid SL + TP attached
3. If missing/invalid: attempt repair with conservative defaults
4. If repair fails and risk exceeds threshold: FLATTEN the position

Events emitted:
- OCO_OK: Trade has valid protections
- OCO_MISSING: Trade missing SL or TP
- OCO_INVALID: Trade has SL/TP but prices are nonsensical
- OCO_REPAIR_ATTEMPT: Attempting to attach missing protections
- OCO_REPAIR_SUCCESS: Repair succeeded
- OCO_REPAIR_FAIL: Repair failed
- EMERGENCY_FLATTEN: Position closed due to unprotected risk

State file: ops/state/oco_health.json
"""
from __future__ import annotations
import os
import time
import json
import logging
import threading
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Configuration
DEFAULT_CONFIG = {
    'enabled': True,
    'interval_sec': int(os.getenv('OCO_RECONCILE_INTERVAL', '10')),
    'repair_attempts': int(os.getenv('OCO_REPAIR_ATTEMPTS', '3')),
    'repair_backoff_sec': float(os.getenv('OCO_REPAIR_BACKOFF', '2.0')),
    'emergency_flatten_usd': float(os.getenv('EMERGENCY_FLATTEN_USD', '100.0')),
    'auto_repair': os.getenv('OCO_AUTO_REPAIR', 'true').lower() in ('true', '1', 'yes'),
    'auto_flatten': os.getenv('OCO_AUTO_FLATTEN', 'true').lower() in ('true', '1', 'yes'),
}

STATE_FILE = os.getenv('OCO_STATE_FILE', 'ops/state/oco_health.json')

# Global state
_reconciler_thread: Optional[threading.Thread] = None
_stop_event = threading.Event()


def _ensure_state_dir():
    """Ensure state directory exists."""
    import pathlib
    pathlib.Path(STATE_FILE).parent.mkdir(parents=True, exist_ok=True)


def _write_state(state: Dict[str, Any]) -> None:
    """Write state to JSON file."""
    try:
        _ensure_state_dir()
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2, default=str)
    except Exception as e:
        logger.warning(f'Failed to write OCO state: {e}')


def _read_state() -> Dict[str, Any]:
    """Read state from JSON file."""
    try:
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return {}


def _log_event(event_type: str, details: Dict[str, Any]) -> None:
    """Log event to durable narration stream."""
    try:
        from multi_broker_phoenix.monitor.pnl_kill_switch import _log_event as durable_log
        durable_log(event_type, details)
    except Exception:
        logger.info(f'OCO_EVENT: {event_type} {details}')


def _get_pip_math():
    """Import pip_math module."""
    try:
        from multi_broker_phoenix.risk.pip_math import (
            pip_value_usd,
            risk_to_sl_usd,
            compute_safe_sl_price,
            compute_safe_tp_price,
            get_config,
        )
        return {
            'pip_value_usd': pip_value_usd,
            'risk_to_sl_usd': risk_to_sl_usd,
            'compute_safe_sl_price': compute_safe_sl_price,
            'compute_safe_tp_price': compute_safe_tp_price,
            'get_config': get_config,
        }
    except ImportError:
        return None


def _extract_trade_info(trade: Dict[str, Any]) -> Dict[str, Any]:
    """Extract relevant trade information from broker response."""
    trade_id = trade.get('tradeID') or trade.get('id') or trade.get('trade_id')
    instrument = trade.get('instrument') or trade.get('symbol')
    units = int(trade.get('currentUnits') or trade.get('units') or trade.get('initialUnits') or 0)
    entry_price = float(trade.get('price') or trade.get('averagePrice') or trade.get('entry_price') or 0)
    
    # Side determination
    if units > 0:
        side = 'BUY'
    elif units < 0:
        side = 'SELL'
    else:
        side = 'UNKNOWN'
    
    # SL/TP extraction (OANDA format)
    sl_info = trade.get('stopLoss') or trade.get('stopLossOrder') or trade.get('stopLossOnFill')
    tp_info = trade.get('takeProfit') or trade.get('takeProfitOrder') or trade.get('takeProfitOnFill')
    
    sl_price = None
    tp_price = None
    
    if sl_info:
        if isinstance(sl_info, dict):
            sl_price = float(sl_info.get('price', 0))
        else:
            sl_price = float(sl_info)
    
    if tp_info:
        if isinstance(tp_info, dict):
            tp_price = float(tp_info.get('price', 0))
        else:
            tp_price = float(tp_info)
    
    # Unrealized P/L
    unrealized_pl = float(trade.get('unrealizedPL') or trade.get('unrealized_pnl') or 0)
    
    return {
        'trade_id': trade_id,
        'instrument': instrument,
        'units': abs(units),
        'side': side,
        'entry_price': entry_price,
        'sl_price': sl_price,
        'tp_price': tp_price,
        'unrealized_pl': unrealized_pl,
        'raw': trade,
    }


def _validate_oco(trade_info: Dict[str, Any]) -> Dict[str, Any]:
    """Validate OCO (SL/TP) for a trade.
    
    Returns:
        {
            'status': 'OK' | 'MISSING' | 'INVALID',
            'has_sl': bool,
            'has_tp': bool,
            'sl_valid': bool,
            'tp_valid': bool,
            'issues': list[str],
            'risk_usd': float or None,
        }
    """
    issues = []
    
    sl_price = trade_info.get('sl_price')
    tp_price = trade_info.get('tp_price')
    entry_price = trade_info.get('entry_price', 0)
    side = trade_info.get('side', 'BUY')
    units = trade_info.get('units', 0)
    instrument = trade_info.get('instrument', 'EUR_USD')
    
    has_sl = sl_price is not None and sl_price > 0
    has_tp = tp_price is not None and tp_price > 0
    
    sl_valid = False
    tp_valid = False
    
    if has_sl:
        # Validate SL direction
        if side == 'BUY':
            sl_valid = sl_price < entry_price
            if not sl_valid:
                issues.append(f'SL_WRONG_DIRECTION: BUY trade SL ({sl_price}) >= entry ({entry_price})')
        elif side == 'SELL':
            sl_valid = sl_price > entry_price
            if not sl_valid:
                issues.append(f'SL_WRONG_DIRECTION: SELL trade SL ({sl_price}) <= entry ({entry_price})')
        else:
            sl_valid = True  # Can't validate direction
    
    if has_tp:
        # Validate TP direction
        if side == 'BUY':
            tp_valid = tp_price > entry_price
            if not tp_valid:
                issues.append(f'TP_WRONG_DIRECTION: BUY trade TP ({tp_price}) <= entry ({entry_price})')
        elif side == 'SELL':
            tp_valid = tp_price < entry_price
            if not tp_valid:
                issues.append(f'TP_WRONG_DIRECTION: SELL trade TP ({tp_price}) >= entry ({entry_price})')
        else:
            tp_valid = True
    
    # Calculate risk if SL present
    risk_usd = None
    pip_math = _get_pip_math()
    if has_sl and sl_valid and pip_math:
        try:
            risk_usd = pip_math['risk_to_sl_usd'](units, instrument, entry_price, sl_price)
        except Exception:
            pass
    
    # Determine status
    if not has_sl:
        issues.append('MISSING_SL')
    if not has_tp:
        issues.append('MISSING_TP')
    
    if not has_sl or not has_tp:
        status = 'MISSING'
    elif not sl_valid or not tp_valid:
        status = 'INVALID'
    else:
        status = 'OK'
    
    return {
        'status': status,
        'has_sl': has_sl,
        'has_tp': has_tp,
        'sl_valid': sl_valid,
        'tp_valid': tp_valid,
        'issues': issues,
        'risk_usd': risk_usd,
    }


def _attempt_repair(client, trade_info: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """Attempt to repair missing/invalid OCO for a trade.
    
    Returns:
        {
            'success': bool,
            'action': 'repair_sl' | 'repair_tp' | 'repair_both' | 'none',
            'error': str or None,
            'new_sl': float or None,
            'new_tp': float or None,
        }
    """
    trade_id = trade_info.get('trade_id')
    instrument = trade_info.get('instrument')
    entry_price = trade_info.get('entry_price')
    side = trade_info.get('side')
    units = trade_info.get('units')
    sl_price = trade_info.get('sl_price')
    tp_price = trade_info.get('tp_price')
    
    pip_math = _get_pip_math()
    if not pip_math:
        return {'success': False, 'action': 'none', 'error': 'pip_math not available'}
    
    risk_config = pip_math['get_config']()
    max_risk = risk_config.get('MAX_RISK_USD_PER_TRADE', 25.0)
    min_rr = risk_config.get('MIN_RR', 1.5)
    
    new_sl = None
    new_tp = None
    actions = []
    
    # Compute safe SL if missing or invalid
    if sl_price is None or sl_price <= 0:
        new_sl = pip_math['compute_safe_sl_price'](units, instrument, entry_price, side, max_risk)
        actions.append('repair_sl')
    
    # Compute safe TP based on SL
    effective_sl = new_sl if new_sl else sl_price
    if (tp_price is None or tp_price <= 0) and effective_sl:
        new_tp = pip_math['compute_safe_tp_price'](entry_price, effective_sl, side, min_rr)
        actions.append('repair_tp')
    
    if not actions:
        return {'success': True, 'action': 'none', 'error': None}
    
    action = 'repair_both' if len(actions) == 2 else actions[0]
    
    # Attempt to modify trade via broker client
    try:
        # OANDA: use trade modify endpoint or create SL/TP orders
        if hasattr(client, 'create_stop_loss') and new_sl:
            client.create_stop_loss(trade_id, new_sl)
        
        # For TP, OANDA may require a separate endpoint
        if hasattr(client, 'create_take_profit') and new_tp:
            client.create_take_profit(trade_id, new_tp)
        elif hasattr(client, 'modify_trade') and (new_sl or new_tp):
            # Some brokers have a single modify endpoint
            modify_payload = {}
            if new_sl:
                modify_payload['stopLoss'] = {'price': str(new_sl)}
            if new_tp:
                modify_payload['takeProfit'] = {'price': str(new_tp)}
            client.modify_trade(trade_id, modify_payload)
        
        return {
            'success': True,
            'action': action,
            'error': None,
            'new_sl': new_sl,
            'new_tp': new_tp,
        }
    except Exception as e:
        return {
            'success': False,
            'action': action,
            'error': str(e),
            'new_sl': new_sl,
            'new_tp': new_tp,
        }


def _flatten_position(client, trade_info: Dict[str, Any]) -> Dict[str, Any]:
    """Emergency flatten a position.
    
    Returns:
        {
            'success': bool,
            'error': str or None,
        }
    """
    instrument = trade_info.get('instrument')
    trade_id = trade_info.get('trade_id')
    
    try:
        # Try close by trade ID first
        if hasattr(client, 'close_trade') and trade_id:
            client.close_trade(trade_id)
            return {'success': True, 'error': None}
        
        # Fall back to close position
        if hasattr(client, 'close_position') and instrument:
            client.close_position(instrument)
            return {'success': True, 'error': None}
        
        return {'success': False, 'error': 'No close method available'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def run_oco_reconcile_once(client, config: Dict[str, Any] = None) -> Dict[str, Any]:
    """Run a single OCO reconciliation pass.
    
    Args:
        client: Broker client with list_open_trades() method
        config: Override config dict
    
    Returns:
        {
            'processed': int,
            'ok': int,
            'missing': int,
            'invalid': int,
            'repaired': int,
            'flattened': int,
            'errors': list,
            'trades': list[dict],  # Per-trade status
            'timestamp': float,
        }
    """
    cfg = config or DEFAULT_CONFIG
    ts = time.time()
    
    results = {
        'processed': 0,
        'ok': 0,
        'missing': 0,
        'invalid': 0,
        'repaired': 0,
        'flattened': 0,
        'errors': [],
        'trades': [],
        'timestamp': ts,
    }
    
    # Fetch open trades
    try:
        trades_resp = client.list_open_trades()
        trades = trades_resp.get('trades', [])
    except Exception as e:
        results['errors'].append(f'list_open_trades failed: {e}')
        _log_event('OCO_RECONCILE_ERROR', {'error': str(e), 'timestamp': ts})
        return results
    
    pip_math = _get_pip_math()
    emergency_threshold = cfg.get('emergency_flatten_usd', 100.0)
    
    for trade in trades:
        trade_info = _extract_trade_info(trade)
        validation = _validate_oco(trade_info)
        
        results['processed'] += 1
        
        trade_result = {
            'trade_id': trade_info['trade_id'],
            'instrument': trade_info['instrument'],
            'units': trade_info['units'],
            'side': trade_info['side'],
            'oco_status': validation['status'],
            'risk_usd': validation['risk_usd'],
            'pip_value_usd': None,
            'sl_distance_pips': None,
        }
        
        # Add pip math details if available
        if pip_math and trade_info['sl_price'] and trade_info['entry_price']:
            try:
                from multi_broker_phoenix.risk.pip_math import pip_value_usd, sl_distance_pips
                trade_result['pip_value_usd'] = pip_value_usd(
                    trade_info['units'],
                    trade_info['instrument'],
                    trade_info['entry_price']
                )
                trade_result['sl_distance_pips'] = sl_distance_pips(
                    trade_info['entry_price'],
                    trade_info['sl_price'],
                    trade_info['instrument']
                )
            except Exception:
                pass
        
        if validation['status'] == 'OK':
            results['ok'] += 1
            _log_event('OCO_OK', {
                'trade_id': trade_info['trade_id'],
                'instrument': trade_info['instrument'],
                'risk_usd': validation['risk_usd'],
                'timestamp': ts,
            })
            trade_result['action'] = 'none'
        
        elif validation['status'] in ('MISSING', 'INVALID'):
            if validation['status'] == 'MISSING':
                results['missing'] += 1
            else:
                results['invalid'] += 1
            
            _log_event(f'OCO_{validation["status"]}', {
                'trade_id': trade_info['trade_id'],
                'instrument': trade_info['instrument'],
                'issues': validation['issues'],
                'timestamp': ts,
            })
            
            # Attempt repair if enabled
            if cfg.get('auto_repair', True):
                _log_event('OCO_REPAIR_ATTEMPT', {
                    'trade_id': trade_info['trade_id'],
                    'instrument': trade_info['instrument'],
                    'timestamp': ts,
                })
                
                repair_ok = False
                for attempt in range(cfg.get('repair_attempts', 3)):
                    repair_result = _attempt_repair(client, trade_info, cfg)
                    if repair_result['success']:
                        results['repaired'] += 1
                        repair_ok = True
                        _log_event('OCO_REPAIR_SUCCESS', {
                            'trade_id': trade_info['trade_id'],
                            'instrument': trade_info['instrument'],
                            'new_sl': repair_result['new_sl'],
                            'new_tp': repair_result['new_tp'],
                            'timestamp': ts,
                        })
                        trade_result['action'] = 'repaired'
                        trade_result['new_sl'] = repair_result['new_sl']
                        trade_result['new_tp'] = repair_result['new_tp']
                        break
                    else:
                        time.sleep(cfg.get('repair_backoff_sec', 2.0) * (2 ** attempt))
                
                if not repair_ok:
                    _log_event('OCO_REPAIR_FAIL', {
                        'trade_id': trade_info['trade_id'],
                        'instrument': trade_info['instrument'],
                        'error': repair_result.get('error'),
                        'timestamp': ts,
                    })
                    
                    # Check if we need emergency flatten
                    # Estimate worst-case risk (if no SL, assume 100 pips)
                    worst_case_risk = emergency_threshold + 1  # Default to flatten
                    if pip_math and trade_info['entry_price']:
                        try:
                            # Assume 100 pip move as worst case
                            pv = pip_math['pip_value_usd'](
                                trade_info['units'],
                                trade_info['instrument'],
                                trade_info['entry_price']
                            )
                            worst_case_risk = pv * 100  # 100 pips
                        except Exception:
                            pass
                    
                    if cfg.get('auto_flatten', True) and worst_case_risk > emergency_threshold:
                        _log_event('EMERGENCY_FLATTEN', {
                            'trade_id': trade_info['trade_id'],
                            'instrument': trade_info['instrument'],
                            'worst_case_risk': worst_case_risk,
                            'threshold': emergency_threshold,
                            'timestamp': ts,
                        })
                        
                        flatten_result = _flatten_position(client, trade_info)
                        if flatten_result['success']:
                            results['flattened'] += 1
                            trade_result['action'] = 'flattened'
                            logger.warning(f'EMERGENCY_FLATTEN: closed {trade_info["instrument"]} trade {trade_info["trade_id"]}')
                        else:
                            results['errors'].append(f'flatten failed for {trade_info["trade_id"]}: {flatten_result["error"]}')
                            trade_result['action'] = 'flatten_failed'
                    else:
                        trade_result['action'] = 'repair_failed_no_flatten'
            else:
                trade_result['action'] = 'no_repair_configured'
        
        results['trades'].append(trade_result)
    
    # Update state file
    _write_state({
        'last_reconcile': ts,
        'processed': results['processed'],
        'ok': results['ok'],
        'missing': results['missing'],
        'invalid': results['invalid'],
        'repaired': results['repaired'],
        'flattened': results['flattened'],
        'trades': results['trades'],
    })
    
    # Emit OCO_RECONCILE_COMPLETE for audit trail (proves loop is running)
    _log_event('OCO_RECONCILE_COMPLETE', {
        'processed': results['processed'],
        'ok': results['ok'],
        'missing': results['missing'],
        'invalid': results['invalid'],
        'repaired': results['repaired'],
        'flattened': results['flattened'],
        'timestamp': ts,
    })
    
    return results


def start_oco_reconciler(client, config: Dict[str, Any] = None) -> threading.Thread:
    """Start the OCO reconciliation background thread.
    
    Args:
        client: Broker client with list_open_trades() method
        config: Override config dict
    
    Returns:
        The reconciler thread
    """
    global _reconciler_thread, _stop_event
    
    cfg = config or DEFAULT_CONFIG
    interval = cfg.get('interval_sec', 10)
    
    if not cfg.get('enabled', True):
        logger.info('OCO reconciler disabled by config')
        return None
    
    _stop_event.clear()
    
    def _run():
        while not _stop_event.is_set():
            try:
                run_oco_reconcile_once(client, cfg)
            except Exception as e:
                logger.exception(f'OCO reconciler error: {e}')
            _stop_event.wait(interval)
    
    _reconciler_thread = threading.Thread(target=_run, daemon=True, name='oco_reconciler')
    _reconciler_thread.start()
    logger.info(f'OCO reconciler started (interval={interval}s)')
    return _reconciler_thread


def stop_oco_reconciler() -> None:
    """Stop the OCO reconciliation background thread."""
    global _stop_event
    _stop_event.set()
    if _reconciler_thread and _reconciler_thread.is_alive():
        _reconciler_thread.join(timeout=5)
    logger.info('OCO reconciler stopped')


def get_oco_health() -> Dict[str, Any]:
    """Get current OCO health status from state file."""
    return _read_state()
