"""Strategy base, registry and simple canonical strategies

This module defines a simple Strategy interface and registers a few lightweight
example strategies for testing and demonstration purposes. They are intentionally
simple and well-tested to provide a foundation to build on.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Callable
from ..risk.trade_risk_gate import TradeCandidate

STRATEGY_REGISTRY: Dict[str, "Strategy"] = {}


def register_strategy(id: str) -> Callable:
    def deco(cls: "Strategy"):
        instance = cls()
        STRATEGY_REGISTRY[id] = instance
        # allow strategies to access registry if needed
        instance.get = get_strategy
        return cls
    return deco


def get_strategy(id: str) -> Optional["Strategy"]:
    return STRATEGY_REGISTRY.get(id)


# Utility for troubleshooting: list registered strategies
def list_strategies() -> Dict[str, str]:
    """Return a mapping of strategy id -> class name for quick inspection."""
    return {k: v.__class__.__name__ for k, v in STRATEGY_REGISTRY.items()}


class Strategy(ABC):
    """Abstract base for strategies. Implement `generate_candidate`.

    The `market_data` dictionary is intentionally generic so strategies can
    be driven by test fixtures or real market sinks. Expected keys:
    - symbol: str
    - platform: str
    - prices: list[float] (most recent prices, older->newer)
    """
    def get(self, id: str) -> Optional["Strategy"]:
        return get_strategy(id)

    @abstractmethod
    def generate_candidate(self, market_data: Dict[str, Any]) -> Optional[TradeCandidate]:
        raise NotImplementedError


# Helpers

def _ema(prices: list[float], span: int) -> Optional[float]:
    if not prices or span <= 0 or len(prices) < span:
        return None
    alpha = 2.0 / (span + 1)
    ema = prices[0]
    for p in prices[1:]:
        ema = alpha * p + (1 - alpha) * ema
    return ema


def _rsi(prices: list[float], period: int = 14) -> Optional[float]:
    if len(prices) < period + 1:
        return None
    gains = 0.0
    losses = 0.0
    for i in range(1, period+1):
        diff = prices[-i] - prices[-i-1]
        if diff > 0:
            gains += diff
        else:
            losses += abs(diff)
    avg_gain = gains / period
    avg_loss = losses / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


# Simple strategies

@register_strategy('ema_scalper')
class EMAScalper(Strategy):
    """Short/long EMA crossover scalper, parameterized at runtime.

    Accepts optional `params` in `market_data`:
    - short_span (int)
    - long_span (int)
    - min_move_pct (float): require |short-long|/long >= threshold
    - transaction_cost (float): used to filter tiny signals

    market_data: {prices: [...], symbol, platform, params: {...}}
    """
    def generate_candidate(self, market_data: Dict[str, Any]) -> Optional[TradeCandidate]:
        prices = market_data.get('prices', [])
        params = market_data.get('params', {}) or {}
        short_span = int(params.get('short_span', 5))
        long_span = int(params.get('long_span', 21))
        min_move_pct = float(params.get('min_move_pct', 0.0005))
        transaction_cost = float(params.get('transaction_cost', 0.0001))
        min_len = max(short_span, long_span)
        if len(prices) < min_len + 1:
            return None
        short = _ema(prices, short_span)
        long = _ema(prices, long_span)
        if short is None or long is None:
            return None
        # require significant move relative to long EMA
        if abs(short - long) / (abs(long) + 1e-12) < (min_move_pct + transaction_cost):
            return None
        symbol = market_data.get('symbol', 'SYM')
        platform = market_data.get('platform', 'OANDA')
        # simple crossover and momentum confirmation
        if short > long and prices[-1] > prices[-2]:
            entry = prices[-1]
            stop = entry - max(0.001, 0.005 * entry)
            return TradeCandidate('ema_scalper', symbol, platform, entry, stop, side='BUY')
        if short < long and prices[-1] < prices[-2]:
            entry = prices[-1]
            stop = entry + max(0.001, 0.005 * entry)
            return TradeCandidate('ema_scalper', symbol, platform, entry, stop, side='SELL')
        return None


@register_strategy('institutional_sd')
class InstitutionalSD(Strategy):
    """Detects elevated standard deviation (volatility) and looks for momentum.

    Very simple: compute stdev of returns and if it exceeds threshold, open a
    momentum trade in the direction of the latest return.
    """
    def generate_candidate(self, market_data: Dict[str, Any]) -> Optional[TradeCandidate]:
        import math
        prices = market_data.get('prices', [])
        if len(prices) < 8:
            return None
        rets = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
        mean = sum(rets) / len(rets)
        var = sum((r - mean) ** 2 for r in rets) / len(rets)
        sd = math.sqrt(var)
        if sd < 0.001:  # threshold
            return None
        last_ret = rets[-1]
        symbol = market_data.get('symbol', 'SYM')
        platform = market_data.get('platform', 'OANDA')
        entry = prices[-1]
        if last_ret > 0:
            stop = entry - 0.01 * entry
            return TradeCandidate('institutional_sd', symbol, platform, entry, stop, side='BUY')
        elif last_ret < 0:
            stop = entry + 0.01 * entry
            return TradeCandidate('institutional_sd', symbol, platform, entry, stop, side='SELL')
        return None


@register_strategy('trap_reversal')
class TrapReversal(Strategy):
    """Mean-reversion candidate when price makes a strong spike then reverts.

    Simple rule: detect a one-bar spike > X% then next bar moves back.
    """
    def generate_candidate(self, market_data: Dict[str, Any]) -> Optional[TradeCandidate]:
        prices = market_data.get('prices', [])
        if len(prices) < 3:
            return None
        p2, p1, p0 = prices[-3], prices[-2], prices[-1]
        if abs((p1 - p2) / p2) > 0.02 and (p0 - p1) * (p1 - p2) < 0:
            # reversal
            symbol = market_data.get('symbol', 'SYM')
            platform = market_data.get('platform', 'OANDA')
            entry = p0
            # place stop a bit beyond previous extreme
            stop = p1 + (p1 - p2) * 0.5
            side = 'SELL' if p0 < p1 else 'BUY'
            return TradeCandidate('trap_reversal', symbol, platform, entry, stop, side=side)
        return None


@register_strategy('holy_grail')
class HolyGrail(Strategy):
    """A conservative trend-following rule with RSI confirmation.

    Adds an RSI filter (default period 14): only open BUYs if RSI < 70 and > 50
    and SELLs if RSI > 30 and < 50, to avoid overbought/oversold extremes.
    """
    def generate_candidate(self, market_data: Dict[str, Any]) -> Optional[TradeCandidate]:
        prices = market_data.get('prices', [])
        params = market_data.get('params', {}) or {}
        rsi_period = int(params.get('rsi_period', 14))
        if len(prices) < max(12, rsi_period + 1):
            return None
        sma = sum(prices[-10:]) / 10.0
        rsi = _rsi(prices, period=rsi_period)
        # compute average return over the RSI period to distinguish sustained small gains
        avg_ret = None
        if len(prices) >= rsi_period + 1:
            try:
                start = prices[-(rsi_period + 1)]
                avg_ret = (prices[-1] - start) / start / float(rsi_period)
            except Exception:
                avg_ret = None
        symbol = market_data.get('symbol', 'SYM')
        platform = market_data.get('platform', 'OANDA')
        if prices[-1] > sma and prices[-1] > prices[-2]:
            # prefer RSI > 50, but allow very high RSI if avg per-bar returns are small
            if rsi is not None:
                if not (rsi > 50):
                    return None
                if rsi > 90 and (avg_ret is not None and avg_ret > 0.005):
                    # extreme rapid run-up, block
                    return None
            entry = prices[-1]
            stop = sma
            return TradeCandidate('holy_grail', symbol, platform, entry, stop, side='BUY')
        if prices[-1] < sma and prices[-1] < prices[-2]:
            if rsi is not None:
                if not (rsi < 50):
                    return None
                if rsi < 10 and (avg_ret is not None and avg_ret < -0.005):
                    return None
            entry = prices[-1]
            stop = sma
            return TradeCandidate('holy_grail', symbol, platform, entry, stop, side='SELL')
        return None
