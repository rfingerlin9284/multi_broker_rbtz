#!/usr/bin/env bash
# Display status of full RBOTZILLA multi-broker system
# Usage: ./status_full_system.sh

set -euo pipefail

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
REPO_ROOT="$(cd "$(dirname "$SCRIPT_PATH")/.." && pwd)"
cd "$REPO_ROOT"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# Load environment
if [[ -f "tools/env_load.sh" ]]; then
  source tools/env_load.sh 2>/dev/null || true
fi

echo ""
echo -e "${BOLD}${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}${BLUE}  RBOTZILLA MULTI-BROKER SYSTEM STATUS${NC}"
echo -e "${BOLD}${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# Check environment toggles
OANDA_ENABLED="${BROKER_OANDA_ENABLED:-1}"
COINBASE_ENABLED="${BROKER_COINBASE_ENABLED:-0}"
IBKR_ENABLED="${BROKER_IBKR_ENABLED:-0}"
AUTO_ARM="${AUTO_ARM_ON_HEALTHY:-0}"

echo -e "${BOLD}Environment Configuration:${NC}"
echo -e "  OANDA:     $([ "$OANDA_ENABLED" == "1" ] && echo -e "${GREEN}ENABLED${NC}" || echo -e "${YELLOW}DISABLED${NC}")"
echo -e "  Coinbase:  $([ "$COINBASE_ENABLED" == "1" ] && echo -e "${GREEN}ENABLED${NC}" || echo -e "${YELLOW}DISABLED${NC}")"
echo -e "  IBKR:      $([ "$IBKR_ENABLED" == "1" ] && echo -e "${GREEN}ENABLED${NC}" || echo -e "${YELLOW}DISABLED${NC}")"
echo -e "  Auto-Arm:  $([ "$AUTO_ARM" == "1" ] && echo -e "${GREEN}YES${NC}" || echo -e "${YELLOW}NO${NC}")"
echo ""

# Orchestrator status
echo -e "${BOLD}Orchestrator:${NC}"
ORCH_PID_FILE="$REPO_ROOT/ops/state/orchestrator.pid"
if [[ -f "$ORCH_PID_FILE" ]]; then
  ORCH_PID=$(cat "$ORCH_PID_FILE")
  if kill -0 "$ORCH_PID" 2>/dev/null; then
    echo -e "  Status: ${GREEN}●${NC} RUNNING (PID=$ORCH_PID)"
  else
    echo -e "  Status: ${RED}●${NC} DEAD (stale PID=$ORCH_PID)"
  fi
else
  echo -e "  Status: ${YELLOW}●${NC} NOT STARTED"
fi
echo ""

# Broker status
display_broker_status() {
  local broker_name="$1"
  local heartbeat_file="$REPO_ROOT/ops/state/brokers/${broker_name}.json"
  local pid_file="$REPO_ROOT/ops/state/brokers/${broker_name}.pid"
  
  echo -e "${BOLD}${CYAN}${broker_name^^}:${NC}"
  
  # Check PID
  if [[ -f "$pid_file" ]]; then
    local pid=$(cat "$pid_file")
    if kill -0 "$pid" 2>/dev/null; then
      echo -e "  Process:   ${GREEN}●${NC} RUNNING (PID=$pid)"
    else
      echo -e "  Process:   ${RED}●${NC} DEAD (stale PID=$pid)"
    fi
  else
    echo -e "  Process:   ${YELLOW}●${NC} NOT STARTED"
  fi
  
  # Check heartbeat
  if [[ -f "$heartbeat_file" ]]; then
    local state=$(jq -r '.state // "UNKNOWN"' "$heartbeat_file" 2>/dev/null || echo "ERROR")
    local fail_count=$(jq -r '.fail_count // 0' "$heartbeat_file" 2>/dev/null || echo "?")
    local last_error=$(jq -r '.last_error // "none"' "$heartbeat_file" 2>/dev/null || echo "?")
    local timestamp=$(jq -r '.timestamp // "unknown"' "$heartbeat_file" 2>/dev/null || echo "?")
    local epoch=$(jq -r '.epoch // 0' "$heartbeat_file" 2>/dev/null || echo "0")
    
    # Calculate heartbeat age
    local now=$(date +%s)
    local age=$((now - ${epoch%.*}))
    
    # Color code state
    local state_color="$YELLOW"
    case "$state" in
      ACTIVE) state_color="$GREEN" ;;
      PAUSED) state_color="$YELLOW" ;;
      FAILED) state_color="$RED" ;;
      DISABLED) state_color="$YELLOW" ;;
    esac
    
    echo -e "  State:     ${state_color}${state}${NC}"
    echo -e "  Failures:  $fail_count"
    echo -e "  Heartbeat: ${age}s ago"
    echo -e "  Last Error: ${last_error:0:60}"
  else
    echo -e "  State:     ${YELLOW}NO HEARTBEAT${NC}"
  fi
  
  echo ""
}

display_broker_status "oanda"
display_broker_status "coinbase"
display_broker_status "ibkr"

# Summary file
SUMMARY_FILE="$REPO_ROOT/ops/state/brokers/summary.json"
if [[ -f "$SUMMARY_FILE" ]]; then
  echo -e "${BOLD}Summary (from orchestrator):${NC}"
  jq '.' "$SUMMARY_FILE" 2>/dev/null || echo "  (Failed to parse summary.json)"
  echo ""
fi

echo -e "${BOLD}${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "Commands:"
echo -e "  ${CYAN}./tools/start_broker.sh {broker}${NC}  - Start specific broker"
echo -e "  ${CYAN}./tools/stop_broker.sh {broker}${NC}   - Stop specific broker"
echo ""
