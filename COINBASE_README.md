# 🚀 Coinbase RBOTzilla - Quick Start

Fully operational headless Coinbase trading bot in paper mode.

## Status: ✅ OPERATIONAL

All core systems validated and working:
- ✅ Live price fetching from Coinbase (no API keys needed)
- ✅ Paper order execution through PaperEngine
- ✅ Strategy integration (Holy Grail RSI)
- ✅ Risk management and position sizing
- ✅ Database persistence

## One-Command Start

```bash
./tools/start_coinbase.sh
```

This script will:
1. Verify configuration
2. Run validation tests
3. Start the headless bot automatically

## Manual Start

```bash
cd MULTI_BROKER_PHOENIX
PYTHONPATH=$PWD:$PYTHONPATH python3 tools/run_headless.py --mode coinbase-only
```

## Configuration

Edit [.env](.env):
```bash
HEADLESS_MODE=coinbase-only
FEED_SYMBOLS=BTC-USD,ETH-USD
DEFAULT_STRATEGY=holy_grail
```

## What It Does

1. **Fetches live prices** from Coinbase every 2 seconds (BTC-USD, ETH-USD)
2. **Runs strategy** on price data (RSI, trend, momentum)
3. **Generates signals** with confidence scores
4. **Validates trades** through risk manager
5. **Executes paper orders** (simulated, no real money)
6. **Logs everything** to console and database

## Documentation

- 📖 **Full Setup Guide**: [DOCS/setup_coinbase.md](DOCS/setup_coinbase.md)
- 🧪 **Validation**: `python3 tools/validate_coinbase.py`
- 🔧 **Configuration**: [.env.example](.env.example)

## Key Features

### Paper Mode (Safe)
- No real money at risk
- Uses Coinbase public API (no credentials needed)
- Simulates fills with realistic slippage and fees

### Live Price Data
- Real-time BTC-USD and ETH-USD prices
- Public API endpoint (no rate limits for basic data)
- Automatic price updates every 2 seconds

### Strategy Engine
- Holy Grail RSI strategy (default)
- Multiple timeframe analysis
- Confidence-based signal generation
- Customizable parameters

### Risk Management
- Position sizing based on account equity
- Maximum order limits
- Daily trade caps
- Drawdown protection

## Quick Commands

```bash
# Validate setup
python3 tools/validate_coinbase.py

# Start bot (quick start)
./tools/start_coinbase.sh

# Start bot (manual)
python3 MULTI_BROKER_PHOENIX/tools/run_headless.py --mode coinbase-only

# View trades
sqlite3 /tmp/trades.db "SELECT * FROM trades ORDER BY timestamp DESC LIMIT 10;"

# Monitor logs
tail -f /var/log/phoenix.log  # If using systemd
```

## What's Disabled

✗ OANDA connector (focusing on Coinbase/IBKR)
- API credentials commented out
- Trailing stop monitor disabled
- Forex symbols removed from feed

## Next Steps

1. ✅ System is ready to run
2. Run in paper mode for 24-48 hours
3. Monitor trade quality and signals
4. Adjust strategy parameters if needed
5. Consider switching to IBKR mode (`HEADLESS_MODE=ibkr-only`)

## Troubleshooting

**No prices showing?**
```bash
# Test Coinbase API directly
curl https://api.exchange.coinbase.com/products/BTC-USD/ticker
```

**Module not found?**
```bash
# Set PYTHONPATH
export PYTHONPATH=/home/ing/RICK/MULTI_BROKER_PHOENIX/MULTI_BROKER_PHOENIX:$PYTHONPATH
```

**Database locked?**
```bash
# Stop all instances first
killall python3
# Clean database
rm /tmp/trades.db
```

## Architecture

```
┌─────────────────────┐
│  Coinbase Public    │
│      API            │
└──────────┬──────────┘
           │ fetch_live_price()
           ↓
┌─────────────────────┐
│ CoinbaseConnector   │
│  (Paper Mode)       │
└──────────┬──────────┘
           │ price data
           ↓
┌─────────────────────┐
│ Holy Grail Strategy │
│  (RSI + Trend)      │
└──────────┬──────────┘
           │ trade signal
           ↓
┌─────────────────────┐
│   Risk Manager      │
│  (size & gates)     │
└──────────┬──────────┘
           │ sized order
           ↓
┌─────────────────────┐
│   Paper Engine      │
│  (simulate fill)    │
└──────────┬──────────┘
           │ persist
           ↓
┌─────────────────────┐
│  SQLite Database    │
│   (/tmp/trades.db)  │
└─────────────────────┘
```

## Safety

- 🟢 Paper mode: No real money risk
- 🟢 Public API: No credentials exposed
- 🟢 Local simulation: All trades simulated
- 🟡 Test thoroughly before live use
- 🔴 Never commit API keys to git

---

**Ready to go!** Run `./tools/start_coinbase.sh` to start trading.
