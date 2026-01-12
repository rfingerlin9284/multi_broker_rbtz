#!/usr/bin/env python3
"""Simple HIVE implementation for WSL without browser automation.

This version uses the existing strategies but adds a simple research layer
that doesn't require external APIs or browser automation. Perfect for WSL.
"""
import json
import random
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class HiveVote:
    """Simple HIVE vote structure."""
    agent_name: str
    signal: str  # buy, sell, neutral
    confidence: float  # 0.0 to 1.0
    reasoning: str


class SimpleHiveEngine:
    """WSL-compatible HIVE that uses built-in logic instead of external APIs."""
    
    def __init__(self):
        self.threshold = 0.30  # 30% consensus needed
        
    def analyze_trade(self, symbol: str, direction: str, entry_price: float, 
                     market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze trade using simple built-in logic."""
        
        prices = market_data.get('prices', [])
        if len(prices) < 20:
            return {"vote": "neutral", "confidence": 0.0, "reasoning": "Insufficient data"}
        
        # Get agent votes using simple technical analysis
        votes = [
            self._oracle_vote(symbol, direction, prices),
            self._prometheus_vote(direction, prices, entry_price),
            self._sentinel_vote(direction, entry_price, prices)
        ]
        
        # Calculate consensus
        buy_votes = sum(1 for v in votes if v.signal == "buy")
        sell_votes = sum(1 for v in votes if v.signal == "sell") 
        total_votes = len(votes)
        
        buy_consensus = buy_votes / total_votes
        sell_consensus = sell_votes / total_votes
        
        avg_confidence = sum(v.confidence for v in votes) / len(votes)
        
        # Determine final decision
        if direction.upper() == "BUY" and buy_consensus >= self.threshold:
            decision = "approve"
        elif direction.upper() == "SELL" and sell_consensus >= self.threshold:
            decision = "approve"
        else:
            decision = "reject"
            
        return {
            "vote": decision,
            "confidence": avg_confidence,
            "consensus": max(buy_consensus, sell_consensus),
            "votes": [{"agent": v.agent_name, "signal": v.signal, "confidence": v.confidence, "reasoning": v.reasoning} for v in votes],
            "reasoning": f"Consensus: {max(buy_consensus, sell_consensus):.1%}, Confidence: {avg_confidence:.1%}"
        }
    
    def _oracle_vote(self, symbol: str, direction: str, prices: list) -> HiveVote:
        """Oracle agent: Looks for momentum and trend strength."""
        recent_trend = (prices[-1] - prices[-5]) / prices[-5] if len(prices) > 5 else 0
        momentum = (prices[-1] - prices[-10]) / prices[-10] if len(prices) > 10 else 0
        
        confidence = min(0.9, abs(momentum) * 20)  # Higher momentum = higher confidence
        
        if direction.upper() == "BUY":
            if recent_trend > 0.002 and momentum > 0.005:  # 0.2% recent, 0.5% longer term
                return HiveVote("Oracle", "buy", confidence, f"Strong upward momentum: {momentum:.1%}")
            elif recent_trend < -0.002:
                return HiveVote("Oracle", "sell", confidence, f"Negative momentum: {recent_trend:.1%}")
        else:  # SELL
            if recent_trend < -0.002 and momentum < -0.005:
                return HiveVote("Oracle", "sell", confidence, f"Strong downward momentum: {momentum:.1%}")
            elif recent_trend > 0.002:
                return HiveVote("Oracle", "buy", confidence, f"Positive momentum: {recent_trend:.1%}")
        
        return HiveVote("Oracle", "neutral", 0.3, "No clear momentum signal")
    
    def _prometheus_vote(self, direction: str, prices: list, entry_price: float) -> HiveVote:
        """Prometheus agent: Technical analysis (RSI, volatility)."""
        if len(prices) < 14:
            return HiveVote("Prometheus", "neutral", 0.2, "Insufficient data for RSI")
        
        # Simple RSI calculation
        gains = []
        losses = []
        for i in range(1, 15):
            change = prices[-i] - prices[-i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = sum(gains) / 14
        avg_loss = sum(losses) / 14
        
        if avg_loss == 0:
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        
        # Calculate volatility
        returns = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(-5, 0)]
        volatility = sum(abs(r) for r in returns) / len(returns)
        
        confidence = 0.7 if 0.01 < volatility < 0.05 else 0.4  # Good volatility range
        
        if direction.upper() == "BUY":
            if rsi < 40 and volatility > 0.01:  # Oversold with volume
                return HiveVote("Prometheus", "buy", confidence, f"Oversold RSI: {rsi:.1f}, good volatility")
            elif rsi > 70:
                return HiveVote("Prometheus", "sell", confidence, f"Overbought RSI: {rsi:.1f}")
        else:  # SELL  
            if rsi > 60 and volatility > 0.01:  # Overbought with volume
                return HiveVote("Prometheus", "sell", confidence, f"Overbought RSI: {rsi:.1f}, good volatility")
            elif rsi < 30:
                return HiveVote("Prometheus", "buy", confidence, f"Oversold RSI: {rsi:.1f}")
        
        return HiveVote("Prometheus", "neutral", 0.4, f"RSI neutral: {rsi:.1f}")
    
    def _sentinel_vote(self, direction: str, entry_price: float, prices: list) -> HiveVote:
        """Sentinel agent: Risk management and stop validation."""
        if len(prices) < 5:
            return HiveVote("Sentinel", "neutral", 0.2, "Insufficient price history")
        
        # Calculate recent volatility for stop distance validation
        recent_moves = [abs(prices[i] - prices[i-1]) / prices[i-1] for i in range(-4, 0)]
        avg_move = sum(recent_moves) / len(recent_moves)
        
        # Check if we're near support/resistance (simplified)
        highs = max(prices[-10:]) if len(prices) >= 10 else max(prices)
        lows = min(prices[-10:]) if len(prices) >= 10 else min(prices)
        price_range = (highs - lows) / lows
        current_position = (entry_price - lows) / (highs - lows) if highs != lows else 0.5
        
        confidence = 0.8
        
        # Risk assessment
        if direction.upper() == "BUY":
            if current_position < 0.3:  # Near support
                return HiveVote("Sentinel", "buy", confidence, f"Near support level, good R:R")
            elif current_position > 0.8:  # Near resistance
                return HiveVote("Sentinel", "sell", confidence, f"Near resistance, high risk")
            elif avg_move > 0.02:  # High volatility
                return HiveVote("Sentinel", "neutral", 0.5, f"High volatility: {avg_move:.1%}")
        else:  # SELL
            if current_position > 0.7:  # Near resistance  
                return HiveVote("Sentinel", "sell", confidence, f"Near resistance level, good R:R")
            elif current_position < 0.2:  # Near support
                return HiveVote("Sentinel", "buy", confidence, f"Near support, high risk")
            elif avg_move > 0.02:  # High volatility
                return HiveVote("Sentinel", "neutral", 0.5, f"High volatility: {avg_move:.1%}")
        
        return HiveVote("Sentinel", "neutral", 0.5, f"Neutral zone, position: {current_position:.1%}")


# Global instance
hive_engine = SimpleHiveEngine()


def get_hive_vote(symbol: str, direction: str, entry_price: float, market_data: Dict[str, Any]) -> Dict[str, Any]:
    """Main interface for HIVE voting."""
    return hive_engine.analyze_trade(symbol, direction, entry_price, market_data)


if __name__ == "__main__":
    # Test with sample data
    test_prices = [100 + i + random.uniform(-2, 2) for i in range(30)]
    test_data = {"prices": test_prices}
    
    result = get_hive_vote("EURUSD", "BUY", test_prices[-1], test_data)
    print(json.dumps(result, indent=2))