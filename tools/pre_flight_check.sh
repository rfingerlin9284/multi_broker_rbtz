#!/bin/bash
# RICK BATTLESTATION - Pre-Flight Check
# Verify all components are ready before launch

echo "========================================================================"
echo "🔍 RICK BATTLESTATION - PRE-FLIGHT CHECK"
echo "========================================================================"
echo ""

WORKSPACE="/home/ing/RICK/MULTI_BROKER_PHOENIX"
cd "$WORKSPACE"

PASS=0
FAIL=0
WARN=0

# Function to check item
check_item() {
    local desc="$1"
    local test_cmd="$2"
    local required="$3"  # true/false
    
    if eval "$test_cmd" > /dev/null 2>&1; then
        echo "✅ $desc"
        PASS=$((PASS + 1))
        return 0
    else
        if [ "$required" = "true" ]; then
            echo "❌ $desc"
            FAIL=$((FAIL + 1))
        else
            echo "⚠️  $desc (optional)"
            WARN=$((WARN + 1))
        fi
        return 1
    fi
}

echo "📦 Dependencies:"
check_item "Python 3" "command -v python3" true
check_item "Node.js" "command -v node" false
check_item "websockets package" "python3 -c 'import websockets'" true
check_item "asyncio support" "python3 -c 'import asyncio'" true

echo ""
echo "📁 Core Files:"
check_item "Battlestation engine" "test -f MULTI_BROKER_PHOENIX/multi_broker_phoenix/engines/rick_battlestation.py" true
check_item "WebSocket API" "test -f MULTI_BROKER_PHOENIX/multi_broker_phoenix/api/websocket_server.py" true
check_item "Coinbase connector" "test -f MULTI_BROKER_PHOENIX/multi_broker_phoenix/brokers/coinbase_safe_connector.py" true
check_item "Progression manager" "test -f MULTI_BROKER_PHOENIX/multi_broker_phoenix/foundation/progression_manager.py" true

echo ""
echo "🧠 AI Components:"
check_item "Crypto entry gates" "test -f rick_hive/crypto_entry_gate_system.py" true
check_item "Guardian gates" "test -f rick_hive/guardian_gates.py" true
check_item "Adaptive AI" "test -f rick_hive/adaptive_rick.py" true
check_item "Hive mind" "test -f rick_hive/rick_hive_mind.py" true

echo ""
echo "🎨 Dashboard:"
check_item "Battlestation HTML" "test -f hive_dashboard/battlestation.html" true
check_item "Voice narrator JS" "test -f hive_dashboard/rick_voice_narrator.js" true
check_item "TMUX server (optional)" "test -f hive_dashboard/tmux_server.js" false

echo ""
echo "🚀 Launchers:"
check_item "Start script" "test -x tools/start_battlestation.sh" true
check_item "Stop script" "test -x tools/stop_battlestation.sh" true

echo ""
echo "🔐 Configuration:"
check_item ".env file exists" "test -f .env" true
check_item "Coinbase API key" "grep -q 'COINBASE_API_KEY=organizations' .env" true
check_item "Coinbase API secret" "grep -q 'BEGIN EC PRIVATE KEY' .env" true
check_item "Progression enabled" "grep -q 'PROGRESSION_ENABLED=true' .env" false

echo ""
echo "📂 Directories:"
check_item "Logs directory" "test -d logs" true
check_item "Data directory" "test -d data" true

echo ""
echo "🌐 Network:"
check_item "Port 8888 available" "! lsof -i :8888 > /dev/null 2>&1" true
check_item "Port 4567 available" "! lsof -i :4567 > /dev/null 2>&1" false
check_item "IBKR TWS on 4002 (optional)" "nc -z localhost 4002" false

echo ""
echo "========================================================================"
echo "📊 RESULTS"
echo "========================================================================"
echo "✅ Passed: $PASS"
echo "⚠️  Warnings: $WARN"
echo "❌ Failed: $FAIL"
echo ""

if [ $FAIL -eq 0 ]; then
    echo "🎯 STATUS: READY TO LAUNCH"
    echo ""
    echo "To start battlestation:"
    echo "  bash tools/start_battlestation.sh"
    echo ""
    echo "Or use VSCode task:"
    echo "  Ctrl+Shift+P → Tasks: Run Task → 🚀 RICK BATTLESTATION: Launch"
    echo ""
    exit 0
else
    echo "⚠️  STATUS: FIX ERRORS BEFORE LAUNCH"
    echo ""
    echo "Fix the ❌ items above, then run this check again:"
    echo "  bash tools/pre_flight_check.sh"
    echo ""
    exit 1
fi
