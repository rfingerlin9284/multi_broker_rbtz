#!/usr/bin/env bash
# Quick status check - shows if RBOTZILLA is ready

echo "════════════════════════════════════════════════════════════════"
echo "🤖 RBOTZILLA STATUS CHECK"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Check if .env exists
if [ -f ".env" ]; then
    echo "✅ Configuration file: PRESENT"
    source .env 2>/dev/null
else
    echo "❌ Configuration file: MISSING"
    exit 1
fi

# Check FABIO threshold
if [ "$FABIO_RSI_THRESHOLD" = "40" ]; then
    echo "✅ FABIO RSI Threshold: 40 (optimized, 167 trades)"
else
    echo "❌ FABIO RSI Threshold: ${FABIO_RSI_THRESHOLD} (should be 40)"
fi

# Check stop losses
if [ -n "$FABIO_STOP_MIN_PCT" ] && [ -n "$HOLY_GRAIL_STOP_PCT" ]; then
    echo "✅ Stop Losses: CONFIGURED for all strategies"
else
    echo "❌ Stop Losses: INCOMPLETE"
fi

# Check AI Hive
if [ "$USE_HIVE_VALIDATION" = "true" ] && [ -n "$AI_HIVE_DAILY_BUDGET_USD" ]; then
    echo "✅ AI Hive: ENABLED with \$${AI_HIVE_DAILY_BUDGET_USD}/day budget"
else
    echo "⚠️  AI Hive: NOT CONFIGURED"
fi

# Check trailing stops
if [ "$OANDA_TRAILING_STOP" = "true" ] && [ "$COINBASE_TRAILING_STOP" = "true" ]; then
    echo "✅ Trailing Stops: ENABLED (OANDA + Coinbase)"
else
    echo "⚠️  Trailing Stops: NOT FULLY ENABLED"
fi

# Check trading mode
if [ "$PAPER_TRADE_MODE" = "true" ]; then
    echo "✅ Trading Mode: PAPER (safe for testing)"
else
    echo "⚠️  Trading Mode: LIVE (real money at risk)"
fi

# Check API keys
keys_ok=true
if [ -n "$OANDA_API_TOKEN" ]; then
    echo "✅ OANDA API: CONFIGURED"
else
    echo "❌ OANDA API: MISSING"
    keys_ok=false
fi

if [ -n "$XAI_API_KEY" ]; then
    echo "✅ XAI (Grok) API: CONFIGURED"
else
    echo "⚠️  XAI (Grok) API: MISSING (AI Hive reduced capacity)"
fi

if [ -n "$OPENAI_API_KEY" ]; then
    echo "✅ OpenAI API: CONFIGURED"
else
    echo "⚠️  OpenAI API: MISSING (AI Hive reduced capacity)"
fi

# Check for running processes
echo ""
echo "Running Processes:"
if pgrep -f "run_headless" > /dev/null; then
    echo "  🟢 Trading Engine: RUNNING"
    pgrep -f "run_headless" | while read pid; do
        echo "     PID: $pid"
    done
else
    echo "  ⚪ Trading Engine: STOPPED"
fi

if pgrep -f "hive_validation" > /dev/null; then
    echo "  🟢 AI Hive: RUNNING"
else
    echo "  ⚪ AI Hive: STOPPED"
fi

# Check backup
echo ""
if [ -d "backups/fabio_v1.1.0" ]; then
    echo "✅ Backup: AVAILABLE (fabio_v1.1.0)"
else
    echo "⚠️  Backup: NOT FOUND"
fi

# Final verdict
echo ""
echo "════════════════════════════════════════════════════════════════"
if [ "$keys_ok" = true ] && [ "$FABIO_RSI_THRESHOLD" = "40" ]; then
    echo "🎉 STATUS: READY TO LAUNCH"
    echo ""
    echo "Quick Start:"
    echo "  ./RBOTZILLA_LAUNCH.sh"
    echo ""
    echo "Recommended: Select Option 2 (OANDA Forex Paper)"
else
    echo "⚠️  STATUS: NEEDS ATTENTION"
    echo ""
    echo "Fix issues above, then run:"
    echo "  ./system_audit.sh"
fi
echo "════════════════════════════════════════════════════════════════"
