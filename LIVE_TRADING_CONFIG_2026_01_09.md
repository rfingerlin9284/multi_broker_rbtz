# LIVE TRADING CONFIGURATION - January 9, 2026

## 🔴 SIMULATION PURGED - API-ONLY MODE ACTIVATED

The system has been reconfigured to use **REAL API CONNECTIONS** instead of internal simulation:

### Broker Configuration

| Broker       | Mode        | API Connection             | Real Money?          |
| ------------ | ----------- | -------------------------- | -------------------- |
| **OANDA**    | 🟡 PRACTICE | `api-fxpractice.oanda.com` | No (paper account)   |
| **IBKR**     | 🟡 PAPER    | TWS Port 4002              | No (paper account)   |
| **COINBASE** | 🔴 LIVE     | Coinbase Advanced API      | **YES - REAL MONEY** |

---

## ✅ Authentication Verified

### OANDA Practice API

- Token: `1bb4ee52c51d...` ✅ VALID
- Account: `101-001-31210531-001`
- API URL: `https://api-fxpractice.oanda.com`
- EUR_USD Price: 1.16358 (live feed working)

### IBKR Paper Trading

- Host: `172.25.80.1:4002`
- Status: ⚠️ **TWS/Gateway needs to be started**
- Port 4002 = Paper trading account

### Coinbase Live Trading

- API Key: `organizations/d5765db5-8d75...` ✅ JWT READY
- BTC-USD Price: $90,237.47 (live feed working)
- **⚠️ REAL MONEY MODE - ENABLED**

---

## 🛡️ Coinbase Safety Limits (Nano-Lot Trading)

The system starts with ultra-conservative limits and auto-scales up as performance proves edge:

| Limit                         | Value  |
| ----------------------------- | ------ |
| Min Trade                     | $5.00  |
| Max Trade                     | $10.00 |
| Daily Loss Limit              | $50.00 |
| Stop After Consecutive Losses | 5      |
| Auto-Scaling                  | ON     |

### Auto-Scaling Tiers

1. **Nano** ($5-10) - Starting tier
2. **Micro** ($10-25) - 60% win rate, +$20 profit, 20+ trades
3. **Mini** ($25-50) - 62% win rate, +$75 profit, 30+ trades
4. **Small** ($50-100) - 64% win rate, +$200 profit, 50+ trades
5. **Standard** ($100-250) - 66% win rate, +$500 profit, 75+ trades
6. **Large** ($250-500) - 68% win rate, +$1500 profit, 100+ trades

---

## 📋 Files Modified

1. **`.env`** - Updated Coinbase to LIVE mode with API key
2. **`MULTI_BROKER_PHOENIX/tools/run_headless.py`** - Rewired broker initialization:
   - OANDA: Uses practice API (real orders on paper account)
   - IBKR: Uses IBKRLiveConnector (real TWS connection to paper port)
   - Coinbase: Uses live orders when `COINBASE_LIVE=true`
3. **`scripts/verify_all_broker_auth.py`** - New verification script

---

## 🚀 How to Start Trading

### 1. Verify Authentication

```bash
python3 scripts/verify_all_broker_auth.py
```

### 2. Start IBKR Gateway (if using IBKR)

- Launch TWS or IB Gateway
- Enable API connections on port 4002 (paper trading)
- Make sure "Read-Only API" is UNCHECKED

### 3. Start the Trading Engine

```bash
python3 MULTI_BROKER_PHOENIX/tools/run_headless.py --mode multi-asset
```

Or use VS Code task: **🚀 RBOTZILLA: Start ALL Brokers + Hive**

---

## ⚠️ IMPORTANT NOTES

1. **OANDA trades will execute on PRACTICE account** (real API, fake money)
2. **IBKR trades will execute on PAPER account** (real TWS, fake money)
3. **COINBASE trades will execute with REAL MONEY** (no paper account exists)

---

## Reference: Jan 7th Configuration

The system was working seamlessly on Jan 7th with OANDA paper account. This configuration restores that capability while adding:

- Coinbase live trading with nano-lot safety limits
- IBKR paper trading via TWS (when running)
- Auto-scaling to increase position size as edge is proven

---

_Generated: January 9, 2026_
