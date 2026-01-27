#!/usr/bin/env bash
# OANDA AUTONOMOUS START - Single command to get trading live
# Sets all toggles, starts system, validates, and arms trading
set -euo pipefail

REPO="/home/ing/RICK/MULTI_BROKER_PHOENIX"
cd "$REPO" || exit 1

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  RBOTZILLA OANDA - AUTONOMOUS START${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo

# Load environment
set -a
[ -f .env ] && source .env
[ -f config/toggles.env ] && source config/toggles.env
set +a

# Force OANDA configuration
export BROKER_OANDA_ENABLED=1
export OANDA_ENABLED=1
export BROKER_COINBASE_ENABLED=0
export COINBASE_ENABLED=0
export BROKER_IBKR_ENABLED=0
export IBKR_ENABLED=0
export ENABLE_ENGINE=1
export ENABLE_HIVE=1
export ENABLE_OANDA=1
export HEADLESS_MODE=oanda-only
export TRADING_MODE=PAPER
export PRACTICE_TRADING_ALLOWED=1
export ALLOW_PRACTICE_ORDERS=1
export REQUIRE_OLLAMA=1
export REQUIRE_AI=1

echo -e "${GREEN}✓${NC} Environment configured for OANDA autonomous operation"
echo "  - OANDA: ENABLED"
echo "  - Mode: PAPER TRADING"
echo "  - AI: OLLAMA REQUIRED"
echo

# Start the system
echo -e "${YELLOW}→${NC} Starting orchestrator and OANDA broker..."
if ! ./tools/start_full_system.sh > /tmp/oanda_start.log 2>&1; then
  echo -e "${RED}❌ Failed to start system${NC}"
  tail -20 /tmp/oanda_start.log
  exit 1
fi
echo -e "${GREEN}✓${NC} System started"
echo

# Wait for orchestrator to settle (2 seconds)
sleep 2

# Run preflight checks
echo -e "${YELLOW}→${NC} Running preflight validation..."
if ! ./tools/preflight_oanda.sh > /tmp/oanda_preflight.log 2>&1; then
  echo -e "${RED}❌ Preflight checks FAILED${NC}"
  echo "Recent output:"
  tail -30 /tmp/oanda_preflight.log
  echo
  echo "Check logs: tail -f logs/oanda/engine.log"
  exit 1
fi

# Show preflight results
echo -e "${GREEN}✓${NC} Preflight validation PASSED"
grep "✅ PASS" /tmp/oanda_preflight.log | tail -5
echo

# Verify marker exists
MARKER="ops/state/preflight_oanda.ok"
if [[ ! -f "$MARKER" ]]; then
  echo -e "${RED}❌ Preflight marker not created: $MARKER${NC}"
  exit 1
fi
echo -e "${GREEN}✓${NC} Preflight marker verified"
echo

# Trading is now ready (AI Hive approval required at runtime)
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}🚀 OANDA AUTONOMOUS OPERATION ACTIVE${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo
echo "System Status:"
if [[ -f "ops/state/brokers/oanda.json" ]]; then
  cat ops/state/brokers/oanda.json | python3 -m json.tool 2>/dev/null | grep -E '"(broker|state|fail_count|timestamp)"' | sed 's/^/  /'
fi
echo
echo -e "${GREEN}✓${NC} AI Hive approval required for all trades"
echo -e "${GREEN}✓${NC} To monitor: run task 'OANDA Status'"
echo -e "${GREEN}✓${NC} To view logs: tail -f logs/oanda/engine.log"
echo -e "${GREEN}✓${NC} To stop: run task 'OANDA Stop'"
echo

exit 0
