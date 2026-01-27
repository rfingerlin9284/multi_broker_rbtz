from __future__ import annotations
import os
from typing import Optional, Dict, Any
from .risk_manager import RiskManager
from .platform_breaker import is_platform_enabled

_risk_manager = RiskManager()

def set_risk_manager(rm: RiskManager):
    global _risk_manager
    _risk_manager = rm

def can_place_order(
    proposed_risk_pct: Optional[float] = None,
    open_trades_count: int = 0,
    total_open_risk_pct: float = 0.0,
    strategy_name: Optional[str] = None,
    pack_name: Optional[str] = None,
    platform: Optional[str] = None,
) -> bool:
    if os.getenv('EXECUTION_ENABLED', '1').lower() in ('0','false','no'):
        return False
    if platform and not is_platform_enabled(platform):
        return False
    if not _risk_manager.is_trading_allowed():
        return False
    proposed = float(proposed_risk_pct) if proposed_risk_pct is not None else float(_risk_manager.config.get('default_risk_per_trade_pct', 0.0075))
    res = _risk_manager.can_place_trade(proposed, open_trades_count, total_open_risk_pct)
    if not res.get('allowed', False):
        return False
    if getattr(_risk_manager.state, 'triage_mode', False):
        if not (strategy_name and pack_name):
            return False
    return True

def get_execution_summary() -> Dict[str, Any]:
    s = _risk_manager.state
    return {
        'execution_enabled': os.getenv('EXECUTION_ENABLED', '1'),
        'equity_now': s.equity_now,
        'equity_peak': s.equity_peak,
        'current_drawdown': s.current_drawdown,
        'daily_pnl_pct': s.daily_pnl_pct,
        'weekly_pnl_pct': s.weekly_pnl_pct,
        'open_risk_pct': s.open_risk_pct,
        'triage_mode': bool(s.triage_mode),
        'halted': bool(s.halted),
        'reduced_risk_scale': s.reduced_risk_scale,
        'policy': getattr(s.policy, 'name', None),
    }
