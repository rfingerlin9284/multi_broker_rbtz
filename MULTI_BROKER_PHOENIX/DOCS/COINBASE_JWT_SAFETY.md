# Coinbase JWT Authentication - Safety System

## 🔐 Implementation Complete

JWT authentication is now **FULLY IMPLEMENTED** with **5 SAFETY GATES** to prevent accidental real money trades.

---

## 🛡️ 5 SAFETY GATES (All Must Pass)

### Gate 1: Paper Mode Default
```python
CoinbaseSafeConnector(paper_mode=True)  # Default - simulation only
```
**Real orders require:** `paper_mode=False` explicitly set

### Gate 2: Environment Check
```bash
# In .env file:
TRADING_MODE=PAPER  # Default - blocks all real orders
```
**Real orders require:** `TRADING_MODE=LIVE`

### Gate 3: Explicit Confirmation Parameter
```python
place_live_order(candidate, size, confirm_real_money=False)  # Default
```
**Real orders require:** `confirm_real_money=True` explicitly passed

### Gate 4: JWT Authentication
```python
# Requires both:
COINBASE_API_KEY=organizations/.../apiKeys/...
COINBASE_API_SECRET=-----BEGIN EC PRIVATE KEY-----\n...
```
**Real orders require:** Valid credentials with JWT token generation

### Gate 5: Nano-Lot Safety Limits
- $5-10 per trade (hard limits)
- $50 daily loss limit
- 10 trades per day maximum
- Stop after 5 consecutive losses

**All 5 gates must pass** - if any fail, order is rejected with specific error message.

---

## ✅ How to Verify Credentials (Safe)

### Step 1: Run Verification Script
```bash
cd /home/ing/RICK/MULTI_BROKER_PHOENIX/MULTI_BROKER_PHOENIX

# Load environment
source ../.venv/bin/activate

# Run READ-ONLY verification
python3 tools/verify_coinbase_auth.py
```

This script:
- ✅ Checks API credentials configured
- ✅ Generates JWT token
- ✅ Calls GET `/accounts` endpoint (read-only)
- ✅ Shows account summary
- ❌ **NEVER places orders**

### Step 2: Expected Output (Success)
```
╔══════════════════════════════════════════════════════════════════╗
║       COINBASE AUTHENTICATION VERIFICATION (READ-ONLY)           ║
╚══════════════════════════════════════════════════════════════════╝

✅ API Key found: organizations/5ae72c85.../apiKeys/0d84aa48...
✅ API Secret configured (EC private key)

Creating Coinbase connector...
🔧 Coinbase Advanced Trade Connector initialized: 🟢 SIMULATION
   API: Coinbase Advanced Trade (v3)
   JWT Auth: ✅ READY
   
🔐 Verifying Coinbase API credentials (read-only)...
✅ Credentials verified! Found 3 accounts
   Account: USD - Available: 1234.56
   Account: BTC - Available: 0.00123
   Account: ETH - Available: 0.0456

📋 VERIFICATION RESULT:

✅ SUCCESS - Credentials are valid!
   Successfully authenticated with 3 accounts

🎯 Your Coinbase Advanced Trade API is properly authenticated.
```

---

## 🚨 How to Place Real Order (Advanced - Use Caution)

**Prerequisites:**
1. ✅ 500+ successful paper trades on IBKR
2. ✅ Positive overall P&L in simulation
3. ✅ Credentials verified with script above
4. ✅ Understanding of all 5 safety gates

### Configuration Changes Required:

**1. Edit .env:**
```bash
# Change this line:
TRADING_MODE=LIVE  # Enables real orders (was PAPER)
```

**2. Code Example:**
```python
from multi_broker_phoenix.brokers.coinbase_safe_connector import CoinbaseSafeConnector

# Initialize with paper_mode=False (Gate 1 bypass)
connector = CoinbaseSafeConnector(
    paper_mode=False,  # ⚠️ REAL MONEY MODE
    engine=None
)

# Create trade candidate
class Candidate:
    symbol = 'BTC-USD'
    side = 'BUY'
    entry_price = 85000.0
    stop_loss = 83000.0
    strategy_id = 'manual_test'

candidate = Candidate()

# Fetch current price
connector.update_price('BTC-USD', 85233.45)

# Place order with ALL safety gates satisfied:
result = connector.place_live_order(
    candidate=candidate,
    size=0.000117,  # ~$10 at $85k
    confirm_real_money=True  # Gate 3: Explicit confirmation
)

print(result)
```

**3. Expected Output:**
```
==========================================
🔴 PLACING LIVE ORDER - REAL MONEY TRADE
==========================================
Symbol: BTC-USD
Side: BUY
Size: 0.000117
Price: $85233.45
Notional: $9.97
---
Trades Today: 1/10
Daily Loss: $0.00/$50.00
==========================================

📤 Sending order to Coinbase: {
  "product_id": "BTC-USD",
  "side": "BUY",
  "order_configuration": {
    "limit_limit_gtc": {
      "base_size": "0.000117",
      "limit_price": "85233.45",
      "post_only": false
    }
  },
  "client_order_id": "RICK-1735123456789"
}

✅ LIVE ORDER PLACED: abc-123-def-456
```

---

## 🧪 Test Scenarios

### Test 1: Verify Credentials (Safe)
```bash
python3 tools/verify_coinbase_auth.py
```
**Risk:** ZERO - read-only operation

### Test 2: Paper Mode (Default)
```python
connector = CoinbaseSafeConnector()  # paper_mode=True by default
connector.place_paper_order(candidate, size)
```
**Risk:** ZERO - simulation only

### Test 3: Attempt Real Order Without All Gates
```python
connector = CoinbaseSafeConnector(paper_mode=False)
# This will FAIL at Gate 2 (TRADING_MODE != LIVE)
result = connector.place_live_order(candidate, size)
# Result: RuntimeError("Set TRADING_MODE=LIVE in .env")
```
**Risk:** ZERO - blocked by safety gate

### Test 4: Attempt Real Order Missing Gate 3
```python
connector = CoinbaseSafeConnector(paper_mode=False)
# TRADING_MODE=LIVE set, but missing confirm_real_money
result = connector.place_live_order(candidate, size)  # confirm_real_money defaults to False
# Result: RuntimeError("Must explicitly confirm real money with confirm_real_money=True")
```
**Risk:** ZERO - blocked by safety gate

### Test 5: Real Order with All Gates Satisfied
```python
connector = CoinbaseSafeConnector(paper_mode=False)
# TRADING_MODE=LIVE set
result = connector.place_live_order(candidate, size, confirm_real_money=True)
# Result: Order placed if all safety limits pass
```
**Risk:** LIMITED - $5-10 max, subject to nano-lot limits

---

## 📊 Safety Limit Examples

### Example 1: Trade Too Small (Blocked)
```python
size = 0.00001  # ~$0.85 worth
# Result: "Below minimum trade size ($0.85 < $5.00)"
```

### Example 2: Trade Too Large (Auto-Adjusted)
```python
size = 0.00015  # ~$12.78 worth
# Result: Auto-adjusted to 0.000117 (~$10.00 max)
```

### Example 3: Daily Loss Limit Hit (Blocked)
```python
# After losing $50 today
result = connector.place_live_order(...)
# Result: "⛔ DAILY LOSS LIMIT HIT: $50.00 >= $50.00"
```

### Example 4: Consecutive Losses (Stopped)
```python
# After 5 consecutive losing trades
result = connector.place_live_order(...)
# Result: "⛔ TRADING STOPPED: 5 consecutive losses"
```

---

## 🔍 Monitoring Real Orders

### View Order in Coinbase
1. Go to https://www.coinbase.com/advanced-trade
2. Click "Orders" tab
3. Look for order with client ID: `RICK-{timestamp}`

### Check in Database
```python
import sqlite3
conn = sqlite3.connect('data/paper_ledger.sqlite')
trades = conn.execute('SELECT * FROM trades WHERE platform="COINBASE"').fetchall()
print(trades)
```

### Log Files
```bash
tail -f logs/rick_battlestation.log | grep COINBASE
```

---

## ⚠️ CRITICAL REMINDERS

1. **Paper Mode is Default** - Real orders require explicit configuration changes
2. **5 Safety Gates** - All must pass for real order execution
3. **Nano-Lot Limits** - Maximum $10 per trade, $50 daily loss
4. **Verification First** - Always run `verify_coinbase_auth.py` before real trading
5. **IBKR Paper First** - Prove edge with 500+ simulated trades before real money

---

## 🛠️ Troubleshooting

### Error: "PyJWT and cryptography packages required"
```bash
pip install pyjwt cryptography
```

### Error: "JWT authentication not configured"
Check `.env` file has both:
```bash
COINBASE_API_KEY=organizations/.../apiKeys/...
COINBASE_API_SECRET=-----BEGIN EC PRIVATE KEY-----\n...
```

### Error: "Coinbase API error: 401"
- API key may be invalid or expired
- Check permissions: key needs "view" and "trade" enabled
- Regenerate key in Coinbase dashboard if needed

### Error: "Set TRADING_MODE=LIVE in .env"
This is **intentional safety** - edit `.env` to enable real orders:
```bash
TRADING_MODE=LIVE  # Change from PAPER
```

---

## 📝 Summary

✅ **What's Implemented:**
- Full JWT token generation with EC private key
- Authenticated GET/POST requests to Coinbase Advanced Trade API
- 5-layer safety gate system
- Read-only credential verification
- Nano-lot safety limits
- Real order placement with comprehensive logging

✅ **What's Safe:**
- Default paper mode (simulation)
- Multiple explicit gates required for real orders
- Maximum $10 per trade
- Daily loss limits
- Consecutive loss circuit breaker

✅ **How to Start:**
1. Run `verify_coinbase_auth.py` to confirm credentials
2. Keep TRADING_MODE=PAPER for learning
3. Use paper mode until 500+ successful trades
4. When ready: Set TRADING_MODE=LIVE, use confirm_real_money=True

**You now have full authentication with maximum safety.**
