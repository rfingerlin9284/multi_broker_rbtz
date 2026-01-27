from __future__ import annotations
from typing import Dict, Any, Optional
import numpy as np
from .base import register_strategy, Strategy, _ema
from ..risk.trade_risk_gate import TradeCandidate


@register_strategy('full_indicator_scan')
class FullIndicatorScan(Strategy):
    """Full Indicator Scan strategy (toggle-gated).

    Conservative: returns None unless confluence threshold met and uses numpy-only
    implementations so no extra deps are required.
    """
    def __init__(self):
        import os
        # default stop (small) if needed for candidate creation
        self.stop_loss_pct = float(os.getenv('FULL_SCAN_STOP_PCT', '0.02'))
        self.required_confluence = int(os.getenv('FULL_INDICATOR_REQUIRED_CONFLUENCE', '6'))

    def _calc_simple_indicators(self, prices: list[float]) -> Dict[str, float]:
        c = np.asarray(prices, dtype=float)
        out: Dict[str, float] = {}
        if len(c) >= 14:
            # RSI naive
            delta = np.diff(c)
            gain = np.where(delta > 0, delta, 0.0)
            loss = np.where(delta < 0, -delta, 0.0)
            avg_gain = np.mean(gain[-14:]) if len(gain) >= 14 else np.mean(gain) if gain.size else 0.0
            avg_loss = np.mean(loss[-14:]) if len(loss) >= 14 else np.mean(loss) if loss.size else 1e-9
            out['RSI_14'] = float(100.0 - (100.0 / (1.0 + (avg_gain / (avg_loss or 1e-9)))))
        if len(c) >= 26:
            out['EMA_12'] = float(_ema(list(c), 12) or 0.0)
            out['EMA_26'] = float(_ema(list(c), 26) or 0.0)
            out['MACD_LINE'] = out['EMA_12'] - out['EMA_26']
        if len(c) >= 20:
            mid = float(np.mean(c[-20:]))
            std = float(np.std(c[-20:]))
            out['BB_UPPER'] = mid + 2.0 * std
            out['BB_LOWER'] = mid - 2.0 * std
        return out

    def _vote(self, indicators: Dict[str, float], price: float) -> (Optional[str], float):
        bull = 0
        bear = 0
        rsi = indicators.get('RSI_14')
        if rsi is not None:
            if rsi < 30:
                bull += 1
            if rsi > 70:
                bear += 1
        macd = indicators.get('MACD_LINE')
        if macd is not None:
            if macd > 0:
                bull += 1
            elif macd < 0:
                bear += 1
        if 'BB_UPPER' in indicators and 'BB_LOWER' in indicators:
            if price > indicators['BB_UPPER']:
                bear += 1
            elif price < indicators['BB_LOWER']:
                bull += 1
        total = bull + bear
        if total < self.required_confluence:
            return None, 0.0
        if bull > bear:
            return 'BUY', bull / total
        if bear > bull:
            return 'SELL', bear / total
        return None, 0.0

    def generate_candidate(self, market_data: Dict[str, Any]):
        prices = market_data.get('prices', []) or []
        if len(prices) < 26:
            return None
        symbol = market_data.get('symbol', 'EUR_USD')
        platform = market_data.get('platform', 'OANDA')
        indicators = self._calc_simple_indicators(prices)
        last_price = float(prices[-1])
        decision, conf = self._vote(indicators, last_price)
        if not decision:
            return None
        # Build minimal TradeCandidate object; use conservative stop
        stop = last_price * (1 - self.stop_loss_pct) if decision == 'BUY' else last_price * (1 + self.stop_loss_pct)
        cand = TradeCandidate('full_indicator_scan', symbol, platform, last_price, stop, side=decision)
        setattr(cand, 'confidence', conf)
        setattr(cand, 'meta', {'indicators': indicators})
        return cand
