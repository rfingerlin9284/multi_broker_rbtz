#!/bin/bash
# RICK BATTLESTATION - Complete Shutdown
# Stops all battlestation components cleanly

set -e

echo "========================================================================"
echo "🛑 RICK BATTLESTATION - SHUTDOWN SEQUENCE"
echo "========================================================================"
echo ""

WORKSPACE="/home/ing/RICK/MULTI_BROKER_PHOENIX"
cd "$WORKSPACE"

STOPPED_COUNT=0

# 1. Stop main battlestation
if [ -f /tmp/rick_battlestation.pid ]; then
    BATTLESTATION_PID=$(cat /tmp/rick_battlestation.pid)
    if ps -p $BATTLESTATION_PID > /dev/null 2>&1; then
        echo "🛑 Stopping Battlestation (PID: $BATTLESTATION_PID)..."
        kill $BATTLESTATION_PID
        sleep 2
        
        # Force kill if still running
        if ps -p $BATTLESTATION_PID > /dev/null 2>&1; then
            echo "⚠️  Force killing battlestation..."
            kill -9 $BATTLESTATION_PID
        fi
        STOPPED_COUNT=$((STOPPED_COUNT + 1))
    fi
    rm -f /tmp/rick_battlestation.pid
fi

# 2. Stop WebSocket API
if [ -f /tmp/rick_ws_api.pid ]; then
    WS_API_PID=$(cat /tmp/rick_ws_api.pid)
    if ps -p $WS_API_PID > /dev/null 2>&1; then
        echo "🛑 Stopping WebSocket API (PID: $WS_API_PID)..."
        kill $WS_API_PID
        STOPPED_COUNT=$((STOPPED_COUNT + 1))
    fi
    rm -f /tmp/rick_ws_api.pid
fi

# 3. Stop TMUX Dashboard
if [ -f /tmp/rick_tmux_dashboard.pid ]; then
    TMUX_PID=$(cat /tmp/rick_tmux_dashboard.pid)
    if ps -p $TMUX_PID > /dev/null 2>&1; then
        echo "🛑 Stopping TMUX Dashboard (PID: $TMUX_PID)..."
        kill $TMUX_PID
        STOPPED_COUNT=$((STOPPED_COUNT + 1))
    fi
    rm -f /tmp/rick_tmux_dashboard.pid
fi

# 4. Kill any remaining processes by name
echo "🧹 Cleaning up remaining processes..."
pkill -f "rick_battlestation.py" && STOPPED_COUNT=$((STOPPED_COUNT + 1)) || true
pkill -f "websocket_server.py" && STOPPED_COUNT=$((STOPPED_COUNT + 1)) || true
pkill -f "tmux_server.js" && STOPPED_COUNT=$((STOPPED_COUNT + 1)) || true

# 5. Remove lock files
rm -f /tmp/rick_battlestation*.lock
rm -f /tmp/rick_phoenix*.lock

sleep 1

echo ""
if [ $STOPPED_COUNT -gt 0 ]; then
    echo "✅ Stopped $STOPPED_COUNT process(es)"
else
    echo "ℹ️  No battlestation processes were running"
fi

echo ""
echo "📊 Final status:"
ps aux | grep -E "(rick_battlestation|websocket_server|tmux_server)" | grep -v grep || echo "   All battlestation processes stopped"

echo ""
echo "========================================================================"
echo "✅ RICK BATTLESTATION SHUTDOWN COMPLETE"
echo "========================================================================"
echo ""
echo "📁 Logs preserved in logs/ directory"
echo "💾 Progression state saved in data/progression_state.json"
echo ""
echo "🚀 To restart: bash tools/start_battlestation.sh"
echo ""
