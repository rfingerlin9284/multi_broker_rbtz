"""
SIMPLE TREND STRENGTH INDICATOR
Counts consecutive closes in same direction - dead simple, no complex math
"""
from typing import List

def trend_strength(prices: List[float], lookback: int = 10) -> float:
    """
    Calculate simple trend strength (0 to 1)
    1.0 = perfect uptrend (all bars higher)
    0.0 = perfect downtrend (all bars lower)
    0.5 = no trend (choppy)
    
    Returns percentage of bars that moved in trending direction
    """
    if len(prices) < lookback + 1:
        return 0.5
    
    recent = prices[-lookback-1:]
    
    # Count how many closes moved in dominant direction
    ups = sum(1 for i in range(1, len(recent)) if recent[i] > recent[i-1])
    downs = sum(1 for i in range(1, len(recent)) if recent[i] < recent[i-1])
    
    total = lookback
    if ups > downs:
        # Uptrend strength
        return ups / total
    else:
        # Downtrend strength (invert)
        return downs / total

def is_strong_trend(prices: List[float], threshold: float = 0.7) -> bool:
    """
    Check if we have strong trend (70%+ bars in same direction)
    
    Returns True if trending strongly, False if choppy
    """
    strength = trend_strength(prices, lookback=10)
    return strength >= threshold

# Test
if __name__ == '__main__':
    # Strong uptrend
    uptrend = [100 + i for i in range(20)]
    print(f"Strong uptrend strength: {trend_strength(uptrend):.2f} ({'✅ TRENDING' if is_strong_trend(uptrend) else '❌ CHOPPY'})")
    
    # Choppy
    choppy = [100, 101, 100, 102, 99, 103, 98, 104, 97, 105]
    print(f"Choppy market strength: {trend_strength(choppy):.2f} ({'✅ TRENDING' if is_strong_trend(choppy) else '❌ CHOPPY'})")
    
    # Moderate trend
    moderate = [100, 101, 100, 102, 103, 102, 104, 105, 104, 106]
    print(f"Moderate trend strength: {trend_strength(moderate):.2f} ({'✅ TRENDING' if is_strong_trend(moderate, 0.6) else '❌ CHOPPY'})")
