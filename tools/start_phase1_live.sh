#!/bin/bash
# Start Phase 1 Live Trading with Coinbase + Progression Manager

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "=============================================="
echo "🚀 STARTING PHASE 1 LIVE TRADING"
echo "=============================================="
echo ""
echo "📊 Configuration:"
echo "   Broker: Coinbase (LIVE - REAL MONEY)"
echo "   Mode: Phase 1 NANO_SPOT"
echo "   Position Size: \$10"
echo "   Stop Loss: 2% (trailing)"
echo "   Daily Limit: \$50 loss, 10 trades"
echo "   Symbols: BTC-USD, ETH-USD"
echo ""
echo "⚠️  WARNING: This uses REAL MONEY on Coinbase!"
echo "   Max risk per trade: \$10"
echo "   Max daily loss: \$50"
echo ""

# Check for API credentials
if ! grep -q "^COINBASE_API_KEY=organizations/" "$PROJECT_ROOT/.env" 2>/dev/null; then
    echo "❌ ERROR: Coinbase API credentials not found in .env"
    echo ""
    echo "Please add your Coinbase API credentials:"
    echo "1. Get API key from https://www.coinbase.com/settings/api"
    echo "2. Add to .env file:"
    echo "   COINBASE_API_KEY=organizations/xxxxx/apiKeys/xxxxx"
    echo "   COINBASE_API_SECRET=-----BEGIN EC PRIVATE KEY-----..."
    echo ""
    echo "See DOCS/coinbase_api_setup.md for details"
    exit 1
fi

echo "✅ API credentials found"
echo ""

# Confirm before starting
read -p "Start live trading? (type 'YES' to confirm): " confirm
if [ "$confirm" != "YES" ]; then
    echo "Cancelled."
    exit 0
fi

echo ""
echo "🔄 Starting live trading..."
echo "   Press Ctrl+C to stop"
echo "   Log file: logs/phase1_live.log"
echo ""

# Create logs directory
mkdir -p "$PROJECT_ROOT/logs"

# Set environment
export PYTHONPATH="$PROJECT_ROOT/MULTI_BROKER_PHOENIX:$PROJECT_ROOT"

# Run live trading with progression manager
python3 "$PROJECT_ROOT/MULTI_BROKER_PHOENIX/tools/run_phase1_live.py" \
    --symbols BTC-USD ETH-USD \
    --poll-seconds 10 \
    2>&1 | tee "$PROJECT_ROOT/logs/phase1_live.log"
