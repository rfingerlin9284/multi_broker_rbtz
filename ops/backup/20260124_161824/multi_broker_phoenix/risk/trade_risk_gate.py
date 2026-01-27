from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Optional, Dict
from .risk_manager import RiskManager

@dataclass
class TradeCandidate:
    strategy_id: str
    symbol: str
    platform: str
    entry_price: float
    stop_loss: float
    side: Optional[str] = None
    take_profit: Optional[float] = None

@dataclass
class TradeDecision:
    allowed: bool
    reason: str
    risk_pct: float = 0.0
    size: float = 0.0

def _lookup_regime_multiplier(trend: str, vol: str, cfg: Dict) -> float:
    """Lookup risk multiplier for regime - default to 1.0 (ALWAYS ALLOW TRADES)"""
    try:
        mult = cfg.get('regime_risk_multipliers', {}).get(trend, {}).get(vol, None)
        if mult is None:
            return 1.0  # DEFAULT: Allow trades when regime config missing
        return float(mult)
    except Exception:
        return 1.0  # DEFAULT: Allow trades on any error

def can_open_trade(candidate: TradeCandidate, account_equity: float, rm: Optional[RiskManager] = None) -> TradeDecision:
    rm = rm or RiskManager()
    st = rm.state
    cfg = rm.config
    pol = st.policy
    if not rm.is_trading_allowed():
        return TradeDecision(False, 'risk_halt_or_brake')
    open_trades_on_platform = st.open_trades_by_platform.get(candidate.platform, 0)
    max_per_platform = pol.max_trades_per_platform if pol else int(cfg.get('platform_limits', {}).get(candidate.platform, {}).get('max_open_trades', 3))
    if open_trades_on_platform >= max_per_platform:
        return TradeDecision(False, 'platform_trade_cap')

    # OCO + TP sanity gate (must have SL + TP, RR within bounds, TP distance capped)
    try:
        entry = float(getattr(candidate, 'entry_price', 0.0) or 0.0)
        sl = float(getattr(candidate, 'stop_loss', 0.0) or 0.0)
        tp = float(getattr(candidate, 'take_profit', 0.0) or 0.0)
    except Exception:
        entry = 0.0
        sl = 0.0
        tp = 0.0

    if entry <= 0 or sl <= 0 or tp <= 0:
        return TradeDecision(False, 'missing_oco')

    try:
        from multi_broker_phoenix.risk.pip_math import calculate_rr_ratio, tp_distance_pips
        rr = calculate_rr_ratio(entry, sl, tp)
        min_rr = float(os.getenv('OCO_MIN_RR', '1.0'))
        max_rr = float(os.getenv('OCO_MAX_RR', '5.0'))
        if rr < min_rr or rr > max_rr:
            return TradeDecision(False, 'rr_out_of_bounds')

        instrument = getattr(candidate, 'symbol', None) or getattr(candidate, 'instrument', None) or ''
        tp_pips = tp_distance_pips(entry, tp, instrument)
        max_tp_pips = float(os.getenv('OCO_MAX_TP_PIPS', '300'))
        if tp_pips > max_tp_pips:
            return TradeDecision(False, 'tp_distance_out_of_bounds')
    except Exception:
        # If pip math fails, fail closed to enforce OCO sanity
        return TradeDecision(False, 'oco_validation_error')
    
    # Regime check - optional, default to TREND/NORMAL if not set
    regimes = st.regime_by_symbol.get(candidate.symbol)
    if not regimes:
        # Auto-assign default regime instead of blocking
        regimes = {'trend': 'TREND', 'vol': 'NORMAL'}
    
    trend = regimes.get('trend') or 'TREND'
    vol = regimes.get('vol') or 'NORMAL'
    mult = _lookup_regime_multiplier(trend, vol, cfg)
    if mult <= 0.0:
        return TradeDecision(False, 'regime_disabled')
    base_risk = float(getattr(pol, 'base_risk_per_trade_pct', cfg.get('default_risk_per_trade_pct', 0.0075)))
    risk_pct = base_risk * mult
    cap = float(getattr(pol, 'max_open_risk_pct', cfg.get('max_total_open_risk_pct', 0.05)))
    if st.open_risk_pct + risk_pct > cap:
        return TradeDecision(False, 'open_risk_cap')
    if st.triage_mode:
        allowed = set(cfg.get('triage_allowed_strategies', ['institutional_sd','ema_scalper','trap_reversal','holy_grail']))
        if candidate.strategy_id not in allowed:
            return TradeDecision(False, 'triage_blocked')
    # query risk manager for size, accounting for fees/slippage
    sizing = rm.size_for_trade(candidate, account_equity)
    if not sizing.get('allowed'):
        return TradeDecision(False, str(sizing.get('reason', 'sizing_rejected')))
    size = sizing.get('size', 0.0)
    return TradeDecision(True, 'OK', risk_pct=sizing.get('risk_pct', risk_pct), size=size)
