#!/usr/bin/env python3
"""
PAYLOAD BUILDER
Assembles dynamic job tickets from UI selections + market data + settings
Converts human inputs to structured AI-ready payloads
"""
from typing import Dict, Any, List, Optional, Literal
from datetime import datetime
import random

class PayloadBuilder:
    """
    Builds comprehensive market data payloads for AI agents
    Handles tiered data (A/B/C) and autofill logic
    """
    
    def __init__(self):
        self.default_risk_rules = {
            "max_risk_per_trade_pct": 0.5,
            "max_daily_loss_pct": 2.0,
            "leverage_cap": 2.0,
            "oco_required": True
        }
        
        self.spread_estimates = {
            # Forex majors (pips)
            "EURUSD": 0.0001,
            "GBPUSD": 0.0002,
            "USDJPY": 0.01,
            "AUDUSD": 0.0002,
            "USDCAD": 0.0002,
            "NZDUSD": 0.0003,
            # Crypto (basis points)
            "BTCUSD": 0.5,
            "ETHUSD": 0.3,
            "BTCUSDT": 0.1,
            # Indices (points)
            "SPY": 0.01,
            "QQQ": 0.01,
            "ES": 0.25,
        }
    
    def build_payload(self,
                     instrument: str,
                     timeframe: str,
                     current_price: float,
                     recent_high: Optional[float] = None,
                     recent_low: Optional[float] = None,
                     prices: Optional[List[float]] = None,
                     candles: Optional[List[Dict]] = None,
                     objective: Literal["scalp", "day", "swing", "hedge", "invest"] = "day",
                     risk_rules: Optional[Dict[str, Any]] = None,
                     cost_model: Optional[Dict[str, Any]] = None,
                     session: Optional[str] = None,
                     news_risk: Optional[str] = None) -> Dict[str, Any]:
        """
        Build complete payload from available inputs
        
        Args:
            instrument: Trading symbol
            timeframe: Chart timeframe
            current_price: Current market price
            recent_high: Session/24h high (calculated if not provided)
            recent_low: Session/24h low (calculated if not provided)
            prices: List of recent closes (for Tier B/C)
            candles: List of OHLC dicts (for Tier B/C)
            objective: Trading style
            risk_rules: Risk parameters (uses defaults if not provided)
            cost_model: Spread/fees (estimated if not provided)
            session: Market session (auto-detected if not provided)
            news_risk: News risk level (low/med/high)
        
        Returns:
            Complete payload dict ready for AI agent
        """
        
        # Build price context
        price_context = self._build_price_context(
            current_price, recent_high, recent_low, prices, candles
        )
        
        # Use provided risk rules or defaults
        if not risk_rules:
            risk_rules = self.default_risk_rules.copy()
        else:
            # Merge with defaults
            merged = self.default_risk_rules.copy()
            merged.update(risk_rules)
            risk_rules = merged
        
        # Build cost model
        if not cost_model:
            cost_model = self._estimate_costs(instrument, objective)
        
        # Determine session
        if not session:
            session = self._detect_session()
        
        # Assemble payload
        payload = {
            "instrument": instrument,
            "timeframe": timeframe,
            "timestamp_utc": datetime.utcnow().isoformat() + "Z",
            "session": session,
            "objective": objective,
            "price_context": price_context,
            "risk_rules": risk_rules,
            "cost_model": cost_model
        }
        
        if news_risk:
            payload["news_risk"] = news_risk
        
        return payload
    
    def _build_price_context(self,
                            current_price: float,
                            recent_high: Optional[float],
                            recent_low: Optional[float],
                            prices: Optional[List[float]],
                            candles: Optional[List[Dict]]) -> Dict[str, Any]:
        """Build tiered price context"""
        context = {
            "current_price": current_price,
            "tier": "A"  # Start with minimum
        }
        
        # Calculate high/low if not provided
        if prices:
            if recent_high is None:
                recent_high = max(prices[-20:] if len(prices) >= 20 else prices)
            if recent_low is None:
                recent_low = min(prices[-20:] if len(prices) >= 20 else prices)
        
        if recent_high is not None:
            context["recent_high"] = recent_high
        else:
            # Fallback: use current price with 2% margin
            context["recent_high"] = current_price * 1.02
        
        if recent_low is not None:
            context["recent_low"] = recent_low
        else:
            # Fallback: use current price with 2% margin
            context["recent_low"] = current_price * 0.98
        
        # Add Tier B data if available
        if prices and len(prices) >= 10:
            context["last_10_closes"] = prices[-10:]
            context["tier"] = "B"
            
            if len(prices) >= 20:
                context["last_20_closes"] = prices[-20:]
        
        # Add Tier C data if available
        if candles and len(candles) >= 50:
            context["last_50_candles"] = candles[-50:]
            context["tier"] = "C"
            
            # Calculate volatility indicators
            context["ATR"] = self._calculate_atr(candles[-14:])
            context["volatility_pct"] = self._calculate_volatility(prices[-20:] if prices else [])
        elif candles and len(candles) >= 10:
            context["last_10_candles"] = candles[-10:]
            if context["tier"] == "A":
                context["tier"] = "B"
        
        return context
    
    def _calculate_atr(self, candles: List[Dict]) -> float:
        """Calculate Average True Range"""
        if not candles or len(candles) < 2:
            return 0.0
        
        true_ranges = []
        for i in range(1, len(candles)):
            high = candles[i].get("high", 0)
            low = candles[i].get("low", 0)
            prev_close = candles[i-1].get("close", 0)
            
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            true_ranges.append(tr)
        
        return sum(true_ranges) / len(true_ranges) if true_ranges else 0.0
    
    def _calculate_volatility(self, prices: List[float]) -> float:
        """Calculate simple volatility (standard deviation as %)"""
        if not prices or len(prices) < 2:
            return 0.0
        
        avg = sum(prices) / len(prices)
        variance = sum((p - avg) ** 2 for p in prices) / len(prices)
        std_dev = variance ** 0.5
        
        return (std_dev / avg * 100) if avg > 0 else 0.0
    
    def _estimate_costs(self, instrument: str, objective: str) -> Dict[str, Any]:
        """Estimate trading costs based on instrument"""
        spread = self.spread_estimates.get(instrument.upper())
        
        cost_model = {
            "estimated_spread": spread,
            "estimated_fees_per_unit": None,
            "broker_fee_preset": "",
            "notes": []
        }
        
        if spread:
            cost_model["notes"].append(f"Estimated spread: {spread}")
        else:
            cost_model["notes"].append("Spread unknown - consider manually setting")
        
        if objective == "scalp":
            cost_model["notes"].append("SCALPING: Costs critical - verify actual spread")
        
        return cost_model
    
    def _detect_session(self) -> str:
        """Detect current market session based on UTC time"""
        hour = datetime.utcnow().hour
        
        # NY session: 13:00-21:00 UTC (8am-4pm EST)
        if 13 <= hour < 21:
            return "NY"
        
        # London session: 7:00-16:00 UTC (8am-5pm GMT)
        elif 7 <= hour < 16:
            return "London"
        
        # Asia session: 0:00-8:00 UTC
        elif 0 <= hour < 8:
            return "Asia"
        
        # Overlap periods
        elif 13 <= hour < 16:
            return "overlap"  # London/NY overlap
        
        return "unknown"
    
    def autofill_from_chart(self, 
                           instrument: str,
                           timeframe: str) -> Dict[str, Any]:
        """
        Simulate autofill from chart data
        In production, this would fetch from actual chart/price feed
        """
        # Simulate realistic price data
        if "BTC" in instrument.upper():
            base = 43000 + random.uniform(-1000, 1000)
        elif "ETH" in instrument.upper():
            base = 2300 + random.uniform(-100, 100)
        elif "EUR" in instrument.upper():
            base = 1.0950 + random.uniform(-0.01, 0.01)
        elif "GBP" in instrument.upper():
            base = 1.2700 + random.uniform(-0.01, 0.01)
        else:
            base = 100.0
        
        # Generate price series
        prices = [base + i * 0.0001 + random.uniform(-0.002, 0.002) for i in range(50)]
        
        # Generate candles
        candles = []
        for i, close in enumerate(prices):
            high = close + random.uniform(0, 0.003)
            low = close - random.uniform(0, 0.003)
            open_price = prices[i-1] if i > 0 else close
            
            candles.append({
                "open": open_price,
                "high": high,
                "low": low,
                "close": close,
                "volume": random.uniform(1000, 10000)
            })
        
        return self.build_payload(
            instrument=instrument,
            timeframe=timeframe,
            current_price=prices[-1],
            recent_high=max(prices[-20:]),
            recent_low=min(prices[-20:]),
            prices=prices,
            candles=candles
        )
    
    def validate_and_enhance(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate payload and add enhancements if needed
        """
        # Ensure required fields exist
        if "timestamp_utc" not in payload:
            payload["timestamp_utc"] = datetime.utcnow().isoformat() + "Z"
        
        if "session" not in payload:
            payload["session"] = self._detect_session()
        
        # Add data quality metadata
        tier = payload.get("price_context", {}).get("tier", "A")
        payload["_metadata"] = {
            "data_tier": tier,
            "build_timestamp": datetime.utcnow().isoformat(),
            "builder_version": "1.0.0"
        }
        
        return payload


# Convenience function
def build_quick_payload(instrument: str,
                       timeframe: str,
                       current_price: float,
                       **kwargs) -> Dict[str, Any]:
    """Quick payload builder with sensible defaults"""
    builder = PayloadBuilder()
    return builder.build_payload(instrument, timeframe, current_price, **kwargs)


# Export
__all__ = ['PayloadBuilder', 'build_quick_payload']
