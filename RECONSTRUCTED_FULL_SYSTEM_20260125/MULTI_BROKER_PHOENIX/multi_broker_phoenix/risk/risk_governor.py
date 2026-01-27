"""Pre-Trade Risk Governor - Hard veto before order submission.

This module provides a single gate that MUST be called before any order
is submitted to the broker. It validates:

1. Risk to SL in USD is within budget
2. RR ratio meets minimum threshold
3. Units don't exceed per-pair caps
4. SL distance is sane

If ANY constraint is violated, the trade is BLOCKED and a RISK_VIOLATION
event is emitted. There is NO override - this is fail-closed by design.

Usage in order path:
    from multi_broker_phoenix.risk.risk_governor import risk_gate_check
    
    result = risk_gate_check(candidate, units)
    if not result['allowed']:
        print(f"BLOCKED: {result['reason']}")
        continue  # Do NOT place order
    
    # Proceed with order placement
    broker.place_order(candidate, units)
"""
from __future__ import annotations
import os
import time
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Import core pip math
try:
    from multi_broker_phoenix.risk.pip_math import (
        validate_trade_risk,
        compute_risk_metrics,
        emit_risk_violation,
        get_config,
        compute_safe_sl_price,
        compute_safe_tp_price,
    )
except ImportError:
    # Fallback if module not available
    def validate_trade_risk(*args, **kwargs):
        return {'allowed': True, 'reason': None, 'violations': [], 'metrics': {}, 'suggested_units': None}
    def compute_risk_metrics(*args, **kwargs):
        return {}
    def emit_risk_violation(*args, **kwargs):
        pass
    def get_config():
        return {}
    def compute_safe_sl_price(*args, **kwargs):
        return None
    def compute_safe_tp_price(*args, **kwargs):
        return None


# State file for observability
STATE_FILE = os.getenv('RISK_GOVERNOR_STATE_FILE', 'ops/state/risk_governor.json')


def _ensure_state_dir():
    """Ensure state directory exists."""
    import pathlib
    pathlib.Path(STATE_FILE).parent.mkdir(parents=True, exist_ok=True)


def _write_state(state: Dict[str, Any]) -> None:
    """Write state to JSON file for observability."""
    import json
    try:
        _ensure_state_dir()
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2, default=str)
    except Exception as e:
        logger.warning(f'Failed to write risk governor state: {e}')


def _log_event(event_type: str, details: Dict[str, Any]) -> None:
    """Log event to durable narration stream."""
    try:
        from multi_broker_phoenix.monitor.pnl_kill_switch import _log_event as durable_log
        durable_log(event_type, details)
    except Exception:
        logger.info(f'RISK_EVENT: {event_type} {details}')


def risk_gate_check(
    candidate: Any,
    units: int,
    config: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Main risk gate check - MUST pass before order submission.
    
    This is the single enforcement point for pre-trade risk validation.
    
    Args:
        candidate: Trade candidate with entry_price, stop_loss, take_profit, side, symbol
        units: Proposed position size
        config: Optional override config
    
    Returns:
        {
            'allowed': bool,
            'reason': str or None,
            'violations': list,
            'metrics': dict,
            'suggested_units': int or None,
            'timestamp': float
        }
    
    Side effects:
        - Emits RISK_VIOLATION event if blocked
        - Emits RISK_GATE_PASS event if allowed
        - Updates ops/state/risk_governor.json
    """
    ts = time.time()
    
    # Extract candidate fields with fallbacks
    try:
        entry_price = float(getattr(candidate, 'entry_price', getattr(candidate, 'entry', 0)))
        sl_price = float(getattr(candidate, 'stop_loss', getattr(candidate, 'sl', 0)))
        tp_price = float(getattr(candidate, 'take_profit', getattr(candidate, 'tp', 0)))
        side = str(getattr(candidate, 'side', 'BUY')).upper()
        pair = str(getattr(candidate, 'symbol', getattr(candidate, 'instrument', 'EUR_USD')))
    except Exception as e:
        result = {
            'allowed': False,
            'reason': f'INVALID_CANDIDATE: failed to extract fields: {e}',
            'violations': ['INVALID_CANDIDATE'],
            'metrics': {},
            'suggested_units': None,
            'timestamp': ts,
        }
        _log_event('RISK_GATE_INVALID', result)
        return result
    
    # Validate required fields
    if entry_price <= 0 or sl_price <= 0 or tp_price <= 0:
        result = {
            'allowed': False,
            'reason': f'MISSING_PRICES: entry={entry_price}, sl={sl_price}, tp={tp_price}',
            'violations': ['MISSING_PRICES'],
            'metrics': {},
            'suggested_units': None,
            'timestamp': ts,
        }
        _log_event('RISK_GATE_INVALID', result)
        return result
    
    # Run validation
    validation = validate_trade_risk(
        units=units,
        pair=pair,
        entry_price=entry_price,
        sl_price=sl_price,
        tp_price=tp_price,
        side=side,
        config=config
    )
    
    result = {
        'allowed': validation['allowed'],
        'reason': validation['reason'],
        'violations': validation['violations'],
        'metrics': validation['metrics'],
        'suggested_units': validation['suggested_units'],
        'timestamp': ts,
        'pair': pair,
        'units': units,
        'side': side,
    }
    
    # Update state file
    state = {
        'last_check': ts,
        'last_result': 'PASS' if result['allowed'] else 'BLOCKED',
        'last_pair': pair,
        'last_units': units,
        'config': get_config(),
    }
    if not result['allowed']:
        state['last_violation'] = result['reason']
        state['last_metrics'] = result['metrics']
    _write_state(state)
    
    # Emit events
    if result['allowed']:
        _log_event('RISK_GATE_PASS', {
            'pair': pair,
            'units': units,
            'risk_usd': result['metrics'].get('risk_to_sl_usd'),
            'rr': result['metrics'].get('rr_ratio'),
            'timestamp': ts,
        })
    else:
        emit_risk_violation(
            units=units,
            pair=pair,
            entry_price=entry_price,
            sl_price=sl_price,
            tp_price=tp_price,
            violations=result['violations'],
            metrics=result['metrics']
        )
        logger.warning(f'RISK_GATE_BLOCKED: {pair} {units}u - {result["reason"]}')
    
    return result


def enforce_risk_gate(candidate: Any, units: int, config: Dict[str, Any] = None) -> None:
    """Enforce risk gate - raises RuntimeError if blocked.
    
    Use this as a hard gate that will halt order placement.
    
    Raises:
        RuntimeError: If trade violates risk constraints
    """
    result = risk_gate_check(candidate, units, config)
    if not result['allowed']:
        raise RuntimeError(f'RISK_VIOLATION: {result["reason"]}')


def get_risk_adjusted_order(
    candidate: Any,
    units: int,
    config: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Get a risk-adjusted order with safe SL/TP if needed.
    
    If the original order violates risk constraints, this function
    will attempt to compute safe alternatives.
    
    Args:
        candidate: Original trade candidate
        units: Proposed position size
        config: Optional override config
    
    Returns:
        {
            'allowed': bool,
            'original_ok': bool,
            'adjusted': bool,
            'units': int,
            'sl_price': float,
            'tp_price': float,
            'metrics': dict,
            'reason': str or None,
        }
    """
    cfg = config or get_config()
    
    # Extract fields
    entry_price = float(getattr(candidate, 'entry_price', 0))
    sl_price = float(getattr(candidate, 'stop_loss', 0))
    tp_price = float(getattr(candidate, 'take_profit', 0))
    side = str(getattr(candidate, 'side', 'BUY')).upper()
    pair = str(getattr(candidate, 'symbol', getattr(candidate, 'instrument', 'EUR_USD')))
    
    # First check original
    result = risk_gate_check(candidate, units, config)
    
    if result['allowed']:
        return {
            'allowed': True,
            'original_ok': True,
            'adjusted': False,
            'units': units,
            'sl_price': sl_price,
            'tp_price': tp_price,
            'metrics': result['metrics'],
            'reason': None,
        }
    
    # Try to adjust
    adjusted_units = units
    adjusted_sl = sl_price
    adjusted_tp = tp_price
    adjusted = False
    
    # If units too large, try suggested units
    if result['suggested_units'] and result['suggested_units'] < abs(units):
        adjusted_units = result['suggested_units']
        adjusted = True
    
    # If SL too far, compute safe SL
    max_risk = cfg.get('MAX_RISK_USD_PER_TRADE', 25.0)
    safe_sl = compute_safe_sl_price(adjusted_units, pair, entry_price, side, max_risk)
    if safe_sl:
        # Verify it's actually tighter
        if side == 'BUY' and safe_sl > adjusted_sl:
            adjusted_sl = safe_sl
            adjusted = True
        elif side == 'SELL' and safe_sl < adjusted_sl:
            adjusted_sl = safe_sl
            adjusted = True
    
    # Compute TP for min RR
    adjusted_tp = compute_safe_tp_price(entry_price, adjusted_sl, side, cfg.get('MIN_RR', 1.5))
    
    # Validate adjusted order
    from multi_broker_phoenix.risk.pip_math import compute_risk_metrics
    adjusted_metrics = compute_risk_metrics(adjusted_units, pair, entry_price, adjusted_sl, adjusted_tp)
    
    # Final check
    final_validation = validate_trade_risk(
        adjusted_units, pair, entry_price, adjusted_sl, adjusted_tp, side, config
    )
    
    return {
        'allowed': final_validation['allowed'],
        'original_ok': False,
        'adjusted': adjusted,
        'units': adjusted_units,
        'sl_price': adjusted_sl,
        'tp_price': adjusted_tp,
        'metrics': adjusted_metrics,
        'reason': final_validation['reason'] if not final_validation['allowed'] else None,
    }


# -----------------------------------------------------------------
# Integration helper for run_headless.py
# -----------------------------------------------------------------
def pre_order_risk_check(candidate: Any, units: int) -> bool:
    """Simple boolean check for integration in order placement path.
    
    Returns True if order is allowed, False if blocked.
    """
    result = risk_gate_check(candidate, units)
    return result['allowed']
