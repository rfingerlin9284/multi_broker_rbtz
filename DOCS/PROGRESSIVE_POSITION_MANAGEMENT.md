# Progressive Position Management with Incremental Closing

## Overview

The Progressive Position Manager implements sophisticated trade management that automatically:

1. **Tightens trailing stops** as profit increases
2. **Closes portions of the position** at profit milestones  
3. **Locks in realized profits** while letting winners run
4. **Works across all brokers** (Coinbase, IBKR, OANDA)

## Default Configuration

```
Stage 1: +$30 profit  → Close 25% position, set 12-pip trailing stop
Stage 2: +$60 profit  → Close 25% more (50% total), set 8-pip trailing stop  
Stage 3: +$100 profit → Close 25% more (75% total), set 5-pip trailing stop
Final:   Remaining 25% runs with tight 5-pip stop
```

## Quick Start

### 1. Import the Manager

```python
from multi_broker_phoenix.engines.progressive_position_manager import (
    ProgressivePositionManager,
    ProgressiveStage,
    PositionSide,
    create_default_manager
)
```

### 2. Create Manager (Default Stages)

```python
manager = create_default_manager()
```

### 3. Open Position

```python
manager.open_position(
    symbol="EURUSD",
    side=PositionSide.LONG,
    entry_price=1.0950,
    size=10000,
    broker_order_id="order_123"
)
```

### 4. Update with Current Price (Every Tick)

```python
actions = manager.update_position("EURUSD", current_price=1.0980)

# Execute returned actions
for action in actions:
    if action['type'] == 'PARTIAL_CLOSE':
        # Close partial position with broker
        broker.close_partial(action['symbol'], action['size'])
    
    elif action['type'] == 'UPDATE_STOP':
        # Update trailing stop
        broker.update_stop(action['symbol'], action['new_stop'])
    
    elif action['type'] == 'STOP_HIT':
        # Close entire position
        broker.close_position(action['symbol'])
```

## Custom Stages

### Forex Example (Conservative)

```python
forex_stages = [
    ProgressiveStage(profit_threshold=20, close_percentage=0.20, trailing_stop_pips=10),
    ProgressiveStage(profit_threshold=40, close_percentage=0.40, trailing_stop_pips=7),
    ProgressiveStage(profit_threshold=60, close_percentage=0.60, trailing_stop_pips=5),
]

manager = ProgressivePositionManager(stages=forex_stages, initial_stop_pips=15)
```

### Crypto Example (Aggressive)

```python
crypto_stages = [
    ProgressiveStage(profit_threshold=100, close_percentage=0.33, trailing_stop_pips=50),
    ProgressiveStage(profit_threshold=250, close_percentage=0.66, trailing_stop_pips=30),
    ProgressiveStage(profit_threshold=500, close_percentage=0.90, trailing_stop_pips=20),
]

manager = ProgressivePositionManager(stages=crypto_stages, initial_stop_pips=100)
```

### Day Trading Example (Very Tight)

```python
day_trading_stages = [
    ProgressiveStage(profit_threshold=10, close_percentage=0.30, trailing_stop_pips=5),
    ProgressiveStage(profit_threshold=20, close_percentage=0.60, trailing_stop_pips=3),
    ProgressiveStage(profit_threshold=30, close_percentage=0.80, trailing_stop_pips=2),
]

manager = ProgressivePositionManager(stages=day_trading_stages, initial_stop_pips=8)
```

## Using with ProgressiveTradingBot

For easier integration with your brokers:

```python
from examples.progressive_trading_example import ProgressiveTradingBot

# Create bot with your broker
bot = ProgressiveTradingBot(
    broker=your_broker_connector,
    progressive_stages=custom_stages  # or None for defaults
)

# Open trade
bot.open_trade(symbol="BTCUSD", side="LONG", entry_price=42000, size=0.1)

# Update positions (call on each price tick)
bot.update_positions({
    "BTCUSD": 42500,
    "EURUSD": 1.0980
})

# Get position status
status = bot.get_position_status("BTCUSD")
print(f"Profit: ${status['total_profit']:.2f}")
print(f"Remaining: {status['current_size']} units")
```

## Action Types

The `update_position()` method returns a list of actions to execute:

### PARTIAL_CLOSE
```python
{
    'type': 'PARTIAL_CLOSE',
    'symbol': 'EURUSD',
    'size': 2500,
    'price': 1.0980,
    'reason': 'Stage 1: +$30',
    'profit': 7.50
}
```

### UPDATE_STOP
```python
{
    'type': 'UPDATE_STOP',
    'symbol': 'EURUSD',
    'old_stop': 1.0930,
    'new_stop': 1.0960
}
```

### STOP_HIT
```python
{
    'type': 'STOP_HIT',
    'symbol': 'EURUSD',
    'price': 1.0940,
    'remaining_size': 5000,
    'total_profit': 80.00,
    'realized_profit': 32.50,
    'unrealized_profit': 47.50
}
```

### MANUAL_CLOSE
```python
{
    'type': 'MANUAL_CLOSE',
    'symbol': 'EURUSD',
    'price': 1.1000,
    'size': 7500,
    'reason': 'End of day',
    'profit': 37.50
}
```

## Position Summary

Get detailed position information:

```python
summary = manager.get_position_summary("EURUSD")

# Returns:
{
    'symbol': 'EURUSD',
    'side': 'LONG',
    'entry_price': 1.0950,
    'original_size': 10000,
    'current_size': 5000,
    'current_stage': 2,
    'trailing_stop_pips': 8.0,
    'current_stop': 1.1042,
    'highest_price': 1.1050,
    'realized_profit': 32.50,
    'unrealized_profit': 47.50,
    'total_profit': 80.00,
    'stages_executed': [1, 2],
    'partial_closes': 2
}
```

## Multi-Position Management

Manage multiple positions simultaneously:

```python
# Open multiple positions
manager.open_position("EURUSD", PositionSide.LONG, 1.0950, 10000, "order1")
manager.open_position("GBPUSD", PositionSide.LONG, 1.2700, 8000, "order2")
manager.open_position("USDJPY", PositionSide.SHORT, 149.50, 5000, "order3")

# Update all positions
price_data = {
    "EURUSD": 1.0980,
    "GBPUSD": 1.2730,
    "USDJPY": 149.20
}

for symbol, price in price_data.items():
    actions = manager.update_position(symbol, price)
    for action in actions:
        execute_action(action)

# Get all positions
all_positions = manager.get_all_positions()
for symbol, status in all_positions.items():
    print(f"{symbol}: ${status['total_profit']:.2f}")
```

## Integration with Existing Brokers

### Coinbase Advanced Trade

```python
from multi_broker_phoenix.brokers.coinbase_safe_connector import CoinbaseSafeConnector

broker = CoinbaseSafeConnector(paper_mode=False)
bot = ProgressiveTradingBot(broker=broker)

# Rest of your trading logic...
```

### Interactive Brokers

```python
from multi_broker_phoenix.brokers.ibkr_connector import IBKRConnector

broker = IBKRConnector(host='127.0.0.1', port=4002, client_id=1)
bot = ProgressiveTradingBot(broker=broker)
```

### OANDA

```python
from multi_broker_phoenix.brokers.oanda_connector import OandaConnector

broker = OandaConnector(account_id="your_account", api_key="your_key")
bot = ProgressiveTradingBot(broker=broker)
```

## Real-World Example

Complete trading loop:

```python
from multi_broker_phoenix.engines.progressive_position_manager import create_default_manager
from multi_broker_phoenix.brokers.coinbase_safe_connector import CoinbaseSafeConnector
import time

# Setup
broker = CoinbaseSafeConnector(paper_mode=False)
manager = create_default_manager()

# Open position from strategy signal
if strategy_signal == "BUY":
    current_price = broker.get_last_price("BTCUSD")
    manager.open_position(
        symbol="BTCUSD",
        side=PositionSide.LONG,
        entry_price=current_price,
        size=0.1,  # 0.1 BTC
        broker_order_id=broker.place_order(...)
    )

# Main loop (runs continuously)
while True:
    current_price = broker.get_last_price("BTCUSD")
    actions = manager.update_position("BTCUSD", current_price)
    
    for action in actions:
        if action['type'] == 'PARTIAL_CLOSE':
            broker.close_partial(action['symbol'], action['size'])
            print(f"✅ Closed {action['size']} units, locked ${action['profit']:.2f}")
        
        elif action['type'] == 'STOP_HIT':
            broker.close_position(action['symbol'])
            print(f"🛑 Position closed, total profit: ${action['total_profit']:.2f}")
            break
    
    time.sleep(1)  # Check every second
```

## Key Benefits

✅ **Automatic Profit Protection** - Locks in gains at each stage  
✅ **Let Winners Run** - Keeps portion of position in play  
✅ **Adaptive Stops** - Tightens as profit increases  
✅ **Multi-Broker Compatible** - Works with any connector  
✅ **Zero Manual Intervention** - Fully automated management  
✅ **Detailed Tracking** - Complete profit/loss accounting  

## Files

- **Engine**: `multi_broker_phoenix/engines/progressive_position_manager.py`
- **Example**: `examples/progressive_trading_example.py`
- **Documentation**: `DOCS/PROGRESSIVE_POSITION_MANAGEMENT.md`

## Testing

Run the test suite:

```bash
# Test the core engine
python3 MULTI_BROKER_PHOENIX/multi_broker_phoenix/engines/progressive_position_manager.py

# Run comprehensive examples
python3 MULTI_BROKER_PHOENIX/examples/progressive_trading_example.py
```

## Support

For questions or issues, check:
- Example implementations in `examples/progressive_trading_example.py`
- Inline documentation in `progressive_position_manager.py`
- Test scenarios in the module's `__main__` block
