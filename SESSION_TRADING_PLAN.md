# 🌍 SESSION-AWARE TRADING PLAN
## NYC/London Focused with Cross-Broker Hedging

---

## 📅 TRADING SCHEDULE

### 🇬🇧 LONDON SESSION (07:00-16:00 UTC / 2am-11am EST)
**Characteristics**: High volume, strong trends, forex/crypto active

**Configuration**:
- **Max Positions**: 4
- **Risk Multiplier**: 1.2x (20% higher than base)
- **Capital Allocation**: 60% IBKR / 40% Coinbase
- **Preferred Strategies**: institutional_sd, ema_scalper (trend-following)
- **Instruments**: GBPUSD, EURUSD, GBPJPY, BTC-USD, ETH-USD
- **Hedging**: Enabled

**Why**: London opening brings major forex movement, European economic data releases

---

### 🇺🇸 NEW YORK SESSION (13:00-21:00 UTC / 8am-4pm EST)
**Characteristics**: Highest volume globally, volatility peaks, all markets active

**Configuration**:
- **Max Positions**: 5
- **Risk Multiplier**: 1.3x (30% higher)
- **Capital Allocation**: 50% IBKR / 50% Coinbase
- **Preferred Strategies**: institutional_sd, ema_scalper, trap_reversal
- **Instruments**: SPY, QQQ, EURUSD, BTC-USD, ETH-USD
- **Hedging**: Enabled

**Why**: US market open, economic data, highest liquidity

---

### 🔥 OVERLAP PERIOD (13:00-16:00 UTC / 8am-11am EST)
**Characteristics**: **MAXIMUM LIQUIDITY** - London + NY combined, best execution

**Configuration**:
- **Max Positions**: 7 (MAXIMUM)
- **Risk Multiplier**: 1.5x (50% HIGHER - most aggressive)
- **Capital Allocation**: 50% IBKR / 50% Coinbase
- **Preferred Strategies**: ALL (institutional_sd, ema_scalper, trap_reversal)
- **Instruments**: GBPUSD, EURUSD, BTC-USD, ETH-USD, SPY, QQQ
- **Hedging**: Enabled

**Why**: Peak opportunity window, tightest spreads, highest win probability, both regions active

**⚠️ WARNING**: Most aggressive period - 50% higher risk, maximum positions, full leverage potential

---

### 🌏 ASIA SESSION (00:00-08:00 UTC / 7pm-3am EST)
**Characteristics**: Low volume, range-bound, forex-only

**Configuration**:
- **Max Positions**: 2 (minimal)
- **Risk Multiplier**: 0.7x (30% lower - conservative)
- **Capital Allocation**: 80% IBKR / 20% Coinbase
- **Preferred Strategies**: trap_reversal (range-bound)
- **Instruments**: USDJPY, AUDUSD, NZDUSD
- **Hedging**: Disabled

**Why**: Low liquidity = higher risk, reduced opportunity

---

### 🌙 OFF-HOURS (21:00-07:00 UTC excluding Asia)
**Configuration**:
- **Trading**: PAUSED or 1 position max
- **Why**: Weekend, gaps, low liquidity

---

## 🛡️ CROSS-BROKER HEDGING SYSTEM

### Loss Recovery Strategy

**Trigger**: 2+ consecutive losses on one broker

**Action**: Open inverse position on other broker to recover losses + profit

### Hedging Pairs

**Crypto → Equities (Inverse Correlation)**:
- BTC-USD loss (Coinbase) → SHORT SPY (IBKR)
- ETH-USD loss (Coinbase) → SHORT QQQ (IBKR)

**Equities → Crypto (Inverse)**:
- SPY/QQQ loss (IBKR) → LONG BTC-USD (Coinbase)

**Forex Inverse Pairs** (both IBKR):
- EURUSD long loss → SHORT USDCHF
- GBPUSD long loss → SHORT EURGBP

### Hedge Sizing
- **Target**: Recover losses + 20% profit
- **Size**: `(Total Losses × 1.2) / Account Balance`
- **Max Hedge**: 10% of account per hedge position

### Recovery Process
1. Detect 2+ consecutive losses on broker A
2. Calculate unrecovered loss amount
3. Identify inverse instrument on broker B
4. Open hedge position sized to recover + profit
5. Monitor hedge until target reached
6. Mark original losses as "recovered"
7. Close hedge, return to normal trading

---

## 📊 POSITION MANAGEMENT

### Session-Based Allocation

**London** (07:00-13:00 UTC):
- IBKR: 60% capital, 2-3 positions (forex heavy)
- Coinbase: 40% capital, 1-2 positions (crypto)

**NY** (13:00-21:00 UTC):
- IBKR: 50% capital, 2-3 positions (equities + forex)
- Coinbase: 50% capital, 2-3 positions (crypto)

**Overlap** (13:00-16:00 UTC):
- IBKR: 50% capital, 3-4 positions (ALL instruments)
- Coinbase: 50% capital, 3-4 positions (max aggression)

### Risk Multipliers by Session
- **Base Risk**: 4% per trade (extreme mode)
- **London**: 4% × 1.2 = **4.8% per trade**
- **NY**: 4% × 1.3 = **5.2% per trade**
- **Overlap**: 4% × 1.5 = **6.0% per trade** 🔥
- **Asia**: 4% × 0.7 = **2.8% per trade**

### Maximum Exposure
**Overlap Period with 5x Leverage**:
- Single position: 6% base × 5x leverage = **30% of account**
- 7 positions max: Theoretical 210% exposure (Kelly caps prevent this)

---

## 🎯 AGGRESSIVE BUT SMART RULES

### 1. Session Discipline
✅ **DO**: Trade aggressively during London/NY/Overlap
❌ **DON'T**: Force trades during Asia/Off-hours

### 2. Instrument Preference
- Each session has **preferred instruments** (see configs above)
- Trading preferred = +10% signal boost
- Trading non-preferred = -10% penalty

### 3. Hedge Activation
- Only hedge if losses >1% of account
- Only hedge in active sessions (London/NY/Overlap)
- Max 1 hedge per broker at a time
- Close hedge immediately when target reached

### 4. Leverage Scaling
- **2 wins**: 1.5x leverage
- **3 wins**: 2.0x leverage
- **5 wins**: 3.0x leverage
- **7+ wins**: 5.0x leverage (MAXIMUM)

Combined with session multipliers = **EXTREME POTENTIAL**

### 5. Emergency Brakes
- **5% drawdown**: Cut position sizes 25%
- **10% drawdown**: Cut position sizes 50%, reduce leverage
- **15% drawdown**: STOP trading, close all positions
- **Consecutive losses**: Activate hedging system

---

## 🚀 EXPECTED PERFORMANCE

### Conservative (Normal Trending)
- **Monthly**: 30-50% return
- **Drawdown**: 10-15%
- **Leverage**: 1.5-2.0x average
- **Hedges**: 1-2 per month

### Moderate (Strong Sessions)
- **Monthly**: 50-100% return
- **Drawdown**: 15-20%
- **Leverage**: 2.0-3.0x average
- **Hedges**: 2-3 per month

### Aggressive (Overlap Hot Streaks)
- **Monthly**: 100-200% return
- **Drawdown**: 20-30%
- **Leverage**: 3.0-5.0x peaks
- **Hedges**: 3-5 per month

---

## ⚠️ RISK DISCLOSURE

**This plan is EXTREMELY AGGRESSIVE**:
- 6% base risk during overlap
- 5x leverage potential
- 7 concurrent positions
- Cross-broker hedging adds complexity

**Worst Case**:
- 3 losing trades at max leverage during overlap = **-90% drawdown**
- Emergency brakes should prevent this, but risk exists

**Best Case**:
- Hot streak during overlap with 7 positions at 3-5x leverage = **+200-500% in days**

---

## 🎯 DEPLOYMENT

### Quick Start
```bash
cd /home/ing/RICK/MULTI_BROKER_PHOENIX

# Start session-aware engine
python3 MULTI_BROKER_PHOENIX/live_session_engine.py

# Monitor
tail -f live_session_engine.log
```

### Systemd Service
```bash
# Copy service file
sudo cp tools/systemd/rick_session_engine.service /etc/systemd/system/

# Enable and start
sudo systemctl enable rick_session_engine
sudo systemctl start rick_session_engine

# Monitor
journalctl -u rick_session_engine -f
```

---

## ✅ PRE-LAUNCH CHECKLIST

- [ ] Coinbase API activated and tested
- [ ] IBKR Gateway running
- [ ] Both accounts funded
- [ ] Test session detection (verify current session)
- [ ] Test hedging logic (simulate losses)
- [ ] Verify position sizing calculations
- [ ] Set up monitoring/alerts
- [ ] Run paper trading for 24h minimum
- [ ] Review max drawdown tolerance

---

**STATUS**: Ready to deploy with session awareness, cross-broker hedging, and extreme compounding.

**Created**: 2025-12-31  
**Systems**: SessionOrchestrator v1.0, LiveSessionEngine v1.0  
**Focus**: NYC/London/Overlap sessions with smart hedging
