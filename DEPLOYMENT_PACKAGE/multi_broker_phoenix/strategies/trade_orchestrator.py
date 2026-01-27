"""
DIVERSE TRADE ORCHESTRATOR
Executes diverse high-quality trades from multiple strategies simultaneously
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from .multi_strategy_scanner import get_scanner, StrategySignal
from .strategy_registry import get_strategy_config

logger = logging.getLogger(__name__)


class TradeOrchestrator:
    """Orchestrates diverse trade execution across multiple strategies."""
    
    def __init__(self, max_concurrent_trades: int = 5, 
                 max_trades_per_strategy: int = 2,
                 max_exposure_per_symbol: float = 0.20):
        """
        Args:
            max_concurrent_trades: Max total open positions
            max_trades_per_strategy: Max concurrent trades per strategy
            max_exposure_per_symbol: Max portfolio % per symbol
        """
        self.max_concurrent_trades = max_concurrent_trades
        self.max_trades_per_strategy = max_trades_per_strategy
        self.max_exposure_per_symbol = max_exposure_per_symbol
        
        self.scanner = get_scanner(max_concurrent=max_concurrent_trades)
        self.active_positions = []
        
        logger.info("🎯 Trade Orchestrator initialized")
        logger.info(f"   Max concurrent: {max_concurrent_trades}")
        logger.info(f"   Max per strategy: {max_trades_per_strategy}")
        logger.info(f"   Max exposure per symbol: {max_exposure_per_symbol:.0%}")
    
    def scan_and_rank(self, universe: List[str], market_data: Dict[str, Any]) -> List[StrategySignal]:
        """Scan all strategies and rank opportunities.
        
        Args:
            universe: List of symbols to scan
            market_data: Market data for all symbols
        
        Returns:
            Ranked list of trade signals ready for execution
        """
        logger.info(f"\n{'='*70}")
        logger.info(f"🔍 MULTI-STRATEGY SCAN")
        logger.info(f"{'='*70}")
        logger.info(f"Universe: {len(universe)} symbols")
        logger.info(f"Active positions: {len(self.active_positions)}")
        
        # 1. Scan ALL enabled strategies
        all_signals = self.scanner.scan_all_strategies(universe, market_data)
        
        if not all_signals:
            logger.info("❌ No signals found from any strategy")
            return []
        
        # 2. Rank and filter for conflicts
        ranked_signals = self.scanner.rank_and_filter(all_signals, self.active_positions)
        
        # 3. Apply orchestrator-level filters
        final_signals = self._apply_orchestrator_filters(ranked_signals)
        
        logger.info(f"\n✅ Final selection: {len(final_signals)} trades ready")
        logger.info(f"{'='*70}\n")
        
        return final_signals
    
    def _apply_orchestrator_filters(self, signals: List[StrategySignal]) -> List[StrategySignal]:
        """Apply additional orchestrator-level filters."""
        filtered = []
        
        # Track strategy usage
        strategy_counts = {}
        for pos in self.active_positions:
            strat = pos.get('strategy_code')
            strategy_counts[strat] = strategy_counts.get(strat, 0) + 1
        
        # Track symbol exposure
        symbol_exposure = {}
        for pos in self.active_positions:
            symbol = pos.get('symbol')
            exposure = pos.get('exposure_pct', 0)
            symbol_exposure[symbol] = symbol_exposure.get(symbol, 0) + exposure
        
        for sig in signals:
            # Check strategy limit
            if strategy_counts.get(sig.strategy_code, 0) >= self.max_trades_per_strategy:
                logger.warning(f"   ⚠️  {sig.strategy_code} at max trades ({self.max_trades_per_strategy})")
                continue
            
            # Check symbol exposure (estimate new exposure)
            estimated_exposure = 0.10  # Assume 10% per trade
            current_exposure = symbol_exposure.get(sig.symbol, 0)
            
            if current_exposure + estimated_exposure > self.max_exposure_per_symbol:
                logger.warning(f"   ⚠️  {sig.symbol} at max exposure ({current_exposure:.0%})")
                continue
            
            # Passed all filters
            filtered.append(sig)
            strategy_counts[sig.strategy_code] = strategy_counts.get(sig.strategy_code, 0) + 1
            symbol_exposure[sig.symbol] = current_exposure + estimated_exposure
        
        return filtered
    
    def execute_signals(self, signals: List[StrategySignal], 
                       broker_connector, hive_gate) -> List[Dict]:
        """Execute validated trade signals.
        
        Args:
            signals: Signals to execute
            broker_connector: Broker connection for order placement
            hive_gate: AI Hive for final validation
        
        Returns:
            List of executed trade results
        """
        executed_trades = []
        
        for sig in signals:
            logger.info(f"\n🎯 Executing: {sig.strategy_code} - {sig.symbol} {sig.direction}")
            
            # 1. Get AI Hive validation
            hive_result = self._get_hive_validation(sig, hive_gate)
            
            if hive_result.get('decision') != 'approve':
                logger.warning(f"   ❌ Hive REJECTED: {hive_result.get('reasoning')}")
                continue
            
            logger.info(f"   ✅ Hive APPROVED: {hive_result.get('consensus_score', 0):.0%} consensus")
            
            # 2. Execute trade
            try:
                trade_result = self._execute_trade(sig, broker_connector)
                
                if trade_result.get('success'):
                    executed_trades.append({
                        'signal': sig,
                        'hive_result': hive_result,
                        'trade_result': trade_result,
                        'timestamp': datetime.now()
                    })
                    
                    # Add to active positions
                    self.active_positions.append({
                        'strategy_code': sig.strategy_code,
                        'symbol': sig.symbol,
                        'direction': sig.direction,
                        'entry_price': sig.entry_price,
                        'exposure_pct': 0.10  # Estimate
                    })
                    
                    logger.info(f"   ✅ Trade executed: {trade_result.get('order_id')}")
                else:
                    logger.error(f"   ❌ Trade failed: {trade_result.get('error')}")
            
            except Exception as e:
                logger.error(f"   ❌ Execution error: {e}")
        
        return executed_trades
    
    def _get_hive_validation(self, signal: StrategySignal, hive_gate) -> Dict:
        """Get AI Hive validation for signal."""
        try:
            # Prepare market data for Hive
            market_data = {
                'prices': [],  # Populate from market data cache
                'high': signal.entry_price * 1.01,
                'low': signal.entry_price * 0.99
            }
            
            # Get Hive vote
            result = hive_gate.analyze_trade(
                symbol=signal.symbol,
                direction=signal.direction,
                entry_price=signal.entry_price,
                market_data=market_data,
                timeframe='1h',
                objective='day'
            )
            
            return result
        
        except Exception as e:
            logger.error(f"Hive validation error: {e}")
            return {'decision': 'reject', 'reasoning': f'Hive error: {e}'}
    
    def _execute_trade(self, signal: StrategySignal, broker_connector) -> Dict:
        """Execute trade through broker."""
        try:
            # Create candidate object (simplified)
            class Candidate:
                def __init__(self, sig: StrategySignal):
                    self.symbol = sig.symbol
                    self.side = sig.direction
                    self.entry_price = sig.entry_price
                    self.stop_loss = sig.stop_loss
                    self.strategy_id = sig.strategy_code
            
            candidate = Candidate(signal)
            
            # Calculate position size (basic example)
            size = 0.01  # Fixed size for now
            
            # Place order
            result = broker_connector.place_paper_order(candidate, size)
            
            return result
        
        except Exception as e:
            logger.error(f"Trade execution error: {e}")
            return {'success': False, 'error': str(e)}
    
    def update_positions(self, closed_positions: List[str]):
        """Remove closed positions from tracking."""
        self.active_positions = [
            pos for pos in self.active_positions 
            if pos.get('id') not in closed_positions
        ]
    
    def get_portfolio_diversity(self) -> Dict[str, Any]:
        """Get portfolio diversity metrics."""
        if not self.active_positions:
            return {'strategies': 0, 'symbols': 0, 'directions': {}}
        
        strategies = set(pos.get('strategy_code') for pos in self.active_positions)
        symbols = set(pos.get('symbol') for pos in self.active_positions)
        
        directions = {'BUY': 0, 'SELL': 0}
        for pos in self.active_positions:
            directions[pos.get('direction', 'BUY')] += 1
        
        return {
            'strategies': len(strategies),
            'symbols': len(symbols),
            'directions': directions,
            'total_positions': len(self.active_positions),
            'strategy_distribution': {
                s: sum(1 for p in self.active_positions if p.get('strategy_code') == s)
                for s in strategies
            }
        }


# Global orchestrator
_orchestrator = None

def get_orchestrator(**kwargs) -> TradeOrchestrator:
    """Get or create global orchestrator."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = TradeOrchestrator(**kwargs)
    return _orchestrator
