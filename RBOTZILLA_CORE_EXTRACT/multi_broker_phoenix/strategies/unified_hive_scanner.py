"""
UNIFIED HIVE-STRATEGY SCANNER
Combines technical strategy scanning with AI Hive deep analysis
to find the highest quality trades collaboratively

With API cost control to prevent budget overruns
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import asyncio

from .multi_strategy_scanner import get_scanner, StrategySignal
from .strategy_registry import get_enabled_strategies, get_strategy_config
from .hive_cost_control import get_budget_manager, get_coordinator

logger = logging.getLogger(__name__)


class HiveAgentScan:
    """Deep scan result from an AI Hive agent."""
    def __init__(self, agent_name: str, symbol: str, direction: str,
                 confidence: float, reasoning: str, recommended_strategy: str,
                 entry_price: float, stop_loss: float, take_profit: float,
                 quality_factors: Dict[str, float]):
        self.agent_name = agent_name
        self.symbol = symbol
        self.direction = direction
        self.confidence = confidence
        self.reasoning = reasoning
        self.recommended_strategy = recommended_strategy  # Which strategy fits best
        self.entry_price = entry_price
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.quality_factors = quality_factors  # Detailed quality breakdown
        self.timestamp = datetime.now()
        
        # Calculate composite quality score
        self.quality_score = self._calculate_quality()
    
    def _calculate_quality(self) -> float:
        """Calculate composite quality from all factors."""
        # Weight different quality factors
        weights = {
            'technical': 0.25,
            'fundamental': 0.20,
            'momentum': 0.20,
            'risk_reward': 0.20,
            'timing': 0.15
        }
        
        score = sum(
            self.quality_factors.get(factor, 0) * weight
            for factor, weight in weights.items()
        )
        
        return score * self.confidence
    
    def __repr__(self):
        return f"<HiveScan {self.agent_name} {self.symbol} {self.direction} quality={self.quality_score:.2f}>"


class UnifiedScanner:
    """Unified scanner combining strategy signals and Hive deep analysis."""
    
    def __init__(self, hive_connector=None):
        """
        Args:
            hive_connector: Connection to AI Hive (api_ai_hive)
        """
        self.strategy_scanner = get_scanner()
        self.hive_connector = hive_connector
        
        # Cost control and coordination
        self.budget_manager = get_budget_manager()
        self.coordinator = get_coordinator()
        
        # Hive agents for deep scanning
        self.hive_agents = {
            'oracle': 'Fundamental & Sentiment Analysis',
            'tactician': 'Technical Analysis & Chart Patterns',
            'analyst': 'Statistical & Quantitative Analysis'
        }
        
        logger.info("🌐 Unified Hive-Strategy Scanner initialized")
        logger.info(f"   Strategy scanner: {len(get_enabled_strategies())} strategies")
        logger.info(f"   Hive agents: {len(self.hive_agents)}")
        logger.info(f"   💰 API Budget: ${self.budget_manager.daily_budget_usd:.2f}/day")
        logger.info(f"   ✅ Cost control: ENABLED")
    
    async def unified_scan(self, universe: List[str], market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run unified scan - strategies + Hive agents with cost control.
        
        STRATEGY-FIRST APPROACH:
        1. Run all strategies (free, fast) - includes FABIO RSI 40 threshold
        2. Only invoke expensive AI Hive for symbols with strong strategy signals
        3. Respects API budget limits
        
        Args:
            universe: Symbols to scan
            market_data: Market data for all symbols
        
        Returns:
            Dict with strategy_signals, hive_scans, and unified_recommendations
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"🔍 UNIFIED HIVE-STRATEGY DEEP SCAN")
        logger.info(f"{'='*80}")
        logger.info(f"Universe: {len(universe)} symbols")
        logger.info(f"Scanning with {len(get_enabled_strategies())} strategies + {len(self.hive_agents)} AI agents")
        
        # PHASE 1: Run strategy scan (always, it's free and fast)
        logger.info(f"\n📈 PHASE 1: Strategy Scan (free)")
        strategy_signals = await self._run_strategy_scan(universe, market_data)
        logger.info(f"   ✅ Found {len(strategy_signals)} strategy signals")
        
        # Build efficient Hive scan plan based on strategy results
        scan_plan = self.coordinator.build_efficient_scan_plan(
            universe, 
            {'signals': [self._signal_to_dict(s) for s in strategy_signals]}
        )
        
        # PHASE 2: Selective Hive scan (only if budget allows and signals warrant it)
        hive_scans = []
        if scan_plan['hive_phase']['symbols']:
            logger.info(f"\n🧠 PHASE 2: Selective Hive Scan")
            logger.info(f"   Scanning {len(scan_plan['hive_phase']['symbols'])} high-priority symbols")
            logger.info(f"   Estimated cost: ${scan_plan['total_estimated_cost']:.2f}")
            
            hive_scans = await self._run_hive_deep_scan(
                scan_plan['hive_phase']['symbols'], 
                market_data
            )
            logger.info(f"   ✅ Found {len(hive_scans)} Hive opportunities")
        else:
            logger.info(f"\n⏭️  PHASE 2: Skipping Hive scan")
            reason = "No strategy signals" if not strategy_signals else "Budget limit"
            logger.info(f"   Reason: {reason}")
        
        logger.info(f"\n📊 SCAN RESULTS:")
        logger.info(f"   Strategy signals: {len(strategy_signals)}")
        logger.info(f"   Hive deep scans: {len(hive_scans)}")
        
        # Combine and rank
        unified_recommendations = self._unify_results(strategy_signals, hive_scans, market_data)
        
        logger.info(f"   ✅ Unified recommendations: {len(unified_recommendations)}")
        logger.info(f"{'='*80}\n")
        
        return {
            'strategy_signals': strategy_signals,
            'hive_scans': hive_scans,
            'unified_recommendations': unified_recommendations,
            'scan_timestamp': datetime.now()
        }
    
    async def _run_strategy_scan(self, universe: List[str], 
                                 market_data: Dict[str, Any]) -> List[StrategySignal]:
        """Run technical strategy scanning."""
        logger.info("📈 Running strategy scanner...")
        
        # Run in thread pool to not block
        loop = asyncio.get_event_loop()
        signals = await loop.run_in_executor(
            None,
            self.strategy_scanner.scan_all_strategies,
            universe,
            market_data
        )
        
        return signals
    
    async def _run_hive_deep_scan(self, universe: List[str],
                                  market_data: Dict[str, Any]) -> List[HiveAgentScan]:
        """Run AI Hive deep analysis on all symbols."""
        logger.info("🧠 Running Hive deep scan...")
        
        if not self.hive_connector:
            logger.warning("   ⚠️  No Hive connector - skipping Hive scan")
            return []
        
        hive_scans = []
        
        # Each agent analyzes all symbols
        for agent_name, agent_desc in self.hive_agents.items():
            logger.info(f"   🤖 {agent_name}: {agent_desc}")
            
            agent_scans = await self._agent_deep_scan(agent_name, universe, market_data)
            hive_scans.extend(agent_scans)
            
            logger.info(f"      Found {len(agent_scans)} opportunities")
        
        return hive_scans
    
    async def _agent_deep_scan(self, agent_name: str, universe: List[str],
                               market_data: Dict[str, Any]) -> List[HiveAgentScan]:
        """Single agent scans all symbols for opportunities."""
        scans = []
        
        for symbol in universe:
            if symbol not in market_data:
                continue
            
            try:
                # Ask agent to analyze this symbol deeply
                analysis = await self._query_agent_for_scan(
                    agent_name, 
                    symbol, 
                    market_data[symbol]
                )
                
                if analysis and analysis.get('has_opportunity'):
                    scan = HiveAgentScan(
                        agent_name=agent_name,
                        symbol=symbol,
                        direction=analysis['direction'],
                        confidence=analysis['confidence'],
                        reasoning=analysis['reasoning'],
                        recommended_strategy=analysis.get('recommended_strategy', 'HOLY_GRAIL'),
                        entry_price=analysis['entry_price'],
                        stop_loss=analysis['stop_loss'],
                        take_profit=analysis['take_profit'],
                        quality_factors=analysis.get('quality_factors', {})
                    )
                    scans.append(scan)
            
            except Exception as e:
                logger.debug(f"Agent {agent_name} error on {symbol}: {e}")
        
        return scans
    
    async def _query_agent_for_scan(self, agent_name: str, symbol: str,
                                    data: Dict[str, Any]) -> Optional[Dict]:
        """Query a specific Hive agent for deep analysis with cost tracking."""
        if not self.hive_connector:
            return None
        
        # Check budget before making call
        if not self.budget_manager.can_make_call('openai', symbol):
            logger.debug(f"💸 Budget limit - skipping {agent_name} for {symbol}")
            return None
        
        try:
            # Build analysis prompt for agent
            prompt = self._build_scan_prompt(agent_name, symbol, data)
            
            # Record call attempt
            self.budget_manager.record_call('openai', symbol)
            
            # Query agent
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                self.hive_connector.query_single_agent,
                agent_name,
                prompt
            )
            
            if not response:
                return None
            
            # Parse response into structured format
            analysis = self._parse_agent_response(response, symbol, data)
            return analysis
        
        except Exception as e:
            logger.debug(f"Query error for {agent_name}: {e}")
            return None
    
    def _build_scan_prompt(self, agent_name: str, symbol: str, data: Dict) -> str:
        """Build scan prompt for agent."""
        prices = data.get('prices', [])
        current_price = prices[-1] if prices else 0
        
        prompt = f"""DEEP SCAN REQUEST for {symbol}

Current Price: {current_price}
Recent Action: {prices[-10:] if len(prices) >= 10 else prices}

Analyze this instrument deeply from your expertise ({agent_name}).
Looking for HIGH QUALITY trade opportunities only.

Provide:
1. Is there a tradeable opportunity? (yes/no)
2. If yes, direction (BUY/SELL)
3. Confidence (0-1.0)
4. Entry, stop loss, take profit prices
5. Which strategy would fit best? (HOLY_GRAIL, LIQUIDITY_SWEEP, FVG_WOLF, etc)
6. Quality factors (technical, fundamental, momentum, risk_reward, timing) - each 0-1.0
7. Reasoning (2-3 sentences)

Format as JSON:
{{
    "has_opportunity": true/false,
    "direction": "BUY" or "SELL",
    "confidence": 0.75,
    "entry_price": price,
    "stop_loss": price,
    "take_profit": price,
    "recommended_strategy": "STRATEGY_NAME",
    "quality_factors": {{"technical": 0.8, "fundamental": 0.7, ...}},
    "reasoning": "explanation"
}}"""
        
        return prompt
    
    def _parse_agent_response(self, response: str, symbol: str, data: Dict) -> Optional[Dict]:
        """Parse agent response into structured format."""
        try:
            import json
            
            # Try to extract JSON from response
            if '{' in response:
                json_start = response.index('{')
                json_end = response.rindex('}') + 1
                json_str = response[json_start:json_end]
                parsed = json.loads(json_str)
                return parsed
            
            return None
        
        except Exception as e:
            logger.debug(f"Parse error: {e}")
            return None
    
    def _unify_results(self, strategy_signals: List[StrategySignal],
                      hive_scans: List[HiveAgentScan],
                      market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Combine strategy signals and Hive scans into unified recommendations.
        
        Creates a ranked list where:
        - Signals confirmed by both strategies AND Hive get highest priority
        - Pure Hive recommendations (no strategy signal) are included if high quality
        - Pure strategy signals (no Hive scan) are included with lower confidence
        """
        unified = []
        
        # Group by symbol
        strategy_by_symbol = {}
        for sig in strategy_signals:
            if sig.symbol not in strategy_by_symbol:
                strategy_by_symbol[sig.symbol] = []
            strategy_by_symbol[sig.symbol].append(sig)
        
        hive_by_symbol = {}
        for scan in hive_scans:
            if scan.symbol not in hive_by_symbol:
                hive_by_symbol[scan.symbol] = []
            hive_by_symbol[scan.symbol].append(scan)
        
        # Process each symbol
        all_symbols = set(strategy_by_symbol.keys()) | set(hive_by_symbol.keys())
        
        for symbol in all_symbols:
            strat_signals = strategy_by_symbol.get(symbol, [])
            hive_signals = hive_by_symbol.get(symbol, [])
            
            # Case 1: Both strategy and Hive agree (highest quality)
            for strat in strat_signals:
                for hive in hive_signals:
                    if strat.direction == hive.direction:
                        # CONSENSUS TRADE - both agree!
                        unified.append({
                            'type': 'CONSENSUS',
                            'symbol': symbol,
                            'direction': strat.direction,
                            'strategy_code': strat.strategy_code,
                            'confidence': (strat.confidence + hive.confidence) / 2,
                            'quality_score': (strat.quality_score + hive.quality_score) / 2 * 1.5,  # Bonus for consensus
                            'entry_price': (strat.entry_price + hive.entry_price) / 2,
                            'stop_loss': max(strat.stop_loss, hive.stop_loss) if strat.direction == 'BUY' else min(strat.stop_loss, hive.stop_loss),
                            'take_profit': (strat.take_profit + hive.take_profit) / 2,
                            'strategy_signal': strat,
                            'hive_scan': hive,
                            'reasoning': f"CONSENSUS: {strat.strategy_code} + {hive.agent_name} agree. {hive.reasoning}"
                        })
            
            # Case 2: Hive-only recommendations (high quality from AI)
            for hive in hive_signals:
                # Only if no matching strategy signal
                if not any(s.direction == hive.direction for s in strat_signals):
                    if hive.quality_score > 0.70:  # High quality threshold
                        unified.append({
                            'type': 'HIVE_DISCOVERY',
                            'symbol': symbol,
                            'direction': hive.direction,
                            'strategy_code': hive.recommended_strategy,
                            'confidence': hive.confidence * 0.9,  # Slight penalty for no strategy confirmation
                            'quality_score': hive.quality_score,
                            'entry_price': hive.entry_price,
                            'stop_loss': hive.stop_loss,
                            'take_profit': hive.take_profit,
                            'hive_scan': hive,
                            'reasoning': f"HIVE DISCOVERY by {hive.agent_name}: {hive.reasoning}"
                        })
            
            # Case 3: Strategy-only signals (no Hive scan found this)
            for strat in strat_signals:
                if not any(h.direction == strat.direction for h in hive_signals):
                    unified.append({
                        'type': 'STRATEGY_ONLY',
                        'symbol': symbol,
                        'direction': strat.direction,
                        'strategy_code': strat.strategy_code,
                        'confidence': strat.confidence * 0.85,  # Penalty for no Hive confirmation
                        'quality_score': strat.quality_score * 0.9,
                        'entry_price': strat.entry_price,
                        'stop_loss': strat.stop_loss,
                        'take_profit': strat.take_profit,
                        'strategy_signal': strat,
                        'reasoning': f"Strategy signal: {strat.reasoning}"
                    })
        
        # Sort by quality score
        unified.sort(key=lambda x: x['quality_score'], reverse=True)
        
        # Log top recommendations
        logger.info(f"\n🎯 TOP UNIFIED RECOMMENDATIONS:")
        for i, rec in enumerate(unified[:10], 1):
            logger.info(f"   {i}. [{rec['type']}] {rec['symbol']} {rec['direction']} "
                       f"({rec['strategy_code']}) - Quality: {rec['quality_score']:.2f}")
        
        return unified
    
    def _signal_to_dict(self, signal: StrategySignal) -> Dict[str, Any]:
        """Convert StrategySignal to dict for coordinator."""
        return {
            'symbol': signal.symbol,
            'direction': signal.direction,
            'confidence': signal.confidence,
            'quality_score': signal.quality_score,
            'strategy_code': signal.strategy_code
        }


# Global unified scanner
_unified_scanner = None

def get_unified_scanner(hive_connector=None) -> UnifiedScanner:
    """Get or create global unified scanner."""
    global _unified_scanner
    if _unified_scanner is None:
        _unified_scanner = UnifiedScanner(hive_connector=hive_connector)
    return _unified_scanner
