# Risk management package for RBOTzilla
"""
Risk management modules:
- pip_math: Deterministic pip→$ conversion for FX
- risk_governor: Pre-trade risk validation gate
"""
from multi_broker_phoenix.risk.pip_math import (
    pip_size,
    pip_value_usd,
    sl_distance_pips,
    tp_distance_pips,
    risk_to_sl_usd,
    reward_to_tp_usd,
    calculate_rr_ratio,
    compute_risk_metrics,
    validate_trade_risk,
    get_config,
)

from multi_broker_phoenix.risk.risk_governor import (
    risk_gate_check,
    enforce_risk_gate,
    pre_order_risk_check,
    get_risk_adjusted_order,
)

__all__ = [
    'pip_size',
    'pip_value_usd',
    'sl_distance_pips',
    'tp_distance_pips',
    'risk_to_sl_usd',
    'reward_to_tp_usd',
    'calculate_rr_ratio',
    'compute_risk_metrics',
    'validate_trade_risk',
    'get_config',
    'risk_gate_check',
    'enforce_risk_gate',
    'pre_order_risk_check',
    'get_risk_adjusted_order',
]
