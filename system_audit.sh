#!/usr/bin/env bash
# FULL SYSTEM AUDIT - Comprehensive check of all components
# Verifies strategies, stop losses, API keys, Hive integration, and more

# Don't exit on errors - we want to continue auditing even if checks fail
set +e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PASSED=0
FAILED=0
WARNINGS=0

pass_check() {
    echo -e "  ${GREEN}✅ $1${NC}"
    ((PASSED++))
}

fail_check() {
    echo -e "  ${RED}❌ $1${NC}"
    ((FAILED++))
}

warn_check() {
    echo -e "  ${YELLOW}⚠️  $1${NC}"
    ((WARNINGS++))
}

echo "════════════════════════════════════════════════════════════════"
echo "🔍 RBOTZILLA FULL SYSTEM AUDIT"
echo "════════════════════════════════════════════════════════════════"
echo ""

# ============================================================================
echo "1️⃣  CRITICAL FILES & STRUCTURE"
echo "────────────────────────────────────────────────────────────────"

if [ -f ".env" ]; then
    pass_check ".env configuration file exists"
else
    fail_check ".env configuration file MISSING"
fi

if [ -d "MULTI_BROKER_PHOENIX/multi_broker_phoenix/strategies" ]; then
    pass_check "Strategies directory exists"
else
    fail_check "Strategies directory MISSING"
fi

if [ -d "backups/fabio_v1.1.0" ]; then
    pass_check "Backup system active"
else
    warn_check "No backups found"
fi

# ============================================================================
echo ""
echo "2️⃣  API KEYS & CONNECTIVITY"
echo "────────────────────────────────────────────────────────────────"

source .env 2>/dev/null || true

# OANDA
if [ -n "$OANDA_API_TOKEN" ]; then
    pass_check "OANDA API token configured"
    if [ -n "$OANDA_ACCOUNT_ID" ]; then
        pass_check "OANDA account ID configured"
    else
        fail_check "OANDA account ID MISSING"
    fi
else
    fail_check "OANDA API token MISSING"
fi

# Coinbase
if [ -n "$COINBASE_API_KEY" ] && [ -n "$COINBASE_API_SECRET" ]; then
    pass_check "Coinbase credentials configured"
else
    warn_check "Coinbase credentials not set (live trading will fail)"
fi

# IBKR
if [ "$IBKR_ENABLED" = "true" ]; then
    pass_check "IBKR Gateway enabled"
    if [ "$IBKR_PORT" = "4002" ]; then
        pass_check "IBKR configured for paper account (port 4002)"
    elif [ "$IBKR_PORT" = "4001" ]; then
        warn_check "IBKR configured for LIVE account (port 4001) - REAL MONEY"
    else
        warn_check "IBKR port ${IBKR_PORT} - verify configuration"
    fi
    if [ -n "$IBKR_SYMBOLS" ]; then
        pass_check "IBKR futures symbols configured"
    fi
else
    warn_check "IBKR disabled (futures trading not available)"
fi

# AI Hive
if [ -n "$OPENAI_API_KEY" ]; then
    pass_check "OpenAI API key configured"
else
    warn_check "OpenAI API key not set"
fi

if [ -n "$XAI_API_KEY" ]; then
    pass_check "XAI (Grok) API key configured"
else
    warn_check "XAI API key not set"
fi

if [ -n "$DEEPSEEK_API_KEY" ]; then
    pass_check "DeepSeek API key configured"
else
    warn_check "DeepSeek API key not set"
fi

# ============================================================================
echo ""
echo "3️⃣  STRATEGY CONFIGURATION"
echo "────────────────────────────────────────────────────────────────"

# Check FABIO RSI threshold
if [ -n "$FABIO_RSI_THRESHOLD" ]; then
    if [ "$FABIO_RSI_THRESHOLD" = "40" ]; then
        pass_check "FABIO_RSI_THRESHOLD=40 (optimized, 167 trades)"
    else
        warn_check "FABIO_RSI_THRESHOLD=$FABIO_RSI_THRESHOLD (not optimized value of 40)"
    fi
else
    fail_check "FABIO_RSI_THRESHOLD not set"
fi

# Check strategy files exist
STRATEGIES=(
    "fabio_aaa_full.py"
    "base.py"
    "unified_hive_scanner.py"
    "hive_cost_control.py"
)

for strat in "${STRATEGIES[@]}"; do
    if [ -f "MULTI_BROKER_PHOENIX/multi_broker_phoenix/strategies/$strat" ]; then
        pass_check "Strategy file: $strat"
    else
        fail_check "Strategy file MISSING: $strat"
    fi
done

# ============================================================================
echo ""
echo "4️⃣  STOP LOSS & RISK MANAGEMENT"
echo "────────────────────────────────────────────────────────────────"

# Check stop loss configurations
if [ -n "$FABIO_STOP_MIN_PCT" ]; then
    pass_check "FABIO stop loss configured: ${FABIO_STOP_MIN_PCT}-${FABIO_STOP_MAX_PCT}%"
else
    warn_check "FABIO stop loss using defaults"
fi

if [ -n "$HOLY_GRAIL_STOP_PCT" ]; then
    pass_check "Holy Grail stop loss: ${HOLY_GRAIL_STOP_PCT}%"
else
    warn_check "Holy Grail stop loss using default"
fi

if [ -n "$EMA_SCALPER_STOP_PCT" ]; then
    pass_check "EMA Scalper stop loss: ${EMA_SCALPER_STOP_PCT}%"
else
    warn_check "EMA Scalper stop loss using default"
fi

# Safety tripwires
if [ -n "$MAX_DRAWDOWN_PCT" ]; then
    pass_check "Max drawdown limit: ${MAX_DRAWDOWN_PCT}%"
else
    fail_check "MAX_DRAWDOWN_PCT not set"
fi

if [ -n "$DAILY_LOSS_LIMIT_USD" ]; then
    pass_check "Daily loss limit: \$${DAILY_LOSS_LIMIT_USD}"
else
    fail_check "DAILY_LOSS_LIMIT_USD not set"
fi

if [ -n "$MAX_CONSECUTIVE_LOSSES" ]; then
    pass_check "Max consecutive losses: ${MAX_CONSECUTIVE_LOSSES}"
else
    fail_check "MAX_CONSECUTIVE_LOSSES not set"
fi

# Trailing stops
if [ "$OANDA_TRAIL_MONITOR_ENABLED" = "true" ]; then
    pass_check "OANDA trailing stops ENABLED"
else
    warn_check "OANDA trailing stops disabled"
fi

if [ "$IBKR_TRAILING_STOP" = "true" ]; then
    pass_check "IBKR trailing stops ENABLED"
else
    warn_check "IBKR trailing stops disabled"
fi

if [ "$COINBASE_USE_TRAILING_STOPS" = "true" ]; then
    pass_check "Coinbase trailing stops ENABLED"
else
    warn_check "Coinbase trailing stops disabled"
fi

# ============================================================================
echo ""
echo "5️⃣  AI HIVE INTEGRATION"
echo "────────────────────────────────────────────────────────────────"

if [ "$ENABLE_AI_HIVE" = "true" ]; then
    pass_check "AI Hive validation ENABLED"
else
    warn_check "AI Hive validation DISABLED"
fi

if [ -n "$AI_HIVE_DAILY_BUDGET_USD" ]; then
    pass_check "AI budget control: \$${AI_HIVE_DAILY_BUDGET_USD}/day"
else
    fail_check "AI_HIVE_DAILY_BUDGET_USD not set"
fi

if [ "$HIVE_STRATEGY_FIRST" = "true" ]; then
    pass_check "Strategy-first mode ENABLED (cost efficient)"
else
    warn_check "Strategy-first mode disabled (higher AI costs)"
fi

if [ "$HIVE_ONLY_ON_SIGNAL" = "true" ]; then
    pass_check "AI only on signals ENABLED (cost efficient)"
else
    warn_check "AI scans all symbols (higher costs)"
fi

# Check Hive consensus settings
if [ -n "$AI_HIVE_MIN_CONSENSUS" ]; then
    pass_check "AI consensus requirement: ${AI_HIVE_MIN_CONSENSUS} agents"
else
    fail_check "AI_HIVE_MIN_CONSENSUS not set"
fi

# ============================================================================
echo ""
echo "6️⃣  TRADING MODE & SYMBOLS"
echo "────────────────────────────────────────────────────────────────"

if [ "$TRADING_MODE" = "PAPER" ]; then
    pass_check "Trading mode: PAPER (safe)"
elif [ "$TRADING_MODE" = "LIVE" ]; then
    warn_check "Trading mode: LIVE (real money!)"
else
    fail_check "TRADING_MODE not set"
fi

if [ "$PAPER_VIA_PLATFORM" = "1" ]; then
    pass_check "Using platform paper accounts"
else
    warn_check "Using simulation (not real platform paper)"
fi

if [ -n "$FEED_SYMBOLS" ]; then
    SYMBOL_COUNT=$(echo "$FEED_SYMBOLS" | tr ',' '\n' | wc -l)
    pass_check "Trading symbols configured: ${SYMBOL_COUNT} symbols"
    echo "     Symbols: ${FEED_SYMBOLS}"
else
    fail_check "FEED_SYMBOLS not set"
fi

if [ -n "$DEFAULT_STRATEGY" ]; then
    pass_check "Default strategy: ${DEFAULT_STRATEGY}"
else
    warn_check "DEFAULT_STRATEGY not set"
fi

# ============================================================================
echo ""
echo "7️⃣  POSITION & RISK LIMITS"
echo "────────────────────────────────────────────────────────────────"

if [ -n "$OANDA_MAX_POSITIONS_PER_INSTRUMENT" ]; then
    pass_check "OANDA max positions: ${OANDA_MAX_POSITIONS_PER_INSTRUMENT} per instrument"
else
    warn_check "OANDA position limits using defaults"
fi

if [ -n "$COINBASE_MAX_TRADES_PER_DAY" ]; then
    pass_check "Coinbase daily trade limit: ${COINBASE_MAX_TRADES_PER_DAY}"
else
    fail_check "COINBASE_MAX_TRADES_PER_DAY not set"
fi

if [ -n "$COINBASE_DAILY_LOSS_LIMIT" ]; then
    pass_check "Coinbase daily loss limit: \$${COINBASE_DAILY_LOSS_LIMIT}"
else
    fail_check "COINBASE_DAILY_LOSS_LIMIT not set"
fi

if [ -n "$MAX_CONCURRENT_TRADES" ]; then
    pass_check "Max concurrent trades: ${MAX_CONCURRENT_TRADES}"
else
    fail_check "MAX_CONCURRENT_TRADES not set"
fi

# ============================================================================
echo ""
echo "8️⃣  CANARY MODE SAFETY"
echo "────────────────────────────────────────────────────────────────"

if [ -n "$CANARY_MAX_RISK_USD" ]; then
    pass_check "Canary max risk: \$${CANARY_MAX_RISK_USD}"
else
    warn_check "CANARY_MAX_RISK_USD not set"
fi

if [ -n "$CANARY_POLL_SECONDS" ]; then
    pass_check "Canary poll interval: ${CANARY_POLL_SECONDS}s"
else
    warn_check "CANARY_POLL_SECONDS using default"
fi

# ============================================================================
echo ""
echo "9️⃣  PYTHON DEPENDENCIES"
echo "────────────────────────────────────────────────────────────────"

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1)
    pass_check "Python available: $PYTHON_VERSION"
else
    fail_check "Python3 not found"
fi

# Check critical Python modules
MODULES=("requests" "pandas" "numpy")
for mod in "${MODULES[@]}"; do
    if python3 -c "import $mod" 2>/dev/null; then
        pass_check "Python module: $mod"
    else
        fail_check "Python module MISSING: $mod"
    fi
done

# ============================================================================
echo ""
echo "🔟  AUTOMATED TESTS"
echo "────────────────────────────────────────────────────────────────"

# Test FABIO threshold
FABIO_FILE="MULTI_BROKER_PHOENIX/multi_broker_phoenix/strategies/fabio_aaa_full.py"
if [ -f "$FABIO_FILE" ]; then
    if grep -q "self.rsi_threshold.*FABIO_RSI_THRESHOLD" "$FABIO_FILE"; then
        pass_check "FABIO uses configurable RSI threshold"
    else
        fail_check "FABIO RSI threshold not configurable"
    fi
    
    if grep -q "< self.rsi_threshold" "$FABIO_FILE"; then
        pass_check "FABIO threshold properly implemented"
    else
        fail_check "FABIO threshold check MISSING"
    fi
fi

# Test restore script
if [ -x "restore_fabio_milestone_v1.1.sh" ]; then
    pass_check "Restore script executable"
else
    warn_check "Restore script not executable"
fi

# ============================================================================
echo ""
echo "════════════════════════════════════════════════════════════════"
echo "📊 AUDIT SUMMARY"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo -e "  ${GREEN}✅ Passed:   ${PASSED}${NC}"
echo -e "  ${RED}❌ Failed:   ${FAILED}${NC}"
echo -e "  ${YELLOW}⚠️  Warnings: ${WARNINGS}${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 SYSTEM READY FOR LIVE PAPER TRADING${NC}"
    exit 0
elif [ $FAILED -le 3 ]; then
    echo -e "${YELLOW}⚠️  SYSTEM HAS MINOR ISSUES - Review failures above${NC}"
    exit 1
else
    echo -e "${RED}❌ SYSTEM NOT READY - Fix critical failures above${NC}"
    exit 2
fi
