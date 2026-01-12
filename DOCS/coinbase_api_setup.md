# Coinbase API Setup for Live Trading

## Get Your API Credentials

1. **Log in to Coinbase**: https://www.coinbase.com/
2. **Navigate to Settings → API**
3. **Create New API Key** with these permissions:
   - ✅ View account balances
   - ✅ View transaction history  
   - ✅ Trade (buy/sell)
   - ❌ Transfer funds (NOT needed - safer without)
   - ❌ Withdraw funds (NOT needed - safer without)

4. **Save credentials immediately** (shown only once):
   - API Key: `organizations/xxxxx/apiKeys/xxxxx`
   - API Secret: Long base64 string

## Add to Your .env File

```bash
# Open your .env file
nano /home/ing/RICK/MULTI_BROKER_PHOENIX/.env

# Add your credentials (replace with actual values):
COINBASE_API_KEY=organizations/xxxxx/apiKeys/xxxxx
COINBASE_API_SECRET=-----BEGIN EC PRIVATE KEY-----\nYOUR_PRIVATE_KEY_HERE\n-----END EC PRIVATE KEY-----
```

## Security Best Practices

- ✅ Store credentials in `.env` file (gitignored)
- ✅ Never commit credentials to git
- ✅ Keep API secret offline (password manager)
- ✅ Disable transfer/withdraw permissions
- ✅ Set IP whitelist in Coinbase (optional)
- ❌ Never share credentials in screenshots/chat

## Verification

Run this test to verify credentials work:

```bash
cd /home/ing/RICK/MULTI_BROKER_PHOENIX
export PYTHONPATH=$PWD/MULTI_BROKER_PHOENIX:$PWD
python3 -c "
from multi_broker_phoenix.brokers.coinbase_safe_connector import CoinbaseSafeConnector
import os
os.chdir('/home/ing/RICK/MULTI_BROKER_PHOENIX')
conn = CoinbaseSafeConnector(paper_mode=False)
price = conn.fetch_live_price('BTC-USD')
print(f'✅ Connected! BTC: \${price:,.2f}')
"
```

If you see the BTC price, you're ready to trade live!

## Start Live Trading

```bash
cd /home/ing/RICK/MULTI_BROKER_PHOENIX
./tools/start_phase1_live.sh
```

## Phase 1 Limits (Safety)

- $5-10 per trade (nano-lots)
- $50 daily loss limit
- 10 trades max per day
- 2% initial stop loss
- 5 consecutive loss breaker
- Auto-stops after safety trigger

You can adjust these in `.env` if needed.
