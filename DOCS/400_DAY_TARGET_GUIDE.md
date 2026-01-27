# 💰 $400/DAY TARGET MODE - Configuration Guide

## Overview

Your system is now configured to target **$400+ profit per trading day** starting with $5,000 capital.

## 📊 Mathematical Reality

```
Starting Capital:    $5,000
Daily Target:        $400 (8% daily return)
Risk Per Trade:      3.5% ($175)
Win Amount:          $525 (3:1 R:R)
Loss Amount:         $175
Expected Value:      $91 per trade

Trades Needed:       5 quality trades/day
Expected Wins:       1.7 (38% WR)
Expected Losses:     2.7
Trade Frequency:     Every ~144 minutes (2.4 hours)
```

## 🎯 Example Profitable Day

```
Trade 1: ❌ LOSS  -$175  (Daily: -$175)
Trade 2: ✅ WIN   +$525  (Daily: +$350)
Trade 3: ❌ LOSS  -$175  (Daily: +$175)
Trade 4: ❌ LOSS  -$175  (Daily: $0)
Trade 5: ✅ WIN   +$525  (Daily: +$525) ✅ TARGET HIT!

Final: 2 wins, 3 losses = +$525/day
```

## ⚙️ System Configuration

### HIVE Consensus (Lowered Threshold)
- **30% approval** (vs 45% standard, 55% conservative)
- Sentinel veto disabled for speed
- Oracle research optional (don't wait for news)
- **Result:** More trade opportunities, still protected

### Position Sizing (Aggressive)
```
Risk per trade:           3.5% (vs 2.5% standard)
Max position size:        15% (vs 10% standard)
Max concurrent positions: 8 (vs 5 standard)
Max daily risk:           12% (vs 8% standard)
```

### Smart Aggression Features (Maxed)

| Feature | Standard | $400/Day Mode |
|---------|----------|---------------|
| **Hedging** | 40% ratio, hedge at -1.5% | 60% ratio, hedge at -1.0% |
| **Sniping** | 2% target, 10min hold | 1.5% target, 5min hold |
| **Pyramiding** | 3 entries, +2% trigger | 4 entries, +1.5% trigger |
| **Breakeven** | BE at +1.5R | BE at +1.0R |
| **Trailing** | Trail at +3R | Trail at +2R |

### Risk Management
```
Max daily loss halt:    -$200 (auto-stop trading)
Min acceptable profit:  +$250 (decent day)
Stop loss range:        1.5% - 6.0%
Min R:R ratio:          2.0:1 (vs 3:1 conservative)
Slippage tolerance:     0.8% (vs 0.5% standard)
```

## ⏰ Trading Schedule

```
Trading Hours:    12-14 hours/day
Start:            1 AM UTC (8 PM EST)
End:              9 PM UTC (4 PM EST)
Covers:           Asian + London + New York sessions
Trade frequency:  ~5 trades spread across day
Weekend:          No trading (liquidity too thin)
News events:      Trade through them (momentum plays)
```

## 🚀 Launch Commands

### 1. Show Daily Plan
```bash
python3 MULTI_BROKER_PHOENIX/tools/launch_400_day_hunter.py 5000
```

### 2. Run Simulation
```bash
python3 MULTI_BROKER_PHOENIX/tools/launch_400_day_hunter.py 5000 <<< "yes"
```

### 3. Start Live Trading (When Ready)
```bash
# Configure broker first
python3 tools/validate_oanda.sh

# Launch real trading
python3 -m multi_broker_phoenix.engines.real_trading_engine \
    --mode daily_target \
    --capital 5000 \
    --broker oanda
```

## 📈 Growth Projection

| Time Period | Capital Growth | Days | Avg Daily |
|-------------|---------------|------|-----------|
| Week 1 | $5,000 → $7,800 | 7 | $400/day |
| Month 1 | $5,000 → $13,000 | 20 | $400/day |
| Month 2 | $13,000 → $21,000 | 40 | $400/day |
| Month 3 | $21,000 → $29,000 | 60 | $400/day |

**Note:** Assumes consistent $400/day avg. Reality will have variance.

## ⚠️ Reality Checks

### What Could Go Wrong

1. **Bad days WILL happen**
   - Some days: -$200 (hit loss limit)
   - Win rate variance: 30-45% actual vs 38% expected
   - 3-4 consecutive losses possible

2. **Trade frequency is aggressive**
   - Need 5 quality setups/day
   - Lowered HIVE threshold = more risk
   - May execute 8-12 trades, only 5 profitable

3. **Capital growth compounds issues**
   - At $10k capital: Need $400 = 4% daily (easier)
   - But positions also larger (more risk per trade)
   - Charter may constrain position size

4. **Market conditions matter**
   - Ranging markets: Few quality setups
   - High volatility: More stop-outs
   - News events: Unpredictable spikes

### Mitigation Strategies

✅ **HIVE still protects** (30% threshold, not 0%)
✅ **Auto-halt at -$200 daily loss** (can't blow account in one day)
✅ **Smart aggression** (hedging, trailing stops)
✅ **Growth charter** (enforces capital preservation)
✅ **Track every trade** (review and improve)

## 🎓 Best Practices

### Daily Routine

**Morning (Pre-Market):**
1. Review overnight news
2. Check economic calendar
3. Identify 3-5 high-probability setups
4. Set daily target tracker

**During Trading:**
1. Wait for HIVE consensus signals
2. Don't force trades (quality > quantity)
3. Monitor positions actively
4. Check target progress every 2 hours

**End of Day:**
1. Review all trades
2. Identify mistakes
3. Update win rate stats
4. Plan tomorrow's targets

### Trade Selection

✅ **Do:**
- Wait for strong HIVE consensus (even at 30%)
- Focus on GBP/USD (proven 38% WR)
- Trade with momentum and catalysts
- Use proper R:R ratios (2:1 minimum)

❌ **Don't:**
- Chase trades to hit target
- Override HIVE rejections
- Risk more than 3.5% per trade
- Trade when tired/emotional

## 📊 Performance Tracking

### Key Metrics to Monitor

```
Daily P&L:           Track vs $400 target
Win Rate:            Should stay 35-42%
Avg Win:             Should be ~$525
Avg Loss:            Should be ~$175
R:R Ratio:           Should be 2.5-3.5:1
HIVE Approval Rate:  Should be 20-35%
Trades/Day:          Should be 5-8
```

### Warning Signs

🔴 **Stop and Review If:**
- Win rate drops below 30% for 3+ days
- Avg R:R drops below 2:1
- More than 2 consecutive -$200 days
- HIVE approving >50% of signals (too loose)
- Taking >10 trades/day (overtrading)

## 🎯 Capital Milestones

### Phase 1: $5k → $10k (13 days)
- Risk: 3.5% per trade
- Target: $400/day
- Mode: AGGRESSIVE
- HIVE: 30% threshold

### Phase 2: $10k → $20k (25 days)
- Risk: 2.5% per trade (lower)
- Target: $400/day (easier now)
- Mode: BALANCED
- HIVE: 35% threshold (tighter)

### Phase 3: $20k → $50k (75 days)
- Risk: 2.0% per trade
- Target: $400-800/day
- Mode: SMART_AGGRESSIVE
- HIVE: 40% threshold

### Phase 4: $50k+ (Institutional)
- Growth Charter graduates to institutional rules
- Min notional: $15k
- Max leverage: 3x
- Target: $1k+/day

## 🔧 Configuration Files

```
daily_target_mode.py          # Target mode configuration
smart_aggression.py           # Aggression settings  
real_trading_engine.py        # Live trading engine
launch_400_day_hunter.py      # Launch script
```

## 🚨 Emergency Procedures

### If Daily Loss Hits -$200
1. Auto-halt triggered
2. No more trades today
3. Review what went wrong
4. Adjust tomorrow's plan
5. Don't revenge trade

### If 3 Consecutive Red Days
1. Pause trading
2. Full system review
3. Check HIVE agents
4. Verify market conditions
5. Paper trade 10 setups
6. Resume when confident

### If Capital Drops Below $4k
1. STOP IMMEDIATELY
2. Full strategy review
3. Lower risk to 2% per trade
4. Rebuild to $5k before resuming
5. Consider adding capital

## ✅ Ready to Launch

Your system has:
- ✅ Daily target tracking ($400/day)
- ✅ Aggressive position sizing (3.5% risk)
- ✅ Lowered HIVE threshold (30%)
- ✅ All smart aggression features enabled
- ✅ Auto-halt at -$200 daily loss
- ✅ Real-time progress monitoring

**Launch when ready:**
```bash
python3 MULTI_BROKER_PHOENIX/tools/launch_400_day_hunter.py 5000
```

**May the edge be with you. 🎯🔥**
