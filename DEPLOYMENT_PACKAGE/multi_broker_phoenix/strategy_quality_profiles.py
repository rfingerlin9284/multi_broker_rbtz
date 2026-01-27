"""
STRATEGY QUALITY PROFILES - DETAILED INDICATORS & CATALYSTS
Each strategy has specific entry signals, catalyst requirements, and quality scoring
AI (GPT/Grok) searches for these specific setups, not generic scalping
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

@dataclass
class IndicatorSignal:
    """Single indicator signal requirement."""
    name: str
    threshold: float
    operator: str  # '>', '<', '==', '>=', '<='
    weight: float  # 0.0-1.0 importance
    description: str

@dataclass
class CatalystRequirement:
    """Market catalyst that must be present."""
    name: str
    description: str
    detection_method: str
    required: bool  # True = must be present for trade

@dataclass
class StrategyProfile:
    """Complete strategy definition with all requirements."""
    name: str
    purpose: str
    timeframes: List[str]  # ['1H', '4H', '1D'] etc
    indicators: List[IndicatorSignal]
    catalysts: List[CatalystRequirement]
    min_quality_score: float  # 0-100, must exceed for trade
    risk_reward_ratio: float  # Minimum R:R required
    max_holding_hours: int
    position_sizing_rule: str

class TrapReversalStrategy(StrategyProfile):
    """
    TRAP REVERSAL STRATEGY
    Catches liquidity traps and institutional reversals
    NOT scalping - requires reversal confirmation
    """
    
    def __init__(self):
        self.name = "Trap Reversal"
        self.purpose = "Detect liquidity traps and institutional reversals"
        self.timeframes = ['4H', '1D']  # Not fast - wait for confirmation
        
        self.indicators = [
            IndicatorSignal(
                name="Support/Resistance Break",
                threshold=0.5,  # % breach of level
                operator=">=",
                weight=0.25,
                description="Price breaks clear S/R level by 0.5%+ with volume"
            ),
            IndicatorSignal(
                name="False Break Confirmation",
                threshold=2.0,  # % bounce back
                operator=">=",
                weight=0.30,
                description="Price bounces back 2%+ from break (trap signal)"
            ),
            IndicatorSignal(
                name="Volume Surge",
                threshold=200,  # % vs average
                operator=">",
                weight=0.20,
                description="Volume spike 200%+ above 20-day average at break"
            ),
            IndicatorSignal(
                name="RSI Divergence",
                threshold=30,  # RSI < 30 on higher close (oversold divergence)
                operator="<",
                weight=0.15,
                description="RSI shows divergence with price (lower low on higher close)"
            ),
            IndicatorSignal(
                name="Volatility Contraction",
                threshold=0.7,  # ATR ratio
                operator="<",
                weight=0.10,
                description="ATR is 30% below 50-day average (before breakout)"
            )
        ]
        
        self.catalysts = [
            CatalystRequirement(
                name="Institutional Volume",
                description="Large block trade at S/R level creating trap",
                detection_method="Volume profile + footprint analysis",
                required=True
            ),
            CatalystRequirement(
                name="Market Structure Break",
                description="Clear break of recent swing high/low",
                detection_method="Higher timeframe trendline",
                required=True
            ),
            CatalystRequirement(
                name="Liquidity Cluster",
                description="Stop cluster or liquidity zone identified",
                detection_method="Order flow / depth analysis",
                required=False
            )
        ]
        
        self.min_quality_score = 75.0
        self.risk_reward_ratio = 1.5
        self.max_holding_hours = 8
        self.position_sizing_rule = "Based on ATR distance to stops (1% risk per trade)"

class InstitutionalSDStrategy(StrategyProfile):
    """
    INSTITUTIONAL SMART DISTRIBUTION STRATEGY
    Identifies institutional entries based on volatility and structure
    Follows smart money patterns
    """
    
    def __init__(self):
        self.name = "Institutional SD"
        self.purpose = "Follow smart money volatility distribution patterns"
        self.timeframes = ['1H', '4H']
        
        self.indicators = [
            IndicatorSignal(
                name="Bollinger Band Width Expansion",
                threshold=1.5,  # Ratio of current to 50-day average
                operator=">",
                weight=0.25,
                description="BB width 50%+ above normal (institutional accumulation)"
            ),
            IndicatorSignal(
                name="ATR Breakout Above 50MA",
                threshold=1.3,  # Ratio
                operator=">",
                weight=0.25,
                description="Current ATR 30% above 50-day MA (volatility spike)"
            ),
            IndicatorSignal(
                name="Volume Profile Balance",
                threshold=0.6,  # Buy/sell ratio
                operator=">",
                weight=0.20,
                description="Buy volume > 60% of total (institutional buying pressure)"
            ),
            IndicatorSignal(
                name="Moving Average Alignment",
                threshold=10,  # SMA50 > EMA100 by this %
                operator=">",
                weight=0.15,
                description="50MA > 200MA (uptrend) or vice versa"
            ),
            IndicatorSignal(
                name="Stochastic Alignment",
                threshold=70,  # Stoch K > 70
                operator=">",
                weight=0.15,
                description="Stochastic shows momentum continuation, not overbought"
            )
        ]
        
        self.catalysts = [
            CatalystRequirement(
                name="Institutional Accumulation",
                description="Large orders appearing at key levels",
                detection_method="Order book asymmetry + large fills",
                required=True
            ),
            CatalystRequirement(
                name="Volatility Expansion",
                description="Sudden increase in realized volatility",
                detection_method="ATR expansion + historical vol comparison",
                required=True
            ),
            CatalystRequirement(
                name="Macro Catalyst",
                description="Economic data, earnings, or geopolitical event",
                detection_method="Economic calendar + news API",
                required=False
            )
        ]
        
        self.min_quality_score = 70.0
        self.risk_reward_ratio = 2.0
        self.max_holding_hours = 6
        self.position_sizing_rule = "Based on ATR volatility, larger size in lower vol"

class HolyGrailStrategy(StrategyProfile):
    """
    HOLY GRAIL STRATEGY
    Multi-timeframe confirmation with trend alignment
    Requires 3x confirmation before entry
    """
    
    def __init__(self):
        self.name = "Holy Grail"
        self.purpose = "Multi-timeframe trend confirmation"
        self.timeframes = ['1H', '4H', '1D']
        
        self.indicators = [
            IndicatorSignal(
                name="Daily Trend Alignment",
                threshold=0,  # -1=down, 0=flat, 1=up (MUST be aligned)
                operator="!=",
                weight=0.30,
                description="1D timeframe shows clear trend (not range-bound)"
            ),
            IndicatorSignal(
                name="4H Confluence",
                threshold=0,
                operator="!=",
                weight=0.25,
                description="4H trend aligned with 1D, with 4H pullback setup"
            ),
            IndicatorSignal(
                name="1H Entry Trigger",
                threshold=0,
                operator="!=",
                weight=0.20,
                description="1H shows EMA cross or price touches 20MA support"
            ),
            IndicatorSignal(
                name="Volume Confirmation",
                threshold=100,  # % vs 20-day average
                operator=">",
                weight=0.15,
                description="Entry bar has volume > 100% of average (conviction)"
            ),
            IndicatorSignal(
                name="MACD Alignment",
                threshold=0,
                operator=">",
                weight=0.10,
                description="MACD histogram positive across timeframes"
            )
        ]
        
        self.catalysts = [
            CatalystRequirement(
                name="Multiple Timeframe Alignment",
                description="All 3 timeframes (1H, 4H, 1D) aligned same direction",
                detection_method="Technical analysis across all timeframes",
                required=True
            ),
            CatalystRequirement(
                name="Pullback to MA",
                description="Price pulls back to key MA before next leg",
                detection_method="Distance from 20/50/200 MA",
                required=True
            ),
            CatalystRequirement(
                name="Support/Resistance Confluence",
                description="Entry near multi-timeframe support/resistance",
                detection_method="Level analysis across timeframes",
                required=True
            )
        ]
        
        self.min_quality_score = 80.0
        self.risk_reward_ratio = 2.5
        self.max_holding_hours = 8
        self.position_sizing_rule = "Conservative due to confirmation layers (0.5-1% risk)"

class EMAScalperStrategy(StrategyProfile):
    """
    EMA SCALPER STRATEGY
    Fast EMA crosses on 5M/15M
    Quick hits, high win rate, small wins
    NOT spray-and-pray - requires specific confluence
    """
    
    def __init__(self):
        self.name = "EMA Scalper"
        self.purpose = "Fast EMA cross scalping with confluence"
        self.timeframes = ['5M', '15M']
        
        self.indicators = [
            IndicatorSignal(
                name="EMA 9/21 Cross",
                threshold=0,
                operator="!=",
                weight=0.35,
                description="EMA 9 crosses above/below EMA 21"
            ),
            IndicatorSignal(
                name="RSI Alignment",
                threshold=50,
                operator=">",
                weight=0.20,
                description="RSI > 50 for long, < 50 for short (momentum confirms direction)"
            ),
            IndicatorSignal(
                name="VWAP Proximity",
                threshold=0.5,  # % distance from VWAP
                operator="<",
                weight=0.20,
                description="Price within 0.5% of VWAP (institutional reference)"
            ),
            IndicatorSignal(
                name="Volatility Filter",
                threshold=0.8,  # ATR ratio
                operator=">",
                weight=0.15,
                description="Current ATR > 80% of hourly average (enough movement)"
            ),
            IndicatorSignal(
                name="Volume Burst",
                threshold=150,  # % vs 5min average
                operator=">",
                weight=0.10,
                description="Entry bar volume > 150% of 5-min average"
            )
        ]
        
        self.catalysts = [
            CatalystRequirement(
                name="EMA Cross",
                description="Clean EMA 9/21 cross signal",
                detection_method="Technical indicator",
                required=True
            ),
            CatalystRequirement(
                name="Hourly Trend Support",
                description="4-hour trend supports scalp direction",
                detection_method="Check 4H trend before taking scalp",
                required=True
            ),
            CatalystRequirement(
                name="Liquidity Window",
                description="Entry during high-liquidity market hours",
                detection_method="Market hour check (9-16 EST for stocks, 24h for crypto)",
                required=False
            )
        ]
        
        self.min_quality_score = 65.0  # Lower for scalps (higher frequency)
        self.risk_reward_ratio = 1.0
        self.max_holding_hours = 1  # Scalps held under 1 hour usually
        self.position_sizing_rule = "Larger size (max 2% risk) due to tight stops"

class FabioAAAStrategy(StrategyProfile):
    """
    FABIO AAA STRATEGY
    Advanced pattern recognition + precision entries
    Requires specific chart pattern + supply/demand confluence
    """
    
    def __init__(self):
        self.name = "Fabio AAA"
        self.purpose = "Advanced chart patterns + supply/demand precision"
        self.timeframes = ['1H', '4H']
        
        self.indicators = [
            IndicatorSignal(
                name="Chart Pattern Recognition",
                threshold=0.8,  # Pattern confidence score
                operator=">=",
                weight=0.30,
                description="Identified pattern (flag, triangle, wedge) with 80%+ confidence"
            ),
            IndicatorSignal(
                name="Supply/Demand Imbalance",
                threshold=2.0,  # Ratio of unfilled orders
                operator=">",
                weight=0.25,
                description="Significant supply/demand imbalance at key level"
            ),
            IndicatorSignal(
                name="Order Block Identification",
                threshold=0,
                operator="!=",
                weight=0.20,
                description="Price approaching untested order block (high probability"
            ),
            IndicatorSignal(
                name="Fair Value Gap",
                threshold=0.3,  # % gap size
                operator=">=",
                weight=0.15,
                description="FVG present and price approaching gap for fill"
            ),
            IndicatorSignal(
                name="Candle Precision",
                threshold=0.85,  # Candle pattern quality
                operator=">=",
                weight=0.10,
                description="Entry candle shows specific pattern (pin bar, engulf, etc)"
            )
        ]
        
        self.catalysts = [
            CatalystRequirement(
                name="Advanced Pattern Formation",
                description="Specific chart pattern (not generic reversal)",
                detection_method="Pattern recognition algorithm",
                required=True
            ),
            CatalystRequirement(
                name="Institutional Order Block",
                description="Entry at untested order block with depth",
                detection_method="Order flow + time/price analysis",
                required=True
            ),
            CatalystRequirement(
                name="Multiple Timeframe Confluence",
                description="Pattern valid on multiple timeframes",
                detection_method="Cross-timeframe pattern confirmation",
                required=True
            )
        ]
        
        self.min_quality_score = 78.0
        self.risk_reward_ratio = 3.0
        self.max_holding_hours = 8
        self.position_sizing_rule = "Based on pattern confidence + risk/reward (conservative)"

class StrategyQualityScorer:
    """
    Scores setups against strategy requirements.
    Only high-quality setups get executed.
    """
    
    def __init__(self):
        self.strategies = {
            'trap_reversal': TrapReversalStrategy(),
            'institutional_sd': InstitutionalSDStrategy(),
            'holy_grail': HolyGrailStrategy(),
            'ema_scalper': EMAScalperStrategy(),
            'fabio_aaa': FabioAAAStrategy()
        }
        
        logger.info("✅ Strategy Quality Scorer initialized with 5 detailed profiles")
    
    def score_setup(self, strategy_name: str, indicators_data: Dict[str, float],
                   catalysts_present: Dict[str, bool]) -> Dict[str, Any]:
        """
        Score a potential setup against strategy requirements.
        
        Args:
            strategy_name: Strategy to evaluate
            indicators_data: Dict of indicator values
            catalysts_present: Dict of catalyst confirmations
        
        Returns:
            Detailed score with breakdown
        """
        if strategy_name not in self.strategies:
            return {'quality_score': 0, 'pass': False, 'error': f'Unknown strategy: {strategy_name}'}
        
        strategy = self.strategies[strategy_name]
        
        # Score indicators
        indicator_score = 0.0
        indicator_breakdown = {}
        
        for indicator in strategy.indicators:
            # Check if indicator meets threshold
            value = indicators_data.get(indicator.name, 0)
            meets_criteria = False
            
            if indicator.operator == '>':
                meets_criteria = value > indicator.threshold
            elif indicator.operator == '>=':
                meets_criteria = value >= indicator.threshold
            elif indicator.operator == '<':
                meets_criteria = value < indicator.threshold
            elif indicator.operator == '<=':
                meets_criteria = value <= indicator.threshold
            elif indicator.operator == '!=':
                meets_criteria = value != indicator.threshold
            elif indicator.operator == '==':
                meets_criteria = value == indicator.threshold
            
            weighted_score = 100.0 * indicator.weight if meets_criteria else 0.0
            indicator_score += weighted_score
            
            indicator_breakdown[indicator.name] = {
                'requirement': indicator.description,
                'value': value,
                'threshold': indicator.threshold,
                'meets': meets_criteria,
                'contribution': weighted_score
            }
        
        # Check catalysts
        catalyst_score = 0.0
        catalyst_breakdown = {}
        required_catalysts_met = True
        
        for catalyst in strategy.catalysts:
            present = catalysts_present.get(catalyst.name, False)
            catalyst_breakdown[catalyst.name] = {
                'description': catalyst.description,
                'required': catalyst.required,
                'present': present,
                'status': '✅' if present else ('❌ REQUIRED' if catalyst.required else '⚠️  Optional')
            }
            
            if catalyst.required and not present:
                required_catalysts_met = False
        
        # Calculate final score
        quality_score = (indicator_score + (100.0 if required_catalysts_met else 0.0)) / 2.0
        passes_quality = quality_score >= strategy.min_quality_score and required_catalysts_met
        
        return {
            'strategy': strategy_name,
            'quality_score': quality_score,
            'passes': passes_quality,
            'passes_quality_threshold': quality_score >= strategy.min_quality_score,
            'catalysts_met': required_catalysts_met,
            'min_required': strategy.min_quality_score,
            'indicators': indicator_breakdown,
            'catalysts': catalyst_breakdown,
            'reason': self._get_fail_reason(quality_score, strategy.min_quality_score, required_catalysts_met)
        }
    
    def _get_fail_reason(self, score: float, min_required: float, catalysts_met: bool) -> str:
        """Get reason why setup didn't pass."""
        if not catalysts_met:
            return "❌ Required catalyst missing"
        if score < min_required:
            return f"❌ Quality score {score:.1f} < required {min_required:.0f}"
        return "✅ PASSES - High quality setup"
    
    def get_strategy_profile(self, strategy_name: str) -> Optional[StrategyProfile]:
        """Get full strategy profile."""
        return self.strategies.get(strategy_name)
    
    def print_strategy_details(self, strategy_name: str):
        """Print full strategy details."""
        strategy = self.strategies.get(strategy_name)
        if not strategy:
            logger.warning(f"Unknown strategy: {strategy_name}")
            return
        
        logger.info("")
        logger.info("="*80)
        logger.info(f"📋 STRATEGY: {strategy.name.upper()}")
        logger.info("="*80)
        logger.info(f"Purpose: {strategy.purpose}")
        logger.info(f"Timeframes: {', '.join(strategy.timeframes)}")
        logger.info(f"Min Quality Score: {strategy.min_quality_score:.0f}/100")
        logger.info(f"Risk/Reward Ratio: {strategy.risk_reward_ratio}:1")
        logger.info(f"Max Hold Time: {strategy.max_holding_hours}h")
        logger.info("")
        
        logger.info("REQUIRED INDICATORS:")
        for ind in strategy.indicators:
            logger.info(f"  • {ind.name} ({ind.weight*100:.0f}% weight)")
            logger.info(f"    {ind.description}")
            logger.info(f"    Threshold: {ind.operator} {ind.threshold}")
        
        logger.info("")
        logger.info("CATALYSTS (MUST BE PRESENT):")
        for cat in strategy.catalysts:
            required = "🔴 REQUIRED" if cat.required else "🟡 OPTIONAL"
            logger.info(f"  {required}: {cat.name}")
            logger.info(f"    {cat.description}")
        
        logger.info("")
        logger.info(f"POSITION SIZING: {strategy.position_sizing_rule}")
        logger.info("="*80)
        logger.info("")
