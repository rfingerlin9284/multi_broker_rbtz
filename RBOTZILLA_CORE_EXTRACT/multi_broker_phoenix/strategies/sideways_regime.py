"""Sideways regime strategy: small-range scalping logic (alias for `institutional_sd`)."""
from __future__ import annotations
from ..strategies.base import register_strategy, Strategy
from typing import Optional, Dict, Any
from ..risk.trade_risk_gate import TradeCandidate

@register_strategy('sideways_regime')
class SidewaysRegime(Strategy):
    def generate_candidate(self, market_data: Dict[str, Any]) -> Optional[TradeCandidate]:
        strat = self.get('institutional_sd')
        if not strat:
            return None
        return strat.generate_candidate(market_data)
