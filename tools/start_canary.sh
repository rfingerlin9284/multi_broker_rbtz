#!/bin/bash
# CANARY MODE QUICK START
# Ultra-simple script to launch Coinbase in canary mode

cd /home/ing/RICK/MULTI_BROKER_PHOENIX

export PYTHONPATH=$PWD/MULTI_BROKER_PHOENIX:$PWD
export CANARY_MODE=true
export HEADLESS_MODE=coinbase-only
export DEFAULT_STRATEGY=holy_grail
export FEED_SYMBOLS=BTC-USD,ETH-USD

echo "🐤 Starting Coinbase RBOTzilla in CANARY MODE"
echo "=============================================="
echo "  Mode: Ultra-Conservative Monitoring"
echo "  Broker: Coinbase Only (Paper)"
echo "  Strategy: Holy Grail RSI"
echo "  Symbols: BTC-USD, ETH-USD"
echo "  Polling: 30s (slow & safe)"
echo "  Max Risk: \$10 per trade"
echo "=============================================="
echo ""

./tools/py_venv.sh MULTI_BROKER_PHOENIX/tools/run_headless.py --mode coinbase-only

