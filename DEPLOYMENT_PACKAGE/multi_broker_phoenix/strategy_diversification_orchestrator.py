"""
STRATEGY DIVERSIFICATION ORCHESTRATOR
Distributes positions across 5 diverse strategies
Ensures no concentration, maximizes edge variety
Works across Coinbase, OANDA, IBKR
"""

import logging
from typing import Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)

class Strategy(Enum):
    """Active trading strategies."""
    TRAP_REVERSAL = "trap_reversal"
    INSTITUTIONAL_SD = "institutional_sd"
    HOLY_GRAIL = "holy_grail"
    EMA_SCALPER = "ema_scalper"
    FABIO_AAA = "fabio_aaa"

class StrategyDiversificationOrchestrator:
    """
    Distributes positions across strategies intelligently.
    Ensures portfolio has edge variety, not single-strategy risk.
    Manages position allocation by broker.
    """
    
    def __init__(self):
        """Initialize orchestrator."""
        
        # Total position allocation by broker
        self.broker_limits = {
            'coinbase': {'max_positions': 5, 'current_positions': 0},
            'oanda': {'max_positions': 10, 'current_positions': 0},
            'ibkr': {'max_positions': 10, 'current_positions': 0}
        }
        
        # Strategy distribution - ensures diversity
        self.strategy_distribution = {
            Strategy.TRAP_REVERSAL: {
                'brokers': ['oanda', 'ibkr'],
                'symbols': {
                    'oanda': ['GBP/USD', 'EUR/GBP'],
                    'ibkr': ['QQQ', 'SPY']
                },
                'max_positions': 3,
                'current_positions': 0,
                'purpose': 'Reversal detection, liquidity traps'
            },
            Strategy.INSTITUTIONAL_SD: {
                'brokers': ['oanda', 'ibkr'],
                'symbols': {
                    'oanda': ['EUR/USD', 'AUD/USD'],
                    'ibkr': ['IWM', 'DIA']
                },
                'max_positions': 3,
                'current_positions': 0,
                'purpose': 'Volatility-based entries, institutional patterns'
            },
            Strategy.HOLY_GRAIL: {
                'brokers': ['coinbase', 'oanda', 'ibkr'],
                'symbols': {
                    'coinbase': ['BTC-USD', 'ETH-USD'],
                    'oanda': ['USD/JPY', 'NZD/USD'],
                    'ibkr': ['TLT', 'GLD']
                },
                'max_positions': 3,
                'current_positions': 0,
                'purpose': 'Multi-timeframe confirmation, trend following'
            },
            Strategy.EMA_SCALPER: {
                'brokers': ['coinbase', 'oanda'],
                'symbols': {
                    'coinbase': ['BTC-USD'],
                    'oanda': ['GBP/JPY']
                },
                'max_positions': 3,
                'current_positions': 0,
                'purpose': 'Fast EMA crosses, momentum scalping'
            },
            Strategy.FABIO_AAA: {
                'brokers': ['oanda', 'ibkr'],
                'symbols': {
                    'oanda': ['CAD/JPY'],
                    'ibkr': ['AAPL', 'MSFT']
                },
                'max_positions': 3,
                'current_positions': 0,
                'purpose': 'Advanced pattern recognition, precision entries'
            }
        }
        
        logger.info("✅ Strategy Diversification Orchestrator initialized")
        self._print_distribution_plan()
    
    def _print_distribution_plan(self):
        """Print strategy distribution plan."""
        logger.info("")
        logger.info("="*80)
        logger.info("📊 STRATEGY DIVERSIFICATION PLAN")
        logger.info("="*80)
        logger.info("")
        logger.info("BROKER LIMITS:")
        logger.info(f"  Coinbase:  5 positions max (nano-mode, crypto)")
        logger.info(f"  OANDA:    10 positions max (FX/CFDs, unlimited trades/day)")
        logger.info(f"  IBKR:     10 positions max (Equities/Futures, unlimited trades/day)")
        logger.info(f"  TOTAL:    25 positions max across all brokers")
        logger.info("")
        logger.info("STRATEGY ALLOCATION (Diverse, Distributed):")
        logger.info("")
        
        total_slots = 0
        for strategy, config in self.strategy_distribution.items():
            max_pos = config['max_positions']
            total_slots += max_pos
            brokers = ', '.join(config['brokers'])
            logger.info(f"  {strategy.value:20} | Max: {max_pos} | Brokers: {brokers}")
            logger.info(f"     Purpose: {config['purpose']}")
            logger.info("")
        
        logger.info(f"TOTAL STRATEGY SLOTS: {total_slots}")
        logger.info("")
        logger.info("KEY BENEFITS:")
        logger.info("  ✓ No single-strategy concentration")
        logger.info("  ✓ Each strategy has max 3 positions (risk capped)")
        logger.info("  ✓ Crypto + FX + Equities diversification")
        logger.info("  ✓ Fast + Medium + Slow strategies running together")
        logger.info("  ✓ Failover: If one strategy underperforms, others continue")
        logger.info("")
        logger.info("="*80)
        logger.info("")
    
    def allocate_next_position(self, broker: str) -> Optional[Dict[str, str]]:
        """
        Get next position allocation for broker.
        Returns strategy, symbol, and purpose.
        
        Args:
            broker: Target broker (coinbase, oanda, ibkr)
        
        Returns:
            Dict with strategy, symbol, purpose OR None if limit reached
        """
        if broker not in self.broker_limits:
            logger.warning(f"⚠️  Unknown broker: {broker}")
            return None
        
        broker_limit = self.broker_limits[broker]
        if broker_limit['current_positions'] >= broker_limit['max_positions']:
            logger.warning(f"⚠️  {broker.upper()} position limit reached ({broker_limit['max_positions']})")
            return None
        
        # Find strategy with lowest current positions that supports this broker
        best_strategy = None
        min_positions = float('inf')
        
        for strategy, config in self.strategy_distribution.items():
            if broker not in config['brokers']:
                continue  # This broker doesn't support this strategy
            
            if config['current_positions'] >= config['max_positions']:
                continue  # Strategy at capacity
            
            if config['current_positions'] < min_positions:
                min_positions = config['current_positions']
                best_strategy = strategy
        
        if not best_strategy:
            logger.warning(f"⚠️  No available strategies for {broker}")
            return None
        
        # Get symbol for this broker
        strategy_config = self.strategy_distribution[best_strategy]
        symbols = strategy_config['symbols'].get(broker, [])
        
        if not symbols:
            logger.warning(f"⚠️  No symbols defined for {broker}/{best_strategy.value}")
            return None
        
        # Pick first available symbol (in production, use least-recent)
        symbol = symbols[0]
        
        # Update counts
        self.broker_limits[broker]['current_positions'] += 1
        self.strategy_distribution[best_strategy]['current_positions'] += 1
        
        result = {
            'strategy': best_strategy.value,
            'symbol': symbol,
            'broker': broker,
            'purpose': strategy_config['purpose'],
            'strategy_positions': self.strategy_distribution[best_strategy]['current_positions'],
            'broker_positions': self.broker_limits[broker]['current_positions']
        }
        
        logger.info(f"📍 Allocated: {broker:10} | {best_strategy.value:20} | {symbol}")
        logger.info(f"    ({self.broker_limits[broker]['current_positions']}/{broker_limit['max_positions']} "
                   f"on broker, {result['strategy_positions']}/3 for strategy)")
        
        return result
    
    def complete_position(self, broker: str, strategy: str):
        """
        Mark position as completed.
        
        Args:
            broker: Broker that held position
            strategy: Strategy that executed
        """
        if broker in self.broker_limits:
            self.broker_limits[broker]['current_positions'] = max(0, 
                self.broker_limits[broker]['current_positions'] - 1)
        
        for s, config in self.strategy_distribution.items():
            if s.value == strategy:
                config['current_positions'] = max(0, config['current_positions'] - 1)
                break
        
        logger.info(f"✅ Position completed: {broker} | {strategy}")
    
    def get_portfolio_status(self) -> Dict:
        """Get current portfolio diversification status."""
        return {
            'brokers': self.broker_limits,
            'strategies': {
                s.value: {
                    'current': config['current_positions'],
                    'max': config['max_positions'],
                    'utilization': f"{(config['current_positions'] / config['max_positions'] * 100):.0f}%"
                }
                for s, config in self.strategy_distribution.items()
            }
        }
    
    def print_portfolio_status(self):
        """Print current portfolio status."""
        status = self.get_portfolio_status()
        
        logger.info("")
        logger.info("="*80)
        logger.info("📈 CURRENT PORTFOLIO STATUS")
        logger.info("="*80)
        logger.info("")
        
        # Broker status
        logger.info("POSITIONS BY BROKER:")
        total_positions = 0
        for broker, limits in status['brokers'].items():
            total_positions += limits['current_positions']
            utilization = f"{(limits['current_positions'] / limits['max_positions'] * 100):.0f}%"
            logger.info(f"  {broker:10} | {limits['current_positions']}/{limits['max_positions']} "
                       f"({utilization:>3})")
        
        logger.info(f"  {'TOTAL':10} | {total_positions}/25")
        logger.info("")
        
        # Strategy status
        logger.info("POSITIONS BY STRATEGY:")
        for strategy, stats in status['strategies'].items():
            logger.info(f"  {strategy:20} | {stats['current']}/3 ({stats['utilization']:>3})")
        
        logger.info("")
        logger.info("="*80)
        logger.info("")
    
    def reset_allocations(self):
        """Reset position counts (use at end of trading day)."""
        for broker in self.broker_limits:
            self.broker_limits[broker]['current_positions'] = 0
        for strategy in self.strategy_distribution:
            self.strategy_distribution[strategy]['current_positions'] = 0
        
        logger.info("🔄 Position allocations reset for new session")

# Global orchestrator instance
_orchestrator = None

def get_orchestrator() -> StrategyDiversificationOrchestrator:
    """Get or create global orchestrator."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = StrategyDiversificationOrchestrator()
    return _orchestrator
