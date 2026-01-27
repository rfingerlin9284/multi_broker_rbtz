#!/bin/bash
# RICK EXTREME TRADING - LIVE MONITOR
# Watch the trading engine in real-time

clear
echo "🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥"
echo "       RICK EXTREME TRADING ENGINE - LIVE MONITOR"
echo "🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥"
echo ""
echo "💰 Coinbase: LIVE (Real Money) | $5-10 trades"
echo "📝 OANDA: Practice | Unlimited forex trading"
echo "📝 IBKR: Paper | Stocks ready when markets open"
echo ""
echo "📊 Strategies: trap_reversal, institutional_sd, holy_grail, ema_scalper"
echo "🎯 Signal Threshold: >65% strength | Momentum: >0.05%"
echo "⚡ Validated: 21/35 tests (60%) | Best: +5,408%"
echo ""
echo "Press Ctrl+C to stop watching"
echo "==========================================================="
echo ""

# Live tail with colorization
tail -f /tmp/extreme_trading.log 2>/dev/null | while read line; do
    # Highlight signals in green
    if [[ "$line" == *"🎯 SIGNAL"* ]]; then
        echo -e "\033[1;32m$line\033[0m"
    elif [[ "$line" == *"✅ ORDER EXECUTED"* ]]; then
        echo -e "\033[1;36m$line\033[0m"
    elif [[ "$line" == *"💰 LIVE"* ]]; then
        echo -e "\033[1;33m$line\033[0m"
    elif [[ "$line" == *"❌"* ]]; then
        echo -e "\033[1;31m$line\033[0m"
    else
        echo "$line"
    fi
done
