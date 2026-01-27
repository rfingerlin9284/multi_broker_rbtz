# AI HIVE BUDGET TIERS & ROI ANALYSIS

## CURRENT SETUP (Conservative)
```bash
AI_HIVE_DAILY_BUDGET_USD=10.0    # $70/week, $300/month
```

**What you get:**
- ~5-10 symbols validated per scan
- ~720 AI calls/day (24 scans × 30 calls each)
- Strategy scan: UNLIMITED (free, local)
- 167 FABIO trades still generated (that's locked)

## COST TIERS - ADJUST TO YOUR RISK TOLERANCE

### TIER 1: CONSERVATIVE ($10/day = $300/month)
```bash
AI_HIVE_DAILY_BUDGET_USD=10.0
AI_MAX_CALLS_PER_SCAN=50
```
- Best for: Initial testing, low-capital accounts ($1k-$5k)
- AI validates: Top 10-15 signals per scan
- Coverage: ~20% of strategy signals get AI validation
- Expected: 5-10 high-quality trades/day

### TIER 2: BALANCED ($25/day = $750/month)
```bash
AI_HIVE_DAILY_BUDGET_USD=25.0
AI_MAX_CALLS_PER_SCAN=150
```
- Best for: Mid-capital accounts ($5k-$20k)
- AI validates: Top 30-50 signals per scan
- Coverage: ~50% of strategy signals get AI validation
- Expected: 15-25 high-quality trades/day

### TIER 3: AGGRESSIVE ($50/day = $1,500/month)
```bash
AI_HIVE_DAILY_BUDGET_USD=50.0
AI_MAX_CALLS_PER_SCAN=300
```
- Best for: Larger accounts ($20k+)
- AI validates: Nearly ALL strategy signals
- Coverage: ~90% of strategy signals get AI validation
- Expected: 30-50 high-quality trades/day

### TIER 4: UNLIMITED (Strategy-Only, $0/day)
```bash
ENABLE_AI_HIVE=false
AI_HIVE_DAILY_BUDGET_USD=0.0
```
- Best for: Pure technical trading, no AI validation
- Strategies run unlimited (FABIO 167 trades locked)
- Coverage: 0% AI validation (strategies decide everything)
- Expected: 50-100 trades/day (no AI filter)

## ROI BREAK-EVEN ANALYSIS

### Tier 1: $10/day → Need $0.67 profit per AI-validated trade
Monthly cost: $300
AI-validated trades: ~150/month (5/day × 30 days)
Break-even: $2 profit per trade
**Target: $450+ profit/month (150% ROI)**

### Tier 2: $25/day → Need $1.11 profit per AI-validated trade
Monthly cost: $750
AI-validated trades: ~450/month (15/day × 30 days)
Break-even: $1.67 profit per trade
**Target: $1,125+ profit/month (150% ROI)**

### Tier 3: $50/day → Need $1.67 profit per AI-validated trade
Monthly cost: $1,500
AI-validated trades: ~900/month (30/day × 30 days)
Break-even: $1.67 profit per trade
**Target: $2,250+ profit/month (150% ROI)**

## RECOMMENDED APPROACH

**Start at Tier 2 ($25/day) if your capital is $10k+**

Why?
- You're already comfortable with $70/week ($10/day)
- $25/day = $175/week (still reasonable)
- Better AI coverage = fewer false signals
- Still protects against runaway costs
- Easy to scale down if needed

## SOLUTION: ADAPTIVE BUDGET TIERS

I'll create a script that auto-adjusts budget based on performance:

```bash
# Auto-scale budget based on account size and profitability
ADAPTIVE_BUDGET=true
BUDGET_AS_PCT_OF_CAPITAL=0.01    # 1% of capital per month

# Example: $10k account → $100/month budget → ~$3.33/day
# Example: $50k account → $500/month budget → ~$16.67/day
```

## QUICK ADJUSTMENT COMMANDS

### Increase to $25/day (Balanced):
```bash
# Edit .env directly
sed -i 's/AI_HIVE_DAILY_BUDGET_USD=10.0/AI_HIVE_DAILY_BUDGET_USD=25.0/' .env
sed -i 's/AI_MAX_CALLS_PER_SCAN=50/AI_MAX_CALLS_PER_SCAN=150/' .env
```

### Increase to $50/day (Aggressive):
```bash
sed -i 's/AI_HIVE_DAILY_BUDGET_USD=10.0/AI_HIVE_DAILY_BUDGET_USD=50.0/' .env
sed -i 's/AI_MAX_CALLS_PER_SCAN=50/AI_MAX_CALLS_PER_SCAN=300/' .env
```

### Disable AI entirely (Free):
```bash
sed -i 's/ENABLE_AI_HIVE=true/ENABLE_AI_HIVE=false/' .env
```

## REAL-WORLD COST EXAMPLES

**100 symbols, 1 scan/hour, 24 hours:**

**With $10/day budget:**
- Strategy scan: 100 symbols × 24 scans = 2,400 (free)
- AI validation: ~10 symbols × 3 agents × 24 = 720 calls
- Cost: $7.20/day (under budget)
- Symbols validated: 10% of universe

**With $25/day budget:**
- Strategy scan: 100 symbols × 24 scans = 2,400 (free)
- AI validation: ~25 symbols × 3 agents × 24 = 1,800 calls
- Cost: $18.00/day (under budget)
- Symbols validated: 25% of universe

**With $50/day budget:**
- Strategy scan: 100 symbols × 24 scans = 2,400 (free)
- AI validation: ~50 symbols × 3 agents × 24 = 3,600 calls
- Cost: $36.00/day (under budget)
- Symbols validated: 50% of universe

## KEY INSIGHT: QUALITY VS QUANTITY

**More budget ≠ More trades**
**More budget = Better quality trades**

- FABIO generates 167 trades regardless (RSI 40 locked)
- AI budget only affects WHICH trades get validation
- Higher budget = More trades validated = Fewer false positives

## WHAT'S ACTUALLY HAPPENING

**WITHOUT AI HIVE:**
- Strategy: "I see 167 opportunities!"
- You: "Take all of them!"
- Result: 167 trades, mix of good and bad

**WITH AI HIVE ($10/day):**
- Strategy: "I see 167 opportunities!"
- AI Hive: "I can validate your top 10 best ones"
- You: "Take those 10 confirmed trades"
- Result: 10 high-quality trades

**WITH AI HIVE ($50/day):**
- Strategy: "I see 167 opportunities!"
- AI Hive: "I can validate your top 50 best ones"
- You: "Take those 50 confirmed trades"
- Result: 50 high-quality trades

## RECOMMENDATION

**For your $10k+ account, set this:**

```bash
AI_HIVE_DAILY_BUDGET_USD=25.0
AI_MAX_CALLS_PER_SCAN=150
HIVE_MIN_STRATEGY_CONF=0.55    # Lower from 0.60 to validate more
```

This gives you:
- $175/week spend (vs your comfortable $70)
- 15-25 AI-validated trades/day
- Better coverage of FABIO's 167 signals
- Still protected from runaway costs

**If profits are good, scale to $50/day after 1-2 weeks**

## MONITORING & AUTO-CUTOFF

Current system already protects you:
- Daily budget HARD LIMIT (stops at threshold)
- Per-symbol limits (max 3 AI calls per symbol)
- Per-scan limits (max N calls per scan cycle)
- Resets at midnight automatically

**You're protected from:**
- ❌ Runaway API costs (hard cap)
- ❌ Repeated calls on same symbol (3-call limit)
- ❌ Infinite loops (per-scan limit)

**You're NOT protected from:**
- ✅ Intentional scaling (you control the limits)
- ✅ Profitable trading (that's the goal!)

## NEXT STEPS

1. Choose your tier (I recommend Tier 2: $25/day)
2. I'll update the .env for you
3. Run a test scan to see coverage
4. Monitor for 24-48 hours
5. Adjust up/down based on results

**Want me to set you up at $25/day now?**
