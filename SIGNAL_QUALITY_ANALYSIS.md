# 🎯 Signal Quality Analysis - EUR/USD & GBP/USD Profitable Trades

## What Happened (2026-01-12 ~05:32 UTC)

Two high-quality BUY signals were generated and filled:

- **EUR/USD**: Entry ~$1.172, Profit +$91 unrealized
- **GBP/USD**: Entry ~$1.350, Profit +$72 unrealized

Both trades were manually closed at profit after trailing stops were found non-functional.

---

## How The Signals Were Generated

### 4 Strategies Running Simultaneously

| Strategy           | Description         | Triggers On                                   |
| ------------------ | ------------------- | --------------------------------------------- |
| `fabio_aaa_full`   | RSI + tranche OCO   | RSI ≤40 = BUY, RSI ≥60 = SELL                 |
| `holy_grail`       | Momentum + trend    | 60%+ bars same dir + 0.1%+ momentum           |
| `ema_scalper`      | EMA crossover       | Short EMA > Long EMA + price momentum         |
| `institutional_sd` | Volatility breakout | 1.5x historical volatility + directional move |

### Most Likely Signal Source: `holy_grail` or `ema_scalper`

Based on the log pattern showing **consistent BUY signals** for both pairs, these strategies detected:

1. **Uptrend**: 6+ of last 10 bars moving up
2. **Momentum**: Positive price change over 5 bars
3. **RSI neutral zone**: Not overbought (room to run up)

---

## AI Hive Validation

| Model        | EUR/USD Vote     | GBP/USD Vote     |
| ------------ | ---------------- | ---------------- |
| **Grok**     | BUY 70-75%       | BUY 75-80%       |
| **OpenAI**   | Rate-limited     | Rate-limited     |
| **Decision** | APPROVE (70-75%) | APPROVE (75-80%) |

Grok provided the decisive vote while OpenAI was rate-limited.

---

## Signal Quality Criteria (What Made These Good)

✅ **Trend Alignment**: Both pairs in uptrends  
✅ **AI Consensus**: 70-80% confidence from Grok  
✅ **Position Sizing**: $5-8K notional (appropriate for $7K account)  
✅ **Risk/Reward**: 2:1 R:R built-in  
✅ **Market Timing**: Caught actual upward price movement

---

## How To Recreate These Signals

### Environment Settings (.env)

```bash
# Strategies that generated the signals
ENABLED_STRATEGIES=fabio_aaa_full,holy_grail,ema_scalper,institutional_sd

# Confidence threshold (signals passed at 70%+)
OANDA_SIGNAL_CONFIDENCE_THRESHOLD=0.70

# Position sizing (matched account size)
MIN_NOTIONAL_USD=5000
MAX_NOTIONAL_USD=8000

# AI Hive enabled (Grok validated)
ENABLE_AI_HIVE=true
USE_HIVE_VALIDATION=true
```

### Market Conditions Required

1. **Clear trend**: 6+ of 10 bars same direction
2. **Momentum**: >0.1% move over 5 bars
3. **RSI**: 45-55 (neutral, not extended)
4. **AI agreement**: ≥70% from at least one model

---

## Logging Improvement (Added 2026-01-12)

Signals now log with strategy name:

```
🎯 SIGNAL [holy_grail]: EUR_USD BUY @ $1.17200 (conf: 75%)
🤖 AI HIVE ANALYSIS: EUR_USD BUY
   ✅ Grok: BUY (75%)
   📊 Decision: APPROVE (75%)
```

This allows tracing which strategy generated each winning signal.

---

## Summary

| Metric            | Value                                                |
| ----------------- | ---------------------------------------------------- |
| Strategies Active | 4                                                    |
| Signal Generator  | Likely `holy_grail` or `ema_scalper`                 |
| AI Validator      | Grok @ 70-80%                                        |
| Position Size     | ~$5-8K notional                                      |
| Result            | +$163 combined profit                                |
| Issue Found       | Engine-side trailing stops died with engine          |
| Fix Applied       | OANDA broker-side trailing stops (survives restarts) |

---

## Next Steps

1. ✅ Strategy logging improved (shows which strategy)
2. ✅ Broker-side trailing stops enabled by default
3. 🔄 Run engine again to collect more winning signals
4. 📊 Track which strategies produce best results

_Generated 2026-01-12 by RICK Signal Analysis_
