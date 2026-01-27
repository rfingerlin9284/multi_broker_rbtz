#!/bin/bash
# Start Dual-Broker Live Trading (Coinbase + IBKR)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "=============================================="
echo "🚀 STARTING DUAL-BROKER LIVE TRADING"
echo "=============================================="
echo ""
echo "📊 Configuration:"
echo "   Broker 1: Coinbase Advanced (LIVE - REAL MONEY)"
echo "   Broker 2: IBKR Paper (Port 4002 - FAKE MONEY)"
echo "   Mode: Phase 1 NANO_SPOT"
echo "   Position Size: \$10"
echo "   Stop Loss: 2% (trailing)"
echo "   Daily Limit: \$50 loss, 10 trades"
echo "   Symbols: BTC-USD, ETH-USD"
echo ""
echo "⚠️  WARNING: Coinbase uses REAL MONEY!"
echo "   IBKR uses PAPER account (zero risk)"
echo "   Max risk per trade: \$10"
echo "   Max daily loss: \$50"
echo ""

# Check for Coinbase API credentials
if ! grep -q "^COINBASE_API_KEY=organizations/" "$PROJECT_ROOT/.env" 2>/dev/null; then
    echo "❌ ERROR: Coinbase API credentials not found in .env"
    exit 1
fi

echo "✅ Coinbase API credentials found"

# Check for IBKR (non-fatal)
if ! nc -z localhost 4002 2>/dev/null; then
    echo "⚠️  WARNING: IBKR TWS Gateway not responding on port 4002"
    echo "   Continuing with Coinbase only..."
    echo ""
    IBKR_AVAILABLE=false
else
    echo "✅ IBKR TWS Gateway detected"
    IBKR_AVAILABLE=true
fi

echo ""

# Confirm before starting
read -p "Start dual-broker live trading? (type 'YES' to confirm): " confirm
if [ "$confirm" != "YES" ]; then
    echo "Cancelled."
    exit 0
fi

echo ""
echo "🔄 Starting dual-broker trading engine..."
echo "   Press Ctrl+C to stop gracefully"
echo "   PID file: /tmp/rick_phoenix_trading.pid"
echo "   Log file: logs/dual_broker_live.log"
echo ""

# Create logs directory
mkdir -p "$PROJECT_ROOT/logs"

# Kill any existing instances
"$SCRIPT_DIR/stop_trading_engine.sh" --quiet

# Set environment
export PYTHONPATH="$PROJECT_ROOT/MULTI_BROKER_PHOENIX:$PROJECT_ROOT"

# Run dual-broker trading
python3 "$PROJECT_ROOT/MULTI_BROKER_PHOENIX/tools/run_dual_broker_live.py" \
    --symbols BTC-USD ETH-USD \
    --poll-seconds 10 \
    --ibkr-enabled="$IBKR_AVAILABLE" \
    2>&1 | tee "$PROJECT_ROOT/logs/dual_broker_live.log" &

# Save PID
echo $! > /tmp/rick_phoenix_trading.pid

echo ""
echo "✅ Trading engine started (PID: $(cat /tmp/rick_phoenix_trading.pid))"
echo ""
echo "📊 Monitoring: logs/dual_broker_live.log"
echo "🛑 To stop: Run 'Stop Trading Engine' task or Ctrl+C"
echo ""

# Wait for process
wait
