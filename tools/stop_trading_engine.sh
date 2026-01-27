#!/bin/bash
# Stop Trading Engine - Kills all instances and cleans up for fresh restart

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

QUIET=false
if [ "$1" == "--quiet" ]; then
    QUIET=true
fi

if [ "$QUIET" == "false" ]; then
    echo "=============================================="
    echo "🛑 STOPPING TRADING ENGINE"
    echo "=============================================="
    echo ""
fi

# Kill by PID file
if [ -f /tmp/rick_phoenix_trading.pid ]; then
    PID=$(cat /tmp/rick_phoenix_trading.pid)
    if ps -p "$PID" > /dev/null 2>&1; then
        [ "$QUIET" == "false" ] && echo "🔪 Killing main process (PID: $PID)..."
        kill "$PID" 2>/dev/null || kill -9 "$PID" 2>/dev/null
        sleep 1
    fi
    rm -f /tmp/rick_phoenix_trading.pid
fi

# Kill any Python trading processes
PROCS=$(ps aux | grep -E "(run_phase1_live|run_dual_broker_live)" | grep -v grep | awk '{print $2}')
if [ -n "$PROCS" ]; then
    [ "$QUIET" == "false" ] && echo "🔪 Killing remaining trading processes..."
    echo "$PROCS" | xargs kill -9 2>/dev/null || true
fi

# Kill any stuck Python processes with MULTI_BROKER_PHOENIX in path
STUCK=$(ps aux | grep python3 | grep MULTI_BROKER_PHOENIX | grep -v grep | awk '{print $2}')
if [ -n "$STUCK" ]; then
    [ "$QUIET" == "false" ] && echo "🔪 Cleaning up stuck processes..."
    echo "$STUCK" | xargs kill -9 2>/dev/null || true
fi

# Clear progression state for fresh restart (optional - commented out to preserve progress)
# rm -f "$PROJECT_ROOT/data/progression_state.json"

# Clear any lock files
rm -f /tmp/rick_phoenix_*.lock 2>/dev/null || true

if [ "$QUIET" == "false" ]; then
    echo ""
    echo "✅ All trading processes stopped"
    echo "✅ System ready for fresh restart"
    echo ""
fi
