#!/usr/bin/env python3
"""
EXTREME MARKET SIMULATOR
Generates volatile, chaotic market conditions for stress testing
"""
import random
from typing import List, Dict
import math


def gen_extreme_volatility_spike(length: int = 500, seed: int | None = None) -> List[float]:
    """
    Extreme volatility with random 10-50% spikes
    Simulates flash crashes, news events, liquidity crises
    """
    rnd = random.Random(seed)
    p = 1.0
    series = []
    
    for i in range(length):
        # 5% chance of volatility spike
        if rnd.random() < 0.05:
            spike = rnd.choice([0.10, 0.15, 0.20, 0.30, 0.50])  # 10-50% move
            direction = rnd.choice([-1, 1])
            p *= (1.0 + direction * spike)
            series.append(p)
        else:
            # Normal high volatility
            p *= 1.0 + rnd.uniform(-0.03, 0.03)
            series.append(p)
    
    return series


def gen_whipsaw_chop(length: int = 500, seed: int | None = None) -> List[float]:
    """
    Choppy sideways action with false breakouts
    Kills trend-following strategies
    """
    rnd = random.Random(seed)
    p = 1.0
    series = []
    
    # Oscillate around mean with fake breakouts
    for i in range(length):
        if i % 50 == 0:  # Fake breakout every 50 bars
            fake_move = rnd.choice([0.05, -0.05, 0.08, -0.08])
            for _ in range(10):  # Breakout lasts 10 bars then reverses
                if len(series) < length:
                    p *= 1.0 + fake_move
                    series.append(p)
        else:
            # Tight chop
            p *= 1.0 + rnd.uniform(-0.005, 0.005)
            if len(series) < length:
                series.append(p)
    
    return series[:length]


def gen_trending_with_brutal_retracements(length: int = 500, drift: float = 0.001, seed: int | None = None) -> List[float]:
    """
    Strong trend with sudden 30-40% retracements
    Tests trailing stop survival
    """
    rnd = random.Random(seed)
    p = 1.0
    series = []
    
    for i in range(length):
        # 3% chance of brutal retracement
        if rnd.random() < 0.03:
            retrace = rnd.uniform(0.30, 0.40)  # 30-40% pullback
            p *= (1.0 - retrace)
            series.append(p)
        else:
            # Strong trend
            p *= 1.0 + drift + rnd.uniform(-0.002, 0.002)
            series.append(p)
    
    return series


def gen_gap_fest(length: int = 500, seed: int | None = None) -> List[float]:
    """
    Frequent price gaps (simulates crypto weekends, news events)
    Tests stop-loss execution
    """
    rnd = random.Random(seed)
    p = 1.0
    series = []
    
    for i in range(length):
        # 10% chance of gap
        if rnd.random() < 0.10:
            gap = rnd.uniform(-0.05, 0.05)  # 5% gap
            p *= (1.0 + gap)
            series.append(p)
        else:
            p *= 1.0 + rnd.uniform(-0.01, 0.01)
            series.append(p)
    
    return series


def gen_liquidity_crisis(length: int = 500, seed: int | None = None) -> List[float]:
    """
    Thin liquidity with wide bid-ask spreads
    Simulates overnight/weekend/crisis conditions
    """
    rnd = random.Random(seed)
    p = 1.0
    series = []
    
    for i in range(length):
        # Random walk but with occasional liquidity holes
        if rnd.random() < 0.08:  # 8% chance of no liquidity
            # Price freezes for 3-5 bars
            freeze_bars = rnd.randint(3, 5)
            for _ in range(freeze_bars):
                if len(series) < length:
                    series.append(p)  # No movement
        else:
            # High volatility when liquid
            p *= 1.0 + rnd.uniform(-0.04, 0.04)
            if len(series) < length:
                series.append(p)
    
    return series[:length]


def gen_momentum_trap(length: int = 500, seed: int | None = None) -> List[float]:
    """
    False momentum signals followed by reversals
    Traps momentum chasers
    """
    rnd = random.Random(seed)
    p = 1.0
    series = []
    
    phase = "accumulation"
    bars_in_phase = 0
    
    for i in range(length):
        bars_in_phase += 1
        
        if phase == "accumulation" and bars_in_phase > 30:
            # Switch to fake breakout
            phase = "breakout"
            bars_in_phase = 0
        elif phase == "breakout" and bars_in_phase > 15:
            # Reverse
            phase = "reversal"
            bars_in_phase = 0
        elif phase == "reversal" and bars_in_phase > 20:
            # Back to accumulation
            phase = "accumulation"
            bars_in_phase = 0
        
        if phase == "accumulation":
            p *= 1.0 + rnd.uniform(-0.002, 0.002)
        elif phase == "breakout":
            p *= 1.0 + 0.01 + rnd.uniform(-0.001, 0.001)  # Fake momentum
        elif phase == "reversal":
            p *= 1.0 - 0.015 + rnd.uniform(-0.002, 0.002)  # Sharp drop
        
        series.append(p)
    
    return series


# Composite extreme scenario
def gen_extreme_chaos(length: int = 500, seed: int | None = None) -> List[float]:
    """
    Combination of all worst-case scenarios
    Ultimate stress test
    """
    rnd = random.Random(seed)
    p = 1.0
    series = []
    
    for i in range(length):
        r = rnd.random()
        
        if r < 0.1:  # 10% - Volatility spike
            p *= 1.0 + rnd.uniform(-0.30, 0.30)
        elif r < 0.2:  # 10% - Gap
            p *= 1.0 + rnd.uniform(-0.08, 0.08)
        elif r < 0.25:  # 5% - Freeze (liquidity hole)
            pass  # No change
        elif r < 0.4:  # 15% - Whipsaw
            p *= 1.0 + rnd.choice([-0.02, 0.02])
        else:  # 60% - High volatility
            p *= 1.0 + rnd.uniform(-0.04, 0.04)
        
        series.append(p)
    
    return series


EXTREME_SCENARIOS = {
    "extreme_volatility_spike": gen_extreme_volatility_spike,
    "whipsaw_chop": gen_whipsaw_chop,
    "trending_with_brutal_retracements": gen_trending_with_brutal_retracements,
    "gap_fest": gen_gap_fest,
    "liquidity_crisis": gen_liquidity_crisis,
    "momentum_trap": gen_momentum_trap,
    "extreme_chaos": gen_extreme_chaos,
}
