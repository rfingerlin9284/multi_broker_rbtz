# Coinbase RBOTzilla Setup Guide

## Overview
This guide helps you set up and run the headless Coinbase trading bot (RBOTzilla) in paper mode. The system can fetch live prices from Coinbase's public API and simulate trades without requiring API credentials.

## Quick Start

### 1. Verify Configuration

Check your `.env` file has these settings:

```bash
# Trading mode
TRADING_MODE=PAPER
PAPER_VIA_PLATFORM=1

# Headless mode set to Coinbase-only
HEADLESS_MODE=coinbase-only

# Crypto symbols to trade (hyphen format for Coinbase)
FEED_SYMBOLS=BTC-USD,ETH-USD

# Polling interval (seconds)
HEADLESS_POLL_SECONDS=2.0

# Default strategy
DEFAULT_STRATEGY=holy_grail
```

### 2. Validate Coinbase Connector

Run the validation script to ensure everything works:

```bash
cd /home/ing/RICK/MULTI_BROKER_PHOENIX
PYTHONPATH=/home/ing/RICK/MULTI_BROKER_PHOENIX/MULTI_BROKER_PHOENIX:$PYTHONPATH \
  python3 tools/validate_coinbase.py
```

Expected output:
```
✓ BTC-USD: $89,343.36
✓ ETH-USD: $3,006.08
✓ Order placed successfully
✓ ALL TESTS PASSED - Coinbase connector is operational!
```

### 3. Run Headless Bot

Start the headless runner:

```bash
cd /home/ing/RICK/MULTI_BROKER_PHOENIX/MULTI_BROKER_PHOENIX
PYTHONPATH=/home/ing/RICK/MULTI_BROKER_PHOENIX/MULTI_BROKER_PHOENIX:$PYTHONPATH \
  python3 tools/run_headless.py --mode coinbase-only
```

Or use the task runner in VS Code:
- Press `Ctrl+Shift+P`
- Type "Run Task"
- Select "Run Headless (choose mode)"
- Choose "coinbase-only"

### 4. Monitor Operation

The bot will:
1. Fetch live prices from Coinbase every 2 seconds
2. Run the Holy Grail strategy on price data
3. Generate trade candidates
4. Execute paper trades through the engine
5. Log all activity to console

Example output:
```
Starting headless runner (minimal).
Headless mode: coinbase-only (Use Coinbase only)
Fetching BTC-USD: $89,343.36
Fetching ETH-USD: $3,006.08
placed order: {'id': 'PAPER-123', 'status': 'FILLED', ...}
```

## Configuration Details

### Symbol Format

**Coinbase uses hyphen format:**
- ✓ Correct: `BTC-USD`, `ETH-USD`, `SOL-USD`
- ✗ Wrong: `BTC_USD`, `BTCUSD`

### Available Modes

Set `HEADLESS_MODE` to:
- `coinbase-only` - Use only Coinbase (recommended)
- `ibkr-only` - Use only Interactive Brokers
- `auto` - Auto-select based on symbol format
- `simulate` - Pure simulation (no connector)
- `platform-paper` - Prefer platform paper accounts

### No API Keys Required (Paper Mode)

The Coinbase connector uses the **public API** to fetch prices, requiring no authentication. Paper trading is simulated locally.

### Optional: Live Trading (Not Recommended)

To enable live trading (requires Coinbase Advanced Trade API):
1. Get API credentials from Coinbase Advanced Trade
2. Set in `.env`:
   ```bash
   COINBASE_API_KEY=your_key_here
   COINBASE_API_SECRET=your_secret_here
   ALLOW_LIVE_REAL=1
   TRADING_MODE=LIVE
   ```

**⚠️ WARNING:** Live trading risks real money. Test thoroughly in paper mode first!

## Architecture

### Components

1. **CoinbaseConnector** ([coinbase_connector.py](../MULTI_BROKER_PHOENIX/multi_broker_phoenix/brokers/coinbase_connector.py))
   - Fetches live prices from Coinbase public API
   - Simulates paper order execution
   - Integrates with PaperEngine

2. **PaperEngine** ([paper_engine.py](../MULTI_BROKER_PHOENIX/multi_broker_phoenix/engines/paper_engine.py))
   - Tracks simulated positions and orders
   - Records trades to SQLite database
   - Calculates P&L and fees

3. **Headless Runner** ([run_headless.py](../MULTI_BROKER_PHOENIX/tools/run_headless.py))
   - Main loop that polls prices
   - Runs strategy logic
   - Routes orders to appropriate connector

4. **RiskManager** ([risk_manager.py](../MULTI_BROKER_PHOENIX/multi_broker_phoenix/risk/risk_manager.py))
   - Position sizing
   - Drawdown limits
   - Trade risk gates

### Data Flow

```
Coinbase Public API
    ↓ (fetch_live_price)
CoinbaseConnector
    ↓ (price data)
Strategy (Holy Grail RSI)
    ↓ (trade candidate)
RiskManager
    ↓ (size validation)
CoinbaseConnector.place_paper_order
    ↓
PaperEngine
    ↓
SQLite Database (trades.db)
```

## Troubleshooting

### "No price data"
- Check internet connection
- Verify symbol format (use hyphens: `BTC-USD`)
- Try: `curl https://api.exchange.coinbase.com/products/BTC-USD/ticker`

### "Module not found: multi_broker_phoenix"
- Set PYTHONPATH:
  ```bash
  export PYTHONPATH=/home/ing/RICK/MULTI_BROKER_PHOENIX/MULTI_BROKER_PHOENIX:$PYTHONPATH
  ```

### "Database is locked"
- Only run one instance at a time
- Delete `/tmp/trades.db` if corrupted

### "Trade blocked"
- Check risk limits in RiskManager
- Review `TEST_ORDER_MAX_USD` in `.env`
- Check daily order limits

### "Coinbase authentication failed (401)"
- Ensure `COINBASE_API_KEY` is the full key path (e.g. `organizations/.../apiKeys/...`).
- If `COINBASE_API_SECRET` is stored in `.env`, remove any surrounding quotes and either:
  - Store the PEM on a single line using `\n` for newlines, or
  - Use `COINBASE_API_SECRET_FILE=/path/to/key.pem` and point the env var to the file (recommended).
- Run `python3 tools/debug_coinbase_auth.py` to print the generated JWT header/claims and the verification result.
- If problems persist, double-check the API key permissions in the Coinbase dashboard.


## Testing Strategies

Edit `DEFAULT_STRATEGY` in `.env`:
- `holy_grail` - RSI + Trend + Momentum (default)
- `bullish_regime` - Bull market strategy
- Custom strategies in [strategies/](../MULTI_BROKER_PHOENIX/multi_broker_phoenix/strategies/)

## Logs and Data

- Trades database: `/tmp/trades.db`
- View trades: `sqlite3 /tmp/trades.db "SELECT * FROM trades;"`
- Console logs: All activity printed to stdout

## Next Steps

1. ✓ Verify configuration
2. ✓ Run validation script
3. ✓ Start headless bot
4. Monitor for 24 hours in paper mode
5. Review trade quality and P&L
6. Adjust strategy parameters
7. Consider additional risk limits

## Support Files

- [.env.example](../.env.example) - Environment template
- [validate_coinbase.py](../tools/validate_coinbase.py) - Validation script
- [run_headless.py](../MULTI_BROKER_PHOENIX/tools/run_headless.py) - Main runner

## Safety Notes

- ✓ Paper mode is safe (no real money)
- ✓ Public API has no auth (no keys exposed)
- ✓ All trades are simulated locally
- ⚠️ Never commit real API keys to git
- ⚠️ Test strategies thoroughly before live use
