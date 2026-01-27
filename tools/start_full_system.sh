#!/usr/bin/env bash
# Start full RBOTZILLA multi-broker system
# Usage: ./start_full_system.sh

set -euo pipefail

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
REPO_ROOT="$(cd "$(dirname "$SCRIPT_PATH")/.." && pwd)"
cd "$REPO_ROOT"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  RBOTZILLA MULTI-BROKER SYSTEM START${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"

# Load environment
if [[ -f "tools/env_load.sh" ]]; then
  echo -e "${YELLOW}→${NC} Loading environment..."
  source tools/env_load.sh
else
  echo -e "${RED}✗${NC} env_load.sh not found. Cannot start."
  exit 1
fi

# Ensure canonical package structure
echo -e "${YELLOW}→${NC} Verifying canonical package structure..."
CANONICAL_PKG="$REPO_ROOT/multi_broker_phoenix"
NESTED_PKG="$REPO_ROOT/MULTI_BROKER_PHOENIX/multi_broker_phoenix"

if [[ ! -d "$CANONICAL_PKG" ]]; then
  echo -e "${RED}✗${NC} Canonical package not found: $CANONICAL_PKG"
  exit 1
fi

if [[ -d "$REPO_ROOT/MULTI_BROKER_PHOENIX" ]]; then
  if [[ -d "$NESTED_PKG" && ! -L "$NESTED_PKG" ]]; then
    echo -e "${YELLOW}⚠${NC} Nested package is a directory (not symlink). Creating backup and symlinking..."
    mv "$NESTED_PKG" "${NESTED_PKG}.bak.$(date +%s)"
    ln -sf "$CANONICAL_PKG" "$NESTED_PKG"
    echo -e "${GREEN}✓${NC} Symlinked nested package to canonical location"
  fi
fi

# Ensure ops directories exist
mkdir -p "$REPO_ROOT/ops/state/brokers"
mkdir -p "$REPO_ROOT/logs/runs"

# Check broker toggles - read from ENABLE_* or BROKER_* (with fallback)
OANDA_ENABLED="${BROKER_OANDA_ENABLED:-${ENABLE_OANDA:-1}}"
COINBASE_ENABLED="${BROKER_COINBASE_ENABLED:-${ENABLE_COINBASE:-0}}"
IBKR_ENABLED="${BROKER_IBKR_ENABLED:-${ENABLE_IBKR:-0}}"
AUTO_ARM="${AUTO_ARM_ON_HEALTHY:-0}"

# Export BROKER_* variables for orchestrator subprocess
export BROKER_OANDA_ENABLED="$OANDA_ENABLED"
export BROKER_COINBASE_ENABLED="$COINBASE_ENABLED"
export BROKER_IBKR_ENABLED="$IBKR_ENABLED"
export AUTO_ARM_ON_HEALTHY="$AUTO_ARM"

echo ""
echo -e "${BLUE}Broker Configuration:${NC}"
echo -e "  OANDA:     $([ "$OANDA_ENABLED" == "1" ] && echo -e "${GREEN}ENABLED${NC}" || echo -e "${YELLOW}DISABLED${NC}")"
echo -e "  Coinbase:  $([ "$COINBASE_ENABLED" == "1" ] && echo -e "${GREEN}ENABLED${NC}" || echo -e "${YELLOW}DISABLED${NC}")"
echo -e "  IBKR:      $([ "$IBKR_ENABLED" == "1" ] && echo -e "${GREEN}ENABLED${NC}" || echo -e "${YELLOW}DISABLED${NC}")"
echo -e "  Auto-Arm:  $([ "$AUTO_ARM" == "1" ] && echo -e "${GREEN}YES${NC}" || echo -e "${YELLOW}NO${NC}")"
echo ""

# Start orchestrator
echo -e "${YELLOW}→${NC} Starting orchestrator..."
python3 -m multi_broker_phoenix.core.orchestrator &
ORCH_PID=$!
echo "$ORCH_PID" > "$REPO_ROOT/ops/state/orchestrator.pid"
echo -e "${GREEN}✓${NC} Orchestrator started (PID=$ORCH_PID)"

# Wait a moment for orchestrator to initialize
sleep 2

# Orchestrator will start enabled brokers automatically
# But we can also start them explicitly here if needed
if [[ "$OANDA_ENABLED" == "1" ]]; then
  echo -e "${YELLOW}→${NC} OANDA broker startup initiated by orchestrator..."
fi

if [[ "$COINBASE_ENABLED" == "1" ]]; then
  echo -e "${YELLOW}→${NC} Coinbase broker startup initiated by orchestrator..."
fi

if [[ "$IBKR_ENABLED" == "1" ]]; then
  echo -e "${YELLOW}→${NC} IBKR broker startup initiated by orchestrator..."
fi

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  RBOTZILLA SYSTEM STARTED${NC}"

# RBOTZILLA_PREFLIGHT_OANDA: auto preflight on every restart (OANDA)
if [[ "${BROKER_OANDA_ENABLED:-0}" == "1" || "${OANDA_ENABLED:-0}" == "1" ]]; then
  echo ""
  echo "═══════════════════════════════════════════════════════════════"
  echo "  OANDA PRE-FLIGHT (AUTO) — MUST PASS BEFORE ARM"
  echo "═══════════════════════════════════════════════════════════════"
  ./tools/preflight_oanda.sh || { echo ""; echo "Preflight failed."; exit 1; }
fi

echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "Run ${BLUE}./tools/status_full_system.sh${NC} to check broker health"
echo ""
