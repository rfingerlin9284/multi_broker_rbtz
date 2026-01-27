# 🐤 PHASE 1: COINBASE CANARY MODE - COMPLETE ✅

## Status: READY FOR DEPLOYMENT

---

## What is Canary Mode?

**Canary Mode** is an ultra-conservative testing mode that runs the trading system with:
- 🐢 **Slower polling** (30s vs 2s) - Less aggressive, more monitoring time
- 📢 **Verbose narration** - Every action logged with emoji indicators
- 💵 **Ultra-low risk** ($10 vs $30 max per trade) - Minimal exposure
- 📊 **Detailed logging** - Health checks, signal detection, risk decisions
- 🎯 **Single broker focus** - Coinbase only, crypto stable

**Purpose**: Prove system stability before scaling to multiple brokers

---

## ✅ Implementation Checklist

### Configuration Files
- [x] **.env** - Added CANARY_MODE, CANARY_POLL_SECONDS, CANARY_MAX_RISK_USD
- [x] **.env.example** - Updated with canary settings template
- [x] Settings default to `CANARY_MODE=false` (manual enable required)

### Code Enhancements
- [x] **run_headless.py** - Added canary detection and verbose logging
  - `_is_canary_mode()` - Environment check function
  - `_canary_log()` - Timestamped emoji logging
  - `_get_poll_interval()` - Respects canary override (30s)
  - `_get_max_risk_usd()` - Respects canary override ($10)
  - Enhanced narration for:
    - 🚨 Mode activation
    - 📊 Price fetching
    - 🎯 Signal generation
    - ✋ No signal events
    - ✅ Risk checks passed
    - 🚫 Trade/sizing blocks
    - 📝 Order placement
    - ⚠️ Errors/fallbacks
    - 😴 Sleep intervals
    - 🏥 Health checks (every 10 loops)

### VSCode Tasks
- [x] **🐤 RBOTZILLA: Start Coinbase Canary Mode** - One-click canary start
- [x] **📊 RBOTZILLA: View Live Status** - Log monitoring
- [x] **🚨 RBOTZILLA: Emergency Stop** - Kill switch
- [x] **🔍 RBOTZILLA: Check Market Sessions** - Session status

### Deployment Scripts
- [x] **deploy_canary_mode.sh** - Safe .env updater with backup
- [x] **start_canary.sh** - Quick-start launcher

---

## 🚀 How to Deploy Phase 1

### Method 1: Automated Deployment (Recommended)
```bash
cd /home/ing/RICK/MULTI_BROKER_PHOENIX
./tools/deploy_canary_mode.sh
./tools/start_canary.sh
```

### Method 2: Manual .env Edit
Edit `.env` and set:
```bash
CANARY_MODE=true
HEADLESS_MODE=coinbase-only
DEFAULT_STRATEGY=holy_grail
FEED_SYMBOLS=BTC-USD,ETH-USD
```

Then run:
```bash
cd /home/ing/RICK/MULTI_BROKER_PHOENIX
export PYTHONPATH=$PWD
python3 MULTI_BROKER_PHOENIX/tools/run_headless.py --mode coinbase-only
```

### Method 3: VSCode Task (Easiest)
1. Press `Ctrl+Shift+P`
2. Type "Tasks: Run Task"
3. Select "🐤 RBOTZILLA: Start Coinbase Canary Mode"
4. Monitor in dedicated terminal panel

---

## 📊 Expected Canary Output

### Startup
```
🐤 CANARY [2025-12-29 01:23:45] 🚨 CANARY MODE ACTIVE - Ultra-conservative monitoring enabled
🐤 CANARY [2025-12-29 01:23:45] Polling interval: 30.0s (slower for safety)
🐤 CANARY [2025-12-29 01:23:45] Max risk per trade: $10.0 (ultra-low)
Starting headless runner (minimal).
Headless mode: coinbase-only (Use Coinbase only)
🐤 CANARY [2025-12-29 01:23:45] Selected mode: coinbase-only
🐤 CANARY [2025-12-29 01:23:45] Initializing connectors for symbols: BTC-USD, ETH-USD
🐤 CANARY [2025-12-29 01:23:45] OANDA connector disabled/unavailable
🐤 CANARY [2025-12-29 01:23:45] Strategy loaded: holy_grail
🐤 CANARY [2025-12-29 01:23:45] 🚀 Starting main loop - monitoring all activity
```

### Normal Operation
```
🐤 CANARY [2025-12-29 01:23:47] Loop #1 - Health check OK
🐤 CANARY [2025-12-29 01:23:47] 📊 BTC-USD price: $89355.97 (Coinbase)
🐤 CANARY [2025-12-29 01:23:47] ✋ BTC-USD - No signal generated
🐤 CANARY [2025-12-29 01:23:48] 📊 ETH-USD price: $3007.05 (Coinbase)
🐤 CANARY [2025-12-29 01:23:48] ✋ ETH-USD - No signal generated
🐤 CANARY [2025-12-29 01:23:48] 😴 Sleeping 30.0s until next check...
```

### Signal Detection
```
🐤 CANARY [2025-12-29 01:24:18] 📊 BTC-USD price: $89432.10 (Coinbase)
🐤 CANARY [2025-12-29 01:24:18] 🎯 BTC-USD SIGNAL: LONG @ $89432.10 (confidence: 0.75)
🐤 CANARY [2025-12-29 01:24:18] ✅ Risk checks PASSED - Size: 0.0001 units
🐤 CANARY [2025-12-29 01:24:18] 📝 Preparing order: LONG BTC-USD via COINBASE
🐤 CANARY [2025-12-29 01:24:18] ✅ COINBASE paper order placed: {...}
placed order: {...}
```

### Risk Block Example
```
🐤 CANARY [2025-12-29 01:25:48] 🎯 ETH-USD SIGNAL: SHORT @ $3012.34 (confidence: 0.68)
trade blocked: Confidence below threshold (0.68 < 0.70)
🐤 CANARY [2025-12-29 01:25:48] 🚫 Trade BLOCKED: Confidence below threshold (0.68 < 0.70)
```

---

## 🔍 Validation Tests

### Test 1: Confirm Canary Mode Active
**Expected**: See 🐤 emoji logs and "CANARY MODE ACTIVE" message
```bash
# Should see canary activation
./tools/start_canary.sh | grep "CANARY MODE ACTIVE"
```

### Test 2: Verify Slow Polling (30s)
**Expected**: 30-second gaps between price checks (not 2s)
```bash
# Timestamps should be ~30s apart
./tools/start_canary.sh | grep "Sleeping"
```

### Test 3: Confirm Price Fetching
**Expected**: Live BTC-USD and ETH-USD prices from Coinbase
```bash
# Should see current market prices
./tools/start_canary.sh | grep "📊"
```

### Test 4: Verify Paper Mode (No Real Orders)
**Expected**: All orders go through PaperEngine, no real API calls
```bash
# All orders should be "paper"
./tools/start_canary.sh | grep "COINBASE paper order"
```

### Test 5: Emergency Stop
**Expected**: Process terminates cleanly
```bash
# In another terminal:
pkill -f run_headless.py
# Should see "Headless runner stopped by user"
```

---

## 🛡️ Safety Guarantees

### Multi-Layer Protection
1. ✅ **PAPER_TRADING=true** - No real money
2. ✅ **CANARY_MAX_RISK_USD=10.0** - Ultra-low exposure
3. ✅ **HEADLESS_MODE=coinbase-only** - Single broker focus
4. ✅ **30s polling** - Non-aggressive, observable
5. ✅ **Risk gates active** - Drawdown, confidence, sizing checks
6. ✅ **Market session awareness** - Trade-time restrictions
7. ✅ **Verbose logging** - Full audit trail

### No Real Money Risk
- Coinbase connector in `paper_mode=True`
- No API keys required (public price API only)
- PaperEngine simulates all fills
- Database: `/tmp/trades.db` (local simulation)

---

## 📈 Success Criteria for Phase 1

Before proceeding to Phase 2 (IBKR), confirm:

- [ ] Canary mode starts without errors
- [ ] Prices fetch every 30 seconds
- [ ] Canary emoji logs visible (🐤)
- [ ] Holy Grail strategy loads successfully
- [ ] Risk checks block inappropriate trades
- [ ] Paper orders execute (when signals fire)
- [ ] No real API calls to Coinbase trading endpoints
- [ ] System runs stable for 30+ minutes
- [ ] Emergency stop works cleanly
- [ ] Market session checks pass

**Phase 1 Status**: 🟢 READY TO TEST

---

## 🔄 Next Steps

### Immediate
1. Deploy canary mode using one of three methods above
2. Monitor for 30-60 minutes
3. Verify all success criteria
4. Review logs for any warnings/errors

### After Validation
- **Phase 2**: Add IBKR paper connector (SPY, QQQ)
- **Phase 3**: Re-enable OANDA paper (EUR_USD, GBP_USD)
- **Phase 4**: Multi-broker orchestration with shared risk

---

## 🆘 Troubleshooting

### "Module not found" errors
```bash
cd /home/ing/RICK/MULTI_BROKER_PHOENIX
export PYTHONPATH=$PWD
```

### Canary logs not showing
Check `.env`:
```bash
grep "CANARY_MODE" .env
# Should show: CANARY_MODE=true
```

### No prices fetching
Test Coinbase API:
```bash
python3 tools/validate_coinbase.py
```

### Task not appearing in VSCode
Reload window: `Ctrl+Shift+P` → "Developer: Reload Window"

---

## 📁 Modified Files Summary

| File | Change | Purpose |
|------|--------|---------|
| `.env` | Added CANARY_MODE flags | Enable canary testing |
| `.env.example` | Added CANARY_MODE template | Configuration guide |
| `run_headless.py` | Added canary detection & logging | Verbose monitoring |
| `tasks.json` | Added 4 new tasks | VSCode integration |
| `deploy_canary_mode.sh` | New deployment script | Safe config updater |
| `start_canary.sh` | New quick-start script | One-command launch |

**Total Changes**: 6 files (0 new folders, respecting constraints)

---

## 🎯 Phase 1 Completion Summary

**Status**: ✅ **COMPLETE AND READY**

All Phase 1 requirements met:
- [x] CANARY_MODE configuration in .env
- [x] Ultra-conservative settings ($10 risk, 30s polling)
- [x] Verbose narration with emoji indicators
- [x] VSCode task for one-click start
- [x] Emergency stop task
- [x] Deployment automation scripts
- [x] Validation test procedures
- [x] Safety guarantees documented

**Ready to deploy**: Use `./tools/start_canary.sh` or VSCode task

---

**Next**: After 30-60 minutes of stable canary operation, proceed to Phase 2 (IBKR integration)
