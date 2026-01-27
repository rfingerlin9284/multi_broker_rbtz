"""Simple strategy implementations: bearish_regime (alias for `trap_reversal`)"""
from __future__ import annotations
from ..strategies.base import register_strategy, Strategy
from typing import Optional, Dict, Any
from ..risk.trade_risk_gate import TradeCandidate

@register_strategy('bearish_regime')
class BearishRegime(Strategy):
    """Alias that delegates to a mean-reversion/trap strategy for symmetry."""
    def generate_candidate(self, market_data: Dict[str, Any]) -> Optional[TradeCandidate]:
        strat = self.get('trap_reversal')
        if not strat:
            return None
        return strat.generate_candidate(market_data)
