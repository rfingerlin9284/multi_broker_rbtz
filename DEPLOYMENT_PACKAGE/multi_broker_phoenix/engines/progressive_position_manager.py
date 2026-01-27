"""
Progressive Position Manager with Incremental Closing
======================================================

Implements multi-stage position management:
- Progressive trailing stops that tighten as profit increases
- Incremental position closing to lock in profits
- Works across all brokers (Coinbase, IBKR, OANDA)

Example Configuration:
Stage 1: +$30 profit  → Close 25% of position, set 12-pip trailing stop
Stage 2: +$60 profit  → Close 25% more (50% total), set 8-pip trailing stop
Stage 3: +$100 profit → Close 25% more (75% total), set 5-pip trailing stop
Stage 4: Let remaining 25% run with 5-pip stop
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Callable
from enum import Enum

logger = logging.getLogger(__name__)


class PositionSide(Enum):
    """Position direction"""
    LONG = "LONG"
    SHORT = "SHORT"


@dataclass
class ProgressiveStage:
    """Configuration for a profit-based stage"""
    profit_threshold: float  # Dollar profit to trigger this stage
    close_percentage: float  # % of ORIGINAL position to close (0.0-1.0)
    trailing_stop_pips: float  # Trailing stop distance in pips
    stage_name: str = ""  # Human-readable name
    
    def __post_init__(self):
        if not self.stage_name:
            self.stage_name = f"Stage +${self.profit_threshold}"


@dataclass
class ManagedPosition:
    """A position being actively managed"""
    symbol: str
    side: PositionSide
    entry_price: float
    original_size: float  # Initial position size
    current_size: float   # Remaining position size
    broker_order_id: str
    
    # Tracking
    current_stage: int = 0  # Which stage we're in (0 = initial)
    highest_price: float = 0.0  # For LONG positions
    lowest_price: float = 0.0   # For SHORT positions
    current_stop: float = 0.0
    trailing_stop_pips: float = 20.0  # Current trailing stop distance
    
    # Profit tracking
    realized_profit: float = 0.0  # From partial closes
    unrealized_profit: float = 0.0  # On remaining position
    total_profit: float = 0.0  # realized + unrealized
    
    # Stage tracking
    stages_executed: List[int] = field(default_factory=list)
    partial_close_history: List[Dict] = field(default_factory=list)
    
    # Timestamps
    entry_timestamp: datetime = field(default_factory=datetime.now)
    last_update: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Initialize tracking values"""
        if self.side == PositionSide.LONG:
            self.highest_price = self.entry_price
            self.current_stop = self.entry_price - (self.trailing_stop_pips * self.pip_value())
        else:
            self.lowest_price = self.entry_price
            self.current_stop = self.entry_price + (self.trailing_stop_pips * self.pip_value())
    
    def pip_value(self) -> float:
        """Calculate pip value based on symbol"""
        if 'JPY' in self.symbol:
            return 0.01  # 1 pip for JPY pairs
        else:
            return 0.0001  # 1 pip for other pairs
    
    def calculate_profit(self, current_price: float) -> float:
        """Calculate total profit (realized + unrealized)"""
        if self.side == PositionSide.LONG:
            self.unrealized_profit = (current_price - self.entry_price) * self.current_size
        else:
            self.unrealized_profit = (self.entry_price - current_price) * self.current_size
        
        self.total_profit = self.realized_profit + self.unrealized_profit
        return self.total_profit


class ProgressivePositionManager:
    """
    Manages positions with progressive trailing stops and incremental closing.
    
    Example Usage:
        manager = ProgressivePositionManager([
            ProgressiveStage(profit_threshold=30, close_percentage=0.25, trailing_stop_pips=12),
            ProgressiveStage(profit_threshold=60, close_percentage=0.50, trailing_stop_pips=8),
            ProgressiveStage(profit_threshold=100, close_percentage=0.75, trailing_stop_pips=5),
        ])
        
        # Open position
        manager.open_position("EURUSD", PositionSide.LONG, 1.0950, 10000, "order123")
        
        # Update with current price (call on each tick)
        actions = manager.update_position("EURUSD", 1.0980)
        
        # Execute actions (partial closes, stop updates)
        for action in actions:
            if action['type'] == 'PARTIAL_CLOSE':
                broker.close_partial(symbol, action['size'])
            elif action['type'] == 'STOP_HIT':
                broker.close_position(symbol)
    """
    
    def __init__(self, stages: List[ProgressiveStage], initial_stop_pips: float = 20.0):
        """
        Args:
            stages: List of progressive stages (sorted by profit_threshold)
            initial_stop_pips: Initial trailing stop distance in pips
        """
        self.stages = sorted(stages, key=lambda s: s.profit_threshold)
        self.initial_stop_pips = initial_stop_pips
        self.positions: Dict[str, ManagedPosition] = {}
        
        logger.info(f"🎯 Progressive Position Manager initialized")
        logger.info(f"   Initial stop: {initial_stop_pips} pips")
        for i, stage in enumerate(self.stages, 1):
            logger.info(f"   Stage {i}: +${stage.profit_threshold} → "
                       f"Close {stage.close_percentage*100:.0f}%, "
                       f"Stop {stage.trailing_stop_pips} pips")
    
    def open_position(self, symbol: str, side: PositionSide, entry_price: float, 
                     size: float, broker_order_id: str) -> ManagedPosition:
        """
        Open a new managed position.
        
        Returns:
            ManagedPosition object
        """
        position = ManagedPosition(
            symbol=symbol,
            side=side,
            entry_price=entry_price,
            original_size=size,
            current_size=size,
            broker_order_id=broker_order_id,
            trailing_stop_pips=self.initial_stop_pips
        )
        
        self.positions[symbol] = position
        
        logger.info(f"📍 Position opened: {symbol} {side.value}")
        logger.info(f"   Entry: ${entry_price:.5f}")
        logger.info(f"   Size: {size:,.0f} units")
        logger.info(f"   Initial stop: ${position.current_stop:.5f} ({self.initial_stop_pips} pips)")
        
        return position
    
    def update_position(self, symbol: str, current_price: float) -> List[Dict]:
        """
        Update position with current price and return required actions.
        
        Returns:
            List of actions to execute:
            [
                {'type': 'PARTIAL_CLOSE', 'symbol': 'EURUSD', 'size': 2500, 'reason': 'Stage 1'},
                {'type': 'UPDATE_STOP', 'symbol': 'EURUSD', 'new_stop': 1.0960},
                {'type': 'STOP_HIT', 'symbol': 'EURUSD', 'price': 1.0940}
            ]
        """
        if symbol not in self.positions:
            return []
        
        position = self.positions[symbol]
        actions = []
        
        # Calculate current profit
        profit = position.calculate_profit(current_price)
        
        # Update highest/lowest price for trailing
        if position.side == PositionSide.LONG:
            if current_price > position.highest_price:
                position.highest_price = current_price
                # Update trailing stop
                new_stop = current_price - (position.trailing_stop_pips * position.pip_value())
                if new_stop > position.current_stop:
                    old_stop = position.current_stop
                    position.current_stop = new_stop
                    logger.info(f"📈 {symbol} trailing stop: ${old_stop:.5f} → ${new_stop:.5f}")
                    actions.append({
                        'type': 'UPDATE_STOP',
                        'symbol': symbol,
                        'old_stop': old_stop,
                        'new_stop': new_stop
                    })
        else:  # SHORT
            if current_price < position.lowest_price:
                position.lowest_price = current_price
                # Update trailing stop
                new_stop = current_price + (position.trailing_stop_pips * position.pip_value())
                if new_stop < position.current_stop:
                    old_stop = position.current_stop
                    position.current_stop = new_stop
                    logger.info(f"📉 {symbol} trailing stop: ${old_stop:.5f} → ${new_stop:.5f}")
                    actions.append({
                        'type': 'UPDATE_STOP',
                        'symbol': symbol,
                        'old_stop': old_stop,
                        'new_stop': new_stop
                    })
        
        # Check if we should advance to next stage
        for i, stage in enumerate(self.stages):
            stage_number = i + 1
            
            # Skip if already executed
            if stage_number in position.stages_executed:
                continue
            
            # Check if profit threshold reached
            if profit >= stage.profit_threshold:
                logger.info(f"🎯 {symbol} Stage {stage_number} triggered: "
                           f"Profit ${profit:.2f} >= ${stage.profit_threshold}")
                
                # Calculate size to close (% of ORIGINAL position)
                cumulative_closed = sum(
                    stage.close_percentage for i, stage in enumerate(self.stages)
                    if (i + 1) in position.stages_executed
                )
                size_to_close = (stage.close_percentage - cumulative_closed) * position.original_size
                
                if size_to_close > 0:
                    # Record partial close
                    close_record = {
                        'stage': stage_number,
                        'timestamp': datetime.now(),
                        'price': current_price,
                        'size': size_to_close,
                        'profit': (current_price - position.entry_price) * size_to_close if position.side == PositionSide.LONG
                                 else (position.entry_price - current_price) * size_to_close
                    }
                    position.partial_close_history.append(close_record)
                    
                    # Update position size
                    position.current_size -= size_to_close
                    
                    # Update realized profit
                    position.realized_profit += close_record['profit']
                    
                    logger.info(f"💰 {symbol} Partial close: {size_to_close:,.0f} units @ ${current_price:.5f}")
                    logger.info(f"   Profit locked: ${close_record['profit']:.2f}")
                    logger.info(f"   Remaining: {position.current_size:,.0f} units")
                    
                    actions.append({
                        'type': 'PARTIAL_CLOSE',
                        'symbol': symbol,
                        'size': size_to_close,
                        'price': current_price,
                        'reason': f'Stage {stage_number}: +${stage.profit_threshold}',
                        'profit': close_record['profit']
                    })
                
                # Update trailing stop distance
                if stage.trailing_stop_pips != position.trailing_stop_pips:
                    old_pips = position.trailing_stop_pips
                    position.trailing_stop_pips = stage.trailing_stop_pips
                    logger.info(f"🔧 {symbol} Trailing stop distance: {old_pips} pips → {stage.trailing_stop_pips} pips")
                    
                    # Recalculate stop with new distance
                    if position.side == PositionSide.LONG:
                        position.current_stop = position.highest_price - (position.trailing_stop_pips * position.pip_value())
                    else:
                        position.current_stop = position.lowest_price + (position.trailing_stop_pips * position.pip_value())
                
                # Mark stage as executed
                position.stages_executed.append(stage_number)
        
        # Check if stop loss hit
        stop_hit = False
        if position.side == PositionSide.LONG:
            stop_hit = current_price <= position.current_stop
        else:
            stop_hit = current_price >= position.current_stop
        
        if stop_hit:
            logger.warning(f"🛑 {symbol} STOP HIT @ ${current_price:.5f} (stop: ${position.current_stop:.5f})")
            logger.info(f"   Total profit: ${position.total_profit:.2f}")
            logger.info(f"   Realized: ${position.realized_profit:.2f}, Unrealized: ${position.unrealized_profit:.2f}")
            
            actions.append({
                'type': 'STOP_HIT',
                'symbol': symbol,
                'price': current_price,
                'stop': position.current_stop,
                'remaining_size': position.current_size,
                'total_profit': position.total_profit,
                'realized_profit': position.realized_profit,
                'unrealized_profit': position.unrealized_profit
            })
            
            # Remove position
            del self.positions[symbol]
        
        position.last_update = datetime.now()
        return actions
    
    def close_position(self, symbol: str, current_price: float, reason: str = "Manual close") -> Optional[Dict]:
        """
        Manually close a position.
        
        Returns:
            Action dict or None if position doesn't exist
        """
        if symbol not in self.positions:
            return None
        
        position = self.positions[symbol]
        profit = position.calculate_profit(current_price)
        
        logger.info(f"🔒 {symbol} Manual close: {reason}")
        logger.info(f"   Price: ${current_price:.5f}")
        logger.info(f"   Total profit: ${profit:.2f}")
        
        action = {
            'type': 'MANUAL_CLOSE',
            'symbol': symbol,
            'price': current_price,
            'size': position.current_size,
            'reason': reason,
            'profit': profit
        }
        
        del self.positions[symbol]
        return action
    
    def get_position_summary(self, symbol: str) -> Optional[Dict]:
        """Get detailed position summary"""
        if symbol not in self.positions:
            return None
        
        position = self.positions[symbol]
        return {
            'symbol': symbol,
            'side': position.side.value,
            'entry_price': position.entry_price,
            'original_size': position.original_size,
            'current_size': position.current_size,
            'current_stage': position.current_stage,
            'trailing_stop_pips': position.trailing_stop_pips,
            'current_stop': position.current_stop,
            'highest_price': position.highest_price if position.side == PositionSide.LONG else None,
            'lowest_price': position.lowest_price if position.side == PositionSide.SHORT else None,
            'realized_profit': position.realized_profit,
            'unrealized_profit': position.unrealized_profit,
            'total_profit': position.total_profit,
            'stages_executed': position.stages_executed,
            'partial_closes': len(position.partial_close_history),
            'entry_timestamp': position.entry_timestamp.isoformat(),
            'last_update': position.last_update.isoformat()
        }
    
    def get_all_positions(self) -> Dict[str, Dict]:
        """Get all active positions"""
        return {symbol: self.get_position_summary(symbol) for symbol in self.positions}


# Default configuration matching OANDA example
DEFAULT_STAGES = [
    ProgressiveStage(profit_threshold=30.0, close_percentage=0.25, trailing_stop_pips=12.0, stage_name="Stage 1: +$30"),
    ProgressiveStage(profit_threshold=60.0, close_percentage=0.50, trailing_stop_pips=8.0, stage_name="Stage 2: +$60"),
    ProgressiveStage(profit_threshold=100.0, close_percentage=0.75, trailing_stop_pips=5.0, stage_name="Stage 3: +$100"),
]


def create_default_manager() -> ProgressivePositionManager:
    """Create manager with default progressive stages"""
    return ProgressivePositionManager(stages=DEFAULT_STAGES, initial_stop_pips=20.0)


if __name__ == "__main__":
    # Test example
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    
    print("\n" + "="*70)
    print("PROGRESSIVE POSITION MANAGER TEST")
    print("="*70)
    
    # Create manager
    manager = create_default_manager()
    
    # Open LONG position
    print("\n1. Opening LONG position on EURUSD...")
    manager.open_position("EURUSD", PositionSide.LONG, 1.0950, 10000, "order_123")
    
    # Simulate price movement
    print("\n2. Price moves to $1.0980 (+30 pips, +$30 profit)...")
    actions = manager.update_position("EURUSD", 1.0980)
    print(f"   Actions: {len(actions)} triggered")
    for action in actions:
        print(f"   - {action['type']}: {action.get('reason', 'N/A')}")
    
    print("\n3. Price moves to $1.1010 (+60 pips, +$60 profit)...")
    actions = manager.update_position("EURUSD", 1.1010)
    print(f"   Actions: {len(actions)} triggered")
    
    print("\n4. Price moves to $1.1050 (+100 pips, +$100 profit)...")
    actions = manager.update_position("EURUSD", 1.1050)
    print(f"   Actions: {len(actions)} triggered")
    
    print("\n5. Price retraces to $1.1045 (stop should trail)...")
    actions = manager.update_position("EURUSD", 1.1045)
    
    print("\n6. Position Summary:")
    summary = manager.get_position_summary("EURUSD")
    if summary:
        for key, value in summary.items():
            print(f"   {key}: {value}")
    
    print("\n" + "="*70)
