#!/usr/bin/env python3
"""
Example: Progressive Position Management with Incremental Closing
==================================================================

Shows how to integrate the Progressive Position Manager with your brokers:
- Coinbase Advanced Trade
- IBKR
- OANDA

This system automatically:
1. Tightens trailing stops as profit increases
2. Closes portions of the position at profit milestones
3. Locks in realized profits while letting winners run
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from multi_broker_phoenix.engines.progressive_position_manager import (
    ProgressivePositionManager,
    ProgressiveStage,
    PositionSide,
    create_default_manager
)
from multi_broker_phoenix.brokers.coinbase_safe_connector import CoinbaseSafeConnector
import logging
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


class ProgressiveTradingBot:
    """
    Trading bot with progressive position management.
    
    Features:
    - Multi-stage profit targets
    - Incremental position closing
    - Progressive trailing stops
    - Works with any broker
    """
    
    def __init__(self, broker, progressive_stages=None):
        """
        Args:
            broker: Broker connector (Coinbase, IBKR, OANDA)
            progressive_stages: List of ProgressiveStage objects (uses defaults if None)
        """
        self.broker = broker
        
        if progressive_stages:
            self.position_manager = ProgressivePositionManager(
                stages=progressive_stages,
                initial_stop_pips=20.0
            )
        else:
            self.position_manager = create_default_manager()
        
        logger.info("✅ Progressive Trading Bot initialized")
    
    def open_trade(self, symbol: str, side: str, entry_price: float, size: float):
        """
        Open a new trade with progressive management.
        
        Args:
            symbol: Trading symbol (e.g., "BTCUSD", "EURUSD")
            side: "LONG" or "SHORT"
            entry_price: Entry price
            size: Position size
        """
        # Convert side to enum
        position_side = PositionSide.LONG if side.upper() in ('LONG', 'BUY') else PositionSide.SHORT
        
        # Place order with broker
        order_id = f"progressive_{symbol}_{int(time.time())}"
        
        logger.info(f"📤 Placing {side} order: {symbol}")
        logger.info(f"   Size: {size:,.0f} units @ ${entry_price:.5f}")
        
        # Register with position manager
        position = self.position_manager.open_position(
            symbol=symbol,
            side=position_side,
            entry_price=entry_price,
            size=size,
            broker_order_id=order_id
        )
        
        return position
    
    def update_positions(self, price_data: dict):
        """
        Update all positions with current prices.
        
        Args:
            price_data: Dict of {symbol: current_price}
        """
        for symbol, current_price in price_data.items():
            actions = self.position_manager.update_position(symbol, current_price)
            
            # Execute actions
            for action in actions:
                self._execute_action(action)
    
    def _execute_action(self, action: dict):
        """Execute an action returned by position manager"""
        action_type = action['type']
        symbol = action['symbol']
        
        if action_type == 'PARTIAL_CLOSE':
            # Close portion of position
            size = action['size']
            price = action['price']
            profit = action['profit']
            
            logger.info(f"💰 Executing partial close: {symbol}")
            logger.info(f"   Size: {size:,.0f} units @ ${price:.5f}")
            logger.info(f"   Profit: ${profit:.2f}")
            logger.info(f"   Reason: {action['reason']}")
            
            # In real implementation, call broker.close_partial(symbol, size)
            # self.broker.close_partial(symbol, size)
        
        elif action_type == 'UPDATE_STOP':
            # Update trailing stop
            new_stop = action['new_stop']
            logger.info(f"🔧 Updating stop loss: {symbol} → ${new_stop:.5f}")
            
            # In real implementation, call broker.update_stop(symbol, new_stop)
            # self.broker.update_stop(symbol, new_stop)
        
        elif action_type == 'STOP_HIT':
            # Close remaining position
            remaining_size = action['remaining_size']
            total_profit = action['total_profit']
            
            logger.info(f"🛑 Stop hit - Closing position: {symbol}")
            logger.info(f"   Size: {remaining_size:,.0f} units")
            logger.info(f"   Total profit: ${total_profit:.2f}")
            logger.info(f"   - Realized: ${action['realized_profit']:.2f}")
            logger.info(f"   - Unrealized: ${action['unrealized_profit']:.2f}")
            
            # In real implementation, call broker.close_position(symbol)
            # self.broker.close_position(symbol)
        
        elif action_type == 'MANUAL_CLOSE':
            logger.info(f"🔒 Manual close: {symbol}")
            logger.info(f"   Reason: {action['reason']}")
            logger.info(f"   Profit: ${action['profit']:.2f}")
    
    def get_position_status(self, symbol: str):
        """Get detailed position status"""
        return self.position_manager.get_position_summary(symbol)
    
    def get_all_positions(self):
        """Get all active positions"""
        return self.position_manager.get_all_positions()


def example_forex_trading():
    """Example: Forex trading with progressive management"""
    print("\n" + "="*70)
    print("EXAMPLE 1: FOREX TRADING (EURUSD)")
    print("="*70)
    
    # Create broker (paper mode for testing)
    broker = CoinbaseSafeConnector(paper_mode=True)
    
    # Create bot with custom stages
    custom_stages = [
        ProgressiveStage(profit_threshold=30, close_percentage=0.25, trailing_stop_pips=12, stage_name="First Target"),
        ProgressiveStage(profit_threshold=60, close_percentage=0.50, trailing_stop_pips=8, stage_name="Second Target"),
        ProgressiveStage(profit_threshold=100, close_percentage=0.75, trailing_stop_pips=5, stage_name="Third Target"),
    ]
    bot = ProgressiveTradingBot(broker, custom_stages)
    
    # Open LONG trade
    print("\n1. Opening LONG position...")
    bot.open_trade("EURUSD", "LONG", 1.0950, 10000)
    
    # Simulate price updates
    print("\n2. Price moves up (+30 pips)...")
    bot.update_positions({"EURUSD": 1.0980})
    
    print("\n3. Price continues (+60 pips)...")
    bot.update_positions({"EURUSD": 1.1010})
    
    print("\n4. Price hits +100 pips...")
    bot.update_positions({"EURUSD": 1.1050})
    
    print("\n5. Price retraces slightly...")
    bot.update_positions({"EURUSD": 1.1045})
    
    # Show position status
    print("\n6. Position Status:")
    status = bot.get_position_status("EURUSD")
    if status:
        print(f"   Remaining size: {status['current_size']:,.0f} units")
        print(f"   Total profit: ${status['total_profit']:.2f}")
        print(f"   Realized: ${status['realized_profit']:.2f}")
        print(f"   Unrealized: ${status['unrealized_profit']:.2f}")
        print(f"   Current stop: ${status['current_stop']:.5f} ({status['trailing_stop_pips']} pips)")
        print(f"   Stages executed: {status['stages_executed']}")


def example_crypto_trading():
    """Example: Crypto trading with aggressive stages"""
    print("\n" + "="*70)
    print("EXAMPLE 2: CRYPTO TRADING (BTCUSD) - Aggressive Stages")
    print("="*70)
    
    broker = CoinbaseSafeConnector(paper_mode=True)
    
    # More aggressive stages for volatile crypto
    crypto_stages = [
        ProgressiveStage(profit_threshold=100, close_percentage=0.33, trailing_stop_pips=50, stage_name="$100 profit"),
        ProgressiveStage(profit_threshold=250, close_percentage=0.66, trailing_stop_pips=30, stage_name="$250 profit"),
        ProgressiveStage(profit_threshold=500, close_percentage=0.90, trailing_stop_pips=20, stage_name="$500 profit"),
    ]
    bot = ProgressiveTradingBot(broker, crypto_stages)
    
    print("\n1. Opening BTC LONG position...")
    bot.open_trade("BTCUSD", "LONG", 42000, 0.1)  # 0.1 BTC
    
    print("\n2. Price moves to $42500 (+$50 profit)...")
    bot.update_positions({"BTCUSD": 42500})
    
    print("\n3. Price moves to $43000 (+$100 profit) - Stage 1 triggers...")
    bot.update_positions({"BTCUSD": 43000})
    
    print("\n4. Price moves to $44500 (+$250 profit) - Stage 2 triggers...")
    bot.update_positions({"BTCUSD": 44500})
    
    status = bot.get_position_status("BTCUSD")
    if status:
        print(f"\n   Position after Stage 2:")
        print(f"   - Original size: {status['original_size']:.3f} BTC")
        print(f"   - Remaining: {status['current_size']:.3f} BTC")
        print(f"   - Realized profit: ${status['realized_profit']:.2f}")


def example_multi_position():
    """Example: Managing multiple positions simultaneously"""
    print("\n" + "="*70)
    print("EXAMPLE 3: MULTIPLE POSITIONS")
    print("="*70)
    
    broker = CoinbaseSafeConnector(paper_mode=True)
    bot = ProgressiveTradingBot(broker)  # Use default stages
    
    # Open multiple positions
    print("\n1. Opening multiple positions...")
    bot.open_trade("EURUSD", "LONG", 1.0950, 10000)
    bot.open_trade("GBPUSD", "LONG", 1.2700, 8000)
    bot.open_trade("USDJPY", "SHORT", 149.50, 5000)
    
    # Update all positions
    print("\n2. Updating all positions...")
    bot.update_positions({
        "EURUSD": 1.0980,  # +30 pips
        "GBPUSD": 1.2730,  # +30 pips
        "USDJPY": 149.20   # +30 pips in favor
    })
    
    # Show all positions
    print("\n3. All active positions:")
    all_positions = bot.get_all_positions()
    for symbol, status in all_positions.items():
        print(f"\n   {symbol}:")
        print(f"   - Side: {status['side']}")
        print(f"   - Size: {status['current_size']:,.0f} / {status['original_size']:,.0f}")
        print(f"   - Profit: ${status['total_profit']:.2f}")
        print(f"   - Stop: ${status['current_stop']:.5f}")


if __name__ == "__main__":
    # Run examples
    example_forex_trading()
    example_crypto_trading()
    example_multi_position()
    
    print("\n" + "="*70)
    print("PROGRESSIVE TRADING EXAMPLES COMPLETE")
    print("="*70)
    print("\nKey Features Demonstrated:")
    print("✅ Progressive trailing stops (20→12→8→5 pips)")
    print("✅ Incremental closing (25%→50%→75%)")
    print("✅ Profit locking at each stage")
    print("✅ Multi-position management")
    print("✅ Works with any broker (Coinbase, IBKR, OANDA)")
    print("\nIntegration Steps:")
    print("1. Create ProgressiveTradingBot with your broker")
    print("2. Configure custom stages or use defaults")
    print("3. Call open_trade() to enter positions")
    print("4. Call update_positions() on each price tick")
    print("5. Bot automatically manages partial closes and stops")
    print()
