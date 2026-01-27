"""GBP/USD ONLY Strategy - Based on Real OANDA Profitability

Analysis shows:
- GBP/USD was your ONLY profitable pair (18% WR, +$72)  
- EUR/AUD was marginal (33% WR but only +$13)
- All other pairs: 0-9% WR, total losses

This strategy ONLY trades GBP/USD and uses conservative filters
to aim for 15-25% WR (realistic) with proper risk management.
"""
from ..strategies.base import Strategy, register_strategy, _rsi, _ema
from ..risk.trade_risk_gate import TradeCandidate
from typing import Optional, Dict, Any


@register_strategy('gbp_usd_only')
class GBPUSDOnly(Strategy):
    """Conservative GBP/USD strategy based on real profitability data
    
    Key learnings from OANDA data:
    - 95% stop-out rate means stops were TOO TIGHT
    - Only GBP/USD made money (18% WR)
    - Need WIDER stops (3-5%) to survive noise
    - Need strong momentum + volatility confirmation
    - Trade less, win more
    """
    
    def generate_candidate(self, market_data: Dict[str, Any]) -> Optional[TradeCandidate]:
        symbol = market_data.get('symbol', '')
        platform = market_data.get('platform', 'OANDA')
        prices = market_data.get('prices', [])
        
        # ONLY trade GBP/USD (our only profitable pair)
        if 'GBP' not in symbol.upper() or 'USD' not in symbol.upper():
            return None
        
        if len(prices) < 50:
            return None
        
        # Get parameters
        params = market_data.get('params', {}) or {}
        momentum_threshold = float(params.get('momentum_threshold', 0.015))  # 1.5%
        rsi_period = int(params.get('rsi_period', 14))
        stop_pct = float(params.get('stop_pct', 0.04))  # 4% stops (WIDE to avoid 95% stop-out)
        
        current_price = prices[-1]
        
        # 1. Calculate momentum over last 10 bars
        momentum = (prices[-1] - prices[-11]) / prices[-11]
        
        # 2. Calculate RSI
        rsi = _rsi(prices, rsi_period)
        if rsi is None:
            return None
        
        # 3. Calculate short/long EMA
        ema_fast = _ema(prices, 9)
        ema_slow = _ema(prices, 21)
        if ema_fast is None or ema_slow is None:
            return None
        
        # 4. Calculate volatility (need elevated vol for edge)
        import math
        recent_returns = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(-20, 0)]
        vol = math.sqrt(sum(r**2 for r in recent_returns) / len(recent_returns))
        
        # ENTRY RULES (Conservative - aim for quality over quantity)
        
        # LONG: Strong upward momentum + EMA crossover + RSI not overbought + elevated vol
        if (momentum > momentum_threshold and
            ema_fast > ema_slow and
            prices[-1] > prices[-2] and  # bullish bar
            30 < rsi < 65 and  # not overbought (allow some room)
            vol > 0.002):  # elevated volatility
            
            entry = current_price
            stop = entry * (1 - stop_pct)  # 4% stop (WIDE to survive whipsaws)
            
            return TradeCandidate(
                'gbp_usd_only',
                symbol,
                platform,
                entry,
                stop,
                side='BUY'
            )
        
        # SHORT: Strong downward momentum + EMA bearish + RSI not oversold + elevated vol
        if (momentum < -momentum_threshold and
            ema_fast < ema_slow and
            prices[-1] < prices[-2] and  # bearish bar
            35 < rsi < 70 and  # not oversold (allow some room)
            vol > 0.002):  # elevated volatility
            
            entry = current_price
            stop = entry * (1 + stop_pct)  # 4% stop
            
            return TradeCandidate(
                'gbp_usd_only',
                symbol,
                platform,
                entry,
                stop,
                side='SELL'
            )
        
        return None
