#!/bin/bash
# RICK BATTLESTATION - Master Launcher
# Starts complete unified trading system:
# - Python WebSocket API server (port 8888)
# - Node.js TMUX dashboard server (port 4567, ws 8887)
# - RICK Battlestation trading engine
# - Voice narrator (browser-side)

set -e  # Exit on error

WORKSPACE="/home/ing/RICK/MULTI_BROKER_PHOENIX"
cd "$WORKSPACE"

echo "========================================================================"
echo "🚀 RICK BATTLESTATION - MASTER LAUNCHER"
echo "========================================================================"
echo "PIN: 841921 | Charter Compliant | All Systems Armed"
echo ""

# Check required components
echo "🔍 Pre-flight checks..."

get_env_value() {
    local key="$1"
    local default_value="${2:-}"
    local line
    local value

    if [ ! -f ".env" ]; then
        echo "$default_value"
        return 0
    fi

    # Use last occurrence if duplicates exist (prefer file order to match dotenv behavior)
    line=$(grep -E "^[[:space:]]*${key}=" .env 2>/dev/null | tail -n 1 || true)
    if [ -z "$line" ]; then
        echo "$default_value"
        return 0
    fi

    value="${line#*=}"
    value="${value%$'\r'}"
    # Strip surrounding quotes if present
    value="${value%\"}"
    value="${value#\"}"
    value="${value%\'}"
    value="${value#\'}"
    echo "$value"
}

is_truthy() {
    case "$(echo "${1:-}" | tr '[:upper:]' '[:lower:]')" in
        1|true|yes|y|on) return 0 ;;
        *) return 1 ;;
    esac
}

TRADING_MODE="$(get_env_value TRADING_MODE PAPER)"
ALLOW_LIVE_REAL="$(get_env_value ALLOW_LIVE_REAL false)"
HEADLESS_MODE="$(get_env_value HEADLESS_MODE multi-asset)"

COINBASE_API_KEY="$(get_env_value COINBASE_API_KEY "")"
COINBASE_API_SECRET="$(get_env_value COINBASE_API_SECRET "")"
COINBASE_API_SECRET_FILE="$(get_env_value COINBASE_API_SECRET_FILE "")"

COINBASE_HAS_KEY=false
if [[ "$COINBASE_API_KEY" == organizations/* ]]; then
    COINBASE_HAS_KEY=true
fi

COINBASE_HAS_SECRET=false
if [ -n "$COINBASE_API_SECRET" ]; then
    COINBASE_HAS_SECRET=true
elif [ -n "$COINBASE_API_SECRET_FILE" ]; then
    if [ -f "$COINBASE_API_SECRET_FILE" ]; then
        COINBASE_HAS_SECRET=true
    elif [ -f "$WORKSPACE/$COINBASE_API_SECRET_FILE" ]; then
        COINBASE_API_SECRET_FILE="$WORKSPACE/$COINBASE_API_SECRET_FILE"
        COINBASE_HAS_SECRET=true
    fi
fi

COINBASE_AUTH_CONFIGURED=false
if [ "$COINBASE_HAS_KEY" = true ] && [ "$COINBASE_HAS_SECRET" = true ]; then
    COINBASE_AUTH_CONFIGURED=true
fi

# 1. Check Python environment
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found"
    exit 1
fi
echo "✅ Python 3: $(python3 --version)"

# 1.5. Configuration sanity (dotenv preflight)
if [ -f "tools/env_preflight.py" ]; then
    echo "✅ Env preflight: running..."
    if ! python3 tools/env_preflight.py --quiet; then
        echo "❌ Env preflight failed - fix .env and retry"
        exit 1
    fi
else
    echo "⚠️  Env preflight not found (tools/env_preflight.py) - continuing"
fi

# 2. Check Node.js environment (for dashboard)
if ! command -v node &> /dev/null; then
    echo "⚠️  Node.js not found - dashboard will not be available"
    NODE_AVAILABLE=false
else
    echo "✅ Node.js: $(node --version)"
    NODE_AVAILABLE=true
fi

# 3. Check Coinbase API credentials (required ONLY for LIVE real-money mode)
if [ "${TRADING_MODE}" = "LIVE" ]; then
    if ! is_truthy "$ALLOW_LIVE_REAL"; then
        echo "❌ LIVE mode blocked: ALLOW_LIVE_REAL must be true in .env"
        exit 1
    fi

    if [ "$COINBASE_AUTH_CONFIGURED" != true ]; then
        echo "❌ LIVE mode blocked: Coinbase auth not configured in .env"
        echo "   Required: COINBASE_API_KEY=organizations/... and COINBASE_API_SECRET (or COINBASE_API_SECRET_FILE)"
        exit 1
    fi
    echo "✅ Coinbase LIVE credentials configured"
else
    if [ "$COINBASE_AUTH_CONFIGURED" = true ]; then
        echo "✅ Coinbase credentials present (PAPER mode will not place real orders)"
    else
        echo "⚠️  Coinbase credentials not configured (OK in TRADING_MODE=${TRADING_MODE})"
    fi
fi

# 4. Check IBKR TWS (optional)
if ! nc -z localhost 4002 2>/dev/null; then
    echo "⚠️  IBKR TWS not detected on port 4002 (optional)"
    IBKR_AVAILABLE=false
else
    echo "✅ IBKR TWS detected on port 4002"
    IBKR_AVAILABLE=true
fi

# 5. Check required directories
mkdir -p logs data hive_dashboard/logs
echo "✅ Directories ready"

echo ""
echo "========================================================================"
echo "⚠️  REAL MONEY TRADING WARNING"
echo "========================================================================"
echo "Coinbase: LIVE account with real money (nano-lots \$5-10)"
echo "IBKR: Paper account with \$1M fake money"
echo ""
echo "Safety limits:"
echo "- Max trade size: \$10"
echo "- Daily loss limit: \$50"
echo "- Max trades/day: $(get_env_value COINBASE_MAX_TRADES_PER_DAY 999999)"
echo "- Stop on 5 consecutive losses"
echo "- Trailing stops: 2% initial, 1.5% activation, 1% trail"
echo ""
echo "Systems active:"
echo "- Crypto Entry Gates: 90% AI hive consensus"
echo "- Guardian Gates: 35% max margin, 3 max positions"
echo "- 5-Phase Progression: Auto-graduate on performance"
echo "- Adaptive AI Learning: ML parameter optimization"
echo "- Voice Narration: Trade announcements"
echo "- Real-time Dashboard: WebSocket streaming"
echo ""

# Check for auto-confirm flag
if [ "$1" == "--auto" ] || [ "$1" == "-y" ] || [ "$AUTO_LAUNCH" == "true" ]; then
    echo "🚀 Auto-launching (non-interactive mode)..."
    CONFIRM="LAUNCH"
else
    read -p "Type 'LAUNCH' to start battlestation: " CONFIRM
fi

if [ "$CONFIRM" != "LAUNCH" ]; then
    echo "❌ Launch aborted"
    exit 1
fi

echo ""
echo "🚀 LAUNCHING RICK BATTLESTATION..."
echo ""

# Stop any existing instances
echo "🛑 Stopping existing instances..."
bash tools/stop_trading_engine.sh --quiet || true
pkill -f "tmux_server.js" || true
pkill -f "websocket_server.py" || true
pkill -f "rick_battlestation.py" || true
sleep 2

# Start components in sequence
echo ""
echo "1️⃣ Starting Python WebSocket API (port 8888)..."
export PYTHONPATH="$WORKSPACE:$WORKSPACE/MULTI_BROKER_PHOENIX:$WORKSPACE/rick_hive"
cd "$WORKSPACE/MULTI_BROKER_PHOENIX/multi_broker_phoenix/api"
nohup python3 websocket_server.py > "$WORKSPACE/logs/websocket_api.log" 2>&1 &
WS_API_PID=$!
echo "$WS_API_PID" > /tmp/rick_ws_api.pid
echo "✅ WebSocket API started (PID: $WS_API_PID)"
sleep 2

# Check if WebSocket API is running
if ! ps -p $WS_API_PID > /dev/null 2>&1; then
    echo "❌ WebSocket API failed to start"
    cat "$WORKSPACE/logs/websocket_api.log"
    exit 1
fi

echo ""
if [ "$NODE_AVAILABLE" = true ]; then
    echo "2️⃣ Starting Node.js TMUX Dashboard (port 4567, ws 8887)..."
    cd "$WORKSPACE/hive_dashboard"
    
    # Install dependencies if needed
    if [ ! -d "node_modules" ]; then
        echo "📦 Installing Node.js dependencies..."
        npm install express ws
    fi
    
    nohup node tmux_server.js > "$WORKSPACE/logs/tmux_dashboard.log" 2>&1 &
    TMUX_PID=$!
    echo "$TMUX_PID" > /tmp/rick_tmux_dashboard.pid
    echo "✅ TMUX Dashboard started (PID: $TMUX_PID)"
    sleep 2
    
    # Check if dashboard is running
    if ! ps -p $TMUX_PID > /dev/null 2>&1; then
        echo "⚠️  TMUX Dashboard failed to start (optional)"
        cat "$WORKSPACE/logs/tmux_dashboard.log"
    fi
else
    echo "2️⃣ Skipping TMUX Dashboard (Node.js not available)"
fi

echo ""
cd "$WORKSPACE"
export PYTHONPATH="$WORKSPACE:$WORKSPACE/MULTI_BROKER_PHOENIX:$WORKSPACE/rick_hive"

ENGINE_MODE="headless"
if [ "${TRADING_MODE}" = "LIVE" ]; then
    ENGINE_MODE="battlestation"
fi

if [ "$ENGINE_MODE" = "battlestation" ]; then
    echo "3️⃣ Starting RICK Battlestation Trading Engine (LIVE crypto command center)..."
    nohup python3 -u MULTI_BROKER_PHOENIX/multi_broker_phoenix/engines/rick_battlestation.py > logs/rick_battlestation.log 2>&1 &
    BATTLESTATION_PID=$!
    echo "$BATTLESTATION_PID" > /tmp/rick_battlestation.pid
    echo "✅ Battlestation started (PID: $BATTLESTATION_PID)"
    sleep 3

    # Check if battlestation is running
    if ! ps -p $BATTLESTATION_PID > /dev/null 2>&1; then
        echo "❌ Battlestation failed to start"
        echo ""
        echo "Last 30 lines of log:"
        tail -30 logs/rick_battlestation.log
        exit 1
    fi
else
    echo "3️⃣ Starting RBOTZILLA Headless Trading Engine (TRADING_MODE=${TRADING_MODE})..."
    echo "   Mode: ${HEADLESS_MODE}"
    nohup python3 -u MULTI_BROKER_PHOENIX/tools/run_headless.py --mode "${HEADLESS_MODE}" > logs/rbotzilla_headless.log 2>&1 &
    HEADLESS_PID=$!
    echo "$HEADLESS_PID" > /tmp/rick_headless.pid
    echo "✅ Headless engine started (PID: $HEADLESS_PID)"
    sleep 3

    if ! ps -p $HEADLESS_PID > /dev/null 2>&1; then
        echo "❌ Headless engine failed to start"
        echo ""
        echo "Last 40 lines of log:"
        tail -40 logs/rbotzilla_headless.log
        exit 1
    fi
fi

echo ""
echo "========================================================================"
echo "✅ RICK BATTLESTATION FULLY OPERATIONAL"
echo "========================================================================"
echo ""
echo "🎯 Active PIDs:"
echo "   - WebSocket API: $WS_API_PID (port 8888)"
if [ "$NODE_AVAILABLE" = true ] && ps -p $TMUX_PID > /dev/null 2>&1; then
    echo "   - TMUX Dashboard: $TMUX_PID (port 4567)"
fi
if [ "$ENGINE_MODE" = "battlestation" ]; then
    echo "   - Battlestation: $BATTLESTATION_PID"
else
    echo "   - Headless engine: $HEADLESS_PID"
fi
echo ""
echo "📡 Access Points:"
echo "   - WebSocket: ws://localhost:8888"
if [ "$NODE_AVAILABLE" = true ]; then
    echo "   - Dashboard: http://localhost:4567"
    echo "   - TMUX Stream: ws://localhost:8887"
fi
echo ""
echo "📊 Monitoring:"
echo "   - tail -f logs/rick_battlestation.log"
echo "   - tail -f logs/websocket_api.log"
if [ "$NODE_AVAILABLE" = true ]; then
    echo "   - tail -f logs/tmux_dashboard.log"
fi
echo ""
echo "🛑 Shutdown:"
echo "   - bash tools/stop_battlestation.sh"
echo ""
echo "🎤 Voice Narrator:"
echo "   - Open browser to http://localhost:4567"
echo "   - Voice will announce trades automatically"
echo ""
echo "========================================================================"
echo "🚀 BATTLESTATION IS LIVE - GOOD HUNTING!"
echo "========================================================================"
echo ""

# Tail logs in foreground (Ctrl+C to stop monitoring)
if [ "$ENGINE_MODE" = "battlestation" ]; then
    echo "📊 Now tailing battlestation log (Ctrl+C to exit monitor)..."
else
    echo "📊 Now tailing headless engine log (Ctrl+C to exit monitor)..."
fi
echo ""
sleep 2
if [ "$ENGINE_MODE" = "battlestation" ]; then
    tail -f logs/rick_battlestation.log
else
    tail -f logs/rbotzilla_headless.log
fi
