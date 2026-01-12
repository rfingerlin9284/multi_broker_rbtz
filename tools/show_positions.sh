#!/bin/bash
# Quick view of all open positions with narration

cd ~/RICK/MULTI_BROKER_PHOENIX || exit 1

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   📊 LIVE POSITION STATUS DISPLAY      ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# Check if battlestation is running
if pgrep -f "autonomous_trading.py" > /dev/null; then
    echo "✅ BATTLESTATION: RUNNING"
    echo ""
    
    # Show last 50 lines of position updates from logs
    if [ -f logs/rick_battlestation.log ]; then
        echo "📋 Recent position activity:"
        echo ""
        grep -E "(NEW POSITION|TRAILING STOP|POSITION CLOSED|LIVE POSITIONS)" logs/rick_battlestation.log | tail -30
    else
        echo "⚠️  No logs found yet"
    fi
else
    echo "⏸️  BATTLESTATION: STOPPED"
    echo ""
    echo "💡 Start with: rick-start"
fi

echo ""
