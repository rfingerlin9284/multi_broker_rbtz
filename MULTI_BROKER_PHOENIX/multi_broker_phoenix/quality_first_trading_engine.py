"""
QUALITY-FIRST TRADING ENGINE
Integrates strategy profiles, AI setup hunting, and quality scoring
Only executes HIGH-QUALITY setups, not generic scalping
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from strategy_quality_profiles import StrategyQualityScorer, Strategy
from ai_setup_hunter import AISetupHunter
from strategy_diversification_orchestrator import get_orchestrator

logger = logging.getLogger(__name__)

class QualityFirstTradingEngine:
    """
    Only executes setups that meet strategy-specific quality criteria.
    AI actively hunts for high-probability setups matching profiles.
    No generic scalping - every trade must justify itself.
    """
    
    def __init__(self, min_quality_score: float = 70.0):
        """
        Initialize quality-first engine.
        
        Args:
            min_quality_score: Minimum quality threshold (0-100)
        """
        self.min_quality_score = min_quality_score
        self.quality_scorer = StrategyQualityScorer()
        self.ai_hunter = AISetupHunter(api_provider='gpt')
        self.orchestrator = get_orchestrator()
        
        self.executed_trades = []
        self.rejected_setups = []
        
        logger.info(f"✅ Quality-First Trading Engine initialized")
        logger.info(f"   Min quality threshold: {min_quality_score}/100")
        logger.info(f"   AI setup hunting: ACTIVE")
        logger.info(f"   Strategy validation: ENABLED")
    
    def evaluate_and_execute_setup(self, setup: Dict[str, Any], 
                                   broker_connector: Any) -> bool:
        """
        Evaluate setup against strategy criteria, then execute if qualified.
        
        Args:
            setup: Potential trade setup from AI or technical analysis
            broker_connector: Broker connector (Coinbase/OANDA/IBKR)
        
        Returns:
            True if executed, False if rejected
        """
        
        strategy_name = setup.get('strategy', 'unknown')
        symbol = setup.get('symbol', 'unknown')
        
        # Get strategy profile
        strategy_profile = self.quality_scorer.get_strategy_profile(strategy_name)
        if not strategy_profile:
            logger.warning(f"❌ Unknown strategy: {strategy_name}")
            self._record_rejection(setup, "Unknown strategy")
            return False
        
        # Score the setup
        indicators_data = setup.get('indicators', {})
        catalysts_data = setup.get('catalysts', {})
        
        score_result = self.quality_scorer.score_setup(
            strategy_name, 
            indicators_data, 
            catalysts_data
        )
        
        quality_score = score_result.get('quality_score', 0)
        passes = score_result.get('passes', False)
        
        # Log evaluation
        logger.info("")
        logger.info("="*80)
        logger.info(f"🔍 EVALUATING SETUP: {symbol} - {strategy_name.upper()}")
        logger.info("="*80)
        logger.info(f"Quality Score: {quality_score:.1f}/100 (Min required: {strategy_profile.min_quality_score:.0f})")
        logger.info(f"Risk/Reward: {setup.get('risk_reward', 0):.2f}:1 (Min required: {strategy_profile.risk_reward_ratio}:1)")
        logger.info("")
        
        # Check quality threshold
        if quality_score < self.min_quality_score:
            logger.warning(f"❌ REJECTED: Quality score too low ({quality_score:.1f} < {self.min_quality_score:.0f})")
            self._print_rejection_details(score_result)
            self._record_rejection(setup, f"Quality score {quality_score:.1f} below {self.min_quality_score:.0f}")
            return False
        
        # Check strategy minimum
        if quality_score < strategy_profile.min_quality_score:
            logger.warning(f"❌ REJECTED: Below strategy minimum ({quality_score:.1f} < {strategy_profile.min_quality_score:.0f})")
            self._print_rejection_details(score_result)
            self._record_rejection(setup, f"Below {strategy_name} minimum ({strategy_profile.min_quality_score:.0f})")
            return False
        
        # Check required catalysts
        if not score_result.get('catalysts_met', False):
            logger.warning(f"❌ REJECTED: Required catalysts missing")
            self._print_rejection_details(score_result)
            self._record_rejection(setup, "Required catalysts not present")
            return False
        
        # Check risk/reward
        if setup.get('risk_reward', 0) < strategy_profile.risk_reward_ratio:
            logger.warning(f"❌ REJECTED: R:R {setup.get('risk_reward', 0):.2f} < {strategy_profile.risk_reward_ratio:.1f}")
            self._record_rejection(setup, f"R:R below minimum")
            return False
        
        # ✅ ALL CHECKS PASSED - EXECUTE
        logger.info("")
        logger.info("✅ ALL QUALITY CHECKS PASSED - EXECUTING TRADE")
        logger.info("")
        
        # Get position allocation
        broker_name = setup.get('broker', 'unknown')
        allocation = self.orchestrator.allocate_next_position(broker_name)
        
        if not allocation:
            logger.warning(f"⚠️  Position allocation failed (limit reached?)")
            self._record_rejection(setup, "Position limit reached")
            return False
        
        # Execute trade
        try:
            order_result = broker_connector.place_order(
                symbol=symbol,
                side=setup.get('side', 'BUY'),
                size=setup.get('size', 0),
                entry_price=setup.get('entry_price', 0),
                stop_loss=setup.get('stop_loss'),
                take_profit=setup.get('take_profit'),
                strategy=strategy_name
            )
            
            if order_result.get('success'):
                logger.info(f"✅ ORDER EXECUTED: {order_result.get('order_id', 'N/A')}")
                
                # Record execution
                execution_record = {
                    'timestamp': datetime.now().isoformat(),
                    'symbol': symbol,
                    'strategy': strategy_name,
                    'broker': broker_name,
                    'entry_price': setup.get('entry_price'),
                    'stop_loss': setup.get('stop_loss'),
                    'take_profit': setup.get('take_profit'),
                    'quality_score': quality_score,
                    'risk_reward': setup.get('risk_reward'),
                    'order_id': order_result.get('order_id'),
                    'confidence': setup.get('confidence', 0)
                }
                
                self.executed_trades.append(execution_record)
                logger.info(f"📊 Trade recorded for position management")
                
                return True
            else:
                logger.error(f"❌ Order failed: {order_result.get('error', 'Unknown error')}")
                self._record_rejection(setup, f"Order execution failed: {order_result.get('error')}")
                return False
        
        except Exception as e:
            logger.error(f"❌ Execution error: {e}")
            self._record_rejection(setup, f"Exception: {str(e)}")
            return False
    
    def search_all_strategies_active(self, market_data: Dict[str, Any],
                                     symbols: List[str]) -> List[Dict[str, Any]]:
        """
        Actively search for setups across all 5 strategies.
        
        Args:
            market_data: Current market data snapshot
            symbols: Symbols to search
        
        Returns:
            All found setups ranked by quality
        """
        all_setups = []
        
        logger.info("")
        logger.info("="*80)
        logger.info("🤖 AI ACTIVELY SEARCHING FOR HIGH-QUALITY SETUPS")
        logger.info("="*80)
        logger.info(f"Scanning {len(symbols)} symbols across 5 strategies...")
        logger.info("")
        
        # Search each strategy
        strategies_to_search = [
            ('trap_reversal', self.ai_hunter.search_for_trap_reversals),
            ('institutional_sd', self.ai_hunter.search_for_institutional_sd),
            ('holy_grail', self.ai_hunter.search_for_holy_grail),
            ('ema_scalper', self.ai_hunter.search_for_ema_scalps),
            ('fabio_aaa', self.ai_hunter.search_for_fabio_patterns)
        ]
        
        for strategy_name, search_function in strategies_to_search:
            try:
                logger.info(f"🔍 Searching for {strategy_name}...")
                setups = search_function(market_data, symbols)
                
                if setups:
                    # Filter by strategy minimum
                    strategy_profile = self.quality_scorer.get_strategy_profile(strategy_name)
                    min_quality = strategy_profile.min_quality_score if strategy_profile else 70
                    
                    filtered = self.ai_hunter.filter_by_minimum_quality(setups, min_quality)
                    
                    logger.info(f"   Found {len(filtered)} qualified {strategy_name} setups")
                    all_setups.extend(filtered)
                else:
                    logger.info(f"   No setups found")
            
            except Exception as e:
                logger.warning(f"⚠️  Error searching {strategy_name}: {e}")
        
        # Rank by quality
        ranked = self.ai_hunter.rank_setups_by_quality(all_setups)
        
        logger.info("")
        logger.info(f"✅ Search complete: {len(ranked)} high-quality setups found")
        logger.info("")
        
        return ranked
    
    def _print_rejection_details(self, score_result: Dict[str, Any]):
        """Print detailed rejection analysis."""
        logger.info("REJECTION ANALYSIS:")
        logger.info("")
        
        # Indicators
        logger.info("Indicators breakdown:")
        indicators = score_result.get('indicators', {})
        for ind_name, ind_data in indicators.items():
            status = "✅" if ind_data.get('meets') else "❌"
            logger.info(f"  {status} {ind_name}")
            logger.info(f"     Value: {ind_data.get('value')} "
                       f"({ind_data.get('operator')} {ind_data.get('threshold')})")
            logger.info(f"     Contribution: {ind_data.get('contribution'):.1f}%")
        
        logger.info("")
        
        # Catalysts
        logger.info("Catalysts status:")
        catalysts = score_result.get('catalysts', {})
        for cat_name, cat_data in catalysts.items():
            status = cat_data.get('status')
            logger.info(f"  {status} {cat_name}")
        
        logger.info("")
        logger.info(f"Reason: {score_result.get('reason', 'Unknown')}")
    
    def _record_rejection(self, setup: Dict[str, Any], reason: str):
        """Record rejected setup for analysis."""
        self.rejected_setups.append({
            'timestamp': datetime.now().isoformat(),
            'symbol': setup.get('symbol'),
            'strategy': setup.get('strategy'),
            'quality_score': setup.get('quality_score', 0),
            'reason': reason
        })
    
    def print_execution_summary(self):
        """Print summary of executed trades."""
        logger.info("")
        logger.info("="*80)
        logger.info("📈 EXECUTION SUMMARY")
        logger.info("="*80)
        logger.info(f"Executed Trades: {len(self.executed_trades)}")
        logger.info(f"Rejected Setups: {len(self.rejected_setups)}")
        logger.info("")
        
        if self.executed_trades:
            logger.info("EXECUTED TRADES:")
            for i, trade in enumerate(self.executed_trades, 1):
                logger.info(f"\n{i}. {trade['symbol']} - {trade['strategy'].upper()}")
                logger.info(f"   Entry: {trade['entry_price']} | SL: {trade['stop_loss']} | TP: {trade['take_profit']}")
                logger.info(f"   Quality: {trade['quality_score']:.0f}/100 | Confidence: {trade['confidence']:.0f}%")
                logger.info(f"   R:R: {trade['risk_reward']:.2f}:1")
        
        logger.info("")
        logger.info("="*80)
        logger.info("")
    
    def get_quality_report(self) -> Dict[str, Any]:
        """Get detailed quality metrics report."""
        return {
            'total_evaluated': len(self.executed_trades) + len(self.rejected_setups),
            'executed': len(self.executed_trades),
            'rejected': len(self.rejected_setups),
            'execution_rate': f"{(len(self.executed_trades) / max(1, len(self.executed_trades) + len(self.rejected_setups)) * 100):.1f}%",
            'avg_quality_executed': sum(t['quality_score'] for t in self.executed_trades) / max(1, len(self.executed_trades)),
            'avg_risk_reward': sum(t['risk_reward'] for t in self.executed_trades) / max(1, len(self.executed_trades)),
            'executed_trades': self.executed_trades,
            'rejected_setups': self.rejected_setups
        }
