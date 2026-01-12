# 🚀 RBOTZILLA QUICK REFERENCE CARD

## ONE-LINER LAUNCH
```bash
cd /home/ing/RICK/MULTI_BROKER_PHOENIX && ./RBOTZILLA_LAUNCH.sh
```

## COMMON COMMANDS

### Launch System
```bash
./RBOTZILLA_LAUNCH.sh          # Main launcher (select from menu)
```

### Check Status
```bash
./check_status.sh               # Quick health check
./system_audit.sh               # Full 44-point audit
```

### Monitor Live Trading
```bash
tail -f /tmp/trades.db.log      # Main trading log
tail -f logs/fabio_*.log        # FABIO strategy logs
tail -f logs/hive_*.log         # AI Hive logs
```

### Emergency Stop
```bash
pkill -9 -f "run_headless"      # Kill trading engine
pkill -9 -f "hive_validation"   # Kill AI Hive
# OR use launcher: Option 7
```

### Check Running Processes
```bash
ps aux | grep -E "python.*MULTI_BROKER_PHOENIX"
```

### Backup & Restore
```bash
./restore_fabio_milestone_v1.1.sh --backup    # Create backup
./restore_fabio_milestone_v1.1.sh --restore   # Restore from backup
```

---

## SYSTEM STATUS

✅ **44/44 Audit Checks Passed**

### Configuration:
- FABIO RSI Threshold: **40** (167 trades @ 64.7% win)
- All Stop Losses: **ACTIVE**
- AI Hive: **ENABLED** ($10/day budget)
- Trailing Stops: **ENABLED** (OANDA + Coinbase)
- Trading Mode: **PAPER** (safe testing)

### Strategies (All Default ON):
1. FABIO AAA Full - RSI 40, 1-8% volatility stops
2. Holy Grail - 3% fixed stops
3. EMA Scalper - 0.5% tight stops
4. Institutional SD - 1% moderate stops
5. Trap Reversal - 0.5x spike-based stops

### AI Hive (Every Tick Scanning):
- **Grok (XAI)**: Catalyst detection ($0.001/call)
- **OpenAI GPT**: News sentiment ($0.002/call)
- **DeepSeek**: Social media ($0.0005/call)
- **Daily Budget**: $10.00
- **Actual Monthly Cost**: $0.24-$13

### Risk Limits:
- Max Drawdown: 10%
- Daily Loss: $100
- Consecutive Losses: 5
- Coinbase: 10 trades/day, $50 daily loss

---

## LAUNCH OPTIONS

### Option 1: Canary Mode (Coinbase Crypto)
- Real money, nano lots ($5-10)
- BTC-USD, ETH-USD only
- 10 trades/day, $50 daily loss limit

### Option 2: OANDA Forex (Paper) ← **RECOMMENDED FIRST RUN**
- Live API, paper account (no real money)
- All 5 strategies, AI Hive scanning
- Perfect for testing

### Option 3: Multi-Asset (All Brokers)
- OANDA paper + Coinbase real (nano)
- 27 instruments, all strategies
- Full risk management

### Option 4: Strategy Test (Backtest)
- Validation only, no live trading
- FABIO 167 trades @ 64.7% win

### Option 5: AI Hive Only (Scan Mode)
- Catalyst detection, no trading
- News/Reddit/social media analysis

### Option 6: Full Audit (Health Check)
- 44-point system verification
- Run anytime to check status

### Option 7: Emergency Stop
- Kills all processes
- Clean shutdown

---

## KEY FILES

### Control Scripts:
- **RBOTZILLA_LAUNCH.sh** - Master launcher
- **system_audit.sh** - Full audit
- **check_status.sh** - Quick check

### Configuration:
- **.env** - All settings

### Strategy Files:
- **fabio_aaa_full.py** - FABIO strategy
- **base.py** - All base strategies
- **unified_hive_scanner.py** - Strategy + AI
- **hive_cost_control.py** - Budget control

### Documentation:
- **SYSTEM_READY_FOR_LIVE.md** - Complete guide
- **DEPLOYMENT_READY.md** - Deployment summary
- **SETUP_COMPLETE.md** - Setup checklist
- **THIS FILE** - Quick reference

### Backups:
- **Location**: `backups/fabio_v1.1.0/`
- **Restore**: `./restore_fabio_milestone_v1.1.sh --restore`

---

## EXPECTED PERFORMANCE

### FABIO AAA Full:
- Trades: 167 (vs 2 at RSI 50)
- Win Rate: 64.7%
- ROI: 369%
- $10k → $46,900 (projected)

### Combined:
- Win Rate: 60-65%
- Monthly: 5-15% gains
- AI Cost: $0.24-$13/month
- ROI on AI: 3,800%-62,500%

---

## SAFETY FEATURES

✅ Stop losses (all strategies)  
✅ Trailing stops (OANDA + Coinbase)  
✅ Max drawdown 10%  
✅ Daily loss limit $100  
✅ Consecutive loss limit 5  
✅ AI budget control $10/day  
✅ Canary nano-lots $5-10  
✅ Paper trading mode  

---

## EMERGENCY PROCEDURES

### 1. Stop Everything
```bash
./RBOTZILLA_LAUNCH.sh  # Option 7
# OR
pkill -9 -f "run_headless"
```

### 2. Check Status
```bash
./check_status.sh
ps aux | grep python.*MULTI
```

### 3. View Logs
```bash
tail -f /tmp/trades.db.log
ls -lh logs/
```

### 4. Restore Backup
```bash
./restore_fabio_milestone_v1.1.sh --restore
```

### 5. Run Full Audit
```bash
./system_audit.sh
```

---

## FIRST RUN CHECKLIST

Before launching:
- [ ] Run `./check_status.sh` (verify all green)
- [ ] Run `./system_audit.sh` (confirm 44/44 passed)
- [ ] Verify paper trading mode ON
- [ ] Check API keys valid
- [ ] Open monitoring terminal: `tail -f /tmp/trades.db.log`

Launch:
- [ ] Run `./RBOTZILLA_LAUNCH.sh`
- [ ] Select Option 2 (OANDA Forex Paper)
- [ ] Verify strategies loaded
- [ ] Confirm AI Hive scanning
- [ ] Watch for first trade signal

Monitor (1-4 hours):
- [ ] Check trades executed correctly
- [ ] Verify stop losses trigger
- [ ] Confirm AI Hive costs under budget
- [ ] Review win rate > 60%

---

## TROUBLESHOOTING

### No trades executing?
```bash
# Check if system is running
ps aux | grep run_headless

# Check logs for errors
tail -100 /tmp/trades.db.log
tail -100 logs/fabio_*.log

# Verify API connection
grep "Connected" /tmp/trades.db.log
```

### High AI costs?
```bash
# Check budget tracking
grep "AI_HIVE_BUDGET" logs/hive_*.log

# Verify strategy-first mode
grep "HIVE_STRATEGY_FIRST" .env  # Should be "true"

# Check call frequency
grep "API_CALL" logs/hive_*.log | wc -l
```

### Stop losses not triggering?
```bash
# Verify stop loss configuration
grep "STOP" .env | grep -v "#"

# Check for stop loss logs
grep "stop_loss" logs/*.log

# Verify trailing stops enabled
grep "TRAILING_STOP" .env
```

### System won't start?
```bash
# Kill all instances first
pkill -9 -f "run_headless"
pkill -9 -f "hive_validation"

# Check .env file
cat .env | grep -E "API_TOKEN|API_KEY"

# Run audit
./system_audit.sh
```

---

## CONTACT INFO

**System Version**: v1.1.0  
**Last Updated**: December 2024  
**Status**: ✅ ALL SYSTEMS GO

**Documentation**:
- Full Guide: [SYSTEM_READY_FOR_LIVE.md](SYSTEM_READY_FOR_LIVE.md)
- Quick Start: [DEPLOYMENT_READY.md](DEPLOYMENT_READY.md)
- Setup Complete: [SETUP_COMPLETE.md](SETUP_COMPLETE.md)

---

## QUICK TIPS

💡 **Start with Option 2** (OANDA Paper) for safe testing  
💡 **Monitor for 1 hour minimum** before leaving unattended  
💡 **Check logs regularly**: `tail -f /tmp/trades.db.log`  
💡 **Run audit weekly**: `./system_audit.sh`  
💡 **Keep backups updated**: `./restore_fabio_milestone_v1.1.sh --backup`  
💡 **Emergency stop ready**: Option 7 or `pkill -9 -f "run_headless"`  

---

🚀 **ONE-LINER TO START:**
```bash
cd /home/ing/RICK/MULTI_BROKER_PHOENIX && ./RBOTZILLA_LAUNCH.sh
```

**Select Option 2 → OANDA Forex (Paper Account)**

**May the markets be ever in your favor! 📈**
