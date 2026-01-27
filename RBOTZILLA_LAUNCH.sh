#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════════════
# 🤖 RBOTZILLA MASTER LAUNCH CONTROL
# ══════════════════════════════════════════════════════════════════════════════
# Single-selection task launcher with:
# - Auto-cleanup of zombie processes
# - Full system verification
# - Live API market data + paper accounts (OANDA forex, prepare for Coinbase crypto)
# - Default ON strategies: Holy Grail, EMA Scalper, Institutional SD, Trap Reversal (FABIO AAA optional)
# - AI Hive scans EVERY TICK for: catalysts, news sentiment, Reddit/social media
# - All stop losses + smart trailing ACTIVE
# ══════════════════════════════════════════════════════════════════════════════

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# ══════════════════════════════════════════════════════════════════════════════
# CORE FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

kill_all_instances() {
    echo -e "${YELLOW}🧹 Killing all existing instances...${NC}"
    
    # Kill Python trading processes
    pkill -9 -f "autonomous_trading" 2>/dev/null || true
    pkill -9 -f "run_headless" 2>/dev/null || true
    pkill -9 -f "unified_scanner" 2>/dev/null || true
    pkill -9 -f "hive_validation" 2>/dev/null || true
    
    # Kill tmux sessions
    tmux kill-session -t rbotzilla 2>/dev/null || true
    tmux kill-session -t hive 2>/dev/null || true
    tmux kill-session -t battlestation 2>/dev/null || true
    
    # Nuclear option: find and kill all Python trading zombies
    ps aux | grep -E "python.*MULTI_BROKER_PHOENIX" | grep -v grep | awk '{print $2}' | xargs -r kill -9 2>/dev/null || true
    
    sleep 2
    echo -e "${GREEN}✅ All instances terminated${NC}"
}

verify_system() {
    echo -e "${BLUE}🔍 Verifying system configuration...${NC}"

    all_good=true
    
    # Check .env
    if [ ! -f ".env" ]; then
        echo -e "${RED}❌ CRITICAL: .env file missing${NC}"
        exit 1
    fi
    
    source .env 2>/dev/null || true

    # Canonical configuration is the single .env file.
    # If an older .env.oanda file exists, do NOT source it (prevents split-brain configs).
    if [ -f ".env.oanda" ]; then
        echo -e "${YELLOW}⚠️  Detected legacy .env.oanda (ignored). Put OANDA_API_TOKEN in .env only.${NC}"
    fi

    # Derive trading intent (prefer TRADING_MODE; keep PAPER_TRADE_MODE for backward compatibility)
    TRADING_MODE_NORMALIZED="$(echo "${TRADING_MODE:-PAPER}" | tr '[:lower:]' '[:upper:]')"
    if [ "$TRADING_MODE_NORMALIZED" = "LIVE" ] || [ "${PAPER_TRADE_MODE}" = "false" ]; then
        IS_LIVE=true
    else
        IS_LIVE=false
    fi
    
    if [ -z "$OANDA_API_TOKEN" ]; then
        if [ "$IS_LIVE" = true ] || [ "${OANDA_REQUIRED}" = "true" ]; then
            echo -e "${RED}❌ OANDA_API_TOKEN not configured (required)${NC}"
            all_good=false
        else
            echo -e "${YELLOW}⚠️  OANDA_API_TOKEN not configured (OANDA trading will be disabled)${NC}"
        fi
    else
        echo -e "${GREEN}✓ OANDA API ready${NC}"
    fi
    
    if [ "$IBKR_ENABLED" = "true" ]; then
        echo -e "${BLUE}ℹ️  IBKR enabled - ensure Gateway/TWS is running on port ${IBKR_PORT}${NC}"
        if [ "$IBKR_PORT" = "4002" ]; then
            echo -e "${GREEN}✓ IBKR Paper mode (port 4002)${NC}"
        else
            echo -e "${YELLOW}⚠️  IBKR port ${IBKR_PORT} - verify paper vs live${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  IBKR disabled in .env${NC}"
    fi
    
    if [ -z "$XAI_API_KEY" ]; then
        echo -e "${YELLOW}⚠️  XAI_API_KEY not configured (Grok AI disabled)${NC}"
    else
        echo -e "${GREEN}✓ XAI (Grok) API ready${NC}"
    fi
    
    if [ -z "$OPENAI_API_KEY" ]; then
        echo -e "${YELLOW}⚠️  OPENAI_API_KEY not configured (OpenAI disabled)${NC}"
    else
        echo -e "${GREEN}✓ OpenAI API ready${NC}"
    fi
    
    # Verify FABIO threshold optimization
    if [ "$FABIO_RSI_THRESHOLD" = "40" ]; then
        echo -e "${GREEN}✓ FABIO RSI threshold optimized (40 = 167 trades)${NC}"
    else
        echo -e "${RED}❌ FABIO_RSI_THRESHOLD should be 40, currently: ${FABIO_RSI_THRESHOLD}${NC}"
        all_good=false
    fi
    
    # Verify stop losses configured
    if [ -n "$FABIO_STOP_MIN_PCT" ] && [ -n "$HOLY_GRAIL_STOP_PCT" ]; then
        echo -e "${GREEN}✓ Stop losses configured for all strategies${NC}"
    else
        echo -e "${RED}❌ Stop loss configurations incomplete${NC}"
        all_good=false
    fi
    
    # Verify AI Hive cost control
    if [ "$HIVE_STRATEGY_FIRST" = "true" ] && [ -n "$AI_HIVE_DAILY_BUDGET_USD" ]; then
        echo -e "${GREEN}✓ AI Hive cost control active (\$${AI_HIVE_DAILY_BUDGET_USD}/day)${NC}"
    else
        echo -e "${YELLOW}⚠️  AI Hive cost control may not be optimal${NC}"
    fi
    
    # Check trading mode
    if [ "$IS_LIVE" = true ]; then
        echo -e "${RED}⚠️  LIVE TRADING MODE ACTIVE - REAL MONEY AT RISK${NC}"
    else
        echo -e "${GREEN}✓ PAPER TRADING MODE (safe for testing)${NC}"
    fi
    
    if [ "$all_good" = false ]; then
        echo -e "${RED}❌ System verification FAILED${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ System verification PASSED${NC}"
    echo ""
}

run_full_audit() {
    echo -e "${CYAN}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}📊 Running comprehensive system audit...${NC}"
    echo -e "${CYAN}════════════════════════════════════════════════════════════════${NC}"
    echo ""
    
    if [ -f "./system_audit.sh" ]; then
        bash ./system_audit.sh
    else
        echo -e "${RED}❌ system_audit.sh not found${NC}"
        exit 1
    fi
    
    echo ""
    read -p "Press Enter to continue to task selection..."
    echo ""
}

# ══════════════════════════════════════════════════════════════════════════════
# LAUNCH MODES
# ══════════════════════════════════════════════════════════════════════════════

launch_canary_mode() {
    echo -e "${MAGENTA}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${MAGENTA}🐤 CANARY MODE: Coinbase Crypto (BTC, ETH) - Nano Lots Only${NC}"
    echo -e "${MAGENTA}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "Configuration:"
    echo "  • Broker: Coinbase Advanced Trade"
    echo "  • Symbols: BTC-USD, ETH-USD"
    echo "  • Position Size: \$5-10 per trade (nano lots)"
    echo "  • Strategies: (Default ON) Holy Grail, EMA Scalper, Institutional SD, Trap Reversal"
    echo "  • AI Hive: Grok + OpenAI + DeepSeek (catalysts, news, social media)"
    echo "  • Stop Loss: ACTIVE (volatility-adaptive)"
    echo "  • Trailing Stops: ENABLED"
    echo "  • Max Daily Loss: \$50"
    echo "  • Max Trades: 10/day"
    echo ""
    
    kill_all_instances
    
    export CANARY_MODE=true
    export HEADLESS_MODE=coinbase-only
    export DEFAULT_STRATEGY=institutional_sd
    export FEED_SYMBOLS=BTC-USD,ETH-USD
    export PAPER_TRADE_MODE=false
    export COINBASE_MAX_DAILY_TRADES=10
    export COINBASE_DAILY_LOSS_LIMIT=50
    
    echo -e "${GREEN}🚀 Launching Canary Mode...${NC}"
    ./tools/py_venv.sh MULTI_BROKER_PHOENIX/tools/run_headless.py --mode coinbase-only
}

launch_oanda_forex() {
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}🌍 OANDA FOREX MODE: Live API Data + Paper Account${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "Configuration:"
    echo "  • Broker: OANDA (Paper Account)"
    echo "  • Symbols: EUR_USD, GBP_USD, USD_JPY, AUD_USD, NZD_USD, USD_CAD, USD_CHF"
    echo "  • Position Size: 1,000 units (micro lots)"
    echo "  • Strategies: ALL DEFAULT ON"
    echo "    - FABIO AAA Full (RSI 40, 167 trades, 64.7% win rate)"
    echo "    - Holy Grail (3% stop)"
    echo "    - EMA Scalper (0.5% stop)"
    echo "    - Institutional SD (1% stop)"
    echo "    - Trap Reversal (0.5x spike stop)"
    echo "  • AI Hive: ACTIVE every tick"
    echo "    - Major catalysts detection"
    echo "    - News sentiment analysis"
    echo "    - Reddit/social media sentiment"
    echo "  • Stop Loss: ALL STRATEGIES ACTIVE"
    echo "  • Trailing Stops: ENABLED"
    echo "  • Max Drawdown: 10%"
    echo "  • Max Daily Loss: \$100"
    echo "  • Max Consecutive Losses: 5"
    echo ""
    
    kill_all_instances
    
    export PAPER_TRADE_MODE=true
    export HEADLESS_MODE=oanda-only
    export DEFAULT_STRATEGY=institutional_sd
    export OANDA_TRAILING_STOP=true
    export USE_HIVE_VALIDATION=true
    export HIVE_STRATEGY_FIRST=true
    export IBKR_ENABLED=false
    
    # Canonical credentials must live in .env only
    
    echo -e "${GREEN}🚀 Launching OANDA Forex Mode...${NC}"
    export PYTHONPATH="/home/ing/RICK/MULTI_BROKER_PHOENIX:/home/ing/RICK/MULTI_BROKER_PHOENIX/MULTI_BROKER_PHOENIX:$PYTHONPATH"
    ./tools/py_venv.sh MULTI_BROKER_PHOENIX/tools/run_headless.py --mode oanda-only
}

launch_ibkr_futures() {
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}📈 IBKR FUTURES MODE: Paper Account Trading${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "Configuration:"
    echo "  • Broker: IBKR Gateway (Paper Account - Port 4002)"
    echo "  • Symbols: ES, NQ, YM, RTY (indices), GC, SI, CL (commodities)"
    echo "  • Position Size: 1 micro contract per trade"
    echo "  • Strategies: ALL DEFAULT ON"
    echo "    - FABIO AAA Full (optimized for futures volatility)"
    echo "    - Holy Grail, EMA Scalper, Institutional SD, Trap Reversal"
    echo "  • AI Hive: ACTIVE every tick"
    echo "  • Stop Loss: ALL STRATEGIES ACTIVE"
    echo "  • Trailing Stops: ENABLED"
    echo "  • Max Positions: 5 concurrent"
    echo "  • Max Daily Loss: \$100"
    echo ""
    echo -e "${YELLOW}⚠️  IMPORTANT: IBKR Gateway/TWS must be running!${NC}"
    echo "     Launch Gateway → Login → Ensure port 4002 is active"
    echo ""
    read -p "Press Enter when Gateway is ready, or Ctrl+C to cancel..."
    echo ""
    
    kill_all_instances
    
    export PAPER_TRADE_MODE=true
    export HEADLESS_MODE=ibkr-only
    export DEFAULT_STRATEGY=institutional_sd
    export IBKR_ENABLED=true
    export IBKR_TRAILING_STOP=true
    export USE_HIVE_VALIDATION=true
    export HIVE_STRATEGY_FIRST=true
    
    # Canonical credentials must live in .env only
    
    echo -e "${GREEN}🚀 Launching IBKR Futures Mode...${NC}"
    export PYTHONPATH="/home/ing/RICK/MULTI_BROKER_PHOENIX:/home/ing/RICK/MULTI_BROKER_PHOENIX/MULTI_BROKER_PHOENIX:$PYTHONPATH"
    ./tools/py_venv.sh MULTI_BROKER_PHOENIX/tools/run_headless.py --mode ibkr-only
}

launch_multi_asset() {
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}🌐 MULTI-ASSET MODE: All Brokers + All Strategies${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "Configuration:"
    echo "  • Brokers: OANDA (paper) + IBKR (paper) + Coinbase (real, nano lots)"
    echo "  • OANDA: EUR_USD, GBP_USD, USD_JPY, AUD_USD, USD_CAD, NZD_USD, USD_CHF"
    echo "  • IBKR: ES, NQ, YM, RTY, GC, SI, HG, CL, NG, 6E, 6J (futures)"
    echo "  • Coinbase: BTC-USD, ETH-USD (crypto, nano lots)"
    echo "  • Total: ~25 instruments across forex, futures, crypto"
    echo "  • Strategies: ALL 5 DEFAULT ON with AI Hive validation"
    echo "  • AI Hive: Full scan every tick"
    echo "  • Stop Loss: ALL ACTIVE"
    echo "  • Max Risk: Combined \$200/day"
    echo ""
    echo -e "${YELLOW}⚠️  IMPORTANT: IBKR Gateway must be running on port 4002${NC}"
    echo ""
    read -p "Press Enter when Gateway is ready, or Ctrl+C to cancel..."
    echo ""
    
    kill_all_instances
    
    export HEADLESS_MODE=multi-asset
    export DEFAULT_STRATEGY=institutional_sd
    export USE_HIVE_VALIDATION=true
    export HIVE_STRATEGY_FIRST=true
    export IBKR_ENABLED=true
    export IBKR_TRAILING_STOP=true
    
    # Canonical credentials must live in .env only
    
    echo -e "${GREEN}🚀 Launching Multi-Asset Mode...${NC}"
    export PYTHONPATH="/home/ing/RICK/MULTI_BROKER_PHOENIX:/home/ing/RICK/MULTI_BROKER_PHOENIX/MULTI_BROKER_PHOENIX:$PYTHONPATH"
    ./tools/py_venv.sh MULTI_BROKER_PHOENIX/tools/run_headless.py --mode multi-asset
}

launch_strategy_test() {
    echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${YELLOW}🧪 STRATEGY TEST MODE: Backtest + Validation${NC}"
    echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    
    export PYTHONPATH="/home/ing/RICK/MULTI_BROKER_PHOENIX:/home/ing/RICK/MULTI_BROKER_PHOENIX/MULTI_BROKER_PHOENIX:$PYTHONPATH"
    ./tools/py_venv.sh MULTI_BROKER_PHOENIX/test_fabio_threshold.py
    
    echo ""
    read -p "Press Enter to return to menu..."
}

launch_hive_only() {
    echo -e "${MAGENTA}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${MAGENTA}🧠 AI HIVE ONLY MODE: Catalyst Detection${NC}"
    echo -e "${MAGENTA}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "Configuration:"
    echo "  • No trading, scan only"
    echo "  • AI Hive scanning for:"
    echo "    - Major market catalysts"
    echo "    - Breaking news sentiment"
    echo "    - Reddit WSB sentiment"
    echo "    - Social media trends"
    echo "  • Outputs: Alerts + recommendations"
    echo ""
    
    kill_all_instances
    
    export HIVE_SCAN_ONLY=true
    export USE_HIVE_VALIDATION=true
    
    echo -e "${GREEN}🚀 Launching AI Hive Scan Mode...${NC}"
    export PYTHONPATH="/home/ing/RICK/MULTI_BROKER_PHOENIX:/home/ing/RICK/MULTI_BROKER_PHOENIX/MULTI_BROKER_PHOENIX:$PYTHONPATH"
    python3 MULTI_BROKER_PHOENIX/hive_real/api_ai_hive.py --scan-mode
}

stop_all_systems() {
    echo -e "${RED}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${RED}🛑 EMERGENCY STOP - Shutting down all systems${NC}"
    echo -e "${RED}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    
    kill_all_instances
    
    echo -e "${GREEN}✅ All systems stopped${NC}"
    echo ""
    exit 0
}

# ══════════════════════════════════════════════════════════════════════════════
# MAIN MENU
# ══════════════════════════════════════════════════════════════════════════════

show_menu() {
    clear
    echo -e "${CYAN}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}🤖 RBOTZILLA MASTER LAUNCH CONTROL${NC}"
    echo -e "${CYAN}════════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${GREEN}System Status:${NC}"
    echo "  • FABIO RSI Threshold: 40 (167 trades @ 64.7% win rate)"
    echo "  • All Stop Losses: ACTIVE"
    echo "  • AI Hive: READY (Grok \$0.001/call, OpenAI, DeepSeek)"
    echo "  • Trailing Stops: ENABLED"
    echo "  • Paper Trading: SAFE"
    echo ""
    echo -e "${YELLOW}Select Launch Mode:${NC}"
    echo ""
    echo "  1) 🐤 Canary Mode (Coinbase Crypto - Real Money, Nano Lots)"
    echo "  2) 🌍 OANDA Forex (Paper Account - Safe Testing)"
    echo "  3) 📈 IBKR Futures (Paper Account - ES, NQ, GC, CL)"
    echo "  4) 🌐 Multi-Asset (All 3 Brokers: OANDA + IBKR + Coinbase)"
    echo "  5) 🧪 Strategy Test (Backtest Validation)"
    echo "  6) 🧠 AI Hive Only (Catalyst Detection, No Trading)"
    echo "  7) 📊 Full System Audit (Health Check)"
    echo "  8) 🛑 EMERGENCY STOP (Kill All Systems)"
    echo "  9) ❌ Exit"
    echo "  10) 📣 Open Narration Terminal (live human-friendly summary)"
    echo ""
    echo -e "${CYAN}────────────────────────────────────────────────────────────────${NC}"
    echo -n "Enter selection [1-9]: "
}

# ══════════════════════════════════════════════════════════════════════════════
# MAIN LOOP
# ══════════════════════════════════════════════════════════════════════════════

# Run initial verification
verify_system

while true; do
    show_menu
    read -r choice
    echo ""
    
    case $choice in
        1)
            launch_canary_mode
            ;;
        2)
            launch_oanda_forex
            ;;
        3)
            launch_ibkr_futures
            ;;
        4)
            launch_multi_asset
            ;;
        5)
            launch_strategy_test
            ;;
        6)
            launch_hive_only
            ;;
        7)
            run_full_audit
            ;;
        8)
            stop_all_systems
            ;;
        9)
            echo -e "${GREEN}Exiting RBOTZILLA Master Control${NC}"
            exit 0
            ;;
        10)
            # Start narration terminal in tmux if available, else run in background
            if command -v tmux &>/dev/null; then
                tmux new-session -d -s narrator 'bash tools/start_narration_tty.sh'
                echo -e "${GREEN}✅ Narration terminal started in tmux session 'narrator'${NC}"
            else
                nohup bash tools/start_narration_tty.sh >/tmp/narration_tty.log 2>&1 &
                echo -e "${GREEN}✅ Narration terminal started in background (log: /tmp/narration_tty.log)${NC}"
            fi
            ;;
        *)
            echo -e "${RED}Invalid selection. Please try again.${NC}"
            sleep 2
            ;;
    esac
    
    # After task completion, pause before returning to menu
    echo ""
    echo -e "${YELLOW}Task completed or stopped.${NC}"
    read -p "Press Enter to return to main menu..."
done
