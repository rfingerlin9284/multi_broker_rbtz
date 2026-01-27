"""Regime classifier (convenience module at package root).
Delegates a simple deterministic classifier used by strategies and the
self-tuner.
"""
from __future__ import annotations
from typing import Dict, Any


def classify(prices: list, cfg: Dict[str, Any]) -> Dict[str, Any]:
    if not prices or len(prices) < 5:
        return {'regime': 'CHAOP', 'confidence': 0.0, 'reasons': ['insufficient_data']}

    diffs = [abs(prices[i] - prices[i-1]) for i in range(1, len(prices))]
    atr = sum(diffs) / len(diffs)
    ma_diff = sum(diffs[-min(14, len(diffs)):]) / min(14, len(diffs))
    adx_proxy = (ma_diff / atr) * 100 if atr > 0 else 0

    ema_short = sum(prices[-(cfg.get('ema_short_period', 12)):]) / min(len(prices), cfg.get('ema_short_period', 12))
    ema_long = sum(prices[-(cfg.get('ema_long_period', 26)):]) / min(len(prices), cfg.get('ema_long_period', 26))
    slope_ok = (ema_short - ema_long)

    if atr < cfg.get('chaop_atr_threshold', 0.00005) and adx_proxy < cfg.get('adx_trend_threshold', 20.0):
        return {'regime': 'CHAOP', 'confidence': 0.9, 'reasons': ['low_atr_and_low_adx']}

    if adx_proxy >= cfg.get('adx_trend_threshold', 20.0) and abs(slope_ok) > 0:
        dir = 'BULL' if slope_ok > 0 else 'BEAR'
        return {'regime': 'TREND', 'confidence': 0.8, 'reasons': ['adx_trend','ema_slope'], 'trend': dir}

    return {'regime': 'RANGE', 'confidence': 0.6, 'reasons': ['moderate_adx_or_mixed_slope']}
