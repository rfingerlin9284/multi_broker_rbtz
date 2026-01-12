#!/bin/bash
################################################################################
# 🚀 RICK MASTER LAUNCHER - ONE SCRIPT TO RULE THEM ALL
################################################################################
# This is your ONE-STOP launcher for all RICK trading systems
#
# What this script does:
# 1. Shows you a clear menu of what you can run
# 2. Starts the web UI (Flask server) so browser pages work
# 3. Launches browser automation for AI agents
# 4. Starts autonomous trading engine
# 5. Provides task info menu to explain each script
#
# USAGE:
#   ./RICK_START.sh                    # Interactive menu
#   ./RICK_START.sh full              # Start everything (recommended)
#   ./RICK_START.sh web               # Just web UI
#   ./RICK_START.sh engine            # Just trading engine
#   ./RICK_START.sh explain           # Explain all tasks
################################################################################

set -e  # Exit on error

# Colors for pretty output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Project root
PROJECT_ROOT="/home/ing/RICK/MULTI_BROKER_PHOENIX"
cd "$PROJECT_ROOT"

# Activate virtual environment
source .venv/bin/activate

################################################################################
# Helper Functions
################################################################################

print_header() {
    echo -e "${CYAN}"
    echo "════════════════════════════════════════════════════════════════════════"
    echo "  $1"
    echo "════════════════════════════════════════════════════════════════════════"
    echo -e "${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

start_web_ui() {
    print_header "Starting Web UI Server"
    
    if check_port 8080; then
        print_warning "Port 8080 already in use (Web UI may be running)"
    else
        print_info "Starting Flask server on http://127.0.0.1:8080"
        cd "$PROJECT_ROOT/hive_real"
        python3 hive_web_interface.py &
        WEB_PID=$!
        echo $WEB_PID > /tmp/rick_web_ui.pid
        sleep 3
        
        if check_port 8080; then
            print_success "Web UI started successfully"
            print_info "Open browser to: http://127.0.0.1:8080"
        else
            print_error "Web UI failed to start"
            return 1
        fi
    fi
}

start_browser_automation() {
    print_header "Starting Browser Automation"
    
    print_info "Launching Chrome with AI debugging..."
    cd "$PROJECT_ROOT/hive_real"
    # Non-interactive friendly: avoid prompts/EOFError when launched from scripts.
    python3 launch_browser_ai.py --yes &
    BROWSER_PID=$!
    echo $BROWSER_PID > /tmp/rick_browser.pid
    sleep 5
    
    print_success "Browser automation started"
    print_info "Chrome should open with ChatGPT.com"
}

start_autonomous_engine() {
    print_header "Starting Autonomous Trading Engine"
    
    print_warning "This will start PAPER TRADING mode (no real money)"
    print_info "Press Ctrl+C to stop the engine"
    sleep 2
    
    cd "$PROJECT_ROOT/hive_real"
    python3 autonomous_trading_engine.py --mode paper --interval 60
}

stop_all() {
    print_header "Stopping All RICK Services"
    
    # Stop web UI
    if [ -f /tmp/rick_web_ui.pid ]; then
        PID=$(cat /tmp/rick_web_ui.pid)
        if kill -0 $PID 2>/dev/null; then
            kill $PID
            rm /tmp/rick_web_ui.pid
            print_success "Stopped Web UI"
        fi
    fi
    
    # Stop browser
    if [ -f /tmp/rick_browser.pid ]; then
        PID=$(cat /tmp/rick_browser.pid)
        if kill -0 $PID 2>/dev/null; then
            kill $PID
            rm /tmp/rick_browser.pid
            print_success "Stopped Browser"
        fi
    fi
    
    # Kill any remaining processes
    pkill -f "hive_web_interface.py" 2>/dev/null || true
    pkill -f "launch_browser_ai.py" 2>/dev/null || true
    
    print_success "All services stopped"
}

explain_tasks() {
    print_header "📋 RICK TASK EXPLANATIONS"
    
    echo ""
    echo -e "${GREEN}═══ MAIN SCRIPTS (Start Here) ═══${NC}"
    echo ""
    echo -e "${CYAN}./RICK_START.sh full${NC}"
    echo "  → Starts EVERYTHING: Web UI + Browser + Trading Engine"
    echo "  → This is what you want 90% of the time"
    echo "  → Opens http://127.0.0.1:8080 for monitoring"
    echo ""
    
    echo -e "${CYAN}./RICK_START.sh web${NC}"
    echo "  → Just starts the Flask web server"
    echo "  → Needed so browser pages aren't blank"
    echo "  → Opens port 8080 for web UI"
    echo ""
    
    echo -e "${CYAN}./RICK_START.sh engine${NC}"
    echo "  → Just starts the autonomous trading engine"
    echo "  → Paper mode by default (no real money)"
    echo "  → Uses AI agents to trade automatically"
    echo ""
    
    echo ""
    echo -e "${YELLOW}═══ SPECIALIZED SCRIPTS (Advanced) ═══${NC}"
    echo ""
    
    echo -e "${PURPLE}hive_real/autonomous_trading_engine.py${NC}"
    echo "  → Full autonomous AI trading with:"
    echo "    • 10x leverage on win streaks"
    echo "    • 100% compounding"
    echo "    • AI universe filtering"
    echo "    • Session-aware risk (London/NY/Overlap)"
    echo ""
    
    echo -e "${PURPLE}hive_real/hive_web_interface.py${NC}"
    echo "  → Flask server for web dashboard"
    echo "  → Provides UI at http://127.0.0.1:8080"
    echo "  → Shows trades, P&L, AI decisions"
    echo ""
    
    echo -e "${PURPLE}hive_real/launch_browser_ai.py${NC}"
    echo "  → Opens Chrome with ChatGPT for AI agents"
    echo "  → Required for browser-based AI queries"
    echo "  → Creates debugging bridge WSL ↔ Windows"
    echo ""
    
    echo -e "${PURPLE}tools/start_battlestation.sh${NC}"
    echo "  → Alternative launcher (older)"
    echo "  → Use RICK_START.sh instead (recommended)"
    echo ""
    
    echo ""
    echo -e "${RED}═══ CLEANUP SCRIPTS ═══${NC}"
    echo ""
    
    echo -e "${CYAN}./RICK_START.sh stop${NC}"
    echo "  → Stops all running RICK services"
    echo "  → Kills web server, browser, engines"
    echo "  → Clean shutdown"
    echo ""
    
    echo ""
    echo -e "${GREEN}═══ QUICK START ═══${NC}"
    echo -e "${YELLOW}First time? Run:${NC}"
    echo -e "  ${CYAN}./RICK_START.sh full${NC}"
    echo ""
    echo -e "${YELLOW}Then open browser to:${NC}"
    echo -e "  ${CYAN}http://127.0.0.1:8080${NC}"
    echo ""
    
    read -p "Press Enter to continue..."
}

show_menu() {
    clear
    print_header "🚀 RICK MASTER LAUNCHER"
    
    echo ""
    echo -e "${GREEN}What would you like to do?${NC}"
    echo ""
    echo "  1) Start EVERYTHING (Web UI + Browser + Trading Engine)"
    echo "  2) Start Web UI only (fixes blank browser page)"
    echo "  3) Start Trading Engine only"
    echo "  4) Start Browser Automation only"
    echo "  5) Stop all services"
    echo "  6) Explain what each task does"
    echo "  7) Exit"
    echo ""
    read -p "Enter choice [1-7]: " choice
    
    case $choice in
        1)
            start_full
            ;;
        2)
            start_web_ui
            print_info "Web UI running. Press Ctrl+C to stop."
            wait
            ;;
        3)
            start_autonomous_engine
            ;;
        4)
            start_browser_automation
            print_info "Browser running. Press Ctrl+C to stop."
            wait
            ;;
        5)
            stop_all
            ;;
        6)
            explain_tasks
            show_menu
            ;;
        7)
            exit 0
            ;;
        *)
            print_error "Invalid choice"
            sleep 2
            show_menu
            ;;
    esac
}

start_full() {
    print_header "🚀 STARTING FULL RICK BATTLESTATION"
    
    # 1. Start web UI
    start_web_ui
    
    # 2. Start browser
    start_browser_automation
    
    # 3. Wait a bit for everything to stabilize
    sleep 3
    
    # 4. Show status
    print_header "✅ RICK IS READY"
    echo ""
    print_success "Web UI:      http://127.0.0.1:8080"
    print_success "Browser:     Chrome opened with ChatGPT"
    print_success "AI Agents:   GPT-4 + Grok ready"
    echo ""
    print_info "Starting autonomous trading engine in 3 seconds..."
    sleep 3
    
    # 5. Start engine (this runs in foreground)
    start_autonomous_engine
}

################################################################################
# Main Entry Point
################################################################################

main() {
    # Handle command line arguments
    if [ $# -eq 0 ]; then
        # Default (new): RBOTZILLA master menu
        if [ -f "$PROJECT_ROOT/RBOTZILLA_LAUNCH.sh" ]; then
            print_header "🤖 Default Launcher: RBOTZILLA"
            print_info "Launching: ./RBOTZILLA_LAUNCH.sh"
            print_info "(Legacy menu available via: ./RICK_START.sh legacy)"
            echo ""
            exec bash "$PROJECT_ROOT/RBOTZILLA_LAUNCH.sh"
        fi

        # Fallback
        show_menu
    else
        case $1 in
            rbotzilla)
                exec bash "$PROJECT_ROOT/RBOTZILLA_LAUNCH.sh"
                ;;
            legacy)
                show_menu
                ;;
            full)
                start_full
                ;;
            web)
                start_web_ui
                print_info "Web UI running. Press Ctrl+C to stop."
                wait
                ;;
            engine)
                start_autonomous_engine
                ;;
            browser)
                start_browser_automation
                print_info "Browser running. Press Ctrl+C to stop."
                wait
                ;;
            stop)
                stop_all
                ;;
            explain)
                explain_tasks
                ;;
            *)
                print_error "Unknown command: $1"
                echo ""
                echo "Usage:"
                echo "  $0               # Interactive menu"
                echo "  $0 rbotzilla      # RBOTZILLA master menu (default)"
                echo "  $0 legacy        # Legacy menu (web/ui/browser/engine)"
                echo "  $0 full          # Start everything"
                echo "  $0 web           # Web UI only"
                echo "  $0 engine        # Trading engine only"
                echo "  $0 browser       # Browser automation only"
                echo "  $0 stop          # Stop all services"
                echo "  $0 explain       # Explain all tasks"
                exit 1
                ;;
        esac
    fi
}

# Run it
main "$@"
