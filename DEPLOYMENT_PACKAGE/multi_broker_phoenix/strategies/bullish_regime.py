"""Simple strategy implementations: bullish_regime (alias for `holy_grail`)"""
from __future__ import annotations
from ..strategies.base import register_strategy, Strategy, list_strategies
import logging

logger = logging.getLogger(__name__)
from typing import Optional, Dict, Any
from ..risk.trade_risk_gate import TradeCandidate

@register_strategy('bullish_regime')
class BullishRegime(Strategy):
    """Alias strategy that delegates to the `holy_grail` behavior (for symmetry).

    Expected market_data: { 'symbol': str, 'platform': str, 'prices': List[float] }
    Returns a TradeCandidate on clear momentum signals, otherwise None.
    """
    def generate_candidate(self, market_data: Dict[str, Any]) -> Optional[TradeCandidate]:
        # Reuse the holy_grail implementation via its id
        strat = self.get('holy_grail')
        if not strat:
            return None
        # Defensive: avoid recursive self-reference in registry
        if strat is self:
            return None
        try:
            return strat.generate_candidate(market_data)
        except Exception as exc:
            # If delegate fails for any reason, be conservative and return None
            # Log exception with contextual info to ease troubleshooting
            logger.exception("BullishRegime delegate 'holy_grail' failed for symbol=%s platform=%s: %s",
                             market_data.get('symbol'), market_data.get('platform'), exc)
            # helpful debug: list other registered strategies
            logger.debug("Registered strategies: %s", list_strategies())
            return None
