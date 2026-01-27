# 🤖 RBOTZILLA TASK GUIDE

## VS Code Task Descriptions for Autonomous Operation

> **Last Updated:** 2026-01-11
> **Purpose:** Complete reference for all VS Code tasks and what they do

---

## 🚀 LAUNCH TASKS (How to Start)

### **🤖 RBOTZILLA: Launch Menu (DEFAULT)** ⭐ _Press Ctrl+Shift+B_

**What it does:** Opens an interactive menu where you can choose what to start.
**When to use:** When you want to manually select which mode to run.
**Environment:** Uses RBOTZILLA_LAUNCH.sh interactive script.

---

### **🚀 RBOTZILLA: Start ALL Brokers + Hive (multi-asset)** ✅ _RECOMMENDED_

**What it does:** Starts the FULL trading system with:

- **OANDA Practice** (Forex: EUR/USD, GBP/USD, USD/JPY, etc.)
- **IBKR Paper** (Forex: Same pairs through Gateway)
- **Coinbase Live** (Crypto: BTC-USD, ETH-USD)
- **AI Hive** (Grok + OpenAI consensus on every trade)

**Features Enabled:**
| Feature | Status | Description |
|---------|--------|-------------|
| AI Hive | ✅ ON | Every trade gets AI consensus vote |
| Trailing Stops | ✅ ON | Progressive profit locking (20→12→8→5 pips) |
| Kelly Criterion | ✅ ON | Dynamic position sizing based on win rate |
| Smart Aggression | ✅ ON | Hedging, pyramiding, sniping enabled |
| Multi-Broker | ✅ ON | All 3 brokers trade simultaneously |

**Symbols Traded:**

```
Forex: EUR_USD, GBP_USD, USD_JPY, AUD_USD, USD_CAD, NZD_USD, USD_CHF
Crypto: BTC-USD, ETH-USD
```

---

### **🚀 RBOTZILLA: START EVERYTHING (multi-asset + monitors)**

**What it does:** Launches the multi-asset trading + opens monitoring panels:

1. Starts `multi-asset` mode (all brokers)
2. Opens Narration Monitor (human-readable trade explanations)
3. Opens Trade Log tail (see fills in real-time)

**Best for:** Full production monitoring with visibility into what the bot is doing.

---

### **🚀 RBOTZILLA: Start Coinbase Canary Mode** 🐤

**What it does:** CONSERVATIVE mode for crypto only:

- **Coinbase LIVE only** (real money but tiny trades)
- Uses `HOLY_GRAIL` strategy (most tested)
- BTC-USD and ETH-USD only
- Extra verbose logging

**Risk Level:** 🟢 LOW (nano-lot sizes, single broker)
**Best for:** Testing live execution with minimal capital at risk.

---

### **🚀 RBOTZILLA: Run Headless (choose mode)**

**What it does:** Prompts you to pick a mode from a dropdown:

- `auto` - Let the system decide based on .env
- `multi-asset` - All brokers, all symbols
- `platform-paper` - Paper trading only
- `simulate` - Full simulation (no real orders)
- `oanda-only` - OANDA Practice only
- `coinbase-only` - Coinbase only
- `ibkr-only` - IBKR Gateway only

---

## 📊 MONITORING TASKS

### **ONCE STARTED: 🎬 Narration Monitor (human)**

**What it does:** Shows human-readable explanations of every action:

```
[17:05:03] 🎯 SIGNAL: EUR/USD BUY @ 1.0850
           Strategy: HOLY_GRAIL (price action support bounce)
           AI Hive: APPROVE (65% confidence)
           Position: $162.75 (1.55% risk)
           SL: 1.0800 | TP: 1.0950 | R:R 2.0:1
```

**Best for:** Understanding what the bot is thinking and why.

---

### **ONCE STARTED: 📊 View Live Status (tail /tmp/trades.db.log)**

**What it does:** Streams the raw trade database log showing:

- Fills as they happen
- Position updates
- P&L changes

---

### **ONCE STARTED: 🔍 Check Market Sessions**

**What it does:** Shows which market sessions are currently active:

```
🌏 ASIA: CLOSED (opens 18:00 EST)
🇪🇺 LONDON: OPEN (3 hours remaining)
🇺🇸 NEW YORK: OPEN (5 hours remaining)
```

---

## 🛑 STOP/EMERGENCY TASKS

### **ONCE STARTED: 🚨 Emergency Stop (kills run_headless.py)**

**What it does:** IMMEDIATELY kills all trading processes.
**When to use:** Something is wrong and you need to stop NOW.
**Warning:** Does NOT close open positions - they remain on brokers.

---

### **ONCE STARTED: 🛑 Stop Trading Engine**

**What it does:** Gracefully stops the trading engine:

- Cancels pending orders
- Optionally closes positions
- Clean shutdown

---

### **🛑 RICK BATTLESTATION: Shutdown**

**What it does:** Stops the web dashboard and all related services.

---

## 🧠 WHAT EACH COMPONENT DOES

### **AI Hive Consensus System**

Every trade signal passes through the AI Hive:

1. **Grok (xAI)** - Technical analysis agent (PRIMARY)
2. **OpenAI GPT** - Fundamental/sentiment agent (BACKUP)

Both must vote BUY/SELL for trade to execute. VETO from either = no trade.

### **Progressive Trailing Stops**

Positions are managed in stages:
| Profit | Action | New Stop |
|--------|--------|----------|
| +$30 | Close 25% | 12-pip trail |
| +$60 | Close 50% | 8-pip trail |
| +$100 | Close 75% | 5-pip trail |
| Final 25% rides with tight 5-pip stop |

### **Kelly Criterion Position Sizing**

Position size = f(win_rate, avg_win, avg_loss)

- Uses **Half-Kelly** for safety margin
- Scales UP on win streaks (up to 2x leverage)
- Scales DOWN in drawdown (50% size reduction >10% DD)

### **Smart Aggression Features**

| Feature          | Description                              |
| ---------------- | ---------------------------------------- |
| Hedging          | Opens inverse position if down >1.5%     |
| Sniping          | Quick opportunistic trades on vol spikes |
| Pyramiding       | Adds to winners after +2% profit         |
| Mean Reversion   | Counter-trend at RSI extremes            |
| Breakout Hunting | Catches explosive moves on high volume   |

---

## 🔧 BROKER REQUIREMENTS

| Broker   | Requirement                  | Mode     |
| -------- | ---------------------------- | -------- |
| OANDA    | API token in `.env`          | Practice |
| IBKR     | Gateway running on port 7497 | Paper    |
| Coinbase | API keys in `.env`           | LIVE     |

### Starting IBKR Gateway:

1. Open IB Gateway application
2. Login to paper trading account
3. Ensure API is enabled on port 7497
4. Whitelist WSL IP: 172.25.80.1

---

## ⚡ QUICK START

**To start EVERYTHING with full monitoring:**

1. Press `Ctrl+Shift+P` → "Tasks: Run Task"
2. Select **🚀 RBOTZILLA: START EVERYTHING (multi-asset + monitors)**
3. Watch the narration panel for trade decisions

**To stop everything:**

1. Press `Ctrl+Shift+P` → "Tasks: Run Task"
2. Select **ONCE STARTED: 🚨 Emergency Stop**

---

## 📁 Key Files

| File                          | Purpose                           |
| ----------------------------- | --------------------------------- |
| `RBOTZILLA_CORE_EXTRACT/.env` | All API keys and config           |
| `hive_real/api_ai_hive.py`    | AI Hive voting logic              |
| `tools/smoke_test.py`         | Verify all systems before trading |
| `narration.jsonl`             | Trade decision history            |

---

## 🎯 STRATEGIES AVAILABLE

**Currently ENABLED (5):**

1. **HOLY_GRAIL** - Support/resistance + price action
2. **LIQUIDITY_SWEEP** - Sweep reversals (R:R 2.5:1)
3. **EMA_SCALPER** - Fast EMA crossover scalps
4. **INSTITUTIONAL_SD** - Volatility breakouts
5. **TRAP_REVERSAL** - False breakout reversals

**Available but DISABLED (11):** FABIO_AAA_FULL, FVG_WOLF, FIB_CONFLUENCE, CRYPTO_BREAKOUT, BULLISH_WOLF, BEARISH_WOLF, SIDEWAYS_WOLF, CORRELATION_WOLF, FIBONACCI_WOLF, EVENT_STRADDLE, HIGH_PROB_CORE

---

_This guide is for autonomous operation. RBOTzilla will trade according to these rules without human intervention._
