#!/usr/bin/env python3
"""
ZOMBIE TRADE KILLER
Monitors trade performance, cuts losers, reallocates to better opportunities
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class TradeHealth(Enum):
    """Trade health status"""
    STRONG = "STRONG"           # Signal improving, in profit
    HEALTHY = "HEALTHY"         # Signal stable, small profit/loss
    WEAK = "WEAK"              # Signal fading, near breakeven
    ZOMBIE = "ZOMBIE"          # Stagnant, no movement
    DYING = "DYING"            # Signal gone, in loss
    DEAD = "DEAD"              # Cut this immediately


@dataclass
class TradeMonitor:
    """Monitor state for active trade"""
    symbol: str
    entry_time: datetime
    entry_price: float
    current_price: float
    current_profit_pct: float
    
    # Signal strength tracking
    entry_signal_strength: float
    current_signal_strength: float
    signal_trend: str  # "improving", "stable", "fading"
    
    # Activity tracking
    highest_profit_pct: float
    lowest_profit_pct: float
    bars_since_entry: int
    bars_since_last_move: int  # Stagnation detector
    
    # Comparison metrics
    relative_performance: float  # vs other open trades
    opportunity_cost: float      # profit missed by holding this


class ZombieTradeKiller:
    """
    Aggressive trade management:
    - Cut losing/stagnant positions
    - Reallocate capital to better opportunities
    - Maximize capital efficiency
    """
    
    def __init__(self,
                 max_stagnant_bars: int = 20,
                 signal_fade_threshold: float = 0.3,
                 zombie_profit_threshold: float = -0.5,
                 reallocation_threshold: float = 2.0):
        """
        Args:
            max_stagnant_bars: Max bars without meaningful price movement
            signal_fade_threshold: Signal strength drop triggering review
            zombie_profit_threshold: Profit % below which trades are zombies
            reallocation_threshold: Opportunity cost % triggering reallocation
        """
        self.max_stagnant_bars = max_stagnant_bars
        self.signal_fade_threshold = signal_fade_threshold
        self.zombie_profit_threshold = zombie_profit_threshold
        self.reallocation_threshold = reallocation_threshold
        
        self.active_monitors: Dict[str, TradeMonitor] = {}
        self.kill_count = 0
        self.reallocation_count = 0
        
        logger.info("💀 ZOMBIE TRADE KILLER ACTIVATED")
        logger.info(f"   Max Stagnant Bars: {max_stagnant_bars}")
        logger.info(f"   Signal Fade Threshold: {signal_fade_threshold}")
        logger.info(f"   Zombie Threshold: {zombie_profit_threshold}%")
    
    def register_trade(self,
                      symbol: str,
                      entry_price: float,
                      signal_strength: float):
        """Register new trade for monitoring"""
        self.active_monitors[symbol] = TradeMonitor(
            symbol=symbol,
            entry_time=datetime.now(),
            entry_price=entry_price,
            current_price=entry_price,
            current_profit_pct=0.0,
            entry_signal_strength=signal_strength,
            current_signal_strength=signal_strength,
            signal_trend="stable",
            highest_profit_pct=0.0,
            lowest_profit_pct=0.0,
            bars_since_entry=0,
            bars_since_last_move=0,
            relative_performance=0.0,
            opportunity_cost=0.0
        )
        
        logger.info(f"📝 Registered {symbol} for monitoring (signal: {signal_strength:.2f})")
    
    def update_trade(self,
                    symbol: str,
                    current_price: float,
                    current_signal_strength: float,
                    available_opportunities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Update trade status and determine action
        
        Args:
            symbol: Trade symbol
            current_price: Current market price
            current_signal_strength: Current signal quality
            available_opportunities: List of other trade opportunities
        
        Returns:
            {
                'action': 'HOLD' | 'CUT' | 'REALLOCATE',
                'health': TradeHealth,
                'reason': str,
                'reallocation_target': Optional[Dict]
            }
        """
        if symbol not in self.active_monitors:
            return {'action': 'HOLD', 'health': TradeHealth.HEALTHY, 'reason': 'Not monitored'}
        
        monitor = self.active_monitors[symbol]
        
        # Update state
        monitor.current_price = current_price
        monitor.current_signal_strength = current_signal_strength
        monitor.bars_since_entry += 1
        
        # Calculate profit
        profit_pct = ((current_price - monitor.entry_price) / monitor.entry_price) * 100
        monitor.current_profit_pct = profit_pct
        
        # Track extremes
        monitor.highest_profit_pct = max(monitor.highest_profit_pct, profit_pct)
        monitor.lowest_profit_pct = min(monitor.lowest_profit_pct, profit_pct)
        
        # Detect stagnation
        price_move_pct = abs(profit_pct) / (monitor.bars_since_entry + 1)
        if price_move_pct < 0.1:  # Less than 0.1% movement per bar
            monitor.bars_since_last_move += 1
        else:
            monitor.bars_since_last_move = 0
        
        # Track signal trend
        signal_delta = current_signal_strength - monitor.entry_signal_strength
        if signal_delta > 0.2:
            monitor.signal_trend = "improving"
        elif signal_delta < -0.2:
            monitor.signal_trend = "fading"
        else:
            monitor.signal_trend = "stable"
        
        # Calculate opportunity cost
        best_opportunity = max(
            available_opportunities,
            key=lambda x: x.get('signal_strength', 0),
            default={'signal_strength': 0, 'expected_return': 0}
        )
        monitor.opportunity_cost = best_opportunity['expected_return'] - profit_pct
        
        # Assess trade health
        health = self._assess_health(monitor)
        
        # Determine action
        action_result = self._determine_action(monitor, health, best_opportunity)
        
        if action_result['action'] == 'CUT':
            self.kill_count += 1
            logger.warning(f"💀 KILLING {symbol}: {action_result['reason']}")
        elif action_result['action'] == 'REALLOCATE':
            self.reallocation_count += 1
            logger.info(f"🔄 REALLOCATING from {symbol}: {action_result['reason']}")
        
        return action_result
    
    def _assess_health(self, monitor: TradeMonitor) -> TradeHealth:
        """Assess trade health based on multiple factors"""
        
        # DEAD: Big loss + signal gone
        if monitor.current_profit_pct < -3.0 and monitor.current_signal_strength < 0.3:
            return TradeHealth.DEAD
        
        # DYING: Loss + fading signal
        if monitor.current_profit_pct < -1.0 and monitor.signal_trend == "fading":
            return TradeHealth.DYING
        
        # ZOMBIE: Stagnant + near breakeven
        if (monitor.bars_since_last_move > self.max_stagnant_bars and
            abs(monitor.current_profit_pct) < 0.5):
            return TradeHealth.ZOMBIE
        
        # WEAK: Signal fading or small loss
        if (monitor.signal_trend == "fading" or
            monitor.current_profit_pct < self.zombie_profit_threshold):
            return TradeHealth.WEAK
        
        # STRONG: Profit + improving signal
        if monitor.current_profit_pct > 2.0 and monitor.signal_trend == "improving":
            return TradeHealth.STRONG
        
        # HEALTHY: Default
        return TradeHealth.HEALTHY
    
    def _determine_action(self,
                         monitor: TradeMonitor,
                         health: TradeHealth,
                         best_opportunity: Dict) -> Dict[str, Any]:
        """Determine what action to take"""
        
        # KILL IMMEDIATELY
        if health in [TradeHealth.DEAD, TradeHealth.DYING]:
            return {
                'action': 'CUT',
                'health': health,
                'reason': f"{health.value}: P/L={monitor.current_profit_pct:.2f}%, Signal={monitor.current_signal_strength:.2f}",
                'reallocation_target': best_opportunity
            }
        
        # KILL ZOMBIES
        if health == TradeHealth.ZOMBIE:
            return {
                'action': 'CUT',
                'health': health,
                'reason': f"ZOMBIE: {monitor.bars_since_last_move} bars stagnant, P/L={monitor.current_profit_pct:.2f}%",
                'reallocation_target': best_opportunity
            }
        
        # REALLOCATE if opportunity cost too high
        if (health == TradeHealth.WEAK and
            monitor.opportunity_cost > self.reallocation_threshold):
            return {
                'action': 'REALLOCATE',
                'health': health,
                'reason': f"WEAK + High opportunity cost: {monitor.opportunity_cost:.2f}% vs {best_opportunity.get('symbol', 'N/A')}",
                'reallocation_target': best_opportunity
            }
        
        # HOLD everything else
        return {
            'action': 'HOLD',
            'health': health,
            'reason': f"{health.value}: Monitoring",
            'reallocation_target': None
        }
    
    def get_portfolio_health(self) -> Dict[str, Any]:
        """Get overall portfolio health metrics"""
        if not self.active_monitors:
            return {
                'total_trades': 0,
                'health_breakdown': {},
                'avg_profit_pct': 0.0,
                'zombies': 0,
                'kills_total': self.kill_count,
                'reallocations_total': self.reallocation_count
            }
        
        health_counts = {}
        total_profit = 0.0
        zombies = 0
        
        for monitor in self.active_monitors.values():
            health = self._assess_health(monitor)
            health_counts[health.value] = health_counts.get(health.value, 0) + 1
            total_profit += monitor.current_profit_pct
            
            if health in [TradeHealth.ZOMBIE, TradeHealth.DYING, TradeHealth.DEAD]:
                zombies += 1
        
        return {
            'total_trades': len(self.active_monitors),
            'health_breakdown': health_counts,
            'avg_profit_pct': total_profit / len(self.active_monitors),
            'zombies': zombies,
            'kills_total': self.kill_count,
            'reallocations_total': self.reallocation_count
        }
    
    def close_trade(self, symbol: str):
        """Remove trade from monitoring"""
        if symbol in self.active_monitors:
            del self.active_monitors[symbol]


# Example usage
if __name__ == "__main__":
    killer = ZombieTradeKiller(
        max_stagnant_bars=15,
        signal_fade_threshold=0.3,
        zombie_profit_threshold=-0.5
    )
    
    # Register trade
    killer.register_trade("EURUSD", 1.0950, 0.85)
    
    # Simulate stagnation
    opportunities = [
        {'symbol': 'GBPUSD', 'signal_strength': 0.95, 'expected_return': 3.5},
        {'symbol': 'USDJPY', 'signal_strength': 0.75, 'expected_return': 2.0}
    ]
    
    result = killer.update_trade(
        "EURUSD",
        current_price=1.0955,  # Tiny move
        current_signal_strength=0.50,  # Fading signal
        available_opportunities=opportunities
    )
    
    print(f"Action: {result['action']}")
    print(f"Health: {result['health'].value}")
    print(f"Reason: {result['reason']}")
