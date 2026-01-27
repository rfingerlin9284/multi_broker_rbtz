#!/usr/bin/env bash
# Quick start script for dual-broker trading engine

cd "$(dirname "$0")"
export PYTHONPATH="$PWD:$PYTHONPATH"

echo "🚀 Starting RICK Multi-Broker Phoenix Trading Engine"
echo "=================================================="
echo ""
echo "📊 Configuration:"
echo "   - IBKR Paper: 27 futures contracts (Gold, Silver, BTC, etc.)"
echo "   - Coinbase Advanced: BTC/ETH spot trading"
echo "   - AI Hive: GPT-4 + Grok-3 consensus (ENABLED)"
echo "   - Smart Progression: Autonomous leverage scaling (ENABLED)"
echo "   - Mode: Paper trading (zero risk)"
echo ""
echo "💡 Trading will start automatically..."
echo ""

../tools/py_venv.sh tools/run_headless.py --mode auto
