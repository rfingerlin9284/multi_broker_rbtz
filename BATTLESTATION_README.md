# 🚀 RICK BATTLESTATION - Unified Trading Command Center

**PIN: 841921** | **Charter Compliant** | **Full Integration Complete**

---

## 🎯 WHAT IS THIS?

The **RICK BATTLESTATION** is a unified autonomous trading system that combines:
- **Dual-broker execution**: Coinbase (real nano-lots) + IBKR (paper account)
- **5-phase progression**: Auto-graduate from $10 → futures based on performance
- **Multi-layer safety**: Crypto entry gates + Guardian gates + Trailing stops
- **Adaptive AI learning**: ML system that learns from outcomes and optimizes
- **Real-time dashboard**: WebSocket streaming with live P&L, positions, events
- **Voice narration**: Text-to-speech announcements for trades and milestones

---

## 🏗️ ARCHITECTURE

```
RICK BATTLESTATION
├── Trading Engine (Python)
│   ├── Coinbase Safe Connector: Nano-lots ($5-10), trailing stops
│   ├── IBKR Connector: Paper account ($1M fake money)
│   ├── Progression Manager: 5 phases, auto-graduation
│   └── Position Monitoring: 2-second loop, trailing stop updates
│
├── Entry Gates (Python)
│   ├── Hive Mind: Multi-AI consensus (90% threshold for crypto)
│   ├── Crypto Entry Gates: Time windows, volatility sizing, confluence
│   └── Signal Filtering: 4/5 gates must pass before execution
│
├── Guardian Gates (Python)
│   ├── Margin Check: Block if >35% utilization
│   ├── Position Limits: Max 3 concurrent positions
│   └── Correlation: Prevent over-exposure to USD pairs
│
├── Adaptive AI (Python)
│   ├── Learning Database: SQLite storage of decisions + outcomes
│   ├── Pattern Recognition: Success rate analysis
│   └── Parameter Optimization: Auto-adjust based on performance
│
├── WebSocket API (Python)
│   ├── Port 8888: Real-time data streaming
│   ├── Broadcasts: Trades, P&L, phases, gate results
│   └── Dashboard Integration: JSON message protocol
│
├── Dashboard (HTML/JavaScript)
│   ├── Real-time Display: Positions, P&L, phase, statistics
│   ├── Event Log: Trade history with timestamps
│   └── Voice Narrator: Rick-style trade announcements
│
└── TMUX Server (Node.js - Optional)
    ├── Port 4567: Dashboard HTTP server
    ├── Port 8887: TMUX output streaming
    └── Session Management: rbotmaster session
```

---

## 🛡️ SAFETY SYSTEMS

### Trailing Stops
- **Initial Stop**: 2% below entry (LONG) or above entry (SHORT)
- **Activation**: Triggered at 1.5% profit
- **Trail Distance**: 1% from highest price (LONG) or lowest price (SHORT)
- **Update Frequency**: Every 2 seconds

### Position Limits
- **Nano-lots**: $5-10 per trade (Phase 1)
- **Daily Loss**: Max $50 before shutdown
- **Max Trades/Day**: 10 trades
- **Consecutive Losses**: Stop after 5 losses in a row
- **Max Positions**: 3 concurrent positions (Guardian gate)

### Entry Gate Requirements
1. **Hive Consensus**: ≥90% AI agreement (crypto), ≥80% (forex)
2. **Time Windows**: 8 AM - 4 PM ET (optimal volatility)
3. **Volatility Check**: Adjust size based on current volatility
4. **Confluence Score**: 4/5 gates must pass
5. **Risk/Reward**: Minimum 2:1 ratio

### Guardian Gate Checks (Pre-Trade)
1. **Margin Utilization**: Must be <35%
2. **Concurrent Positions**: Must be <3
3. **USD Correlation**: Prevent over-exposure
4. **Charter Compliance**: All trades verified against charter

---

## 📊 5-PHASE PROGRESSION

### Phase 1: NANO_SPOT (Starting Phase)
- **Position Size**: $10
- **Leverage**: 1x (spot only)
- **Graduation**: 100 trades, 55% WR, 1.5 PF, 10% ROI, 14 days

### Phase 2: SCALED_SPOT
- **Position Size**: $50
- **Leverage**: 1x (spot only)
- **Graduation**: 50 trades, 57% WR, 1.6 PF, 15% ROI, 14 days

### Phase 3: LOW_LEVERAGE (First Futures)
- **Position Size**: $100
- **Leverage**: 3x
- **Graduation**: 50 trades, 58% WR, 1.7 PF, 20% ROI, 14 days

### Phase 4: MID_LEVERAGE
- **Position Size**: $200
- **Leverage**: 5x
- **Graduation**: 50 trades, 60% WR, 1.8 PF, 25% ROI, 14 days

### Phase 5: HIGH_LEVERAGE (Maximum Phase)
- **Position Size**: $500
- **Leverage**: 10x
- **Goal**: $200/day profit sustainable

**Graduation is AUTOMATIC** - system checks criteria after each trade.

---

## 🚀 QUICK START

### 1. Prerequisites
```bash
# Python 3.12+ with packages
pip install -r requirements.txt

# Node.js (optional, for TMUX dashboard)
sudo apt install nodejs npm

# Running services
# - Coinbase API credentials in .env
# - IBKR TWS on port 4002 (optional)
```

### 2. Launch Battlestation
```bash
# From workspace root
bash tools/start_battlestation.sh

# Or use VSCode task: "🚀 RICK BATTLESTATION: Launch"
```

**You will be prompted to type "LAUNCH"** to confirm real money trading.

### 3. Access Dashboard
```bash
# Open browser to:
http://localhost:4567/battlestation.html

# Or directly connect WebSocket:
ws://localhost:8888
```

### 4. Monitor Logs
```bash
# Real-time battlestation log
tail -f logs/rick_battlestation.log

# WebSocket API log
tail -f logs/websocket_api.log

# Dashboard log (if Node.js)
tail -f logs/tmux_dashboard.log
```

### 5. Shutdown
```bash
# Graceful shutdown (closes all positions)
bash tools/stop_battlestation.sh

# Or use VSCode task: "🛑 RICK BATTLESTATION: Shutdown"
```

---

## 📡 DASHBOARD FEATURES

### Real-Time Display
- **Current Phase**: Visual indicator with phase number
- **Capital & P&L**: Total and daily profit/loss
- **Win Rate**: Live calculation from all trades
- **Profit Factor**: Gross profit / gross loss ratio
- **Open Positions**: Symbol, entry, size, unrealized P&L
- **Event Log**: Trade entries, exits, phase graduations

### Voice Narration
- **Trade Entry**: "Entering BTC-USD. Position locked and loaded."
- **Trade Exit**: "BTC-USD closed. P and L: profit 2.50 dollars."
- **Phase Graduation**: "Phase graduation achieved. Welcome to phase 2."
- **Gate Rejection**: Silent (not narrated to avoid spam)

### WebSocket Protocol
```json
// Status Update (every 60 seconds)
{
  "type": "status_update",
  "data": {
    "phase": "NANO_SPOT",
    "capital": 15.00,
    "total_pnl": 5.00,
    "win_rate": 0.60,
    "open_positions": [...]
  }
}

// Trade Opened
{
  "type": "trade_opened",
  "data": {
    "symbol": "BTC-USD",
    "side": "BUY",
    "price": 87500.0
  },
  "voice_text": "Entering BTC-USD..."
}

// Trade Closed
{
  "type": "trade_closed",
  "data": {
    "symbol": "BTC-USD",
    "pnl": 2.50
  },
  "voice_text": "BTC-USD closed. Profit 2.50 dollars."
}
```

---

## 🧠 ADAPTIVE AI LEARNING

The battlestation includes a self-learning system that:

1. **Records Every Decision**: Symbol, confidence, reasoning, ML factors
2. **Tracks Outcomes**: Win/loss, P&L, holding time
3. **Identifies Patterns**: High-success setups vs. low-success setups
4. **Adapts Parameters**: Adjusts entry thresholds, position sizing, stop distances
5. **Maintains Database**: `rick_hive/rick_learning.db`

### Learning Metrics
- **Pattern Success Rate**: % wins for each setup type
- **Average P&L**: Mean profit/loss per pattern
- **Frequency**: How often pattern appears
- **Confidence Weighting**: Higher confidence = more weight

### Adaptation Logic
- After 50 trades: Initial parameter adjustments
- After 100 trades: Full optimization enabled
- Continuous: Real-time learning from each outcome

---

## 📂 PROJECT STRUCTURE

```
MULTI_BROKER_PHOENIX/
├── tools/
│   ├── start_battlestation.sh         # Master launcher
│   ├── stop_battlestation.sh          # Complete shutdown
│   ├── start_dual_broker_live.sh      # Legacy dual-broker only
│   └── stop_trading_engine.sh         # Legacy stop only
│
├── MULTI_BROKER_PHOENIX/
│   └── multi_broker_phoenix/
│       ├── brokers/
│       │   ├── coinbase_safe_connector.py    # Nano-lots + trailing stops
│       │   └── ibkr_connector.py             # IBKR paper trading
│       ├── engines/
│       │   ├── rick_battlestation.py         # Main unified system
│       │   └── progression_manager.py        # 5-phase system
│       └── api/
│           └── websocket_server.py           # Dashboard streaming
│
├── rick_hive/
│   ├── crypto_entry_gate_system.py    # 90% consensus gates
│   ├── guardian_gates.py              # Pre-trade validation
│   ├── adaptive_rick.py               # ML learning system
│   ├── rick_hive_mind.py              # Multi-AI delegation
│   └── rick_learning.db               # Learning database
│
├── hive_dashboard/
│   ├── battlestation.html             # Main dashboard UI
│   ├── rick_voice_narrator.js         # Text-to-speech
│   ├── tmux_server.js                 # Node.js server (optional)
│   └── pnl_hud.js                     # Legacy P&L widget
│
├── data/
│   └── progression_state.json         # Phase progression state
│
├── logs/
│   ├── rick_battlestation.log         # Main engine log
│   ├── websocket_api.log              # API server log
│   └── tmux_dashboard.log             # Dashboard log
│
└── .vscode/
    └── tasks.json                     # VSCode tasks integration
```

---

## 🔧 CONFIGURATION

### Environment Variables (.env)
```bash
# Coinbase (REQUIRED)
COINBASE_API_KEY=organizations/.../apiKeys/...
COINBASE_API_SECRET=-----BEGIN EC PRIVATE KEY-----...
COINBASE_MIN_TRADE_USD=5.0
COINBASE_MAX_TRADE_USD=10.0
COINBASE_DAILY_LOSS_LIMIT=50.0
COINBASE_MAX_TRADES_PER_DAY=10
COINBASE_STOP_ON_CONSECUTIVE_LOSSES=5

# Trailing Stops
COINBASE_INITIAL_STOP_LOSS_PCT=2.0
COINBASE_TRAILING_STOP_ACTIVATION_PCT=1.5
COINBASE_TRAILING_STOP_DISTANCE_PCT=1.0

# Progression
PROGRESSION_ENABLED=true
PROGRESSION_STATE_FILE=data/progression_state.json
PROGRESSION_STARTING_CAPITAL=10.0
PROGRESSION_STARTING_PHASE=1

# IBKR (OPTIONAL)
IBKR_HOST=localhost
IBKR_PORT=4002
IBKR_CLIENT_ID=1
IBKR_PAPER_MODE=true
```

---

## 🎬 USAGE EXAMPLES

### Scenario 1: First Day Trading
```bash
# 1. Launch battlestation
bash tools/start_battlestation.sh
# Type "LAUNCH" when prompted

# 2. Open dashboard in browser
# Navigate to http://localhost:4567/battlestation.html

# 3. System starts in Phase 1
# - $10 position size
# - 2% trailing stops
# - Entry gates filtering all signals

# 4. Monitor for 14 days
# - Track win rate, profit factor, ROI
# - System auto-graduates to Phase 2 if criteria met

# 5. Shutdown at end of day
bash tools/stop_battlestation.sh
```

### Scenario 2: Already at Phase 3
```bash
# If progression_state.json shows Phase 3:
# - Position size: $100
# - Leverage: 3x (futures trading enabled)
# - Higher win rate requirement: 58%

# Launch same way, system loads saved state
bash tools/start_battlestation.sh
```

### Scenario 3: Debugging
```bash
# Check why signal was rejected
tail -f logs/rick_battlestation.log | grep "REJECTED"

# Watch all gate evaluations
tail -f logs/rick_battlestation.log | grep -E "(Entry Gates|Guardian)"

# Monitor WebSocket messages
wscat -c ws://localhost:8888
```

---

## ⚠️ TROUBLESHOOTING

### Battlestation Won't Start
```bash
# Check Python path
echo $PYTHONPATH

# Verify Coinbase credentials
grep COINBASE_API_KEY .env

# Check for port conflicts
lsof -i :8888
lsof -i :4567

# View startup errors
cat logs/rick_battlestation.log
```

### Dashboard Not Connecting
```bash
# Is WebSocket server running?
ps aux | grep websocket_server

# Test WebSocket manually
wscat -c ws://localhost:8888

# Check firewall (WSL)
sudo ufw status
```

### IBKR Not Working
```bash
# Check TWS is running on port 4002
nc -z localhost 4002

# IBKR is OPTIONAL - Coinbase will work alone
# System will log warning but continue

# Restart TWS with port 4002 enabled
```

### No Trades Executing
```bash
# Most likely: Entry gates rejecting all signals

# Check rejection reasons
grep "Entry Gates REJECTED" logs/rick_battlestation.log

# Common reasons:
# - Hive consensus <90%
# - Outside time window (8 AM - 4 PM ET)
# - Volatility too high/low
# - Confluence score <4/5

# Lower thresholds (testing only):
# Edit rick_hive/crypto_entry_gate_system.py
# Change CRYPTO_AI_HIVE_VOTE_CONSENSUS = 0.90 to 0.80
```

---

## 🎯 ROADMAP / TODO

- [ ] Integrate actual strategy signal generation (currently monitoring only)
- [ ] Add backtesting mode with historical data replay
- [ ] Implement position correlation calculator in guardian gates
- [ ] Add Telegram notifications for phase graduations
- [ ] Create mobile dashboard (responsive design)
- [ ] Add risk-adjusted performance metrics (Sharpe, Sortino)
- [ ] Implement portfolio heat map (sector exposure)
- [ ] Add machine learning model training interface
- [ ] Create paper trading mode (no API calls)
- [ ] Build IBKR position monitoring (currently TODO)

---

## 📚 RELATED DOCS

- [Coinbase API Setup](DOCS/coinbase_api_setup.md)
- [IBKR Setup](DOCS/setup_ibkr.md)
- [OANDA Setup](DOCS/setup_oanda.md) (legacy)
- [Progression System](PR_DESCRIPTIONS/PR-02-engine-sizing.md)
- [Strategy Registry](PR_DESCRIPTIONS/PR-01-strategies.md)

---

## 🏆 SUCCESS METRICS

### Phase 1 Target (14 days)
- 100 trades @ 55%+ win rate
- Profit factor ≥1.5
- ROI ≥10%
- Max drawdown <10%
- Result: Graduate to Phase 2 ($50 positions)

### Phase 5 Target (6+ months)
- Consistent $200/day profit
- Win rate ≥62%
- Profit factor ≥2.0
- Trading with 10x leverage on futures
- Fully autonomous with ML optimization

---

## 🔐 SECURITY

- **API Keys**: Stored in `.env` (gitignored)
- **PIN Protection**: All components require PIN 841921
- **Charter Enforcement**: Built into every gate system
- **Position Limits**: Hard-coded maximums cannot be exceeded
- **Emergency Shutdown**: Signal handlers (Ctrl+C, SIGTERM)

---

## 📞 SUPPORT

If issues persist:
1. Check all logs in `logs/` directory
2. Verify `.env` configuration
3. Review [CHANGES.md](CHANGES.md) for recent updates
4. Check VSCode task output for errors

**Built with**: Python 3.12, Node.js, WebSocket, SQLite, Chart-compliant architecture
**Tested on**: WSL Ubuntu, Linux
**License**: Private / Internal Use

---

🚀 **GOOD HUNTING!** 🚀
