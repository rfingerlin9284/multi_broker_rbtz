# Authentication & Paper Mode Documentation

## 🔐 AUTHENTICATION STATUS

### Coinbase Advanced Trade API

**Current Status:** ⚠️ **PARTIAL - Public API Only**

#### What's Working:
✅ **Public Data Access (No Auth Required)**
- Live price fetching via: `GET /api/v3/brokerage/products/{symbol}/ticker`
- Endpoint configured correctly: `https://api.coinbase.com/api/v3/brokerage`
- Successfully tested with BTC-USD price retrieval

#### What's NOT Implemented Yet:
❌ **Authenticated API Calls**
- Order placement (requires JWT authentication)
- Account balance checks
- Portfolio queries
- Order status/history

#### Your Credentials in `.env`:
```bash
COINBASE_API_KEY=organizations/5ae72c85.../apiKeys/0d84aa48...
COINBASE_API_SECRET=-----BEGIN EC PRIVATE KEY-----\n...
```

**These credentials are CONFIGURED but NOT YET USED** because authenticated endpoint calls require:
1. JWT token generation using EC private key
2. Request signing with timestamp + method + path + body
3. Headers: `CB-ACCESS-KEY`, `CB-ACCESS-SIGN`, `CB-ACCESS-TIMESTAMP`

#### To Enable Full Authentication:
The `place_live_order()` method currently raises:
```python
NotImplementedError(
    "Real Coinbase order placement not yet implemented. "
    "Requires Coinbase API authentication setup."
)
```

**Next Steps for Real Trading:**
1. Implement JWT token generation with your EC private key
2. Add request signing function
3. Implement authenticated POST to `/api/v3/brokerage/orders`
4. Add error handling for API responses

---

### IBKR (Interactive Brokers)

**Current Status:** ✅ **FULLY AUTHENTICATED (Paper Mode)**

#### Working:
- TWS/IB Gateway connection on port 4002 (paper trading)
- Market data subscriptions
- Order placement in paper account
- Real-time position updates

#### Configuration:
- Connection type: TWS API (native client)
- Paper account: Fully isolated from real money
- All orders go to IBKR's paper trading servers

---

## 📊 PAPER MODE DOCUMENTATION

### Where Everything is Logged

#### 1. SQLite Databases (Primary Storage)

**Location:** `/home/ing/RICK/MULTI_BROKER_PHOENIX/data/`

```bash
paper_ledger.sqlite       # Main production paper ledger (20 KB)
test_ibkr.sqlite         # IBKR test trades (20 KB, 1 trade)
test_coinbase.sqlite     # Coinbase test trades (20 KB, 1 trade)
```

**Database Schema:**
```sql
CREATE TABLE trades (
    id TEXT PRIMARY KEY,              -- e.g. "CB-PAPER-BTCUSD-123456"
    ts TEXT,                          -- ISO timestamp
    platform TEXT,                    -- "COINBASE", "IBKR", "OANDA"
    strategy_id TEXT,                 -- Strategy that generated signal
    symbol TEXT,                      -- e.g. "BTC-USD", "GC"
    side TEXT,                        -- "BUY", "SELL", "LONG", "SHORT"
    entry REAL,                       -- Intended entry price
    fill_price REAL,                  -- Actual simulated fill
    stop REAL,                        -- Stop loss level
    size REAL,                        -- Position size
    fees REAL,                        -- Simulated fees
    status TEXT,                      -- "FILLED", "PENDING", etc.
    execution_type TEXT               -- "SIMULATED", "PAPER_PLATFORM", etc.
)
```

**View Your Trades:**
```bash
cd /home/ing/RICK/MULTI_BROKER_PHOENIX/data

# All trades
python3 -c "import sqlite3; conn = sqlite3.connect('test_coinbase.sqlite'); 
for row in conn.execute('SELECT * FROM trades'): print(row)"

# Summary stats
python3 -c "import sqlite3; conn = sqlite3.connect('test_coinbase.sqlite'); 
print('Total trades:', conn.execute('SELECT COUNT(*) FROM trades').fetchone()[0])"
```

#### 2. Console Logs (Real-Time Output)

**What You See During Testing:**
```
🔧 Coinbase Advanced Trade Connector initialized: 🟢 SIMULATION
   API: Coinbase Advanced Trade (v3)
   Min trade: $5.00, Max: $10.00
   Daily loss limit: $50.00
   Max trades/day: 10

🟢 PAPER: BTC-USD BUY 0.000117 @ $85233.45 ($10.00)
📍 Position opened: BTC-USD BUY 0.000117 @ $85233.45
   Initial stop: $83328.98 (-2%)
   Trail activates at: $86510.95 (+1.5%)
```

#### 3. Log Files

**Active Log Files:**
```bash
./logs/rick_battlestation.log          # Main system log
./logs/websocket_api.log               # WebSocket API events
./logs/tmux_dashboard.log              # Dashboard output
./hive_real/worker.log                 # AI Hive worker logs
./hive_dashboard/hive_server.log       # AI Hive dashboard
```

**AI Hive Repair Logs:**
```bash
./hive_real/repair_logs/repair_log_YYYYMMDD_HHMMSS.json
```

Captures autonomous repair attempts with:
- Error details
- AI diagnosis
- Consensus vote
- Patch code
- Success/failure status

#### 4. Paper Engine Tracking

**In-Memory State:**
- Current equity balance
- Open positions
- Unrealized P&L
- Daily statistics

**Persisted to Database:**
- All filled orders
- Entry/exit prices
- Fees and slippage
- Timestamps

---

## 🎯 HOW TO VERIFY SYSTEM IS WORKING

### Without Placing Orders

#### 1. Check Database Activity
```bash
cd /home/ing/RICK/MULTI_BROKER_PHOENIX/data

# Watch trade count grow
watch -n 5 "python3 -c 'import sqlite3; conn = sqlite3.connect(\"paper_ledger.sqlite\"); print(\"Trades:\", conn.execute(\"SELECT COUNT(*) FROM trades\").fetchone()[0])'"
```

#### 2. Monitor Log Files
```bash
cd /home/ing/RICK/MULTI_BROKER_PHOENIX

# Tail main system log
tail -f logs/rick_battlestation.log

# Watch for strategy signals
grep -i "signal" logs/rick_battlestation.log

# Check AI Hive activity
tail -f hive_real/worker.log
```

#### 3. Check Paper Engine Equity
```python
# In Python console:
from multi_broker_phoenix.engines.paper_engine import PaperEngine

engine = PaperEngine(db_path='data/paper_ledger.sqlite')
equity = engine.get_current_equity()
print(f"Current Equity: ${equity:,.2f}")
```

#### 4. AI Hive Console Output
When running `tools/run_headless.py`, watch for:
```
🤖 API-BASED REAL AI HIVE ANALYSIS
   Symbol: GC
   Direction: BUY
   Entry: 2655.80
   🧠 Querying OpenAI ChatGPT API...
      ✅ BUY (70.0%)
   🧠 Querying xAI Grok API...
      ✅ BUY (85.0%)
```

#### 5. Safety Limit Tracking
Coinbase connector logs daily stats:
```
📊 Today: 3 trades, $12.45 loss
   Remaining trades: 7/10
   Remaining loss budget: $37.55
```

---

## 📈 PROGRESSION TRACKING

### Smart Progression Status

**Enabled in `.env`:**
```bash
PROGRESSION_ENABLED=true
```

**5-Phase Leverage Scaling:**
- Phase 1: 100 trades, 55% win rate, 1.5 PF → 1x leverage
- Phase 2: 100 trades, 58% win rate, 1.7 PF → 2x leverage
- Phase 3: 100 trades, 60% win rate, 1.8 PF → 4x leverage
- Phase 4: 100 trades, 61% win rate, 1.9 PF → 7x leverage
- Phase 5: 100 trades, 62% win rate, 2.0 PF → 10x leverage

**Check Current Phase:**
```python
from multi_broker_phoenix.engines.paper_engine import PaperEngine

engine = PaperEngine(db_path='data/paper_ledger.sqlite')
stats = engine.get_performance_stats()
print(f"Win Rate: {stats['win_rate']:.1%}")
print(f"Profit Factor: {stats['profit_factor']:.2f}")
print(f"Total Trades: {stats['total_trades']}")
```

---

## 🔍 FULL SYSTEM HEALTH CHECK

### Run This to Verify Everything:

```bash
cd /home/ing/RICK/MULTI_BROKER_PHOENIX/MULTI_BROKER_PHOENIX

# Check .env configuration
echo "=== CONFIGURATION ==="
grep -E "HEADLESS_MODE|ENABLE_AI_HIVE|COINBASE_API_KEY|PROGRESSION_ENABLED" ../.env

# Check databases
echo -e "\n=== DATABASES ==="
ls -lh ../data/*.sqlite

# Check trade counts
echo -e "\n=== TRADE COUNTS ==="
for db in ../data/*.sqlite; do
    echo "$(basename $db): $(python3 -c "import sqlite3; print(sqlite3.connect('$db').execute('SELECT COUNT(*) FROM trades').fetchone()[0])")"
done

# Check AI Hive status
echo -e "\n=== AI HIVE ==="
python3 -c "from hive_real.api_ai_hive import api_ai_hive; print('OpenAI:', 'OK' if api_ai_hive.openai_key else 'MISSING'); print('xAI:', 'OK' if api_ai_hive.xai_key else 'MISSING')"

# Check if IBKR TWS is running
echo -e "\n=== IBKR CONNECTION ==="
netstat -an | grep 4002 || echo "Port 4002 not active"

echo -e "\n✅ Health check complete!"
```

---

## 🚨 SAFETY REMINDERS

### Paper Mode is DEFAULT
- All new connectors initialize with `paper_mode=True`
- Real orders require explicit `paper_mode=False` + authenticated API

### Coinbase Safety Limits (Even in Paper Mode)
- $5-10 per trade (nano-lots)
- $50 daily loss limit
- 10 trades per day max
- Stops after 5 consecutive losses

### When Ready for Real Money
1. Verify 500+ paper trades with positive P&L
2. Implement Coinbase JWT authentication
3. Set `TRADING_MODE=LIVE` in `.env`
4. Start with MINIMUM position sizes
5. Monitor EVERY trade manually at first

---

## 📝 SUMMARY

### ✅ What You Have Now:
- Coinbase public API (price fetching) working
- Credentials configured but unused
- Full paper mode logging to SQLite
- Console output for real-time monitoring
- AI Hive consensus system operational
- IBKR paper trading fully functional
- Smart progression tracking ready

### ⚠️ What You Need for Real Trading:
- Coinbase JWT authentication implementation
- Authenticated endpoint testing
- Real money safeguards verification
- Manual approval process for first trades

### 📊 Where to Look:
- **Trades:** `/home/ing/RICK/MULTI_BROKER_PHOENIX/data/*.sqlite`
- **Logs:** `/home/ing/RICK/MULTI_BROKER_PHOENIX/logs/*.log`
- **AI Hive:** `/home/ing/RICK/MULTI_BROKER_PHOENIX/hive_real/repair_logs/`
- **Config:** `/home/ing/RICK/MULTI_BROKER_PHOENIX/.env`

**Everything is being documented. You're safe to learn without risk.**
