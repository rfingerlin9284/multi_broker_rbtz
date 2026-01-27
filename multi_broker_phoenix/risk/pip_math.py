"""Deterministic pip→$ risk math for FX trading.

This module provides precise pip value calculation to ensure:
1. Pre-trade risk (units × SL distance) is known in USD before submission
2. Post-trade reconciliation validates OCO risk matches budget
3. No "$300 surprise" drawdowns from misunderstood position sizing

Key formulas:
- pip_size(pair): 0.0001 for most FX, 0.01 for JPY pairs
- pip_value_usd(units, pair): $ gained/lost per pip movement
- risk_to_sl_usd(units, pair, entry, sl): total $ risk at SL hit

Example:
  >>> pip_value_usd(106765, 'EUR_USD', 1.1200)
  10.6765  # Each pip costs ~$10.68
  >>> risk_to_sl_usd(106765, 'EUR_USD', 1.1200, 1.1170)  # 30 pip SL
  320.295  # ~$320 risk at SL
"""
from __future__ import annotations
import os
import logging
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------
# Configuration (can override via env or config.json)
# -----------------------------------------------------------------
DEFAULT_CONFIG = {
    'MAX_RISK_USD_PER_TRADE': float(os.getenv('MAX_RISK_USD_PER_TRADE', '25.0')),
    'MIN_RR': float(os.getenv('MIN_RR', '1.5')),
    'MAX_UNITS_PER_PAIR': int(os.getenv('MAX_UNITS_PER_PAIR', '100000')),
    'MAX_SL_PIPS': float(os.getenv('MAX_SL_PIPS', '50.0')),
    'EMERGENCY_FLATTEN_USD': float(os.getenv('EMERGENCY_FLATTEN_USD', '100.0')),
    'ACCOUNT_CCY': os.getenv('ACCOUNT_CCY', 'USD'),
}


def get_config() -> Dict[str, Any]:
    """Return current risk configuration (from env or defaults)."""
    return {
        'MAX_RISK_USD_PER_TRADE': float(os.getenv('MAX_RISK_USD_PER_TRADE', DEFAULT_CONFIG['MAX_RISK_USD_PER_TRADE'])),
        'MIN_RR': float(os.getenv('MIN_RR', DEFAULT_CONFIG['MIN_RR'])),
        'MAX_UNITS_PER_PAIR': int(os.getenv('MAX_UNITS_PER_PAIR', DEFAULT_CONFIG['MAX_UNITS_PER_PAIR'])),
        'MAX_SL_PIPS': float(os.getenv('MAX_SL_PIPS', DEFAULT_CONFIG['MAX_SL_PIPS'])),
        'EMERGENCY_FLATTEN_USD': float(os.getenv('EMERGENCY_FLATTEN_USD', DEFAULT_CONFIG['EMERGENCY_FLATTEN_USD'])),
        'ACCOUNT_CCY': os.getenv('ACCOUNT_CCY', DEFAULT_CONFIG['ACCOUNT_CCY']),
    }


# -----------------------------------------------------------------
# Core pip math functions
# -----------------------------------------------------------------
def pip_size(pair: str) -> float:
    """Return the pip size for a currency pair.
    
    - JPY pairs: pip = 0.01
    - All others: pip = 0.0001
    
    Args:
        pair: Currency pair (e.g., 'EUR_USD', 'USD_JPY', 'EUR/USD')
    
    Returns:
        Pip size as float (0.0001 or 0.01)
    """
    pair_upper = pair.upper().replace('-', '_').replace('/', '_')
    if pair_upper.endswith('JPY') or '_JPY' in pair_upper:
        return 0.01
    return 0.0001


def pip_value_usd(units: int, pair: str, price: float = 1.0, account_ccy: str = 'USD') -> float:
    """Calculate the USD value of one pip for a given position size.
    
    For USD-quoted pairs (EUR_USD, GBP_USD, AUD_USD, etc.):
        pip_value = units × pip_size
    
    For USD-base pairs (USD_JPY, USD_CAD, USD_CHF):
        pip_value = (units × pip_size) / price
    
    For cross pairs (EUR_GBP, etc.):
        Requires quote-to-USD conversion (conservative fallback if unavailable)
    
    Args:
        units: Position size in base currency units (can be negative for shorts)
        pair: Currency pair (e.g., 'EUR_USD')
        price: Current market price (used for non-USD-quoted pairs)
        account_ccy: Account currency (default 'USD')
    
    Returns:
        Pip value in USD (always positive)
    
    Example:
        >>> pip_value_usd(106765, 'EUR_USD', 1.1200)
        10.6765
    """
    pair_upper = pair.upper().replace('-', '_').replace('/', '_')
    pip = pip_size(pair_upper)
    abs_units = abs(int(units))
    
    # Extract base and quote currencies
    parts = pair_upper.split('_')
    if len(parts) != 2:
        # Fallback: assume USD-quoted
        logger.warning(f"pip_value_usd: could not parse pair '{pair}', using conservative estimate")
        return abs_units * pip
    
    base_ccy, quote_ccy = parts
    
    if quote_ccy == 'USD':
        # USD-quoted (EUR_USD, GBP_USD, AUD_USD, etc.)
        # pip_value = units × pip_size (direct)
        return abs_units * pip
    
    if base_ccy == 'USD':
        # USD-base pairs (USD_JPY, USD_CAD, USD_CHF)
        # pip_value = (units × pip_size) / price
        if price <= 0:
            logger.warning(f"pip_value_usd: invalid price {price} for {pair}, using 1.0")
            price = 1.0
        return (abs_units * pip) / price
    
    # Cross pairs (EUR_GBP, etc.) - need quote-to-USD conversion
    # For now, use conservative fallback: assume 1:1 quote-to-USD
    # In production, fetch {quote_ccy}_USD or USD_{quote_ccy} rate
    logger.warning(f"pip_value_usd: cross pair '{pair}' uses 1:1 USD conversion (conservative)")
    return abs_units * pip


def sl_distance_pips(entry_price: float, sl_price: float, pair: str) -> float:
    """Calculate stop-loss distance in pips.
    
    Args:
        entry_price: Entry price
        sl_price: Stop-loss price
        pair: Currency pair
    
    Returns:
        Distance in pips (always positive)
    """
    pip = pip_size(pair)
    return abs(entry_price - sl_price) / pip


def tp_distance_pips(entry_price: float, tp_price: float, pair: str) -> float:
    """Calculate take-profit distance in pips.
    
    Args:
        entry_price: Entry price
        tp_price: Take-profit price
        pair: Currency pair
    
    Returns:
        Distance in pips (always positive)
    """
    pip = pip_size(pair)
    return abs(tp_price - entry_price) / pip


def risk_to_sl_usd(units: int, pair: str, entry_price: float, sl_price: float, current_price: float = None) -> float:
    """Calculate the USD risk (loss) if stop-loss is hit.
    
    Formula: sl_distance_pips × pip_value_usd
    
    Args:
        units: Position size
        pair: Currency pair
        entry_price: Entry price
        sl_price: Stop-loss price
        current_price: Current market price (for pip value calculation)
    
    Returns:
        USD loss at stop-loss (always positive)
    
    Example:
        >>> risk_to_sl_usd(106765, 'EUR_USD', 1.1200, 1.1170)  # 30 pip SL
        320.295
    """
    price = current_price if current_price else entry_price
    pips = sl_distance_pips(entry_price, sl_price, pair)
    pv = pip_value_usd(units, pair, price)
    return pips * pv


def reward_to_tp_usd(units: int, pair: str, entry_price: float, tp_price: float, current_price: float = None) -> float:
    """Calculate the USD reward if take-profit is hit.
    
    Args:
        units: Position size
        pair: Currency pair
        entry_price: Entry price
        tp_price: Take-profit price
        current_price: Current market price (for pip value calculation)
    
    Returns:
        USD gain at take-profit (always positive)
    """
    price = current_price if current_price else entry_price
    pips = tp_distance_pips(entry_price, tp_price, pair)
    pv = pip_value_usd(units, pair, price)
    return pips * pv


def calculate_rr_ratio(entry_price: float, sl_price: float, tp_price: float) -> float:
    """Calculate risk-reward ratio.
    
    RR = (TP distance) / (SL distance)
    
    Returns:
        Risk-reward ratio (e.g., 2.0 means 2:1 reward:risk)
    """
    sl_dist = abs(entry_price - sl_price)
    tp_dist = abs(tp_price - entry_price)
    if sl_dist <= 0:
        return 0.0
    return tp_dist / sl_dist


def compute_risk_metrics(units: int, pair: str, entry_price: float, sl_price: float, tp_price: float) -> Dict[str, Any]:
    """Compute comprehensive risk metrics for a trade.
    
    Returns dict with:
        - units: Position size
        - pair: Currency pair
        - pip_size: Pip size for pair
        - pip_value_usd: USD per pip
        - sl_distance_pips: SL distance in pips
        - tp_distance_pips: TP distance in pips
        - risk_to_sl_usd: USD at risk
        - reward_to_tp_usd: USD reward potential
        - rr_ratio: Risk-reward ratio
    """
    return {
        'units': units,
        'pair': pair,
        'pip_size': pip_size(pair),
        'pip_value_usd': pip_value_usd(units, pair, entry_price),
        'sl_distance_pips': sl_distance_pips(entry_price, sl_price, pair),
        'tp_distance_pips': tp_distance_pips(entry_price, tp_price, pair),
        'risk_to_sl_usd': risk_to_sl_usd(units, pair, entry_price, sl_price),
        'reward_to_tp_usd': reward_to_tp_usd(units, pair, entry_price, tp_price),
        'rr_ratio': calculate_rr_ratio(entry_price, sl_price, tp_price),
    }


# -----------------------------------------------------------------
# Pre-trade Risk Governor (hard veto before order submission)
# -----------------------------------------------------------------
def validate_trade_risk(
    units: int,
    pair: str,
    entry_price: float,
    sl_price: float,
    tp_price: float,
    side: str = 'BUY',
    config: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Validate a trade against risk constraints before submission.
    
    Enforces:
        - MAX_RISK_USD_PER_TRADE: Max USD at risk when SL hit
        - MIN_RR: Minimum risk-reward ratio
        - MAX_UNITS_PER_PAIR: Position size cap
        - MAX_SL_PIPS: Optional SL distance cap
    
    Args:
        units: Proposed position size
        pair: Currency pair
        entry_price: Intended entry price
        sl_price: Stop-loss price
        tp_price: Take-profit price
        side: 'BUY' or 'SELL'
        config: Override config dict (defaults to get_config())
    
    Returns:
        {
            'allowed': bool,
            'reason': str or None,
            'violations': list[str],
            'metrics': dict,  # from compute_risk_metrics
            'suggested_units': int or None  # if capped
        }
    """
    cfg = config or get_config()
    violations = []
    
    # Validate SL/TP direction
    side_upper = side.upper()
    if side_upper == 'BUY':
        if sl_price >= entry_price:
            violations.append(f'SL_ABOVE_ENTRY: BUY trade SL ({sl_price}) must be below entry ({entry_price})')
        if tp_price <= entry_price:
            violations.append(f'TP_BELOW_ENTRY: BUY trade TP ({tp_price}) must be above entry ({entry_price})')
    elif side_upper == 'SELL':
        if sl_price <= entry_price:
            violations.append(f'SL_BELOW_ENTRY: SELL trade SL ({sl_price}) must be above entry ({entry_price})')
        if tp_price >= entry_price:
            violations.append(f'TP_ABOVE_ENTRY: SELL trade TP ({tp_price}) must be below entry ({entry_price})')
    
    # Calculate metrics
    metrics = compute_risk_metrics(units, pair, entry_price, sl_price, tp_price)
    
    # Check MAX_UNITS_PER_PAIR
    max_units = cfg.get('MAX_UNITS_PER_PAIR', 100000)
    if abs(units) > max_units:
        violations.append(f'UNITS_EXCEED_MAX: {abs(units)} > {max_units}')
    
    # Check MAX_RISK_USD_PER_TRADE
    max_risk = cfg.get('MAX_RISK_USD_PER_TRADE', 25.0)
    if metrics['risk_to_sl_usd'] > max_risk:
        violations.append(f'RISK_EXCEED_MAX: ${metrics["risk_to_sl_usd"]:.2f} > ${max_risk:.2f}')
    
    # Check MIN_RR
    min_rr = cfg.get('MIN_RR', 1.5)
    if metrics['rr_ratio'] + 1e-9 < min_rr:
        violations.append(f'RR_BELOW_MIN: {metrics["rr_ratio"]:.2f} < {min_rr}')
    
    # Check MAX_SL_PIPS (optional)
    max_sl_pips = cfg.get('MAX_SL_PIPS')
    if max_sl_pips and metrics['sl_distance_pips'] > max_sl_pips:
        violations.append(f'SL_PIPS_EXCEED_MAX: {metrics["sl_distance_pips"]:.1f} > {max_sl_pips}')
    
    # Calculate suggested units if risk too high
    suggested_units = None
    if metrics['risk_to_sl_usd'] > max_risk:
        # Back-calculate: max_risk = pips × (units × pip_size) / price_factor
        pips = metrics['sl_distance_pips']
        pip = pip_size(pair)
        # Simplified: assume USD-quoted; for others, more complex
        if pips > 0:
            suggested_units = int(max_risk / (pips * pip))
    
    allowed = len(violations) == 0
    
    return {
        'allowed': allowed,
        'reason': '; '.join(violations) if violations else None,
        'violations': violations,
        'metrics': metrics,
        'suggested_units': suggested_units,
    }


def compute_safe_sl_price(units: int, pair: str, entry_price: float, side: str, max_risk_usd: float = None) -> float:
    """Calculate the closest SL price that respects max risk budget.
    
    Args:
        units: Position size
        pair: Currency pair
        entry_price: Entry price
        side: 'BUY' or 'SELL'
        max_risk_usd: Maximum risk in USD (defaults to config)
    
    Returns:
        Safe SL price
    """
    cfg = get_config()
    max_risk = max_risk_usd or cfg.get('MAX_RISK_USD_PER_TRADE', 25.0)
    
    pv = pip_value_usd(units, pair, entry_price)
    if pv <= 0:
        pv = 0.0001  # Fallback to prevent division by zero
    
    max_pips = max_risk / pv
    pip = pip_size(pair)
    max_distance = max_pips * pip
    
    side_upper = side.upper()
    if side_upper == 'BUY':
        return entry_price - max_distance
    else:
        return entry_price + max_distance


def compute_safe_tp_price(entry_price: float, sl_price: float, side: str, min_rr: float = None) -> float:
    """Calculate TP price that meets minimum RR ratio.
    
    Args:
        entry_price: Entry price
        sl_price: Stop-loss price
        side: 'BUY' or 'SELL'
        min_rr: Minimum RR ratio (defaults to config)
    
    Returns:
        TP price meeting min RR
    """
    cfg = get_config()
    rr = min_rr or cfg.get('MIN_RR', 1.5)
    
    sl_dist = abs(entry_price - sl_price)
    tp_dist = sl_dist * rr
    
    side_upper = side.upper()
    if side_upper == 'BUY':
        return entry_price + tp_dist
    else:
        return entry_price - tp_dist


# -----------------------------------------------------------------
# Event logging helpers
# -----------------------------------------------------------------
def _log_risk_event(event_type: str, details: Dict[str, Any]) -> None:
    """Log a risk event to the durable narration stream."""
    import time
    try:
        from multi_broker_phoenix.monitor.pnl_kill_switch import _log_event
        _log_event(event_type, details)
    except Exception:
        logger.info(f'RISK_EVENT: {event_type} {details}')


def emit_risk_violation(
    units: int,
    pair: str,
    entry_price: float,
    sl_price: float,
    tp_price: float,
    violations: list,
    metrics: Dict[str, Any]
) -> None:
    """Emit RISK_VIOLATION event for audit trail."""
    _log_risk_event('RISK_VIOLATION', {
        'timestamp': time.time(),
        'pair': pair,
        'units': units,
        'entry': entry_price,
        'sl': sl_price,
        'tp': tp_price,
        'violations': violations,
        'risk_to_sl_usd': metrics.get('risk_to_sl_usd'),
        'rr_ratio': metrics.get('rr_ratio'),
        'pip_value_usd': metrics.get('pip_value_usd'),
    })


import time  # Ensure time is available for emit functions


# -----------------------------------------------------------------
# Quick test / acceptance check
# -----------------------------------------------------------------
if __name__ == '__main__':
    # Acceptance test: Given units=106,765 on EUR_USD, pip value prints ~10.67 USD/pip
    # and 30 pips ≈ ~$320
    
    print("=== Pip Math Acceptance Test ===\n")
    
    units = 106765
    pair = 'EUR_USD'
    entry = 1.1200
    sl = 1.1170  # 30 pips
    tp = 1.1260  # 60 pips (2:1 RR)
    
    pv = pip_value_usd(units, pair, entry)
    print(f"Units: {units:,}")
    print(f"Pair: {pair}")
    print(f"Pip Value: ${pv:.2f}/pip")
    
    risk = risk_to_sl_usd(units, pair, entry, sl)
    print(f"SL Distance: {sl_distance_pips(entry, sl, pair):.0f} pips")
    print(f"Risk to SL: ${risk:.2f}")
    
    reward = reward_to_tp_usd(units, pair, entry, tp)
    rr = calculate_rr_ratio(entry, sl, tp)
    print(f"TP Distance: {tp_distance_pips(entry, tp, pair):.0f} pips")
    print(f"Reward to TP: ${reward:.2f}")
    print(f"RR Ratio: {rr:.2f}")
    
    print("\n=== Risk Validation ===\n")
    
    validation = validate_trade_risk(units, pair, entry, sl, tp, 'BUY')
    print(f"Allowed: {validation['allowed']}")
    if validation['violations']:
        print(f"Violations: {validation['violations']}")
    print(f"Suggested Units: {validation['suggested_units']}")
    
    # Test with conservative config
    print("\n=== With $20 max risk ===\n")
    validation2 = validate_trade_risk(units, pair, entry, sl, tp, 'BUY', {'MAX_RISK_USD_PER_TRADE': 20.0, 'MIN_RR': 1.5, 'MAX_UNITS_PER_PAIR': 100000})
    print(f"Allowed: {validation2['allowed']}")
    if validation2['violations']:
        print(f"Violations: {validation2['violations']}")
    print(f"Suggested Units (for $20 risk): {validation2['suggested_units']}")
