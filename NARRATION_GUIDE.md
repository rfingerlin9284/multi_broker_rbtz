# 🎬 POSITION NARRATOR - Real-Time Trading Event Log

## What is Narration?

**Narration** is a real-time event logging system that records every trade, fill, and position change across all brokers. It creates a **complete audit trail** of your trading activity.

## Narration File: `narration.jsonl`

- **Location**: `/home/ing/RICK/MULTI_BROKER_PHOENIX/narration.jsonl`
- **Format**: JSONL (JSON Lines) - one event per line
- **Entries**: Each trade/event is a JSON object with timestamp, event type, broker, details

## Event Types Recorded

```
TRADE_OPENED       - New trade initiated
TRADE_CLOSED       - Trade exited (profit/loss)
POSITION_UPDATED   - Position size changed
ORDER_FILLED       - Order confirmed filled at broker
ORDER_REJECTED     - Order rejected (failed quality check)
STOP_HIT           - Stop loss triggered
TRAILING_STOP_HIT  - Trailing stop triggered
PROFIT_TAKEN       - Profit target hit
STRATEGY_SIGNAL    - Strategy generated signal
HIVE_VALIDATION    - AI Hive confirmed trade
BROKER_ERROR       - Exchange connection issue
```

## How to View Narration

### View Latest 20 Events:
```bash
tail -20 narration.jsonl | python3 -m json.tool
```

### View All OANDA Trades:
```bash
cat narration.jsonl | grep '"venue":"oanda"' | python3 -m json.tool
```

### View All IBKR Futures Trades:
```bash
cat narration.jsonl | grep '"venue":"ibkr"' | python3 -m json.tool
```

### View All Filled Orders:
```bash
cat narration.jsonl | grep '"event_type":"ORDER_FILLED"' | python3 -m json.tool
```

### Real-time Tail (Follow Live):
```bash
tail -f narration.jsonl | python3 -m json.tool
```

## Example Narration Entry

```json
{
  "ts": "2026-01-07T14:35:22.123456+00:00",
  "event_type": "ORDER_FILLED",
  "venue": "oanda",
  "symbol": "EUR_USD",
  "details": {
    "order_id": "12345",
    "size": 1000,
    "price": 1.0852,
    "direction": "BUY",
    "strategy": "holy_grail",
    "quality_score": 78.5,
    "pnl": 12.50,
    "status": "FILLED"
  }
}
```

## Understanding Each Field

| Field | Meaning | Example |
|-------|---------|---------|
| `ts` | Timestamp (UTC) | 2026-01-07T14:35:22Z |
| `event_type` | What happened | ORDER_FILLED |
| `venue` | Which broker | oanda, ibkr, coinbase |
| `symbol` | Trading pair/contract | EUR_USD, ES, BTC-USD |
| `details.order_id` | Broker's unique ID | 12345 |
| `details.size` | Position size | 1000 units |
| `details.price` | Entry/exit price | 1.0852 |
| `details.direction` | Long or Short | BUY, SELL |
| `details.strategy` | Which strategy fired | holy_grail, fabio_aaa_full |
| `details.quality_score` | Strategy confidence | 78.5 (out of 100) |
| `details.pnl` | Profit/Loss | +12.50, -5.00 |
| `details.status` | Order status | FILLED, PENDING, REJECTED |

## IBKR Proof Example

When IBKR places an order that gets filled, narration will show:

```json
{
  "ts": "2026-01-07T14:45:33.456789+00:00",
  "event_type": "ORDER_FILLED",
  "venue": "ibkr",
  "symbol": "ES",
  "details": {
    "contract": "E-mini S&P 500",
    "order_id": "98765",
    "size": 1,
    "price": 5847.25,
    "direction": "BUY",
    "strategy": "institutional_sd",
    "quality_score": 82.3,
    "status": "FILLED",
    "confirmation": "verified_at_broker"
  }
}
```

## OANDA Proof Example

```json
{
  "ts": "2026-01-07T14:50:12.789456+00:00",
  "event_type": "ORDER_FILLED",
  "venue": "oanda",
  "symbol": "GBP_USD",
  "details": {
    "order_id": "54321",
    "account": "002",
    "size": 2000,
    "price": 1.2645,
    "direction": "SELL",
    "strategy": "trap_reversal",
    "quality_score": 75.2,
    "status": "FILLED",
    "pnl": 18.75,
    "confirmation": "verified_at_broker"
  }
}
```

## Narration Statistics

```bash
# Count total trades
cat narration.jsonl | grep "ORDER_FILLED" | wc -l

# Count profits vs losses
cat narration.jsonl | grep '"pnl"' | grep -E '"\d+\.' | wc -l  # Profits
cat narration.jsonl | grep '"pnl"' | grep -E '"-\d+\.' | wc -l  # Losses

# Total PnL
cat narration.jsonl | python3 << 'EOF'
import json, sys
total = 0
for line in sys.stdin:
    try:
        event = json.loads(line)
        if 'pnl' in event.get('details', {}):
            total += event['details']['pnl']
    except:
        pass
print(f"Total PnL: ${total:,.2f}")
EOF

# By venue breakdown
cat narration.jsonl | python3 << 'EOF'
import json, sys
venues = {}
for line in sys.stdin:
    try:
        event = json.loads(line)
        venue = event.get('venue', 'unknown')
        venues[venue] = venues.get(venue, 0) + 1
    except:
        pass
for venue, count in sorted(venues.items()):
    print(f"{venue}: {count} events")
EOF
```

## How to Monitor Live Trading

### Terminal 1: Watch narration in real-time
```bash
tail -f narration.jsonl | python3 -m json.tool
```

### Terminal 2: Check broker status
```bash
watch -n 2 'tail -5 narration.jsonl'
```

### Terminal 3: Count filled orders
```bash
watch -n 5 'cat narration.jsonl | grep ORDER_FILLED | wc -l'
```

## What Happens When IBKR Trades

1. **Signal Generated**: Strategy analyzes ES contract → generates BUY signal (82% confidence)
2. **Quality Check**: Passes IBKR threshold (80% required) ✅
3. **Order Placed**: IBKR connector calls TWS API → place_order(ES, size=1, direction=BUY)
4. **Awaiting Fill**: Order stored in `_pending_fills` dictionary
5. **Verification**: `verify_order_filled()` polls TWS API every 2 seconds
6. **Fill Confirmed**: Order status = FILLED → moved to `_filled_orders`
7. **Narration Event**: New entry logged to narration.jsonl
   ```json
   {"ts":"...", "event_type":"ORDER_FILLED", "venue":"ibkr", "symbol":"ES", ...}
   ```
8. **Trade Tracked**: `get_filled_orders_count()` increments by 1

## Current Trading Status

**Engine Running**: YES ✅  
**Narration Active**: YES ✅  
**IBKR Connected**: YES ✅  
**Awaiting**: Strategy signals (will generate trades when market conditions match signal criteria)

## Next: Monitor Real Trading

When the engine generates the first trade:
1. Check narration: `tail -f narration.jsonl`
2. Verify fill in narration.jsonl
3. Count confirms in filled_orders_count
4. Check PnL in narration event details

**Narration = Proof of Trading** 📊
