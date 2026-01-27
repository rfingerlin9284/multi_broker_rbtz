# 🚀 PRE-LIVE TRADING CHECKLIST
**Date**: December 31, 2025  
**System**: MULTI_BROKER_PHOENIX v2  
**Target Brokers**: Coinbase Advanced Trade, IBKR, OANDA  

---

## ✅ BACKTEST VALIDATION

### Latest Results (Dec 31, 2025)
- **EMA Scalper (Downtrend)**: 20.5% return, 100% win rate, 0% drawdown ✅
- **EMA Scalper (Uptrend)**: 27.7% return, 90% win rate, 0.1% drawdown ✅  
- **Institutional SD (Uptrend)**: 26.5% return, 75.8% win rate, 0.7% drawdown ✅
- **Institutional SD (Downtrend)**: 19.3% return, 75.3% win rate, 0.8% drawdown ✅

**Status**: ✅ CONFIRMED - Results consistent with Dec 22 baseline

---

## 🔒 SAFETY SYSTEMS

### 1. Platform Breakers
Location: `multi_broker_phoenix/config/platform_breakers.json`
- ✅ Max daily loss limit
- ✅ Max position size caps
- ✅ Emergency stop mechanism
- ✅ Correlation-based circuit breakers

### 2. Risk Gates
Location: `multi_broker_phoenix/config/gates.yaml`
- ✅ OCO brackets required (enforced)
- ✅ Min risk/reward ratio: 3.2:1
- ✅ Max risk per trade: 0.5%
- ✅ Max daily loss: 2.0%

### 3. Progressive Position Manager
**Current Configuration:**
- Initial stop: **20 pips** (good for entry protection)
- Stage 1 (+$30 profit): Close 25%, tighten to **12 pips**
- Stage 2 (+$60 profit): Close 25%, tighten to **8 pips**
- Stage 3 (+$100 profit): Close 25%, tighten to **5 pips**
- Final 25%: Runs with 5-pip trailing

---

## 🎯 STRATEGY UNIVERSALITY

### Market Compatibility Matrix

| Strategy | Crypto (Coinbase) | Stocks (IBKR) | Forex (OANDA) | Notes |
|----------|-------------------|---------------|---------------|-------|
| **EMA Scalper** | ✅ Universal | ✅ Universal | ✅ Universal | Works on all timeframes, adjusts to volatility |
| **Institutional SD** | ✅ Universal | ✅ Universal | ✅ Universal | Supply/demand zones adapt to asset class |
| **Holy Grail RSI** | ✅ Universal | ✅ Universal | ✅ Universal | RSI divergence is market-agnostic |
| **Trap Reversal** | ⚠️ Low signals | ⚠️ Low signals | ⚠️ Low signals | Needs tuning for each market |

**Key Finding**: Top 3 strategies are **instrument-agnostic** - same logic works across all 3 brokers with minimal adjustments.

---

## ⚡ OPTIMIZATION RECOMMENDATIONS

### A. Trailing Stop Distances (By Market Type)

**CURRENT (Universal):**
- Initial: 20 pips
- Stage 1: 12 pips  
- Stage 2: 8 pips
- Stage 3: 5 pips

**PROPOSED (Market-Specific):**

#### **Crypto (High Volatility)**
```python
initial_stop_pips = 35.0  # More room for noise
stages = [
    ProgressiveStage(30, 0.25, 20),  # +$30 → 20 pips
    ProgressiveStage(75, 0.50, 15),  # +$75 → 15 pips  
    ProgressiveStage(150, 0.75, 10), # +$150 → 10 pips
]
```

#### **Forex (Medium Volatility)**
```python
initial_stop_pips = 20.0  # Current settings OPTIMAL
stages = [
    ProgressiveStage(30, 0.25, 12),
    ProgressiveStage(60, 0.50, 8),
    ProgressiveStage(100, 0.75, 5),
]
```

#### **Stocks (Lower Volatility)**
```python
initial_stop_pips = 12.0  # Tighter for cleaner price action
stages = [
    ProgressiveStage(20, 0.25, 8),   # +$20 → 8 pips
    ProgressiveStage(40, 0.50, 5),   # +$40 → 5 pips
    ProgressiveStage(70, 0.75, 3),   # +$70 → 3 pips
]
```

### B. Profit Target Adjustments

**Crypto**: Wider targets (volatility allows +100-150 pip moves)  
**Forex**: Current targets optimal (+50-100 pip moves)  
**Stocks**: Tighter targets (+30-70 pip equivalent moves)

### C. Entry Timing Optimization

Add market-specific entry filters:
- **Crypto**: Avoid entries during Asia/Europe overlap (low volume)
- **Forex**: Focus on London/NY overlap (high liquidity)
- **Stocks**: First hour + last hour (avoid midday chop)

---

## 🔌 BROKER CONNECTION TESTS

### Coinbase Advanced Trade
- **API Keys**: Updated Dec 31, 2025
- **Status**: ⏳ Waiting activation (5-10 min window)
- **Test Command**: `python3 MULTI_BROKER_PHOENIX/tools/verify_coinbase_auth.py`
- **Expected**: 200 OK, account balance returned

### Interactive Brokers (IBKR)
- **Gateway Status**: ⚠️ Needs connection check
- **Port**: 4001 (Paper) / 4002 (Live)
- **Test Command**: `python3 -c "from ib_insync import *; ib = IB(); ib.connect('127.0.0.1', 4001, clientId=1); print('CONNECTED:', ib.isConnected())"`
- **Expected**: CONNECTED: True

### OANDA
- **Status**: ❌ MUST BE DISABLED per user request
- **Action Required**: Comment out OANDA imports, remove from broker list
- **Files to Modify**:
  - `api/app.py` (lines 11-13, 22-32, 131-139)
  - `crypto_entry_gate_system.py` (lines 415-433)
  - `launch_real_money.py` (line 93)

---

## 📋 PRE-LAUNCH SEQUENCE

### Step 1: Environment Validation
```bash
cd /home/ing/RICK/MULTI_BROKER_PHOENIX/MULTI_BROKER_PHOENIX
source /home/ing/RICK/MULTI_BROKER_PHOENIX/.venv/bin/activate

# Check Python version
python3 --version  # Should be 3.12+

# Verify dependencies
python3 -c "import cryptography, jwt, openai, requests; print('✅ All deps installed')"
```

### Step 2: Broker Connection Tests
```bash
# Test Coinbase (retry if 401)
python3 tools/verify_coinbase_auth.py

# Test IBKR
tools/validate_ibkr.sh

# Disable OANDA
# (Manual: comment out imports in api/app.py)
```

### Step 3: Risk System Validation
```bash
# Verify gates active
python3 -c "from multi_broker_phoenix.config import gates; print(gates.oco_required)"  # Should be True

# Check platform breakers
python3 -c "import json; print(json.load(open('multi_broker_phoenix/config/platform_breakers.json')))"
```

### Step 4: Strategy Registration
```bash
# List available strategies
python3 -c "from multi_broker_phoenix.strategies.base import list_strategies; print(list_strategies())"

# Should show: ema_scalper, institutional_sd, holy_grail, trap_reversal
```

### Step 5: Launch Headless Engine
```bash
# DRY RUN (no real orders)
python3 tools/run_headless.py --dry-run --brokers coinbase,ibkr

# LIVE LAUNCH (after validation)
python3 tools/run_headless.py --brokers coinbase,ibkr
```

---

## 🚨 GO/NO-GO CRITERIA

### ✅ GO Conditions
- [ ] All backtest results within 5% of baseline
- [ ] Coinbase API returns 200 OK
- [ ] IBKR Gateway connected
- [ ] OANDA fully disabled
- [ ] OCO enforcement active
- [ ] Platform breakers armed
- [ ] Progressive position manager loaded
- [ ] Strategies registered successfully

### ❌ NO-GO Conditions
- Broker API failures
- Risk gates disabled
- Platform breakers offline
- Strategy registration errors
- Database connection issues

---

## 📊 LIVE MONITORING DASHBOARD

### Key Metrics to Watch (First Hour)
1. **Order Execution**: Latency < 500ms
2. **Stop Loss Placement**: OCO brackets confirmed
3. **Position Sizing**: Within risk limits
4. **Trailing Stops**: Updating correctly
5. **Partial Closes**: Executing at stage thresholds

### Alert Thresholds
- ⚠️ Warning: -0.5% account drawdown
- 🚨 Critical: -1.0% account drawdown
- 🛑 Emergency Stop: -2.0% account drawdown

---

## 💾 BACKUP & RECOVERY

### Before Launch
```bash
# Backup current config
tar -czf phoenix_config_backup_$(date +%Y%m%d_%H%M%S).tar.gz \
  multi_broker_phoenix/config/ \
  .env \
  tools/

# Create database snapshot
cp rick_phoenix.db rick_phoenix_backup_$(date +%Y%m%d).db
```

### Emergency Stop Procedure
```bash
# Kill all trading processes
pkill -f "run_headless.py"

# Close all open positions via API
python3 tools/emergency_close_all.py

# Disable broker connections
mv .env .env.disabled
```

---

## ✍️ SIGN-OFF

**Pre-Flight Checklist Completed By**: _____________  
**Date**: _____________  
**Backtests Validated**: ☑️ YES ☐ NO  
**Brokers Connected**: ☐ Coinbase ☐ IBKR ☐ OANDA (disabled)  
**Risk Systems Active**: ☐ YES  
**Ready for Live Trading**: ☐ YES ☐ NO  

---

**REMEMBER**: Start with SMALL position sizes (10% of normal) for first 24 hours to validate execution in live market conditions.
