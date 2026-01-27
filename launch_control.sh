#!/usr/bin/env bash
# RBOTZILLA MASTER CONTROL - Single Task Selection & Auto-Cleanup
# Kills old instances, starts fresh, ensures green for live paper trading

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "════════════════════════════════════════════════════════════════"
echo "🤖 RBOTZILLA MASTER CONTROL - Task Launcher"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Function to kill all running instances
kill_all_instances() {
    echo -e "${YELLOW}🧹 Cleaning up old instances...${NC}"
    
    # Kill any Python trading processes
    pkill -f "autonomous_trading" 2>/dev/null || true
    pkill -f "run_headless" 2>/dev/null || true
    pkill -f "rick_battlestation" 2>/dev/null || true
    pkill -f "unified_scanner" 2>/dev/null || true
    
    # Kill any stuck tmux sessions
    tmux kill-session -t rbotzilla 2>/dev/null || true
    tmux kill-session -t hive 2>/dev/null || true
    
    # Kill any zombie processes
    ps aux | grep -E "(python.*trading|python.*hive)" | grep -v grep | awk '{print $2}' | xargs -r kill -9 2>/dev/null || true
    
    sleep 2
    echo -e "${GREEN}✅ Cleanup complete${NC}"
    echo ""
}

# Function to verify system readiness
verify_system() {
    echo -e "${BLUE}🔍 Verifying system readiness...${NC}"
    
    # Check .env file exists
    if [ ! -f ".env" ]; then
        echo -e "${RED}❌ .env file not found${NC}"
        exit 1
    fi
    
    # Check critical API keys
    source .env 2>/dev/null || true
    
    if [ -z "$OANDA_API_TOKEN" ]; then
        echo -e "${RED}❌ OANDA_API_TOKEN not set${NC}"
        exit 1
    fi
    
    if [ -z "$FABIO_RSI_THRESHOLD" ]; then
        echo -e "${YELLOW}⚠️  FABIO_RSI_THRESHOLD not set, using default 40${NC}"
    else
        echo -e "${GREEN}✅ FABIO_RSI_THRESHOLD=${FABIO_RSI_THRESHOLD}${NC}"
    fi
    
    # Check Python availability
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}❌ Python3 not found${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ System ready${NC}"
    echo ""
}

# Task menu
show_menu() {
    echo "Select Trading Mode:"
    echo ""
    echo "  1) 🎯 CANARY MODE - Ultra-safe testing (BTC-USD, ETH-USD only, $10 max)"
    echo "  2) 📈 OANDA FOREX - Live paper trading (EUR_USD, GBP_USD, etc.)"
    echo "  3) 🔥 MULTI-ASSET - OANDA + Crypto (Full universe)"
    echo "  4) 🧪 STRATEGY TEST - Backtest strategies on historical data"
    echo "  5) 🧠 HIVE ONLY - AI validation service (no trading)"
    echo "  6) 📊 AUDIT - Full system health check"
    echo "  7) 🛑 STOP ALL - Kill all running instances"
    echo ""
    echo -n "Enter selection (1-7): "
}

# Task functions
launch_canary() {
    echo -e "${GREEN}🐤 Launching CANARY MODE...${NC}"
    kill_all_instances
    
    export CANARY_MODE=true
    export HEADLESS_MODE=coinbase-only
    export FEED_SYMBOLS=BTC-USD,ETH-USD
    export DEFAULT_STRATEGY=holy_grail
    export CANARY_MAX_RISK_USD=10.0
    export ENABLE_AI_HIVE=true
    
    ./tools/py_venv.sh MULTI_BROKER_PHOENIX/tools/run_headless.py --mode coinbase-only
}

launch_oanda() {
    echo -e "${GREEN}📈 Launching OANDA FOREX Paper Trading...${NC}"
    kill_all_instances
    
    export CANARY_MODE=false
    export HEADLESS_MODE=oanda-only
    export FEED_SYMBOLS=EUR_USD,GBP_USD,USD_JPY,AUD_USD,USD_CAD,NZD_USD
    export DEFAULT_STRATEGY=holy_grail
    export ENABLE_AI_HIVE=true
    
    ./tools/py_venv.sh MULTI_BROKER_PHOENIX/tools/run_headless.py --mode oanda-only
}

launch_multi_asset() {
    echo -e "${GREEN}🔥 Launching MULTI-ASSET Trading...${NC}"
    kill_all_instances
    
    export CANARY_MODE=false
    export HEADLESS_MODE=auto
    export FEED_SYMBOLS=EUR_USD,GBP_USD,USD_JPY,BTC-USD,ETH-USD
    export DEFAULT_STRATEGY=holy_grail
    export ENABLE_AI_HIVE=true
    
    ./tools/py_venv.sh MULTI_BROKER_PHOENIX/tools/run_headless.py --mode auto
}

launch_strategy_test() {
    echo -e "${GREEN}🧪 Launching STRATEGY TEST...${NC}"
    kill_all_instances
    
    ./tools/py_venv.sh generate_test_data.py
    ./tools/py_venv.sh test_fabio_threshold.py
}

launch_hive_only() {
    echo -e "${GREEN}🧠 Launching HIVE VALIDATION SERVICE...${NC}"
    kill_all_instances
    
    echo "Hive service standalone not yet implemented"
    echo "Use modes 1-3 which include AI Hive validation"
}

run_audit() {
    echo -e "${GREEN}📊 Running FULL SYSTEM AUDIT...${NC}"
    ./system_audit.sh
}

# Main execution
verify_system

if [ $# -eq 0 ]; then
    # Interactive mode
    show_menu
    read selection
else
    # Command line mode
    selection=$1
fi

case $selection in
    1)
        launch_canary
        ;;
    2)
        launch_oanda
        ;;
    3)
        launch_multi_asset
        ;;
    4)
        launch_strategy_test
        ;;
    5)
        launch_hive_only
        ;;
    6)
        run_audit
        ;;
    7)
        kill_all_instances
        echo -e "${GREEN}✅ All instances stopped${NC}"
        ;;
    *)
        echo -e "${RED}Invalid selection${NC}"
        exit 1
        ;;
esac
