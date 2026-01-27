"""
AI SETUP HUNTER - GPT/GROK ACTIVE SEARCH FOR HIGH-QUALITY SETUPS
Continuously searches for setups matching strategy quality profiles
NOT generic scalping - only specific patterns with high probability
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class AISetupHunter:
    """
    Uses GPT-4/Grok-2 to actively search for high-quality trading setups.
    Evaluates charts and market conditions against specific strategy criteria.
    """
    
    def __init__(self, api_provider: str = 'gpt'):
        """
        Initialize AI Setup Hunter.
        
        Args:
            api_provider: 'gpt' for OpenAI GPT-4, 'grok' for Grok-2
        """
        self.api_provider = api_provider.lower()
        self.gpt_api_key = None
        self.grok_api_key = None
        self.search_history = []
        
        # Initialize API keys from environment
        import os
        if self.api_provider == 'gpt':
            self.gpt_api_key = os.getenv('OPENAI_API_KEY')
            logger.info("🧠 AI Setup Hunter initialized with GPT-4")
        else:
            self.grok_api_key = os.getenv('GROK_API_KEY')
            logger.info("🧠 AI Setup Hunter initialized with Grok-2")
        
        # Search parameters
        self.active_search = True
        self.search_interval_minutes = 5
        
        # Setup cache (to avoid duplicate searches)
        self.found_setups = {}
    
    def search_for_trap_reversals(self, market_data: Dict[str, Any],
                                  symbols: List[str]) -> List[Dict[str, Any]]:
        """
        Search for Trap Reversal setups using AI analysis.
        
        Looks for:
        - Clear S/R breaks with volume spike
        - False breaks (liquidity traps)
        - Institutional footprints
        - Divergences
        """
        
        prompt = f"""
You are an expert technical analyst specializing in institutional liquidity traps.

ANALYZE these market conditions for TRAP REVERSAL setups:
- Symbols: {', '.join(symbols)}
- Current data: {json.dumps(market_data, indent=2)}

LOOK FOR (ALL required):
1. Support/Resistance level break (>0.5% penetration)
2. FALSE BREAK confirmation (price bounces back 2%+ from break)
3. Volume spike (200%+ above 20-day average AT THE BREAK)
4. RSI divergence (lower RSI on higher close)
5. Volatility contraction BEFORE the break

EVALUATE:
- Is this a liquidity trap catching stop losses?
- Institutional order cluster evidence?
- Risk/Reward at least 1.5:1?
- Quality score minimum 75/100?

RESPOND with JSON:
{{
    "setups_found": [
        {{
            "symbol": "EUR/USD",
            "setup_type": "trap_reversal",
            "quality_score": 82,
            "rationale": "Clear break of 1.0950, bounced back 2.3%, volume 280% spike",
            "entry_price": 1.0925,
            "stop_loss": 1.0900,
            "take_profit": 1.0970,
            "risk_reward": 1.67,
            "catalysts": ["institutional_volume", "market_structure_break"],
            "confidence": 85
        }}
    ],
    "analysis": "Detailed market analysis"
}}
"""
        
        return self._call_ai_api(prompt, "trap_reversal")
    
    def search_for_institutional_sd(self, market_data: Dict[str, Any],
                                   symbols: List[str]) -> List[Dict[str, Any]]:
        """
        Search for Institutional Smart Distribution setups.
        
        Looks for:
        - Volatility expansion (ATR > 50MA * 1.3)
        - Bollinger Band width expansion
        - Volume profile buy/sell imbalance
        - Macro catalysts
        """
        
        prompt = f"""
You are an expert technical analyst specializing in institutional smart money patterns.

ANALYZE these market conditions for INSTITUTIONAL SD setups:
- Symbols: {', '.join(symbols)}
- Current data: {json.dumps(market_data, indent=2)}

LOOK FOR (ALL required):
1. Bollinger Band width EXPANSION (current > 50MA width by 50%+)
2. ATR breakout (current ATR > 50MA ATR by 30%+)
3. Volume profile BUY bias (>60% of volume is buy)
4. Moving average alignment (50MA > 200MA for uptrend, or vice versa)
5. Stochastic showing continuation (not exhaustion)

EVALUATE:
- Is institutional accumulation visible?
- Volatility expansion justified by catalyst?
- Risk/Reward at least 2.0:1?
- Quality score minimum 70/100?

RESPOND with JSON:
{{
    "setups_found": [
        {{
            "symbol": "BTC-USD",
            "setup_type": "institutional_sd",
            "quality_score": 76,
            "rationale": "BB width 45% expansion, ATR 32% above MA, volume 65% buy",
            "entry_price": 42500,
            "stop_loss": 41800,
            "take_profit": 44200,
            "risk_reward": 2.14,
            "catalysts": ["volatility_expansion", "institutional_accumulation"],
            "confidence": 78
        }}
    ],
    "analysis": "Detailed market analysis"
}}
"""
        
        return self._call_ai_api(prompt, "institutional_sd")
    
    def search_for_holy_grail(self, market_data: Dict[str, Any],
                             symbols: List[str]) -> List[Dict[str, Any]]:
        """
        Search for Holy Grail multi-timeframe setups.
        
        Looks for:
        - 3x timeframe alignment (1H, 4H, 1D same direction)
        - Pullback to moving average
        - Volume confirmation
        - MACD alignment
        """
        
        prompt = f"""
You are an expert technical analyst specializing in multi-timeframe confirmations.

ANALYZE these market conditions for HOLY GRAIL multi-timeframe setups:
- Symbols: {', '.join(symbols)}
- Current data across ALL timeframes: {json.dumps(market_data, indent=2)}

LOOK FOR (ALL required):
1. Daily trend is CLEAR (not range-bound)
2. 4-hour pullback setup (pulling back to 20MA/50MA)
3. 1-hour entry trigger (EMA cross or 20MA touch)
4. Volume confirmation on entry bar (>100% of 20-day avg)
5. MACD histogram positive across ALL timeframes

EVALUATE:
- Perfect multi-timeframe alignment?
- Entry pullback to key MA confirmed?
- Risk/Reward at least 2.5:1?
- Quality score minimum 80/100?

RESPOND with JSON:
{{
    "setups_found": [
        {{
            "symbol": "QQQ",
            "setup_type": "holy_grail",
            "quality_score": 84,
            "rationale": "All 3 TFs aligned up, 1D uptrend, 4H pullback to 50MA, 1H EMA9 > EMA21",
            "entry_price": 315.50,
            "stop_loss": 312.00,
            "take_profit": 325.00,
            "risk_reward": 2.62,
            "catalysts": ["multiple_timeframe_alignment", "pullback_to_ma", "confluence"],
            "confidence": 86
        }}
    ],
    "analysis": "Detailed multi-timeframe analysis"
}}
"""
        
        return self._call_ai_api(prompt, "holy_grail")
    
    def search_for_ema_scalps(self, market_data: Dict[str, Any],
                             symbols: List[str]) -> List[Dict[str, Any]]:
        """
        Search for EMA Scalper quick-hit setups.
        
        Looks for:
        - EMA 9/21 crosses
        - RSI alignment (>50 for long, <50 for short)
        - VWAP proximity
        - Volume burst on entry
        """
        
        prompt = f"""
You are an expert technical analyst specializing in fast EMA scalping.

ANALYZE these market conditions for EMA SCALPER quick-hit setups:
- Symbols: {', '.join(symbols)}
- Current data on 5M/15M: {json.dumps(market_data, indent=2)}

LOOK FOR (ALL required):
1. EMA 9/21 CROSS (just happened or about to)
2. RSI alignment (RSI > 50 for long, < 50 for short)
3. Price within 0.5% of VWAP (institutional reference)
4. Current ATR > 80% of hourly average (enough movement)
5. Entry bar volume > 150% of 5-min average

EVALUATE:
- Clean EMA cross with momentum?
- 4-hour trend supports scalp direction?
- Tight stops possible? (R:R minimum 1.0:1)
- Quality score minimum 65/100 (lower for high-frequency)?

RESPOND with JSON:
{{
    "setups_found": [
        {{
            "symbol": "ETH-USD",
            "setup_type": "ema_scalper",
            "quality_score": 68,
            "rationale": "EMA9 just crossed above EMA21, RSI 62, price 0.3% above VWAP",
            "entry_price": 1520.00,
            "stop_loss": 1515.00,
            "take_profit": 1525.00,
            "risk_reward": 1.0,
            "catalysts": ["ema_cross", "hourly_trend_support"],
            "confidence": 70,
            "hold_time_minutes": 15
        }}
    ],
    "analysis": "Detailed scalp analysis"
}}
"""
        
        return self._call_ai_api(prompt, "ema_scalper")
    
    def search_for_fabio_patterns(self, market_data: Dict[str, Any],
                                 symbols: List[str]) -> List[Dict[str, Any]]:
        """
        Search for Fabio AAA advanced patterns.
        
        Looks for:
        - Chart pattern recognition (flags, triangles, wedges)
        - Supply/demand imbalance
        - Order blocks
        - Fair value gaps
        """
        
        prompt = f"""
You are an expert technical analyst specializing in advanced chart patterns and order flow.

ANALYZE these market conditions for FABIO AAA advanced pattern setups:
- Symbols: {', '.join(symbols)}
- Current data: {json.dumps(market_data, indent=2)}

LOOK FOR (ALL required):
1. Specific chart pattern (flag, triangle, wedge, rectangle) with 80%+ confidence
2. Supply/demand imbalance (unfilled orders > 2x ratio at key level)
3. Untested order block identified (high probability unfinished business)
4. Fair value gap present that price is approaching
5. Entry candle shows specific pattern (pin bar, engulfing, hammer, etc)

EVALUATE:
- Advanced pattern with high conviction?
- Order block context valid?
- Multiple timeframe pattern confirmation?
- Risk/Reward at least 3.0:1?
- Quality score minimum 78/100?

RESPOND with JSON:
{{
    "setups_found": [
        {{
            "symbol": "GBP/USD",
            "setup_type": "fabio_aaa",
            "quality_score": 82,
            "rationale": "Symmetrical triangle breaking up, order block at 1.2700, FVG 1.2680-1.2690",
            "entry_price": 1.2705,
            "stop_loss": 1.2680,
            "take_profit": 1.2850,
            "risk_reward": 3.33,
            "catalysts": ["advanced_pattern_formation", "institutional_order_block"],
            "confidence": 81,
            "pattern_type": "symmetrical_triangle",
            "timeframes": ["1H", "4H"]
        }}
    ],
    "analysis": "Detailed pattern analysis"
}}
"""
        
        return self._call_ai_api(prompt, "fabio_aaa")
    
    def _call_ai_api(self, prompt: str, strategy_name: str) -> List[Dict[str, Any]]:
        """
        Call AI API (GPT or Grok) with prompt.
        
        Args:
            prompt: Analysis prompt for AI
            strategy_name: Strategy being searched for
        
        Returns:
            List of found setups
        """
        try:
            if self.api_provider == 'gpt':
                return self._call_gpt_api(prompt, strategy_name)
            else:
                return self._call_grok_api(prompt, strategy_name)
        
        except Exception as e:
            logger.warning(f"⚠️  AI API error: {e}")
            return []
    
    def _call_gpt_api(self, prompt: str, strategy_name: str) -> List[Dict[str, Any]]:
        """Call GPT-4 API."""
        if not self.gpt_api_key:
            logger.warning("⚠️  GPT API key not configured")
            return []
        
        try:
            import openai
            
            client = openai.OpenAI(api_key=self.gpt_api_key)
            
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert technical analyst. Respond only with valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # Deterministic for consistency
                timeout=30
            )
            
            response_text = response.choices[0].message.content
            data = json.loads(response_text)
            
            setups = data.get('setups_found', [])
            logger.info(f"✅ GPT found {len(setups)} {strategy_name} setups")
            
            # Cache setups
            for setup in setups:
                setup_id = f"{setup.get('symbol')}_{strategy_name}_{datetime.now().isoformat()}"
                self.found_setups[setup_id] = setup
            
            return setups
        
        except Exception as e:
            logger.warning(f"⚠️  GPT API error: {e}")
            return []
    
    def _call_grok_api(self, prompt: str, strategy_name: str) -> List[Dict[str, Any]]:
        """Call Grok-2 API."""
        if not self.grok_api_key:
            logger.warning("⚠️  Grok API key not configured")
            return []
        
        try:
            # Note: Grok API integration would go here
            # This is placeholder for Grok-2 via X.AI
            logger.info(f"🤖 Searching via Grok-2 for {strategy_name} setups...")
            
            # For now, return empty (would integrate actual Grok API)
            return []
        
        except Exception as e:
            logger.warning(f"⚠️  Grok API error: {e}")
            return []
    
    def rank_setups_by_quality(self, setups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Rank found setups by quality score (highest first).
        
        Returns:
            Sorted list by quality score
        """
        return sorted(setups, key=lambda x: x.get('quality_score', 0), reverse=True)
    
    def filter_by_minimum_quality(self, setups: List[Dict[str, Any]],
                                 min_quality: float = 70.0) -> List[Dict[str, Any]]:
        """
        Filter setups to only those meeting minimum quality threshold.
        
        Args:
            setups: List of potential setups
            min_quality: Minimum quality score (0-100)
        
        Returns:
            Filtered setups
        """
        filtered = [s for s in setups if s.get('quality_score', 0) >= min_quality]
        
        logger.info(f"📊 Filtered {len(setups)} setups → {len(filtered)} above {min_quality:.0f} quality")
        
        return filtered
    
    def print_found_setups(self, setups: List[Dict[str, Any]]):
        """Print found setups in readable format."""
        if not setups:
            logger.info("No high-quality setups found")
            return
        
        logger.info("")
        logger.info("="*80)
        logger.info("🎯 AI-FOUND HIGH-QUALITY SETUPS")
        logger.info("="*80)
        
        for i, setup in enumerate(setups, 1):
            logger.info(f"\n{i}. {setup.get('symbol', 'N/A')} - {setup.get('setup_type', 'N/A').upper()}")
            logger.info(f"   Quality Score: {setup.get('quality_score', 0):.0f}/100 ⭐")
            logger.info(f"   Entry: {setup.get('entry_price', 'N/A')} | "
                       f"SL: {setup.get('stop_loss', 'N/A')} | "
                       f"TP: {setup.get('take_profit', 'N/A')}")
            logger.info(f"   Risk/Reward: {setup.get('risk_reward', 0):.2f}:1")
            logger.info(f"   Confidence: {setup.get('confidence', 0):.0f}%")
            logger.info(f"   Catalysts: {', '.join(setup.get('catalysts', []))}")
            logger.info(f"   Rationale: {setup.get('rationale', 'N/A')}")
        
        logger.info("")
        logger.info("="*80)
        logger.info("")
