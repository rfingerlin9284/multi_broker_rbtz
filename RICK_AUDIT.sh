#!/bin/bash
################################################################################
# 🔍 RICK SYSTEM AUDIT & PERFORMANCE MONITOR
################################################################################
# Comprehensive health check and performance evaluation of all RICK systems
################################################################################

# Don't exit on error - we want to see all checks

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

PROJECT_ROOT="/home/ing/RICK/MULTI_BROKER_PHOENIX"
cd "$PROJECT_ROOT"

print_header() {
    echo -e "${CYAN}"
    echo "════════════════════════════════════════════════════════════════════════"
    echo "  $1"
    echo "════════════════════════════════════════════════════════════════════════"
    echo -e "${NC}"
}

print_section() {
    echo ""
    echo -e "${PURPLE}▶ $1${NC}"
    echo "────────────────────────────────────────────────────────────────────────"
}

check_status() {
    local name=$1
    local condition=$2
    
    if [ $condition -eq 0 ]; then
        echo -e "  ${GREEN}✅${NC} $name"
        return 0
    else
        echo -e "  ${RED}❌${NC} $name"
        return 1
    fi
}

check_warning() {
    local name=$1
    local condition=$2
    
    if [ $condition -eq 0 ]; then
        echo -e "  ${GREEN}✅${NC} $name"
        return 0
    else
        echo -e "  ${YELLOW}⚠️${NC}  $name"
        return 1
    fi
}

################################################################################
# SECTION 1: Environment Check
################################################################################

audit_environment() {
    print_section "1. ENVIRONMENT CHECK"
    
    local issues=0
    
    # Python version
    if command -v python3 &>/dev/null; then
        PY_VER=$(python3 --version 2>&1)
        echo -e "  ${GREEN}✅${NC} Python: $PY_VER"
    else
        echo -e "  ${RED}❌${NC} Python 3 not found"
        ((issues++))
    fi
    
    # Virtual environment
    if [ -d ".venv" ]; then
        echo -e "  ${GREEN}✅${NC} Virtual environment exists"
        if [ -n "$VIRTUAL_ENV" ]; then
            echo -e "  ${GREEN}✅${NC} Virtual environment activated"
        else
            echo -e "  ${YELLOW}⚠️${NC}  Virtual environment not activated (run: source .venv/bin/activate)"
            ((issues++))
        fi
    else
        echo -e "  ${RED}❌${NC} Virtual environment missing"
        ((issues++))
    fi
    
    # Required packages
    echo ""
    echo "  Python Packages:"
    for pkg in flask openai requests pandas; do
        if python3 -c "import $pkg" 2>/dev/null; then
            echo -e "    ${GREEN}✅${NC} $pkg"
        else
            echo -e "    ${RED}❌${NC} $pkg (run: pip install $pkg)"
            ((issues++))
        fi
    done
    
    echo ""
    echo "  Total Issues: $issues"
    return $issues
}

################################################################################
# SECTION 2: Configuration Check
################################################################################

audit_configuration() {
    print_section "2. CONFIGURATION CHECK"
    
    local issues=0
    
    # .env file
    if [ -f ".env" ]; then
        echo -e "  ${GREEN}✅${NC} .env file exists"
        
        # Check critical env vars
        source .env 2>/dev/null || true
        
        if [ -n "$OPENAI_API_KEY" ]; then
            KEY_LEN=${#OPENAI_API_KEY}
            echo -e "  ${GREEN}✅${NC} OPENAI_API_KEY set ($KEY_LEN chars)"
        else
            echo -e "  ${YELLOW}⚠️${NC}  OPENAI_API_KEY not set"
            ((issues++))
        fi
        
        if [ -n "$XAI_API_KEY" ]; then
            KEY_LEN=${#XAI_API_KEY}
            echo -e "  ${GREEN}✅${NC} XAI_API_KEY set ($KEY_LEN chars)"
        else
            echo -e "  ${YELLOW}⚠️${NC}  XAI_API_KEY not set"
            ((issues++))
        fi
        
        if [ -n "$COINBASE_API_KEY" ]; then
            echo -e "  ${GREEN}✅${NC} COINBASE_API_KEY set"
        else
            echo -e "  ${YELLOW}⚠️${NC}  COINBASE_API_KEY not set"
        fi
        
        if [ -n "$IBKR_HOST" ]; then
            echo -e "  ${GREEN}✅${NC} IBKR_HOST set"
        else
            echo -e "  ${YELLOW}⚠️${NC}  IBKR_HOST not set"
        fi
    else
        echo -e "  ${RED}❌${NC} .env file missing"
        ((issues++))
    fi
    
    echo ""
    echo "  Total Issues: $issues"
    return $issues
}

################################################################################
# SECTION 3: Process Check
################################################################################

audit_processes() {
    print_section "3. RUNNING PROCESSES"
    
    local issues=0
    
    # Web UI
    if lsof -Pi :9222 -sTCP:LISTEN -t >/dev/null 2>&1; then
        PID=$(lsof -Pi :9222 -sTCP:LISTEN -t)
        echo -e "  ${GREEN}✅${NC} Web UI running (PID: $PID, Port: 9222)"
    else
        echo -e "  ${YELLOW}⚠️${NC}  Web UI not running (Port 9222 free)"
        ((issues++))
    fi
    
    # Trading engine
    if pgrep -f "autonomous_trading_engine.py" >/dev/null; then
        PID=$(pgrep -f "autonomous_trading_engine.py")
        echo -e "  ${GREEN}✅${NC} Trading engine running (PID: $PID)"
    else
        echo -e "  ${YELLOW}⚠️${NC}  Trading engine not running"
        ((issues++))
    fi
    
    # Browser automation
    if pgrep -f "launch_browser_ai.py" >/dev/null; then
        PID=$(pgrep -f "launch_browser_ai.py")
        echo -e "  ${GREEN}✅${NC} Browser automation running (PID: $PID)"
    else
        echo -e "  ${YELLOW}⚠️${NC}  Browser automation not running"
        ((issues++))
    fi
    
    # Chrome
    if pgrep -i chrome >/dev/null; then
        COUNT=$(pgrep -i chrome | wc -l)
        echo -e "  ${GREEN}✅${NC} Chrome running ($COUNT processes)"
    else
        echo -e "  ${YELLOW}⚠️${NC}  Chrome not running"
        ((issues++))
    fi
    
    echo ""
    if [ $issues -eq 0 ]; then
        echo -e "  ${GREEN}All services running${NC}"
    else
        echo -e "  ${YELLOW}$issues service(s) not running - use ./RICK_START.sh full${NC}"
    fi
    
    return $issues
}

################################################################################
# SECTION 4: File System Check
################################################################################

audit_filesystem() {
    print_section "4. FILE SYSTEM CHECK"
    
    local issues=0
    
    echo "  Critical Files:"
    
    # Core scripts
    for file in "RICK_START.sh" "CHEAT_SHEET.txt" "RICK_QUICK_START.md"; do
        if [ -f "$file" ]; then
            SIZE=$(stat -f "%z" "$file" 2>/dev/null || stat -c "%s" "$file" 2>/dev/null)
            echo -e "    ${GREEN}✅${NC} $file ($SIZE bytes)"
        else
            echo -e "    ${RED}❌${NC} $file missing"
            ((issues++))
        fi
    done
    
    echo ""
    echo "  Core Python Modules:"
    
    # Python files
    for file in "hive_real/autonomous_trading_engine.py" \
                "hive_real/api_ai_hive.py" \
                "hive_real/orchestrator_v2.py" \
                "hive_real/hive_web_interface.py" \
                "hive_real/payload_builder.py"; do
        if [ -f "$file" ]; then
            LINES=$(wc -l < "$file")
            echo -e "    ${GREEN}✅${NC} $file ($LINES lines)"
        else
            echo -e "    ${RED}❌${NC} $file missing"
            ((issues++))
        fi
    done
    
    echo ""
    echo "  Total Issues: $issues"
    return $issues
}

################################################################################
# SECTION 5: API Connectivity Check
################################################################################

audit_api_connectivity() {
    print_section "5. API CONNECTIVITY CHECK"
    
    local issues=0
    
    # Activate venv
    source .venv/bin/activate 2>/dev/null || true
    
    # Test OpenAI
    echo "  Testing OpenAI API..."
    if [ -n "$OPENAI_API_KEY" ]; then
        RESULT=$(python3 << 'EOF'
import sys
import openai
import os
try:
    client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    response = client.chat.completions.create(
        model='gpt-4o-mini',
        messages=[{'role': 'user', 'content': 'Hi'}],
        max_tokens=5
    )
    print("OK")
except Exception as e:
    print(f"FAIL: {e}")
EOF
)
        if [[ $RESULT == "OK" ]]; then
            echo -e "    ${GREEN}✅${NC} OpenAI API working"
        else
            echo -e "    ${RED}❌${NC} OpenAI API failed: $RESULT"
            ((issues++))
        fi
    else
        echo -e "    ${YELLOW}⚠️${NC}  OpenAI API key not set"
        ((issues++))
    fi
    
    # Test xAI
    echo "  Testing xAI/Grok API..."
    if [ -n "$XAI_API_KEY" ]; then
        RESULT=$(python3 << 'EOF'
import requests
import os
try:
    response = requests.post(
        'https://api.x.ai/v1/chat/completions',
        headers={'Authorization': f'Bearer {os.getenv("XAI_API_KEY")}'},
        json={'model': 'grok-beta', 'messages': [{'role': 'user', 'content': 'Hi'}], 'max_tokens': 5},
        timeout=10
    )
    print("OK" if response.status_code == 200 else f"HTTP {response.status_code}")
except Exception as e:
    print(f"FAIL: {e}")
EOF
)
        if [[ $RESULT == "OK" ]]; then
            echo -e "    ${GREEN}✅${NC} xAI/Grok API working"
        else
            echo -e "    ${YELLOW}⚠️${NC}  xAI/Grok API: $RESULT"
            ((issues++))
        fi
    else
        echo -e "    ${YELLOW}⚠️${NC}  xAI API key not set"
        ((issues++))
    fi
    
    # Test Web UI endpoint
    echo "  Testing Web UI endpoint..."
    if curl -s http://127.0.0.1:9222/ >/dev/null 2>&1; then
        echo -e "    ${GREEN}✅${NC} Web UI responding at http://127.0.0.1:9222"
    else
        echo -e "    ${YELLOW}⚠️${NC}  Web UI not responding"
        ((issues++))
    fi
    
    echo ""
    echo "  Total Issues: $issues"
    return $issues
}

################################################################################
# SECTION 6: Performance Metrics
################################################################################

audit_performance() {
    print_section "6. PERFORMANCE METRICS"
    
    # System resources
    echo "  System Resources:"
    
    # CPU
    if command -v top &>/dev/null; then
        CPU=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
        echo -e "    ${BLUE}ℹ️${NC}  CPU Usage: ${CPU}%"
    fi
    
    # Memory
    if command -v free &>/dev/null; then
        MEM=$(free -m | awk 'NR==2{printf "%.1f%%", $3*100/$2 }')
        echo -e "    ${BLUE}ℹ️${NC}  Memory Usage: $MEM"
    fi
    
    # Disk
    DISK=$(df -h . | awk 'NR==2{print $5}')
    echo -e "    ${BLUE}ℹ️${NC}  Disk Usage: $DISK"
    
    echo ""
    echo "  Process Resources:"
    
    # Web UI process
    if pgrep -f "hive_web_interface" >/dev/null; then
        PID=$(pgrep -f "hive_web_interface")
        MEM=$(ps -p $PID -o %mem= | xargs)
        CPU=$(ps -p $PID -o %cpu= | xargs)
        echo -e "    ${BLUE}ℹ️${NC}  Web UI: CPU ${CPU}%, MEM ${MEM}%"
    fi
    
    # Trading engine process
    if pgrep -f "autonomous_trading_engine" >/dev/null; then
        PID=$(pgrep -f "autonomous_trading_engine")
        MEM=$(ps -p $PID -o %mem= | xargs)
        CPU=$(ps -p $PID -o %cpu= | xargs)
        echo -e "    ${BLUE}ℹ️${NC}  Trading Engine: CPU ${CPU}%, MEM ${MEM}%"
    fi
    
    # Log files
    echo ""
    echo "  Log Files:"
    
    if [ -d "logs" ]; then
        LOG_SIZE=$(du -sh logs 2>/dev/null | cut -f1)
        LOG_COUNT=$(find logs -type f | wc -l)
        echo -e "    ${BLUE}ℹ️${NC}  logs/ - $LOG_SIZE ($LOG_COUNT files)"
    else
        echo -e "    ${YELLOW}⚠️${NC}  No logs directory"
    fi
    
    if [ -f "hive_real/worker.log" ]; then
        LOG_SIZE=$(du -h hive_real/worker.log | cut -f1)
        echo -e "    ${BLUE}ℹ️${NC}  worker.log - $LOG_SIZE"
    fi
}

################################################################################
# SECTION 7: Trading Performance (if engine running)
################################################################################

audit_trading_performance() {
    print_section "7. TRADING PERFORMANCE"
    
    if pgrep -f "autonomous_trading_engine" >/dev/null; then
        echo -e "  ${GREEN}Trading engine is active${NC}"
        echo ""
        echo "  To view live performance, check:"
        echo "    • Web UI: http://127.0.0.1:9222"
        echo "    • Terminal output of trading engine"
        echo "    • Log files in logs/"
    else
        echo -e "  ${YELLOW}Trading engine not running${NC}"
        echo "  Start with: ./RICK_START.sh engine"
    fi
}

################################################################################
# SECTION 8: Security Check
################################################################################

audit_security() {
    print_section "8. SECURITY CHECK"
    
    local issues=0
    
    # Check .env permissions
    if [ -f ".env" ]; then
        PERMS=$(stat -c "%a" .env 2>/dev/null || stat -f "%Lp" .env 2>/dev/null)
        if [ "$PERMS" = "600" ] || [ "$PERMS" = "400" ]; then
            echo -e "  ${GREEN}✅${NC} .env file permissions: $PERMS (secure)"
        else
            echo -e "  ${YELLOW}⚠️${NC}  .env file permissions: $PERMS (recommend: chmod 600 .env)"
            ((issues++))
        fi
    fi
    
    # Check for exposed API keys in code
    echo "  Scanning for exposed secrets..."
    if grep -r "sk-proj" --include="*.py" --exclude-dir=".venv" . >/dev/null 2>&1; then
        echo -e "  ${RED}❌${NC} Found hardcoded API keys in code!"
        ((issues++))
    else
        echo -e "  ${GREEN}✅${NC} No hardcoded API keys found"
    fi
    
    # Check git status
    if git rev-parse --git-dir >/dev/null 2>&1; then
        if git ls-files .env >/dev/null 2>&1; then
            echo -e "  ${RED}❌${NC} .env file tracked in git (dangerous!)"
            echo -e "      Run: git rm --cached .env"
            ((issues++))
        else
            echo -e "  ${GREEN}✅${NC} .env file not tracked in git"
        fi
    fi
    
    echo ""
    echo "  Total Issues: $issues"
    return $issues
}

################################################################################
# Main Audit
################################################################################

main() {
    clear
    print_header "🔍 RICK SYSTEM AUDIT & PERFORMANCE REPORT"
    echo ""
    echo "Generated: $(date)"
    echo "Location: $PROJECT_ROOT"
    
    local total_issues=0
    
    audit_environment
    ((total_issues+=$?))
    
    audit_configuration
    ((total_issues+=$?))
    
    audit_processes
    ((total_issues+=$?))
    
    audit_filesystem
    ((total_issues+=$?))
    
    audit_api_connectivity
    ((total_issues+=$?))
    
    audit_performance
    
    audit_trading_performance
    
    audit_security
    ((total_issues+=$?))
    
    # Summary
    print_header "📊 AUDIT SUMMARY"
    
    if [ $total_issues -eq 0 ]; then
        echo -e "${GREEN}"
        echo "  ╔═══════════════════════════════════════════════════╗"
        echo "  ║                                                   ║"
        echo "  ║   ✅  ALL SYSTEMS OPERATIONAL                     ║"
        echo "  ║                                                   ║"
        echo "  ║   RICK is ready for autonomous trading!          ║"
        echo "  ║                                                   ║"
        echo "  ╚═══════════════════════════════════════════════════╝"
        echo -e "${NC}"
    elif [ $total_issues -le 5 ]; then
        echo -e "${YELLOW}"
        echo "  ╔═══════════════════════════════════════════════════╗"
        echo "  ║                                                   ║"
        echo "  ║   ⚠️  $total_issues ISSUES FOUND (Minor)                    ║"
        echo "  ║                                                   ║"
        echo "  ║   System functional but has warnings.            ║"
        echo "  ║   Review issues above for optimization.          ║"
        echo "  ║                                                   ║"
        echo "  ╚═══════════════════════════════════════════════════╝"
        echo -e "${NC}"
    else
        echo -e "${RED}"
        echo "  ╔═══════════════════════════════════════════════════╗"
        echo "  ║                                                   ║"
        echo "  ║   ❌  $total_issues ISSUES FOUND (Critical)             ║"
        echo "  ║                                                   ║"
        echo "  ║   Fix issues before running live trading!        ║"
        echo "  ║                                                   ║"
        echo "  ╚═══════════════════════════════════════════════════╝"
        echo -e "${NC}"
    fi
    
    echo ""
    echo "Quick Actions:"
    echo "  • Start services:  ./RICK_START.sh full"
    echo "  • Stop services:   ./RICK_START.sh stop"
    echo "  • View dashboard:  http://127.0.0.1:9222"
    echo "  • Re-run audit:    ./RICK_AUDIT.sh"
    echo ""
}

main "$@"
