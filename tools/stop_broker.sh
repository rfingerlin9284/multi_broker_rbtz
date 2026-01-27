#!/usr/bin/env bash
# Stop a specific broker or all brokers
# Usage: ./stop_broker.sh {oanda|coinbase|ibkr|orchestrator|all}

set -euo pipefail

TARGET="${1:-}"

if [[ -z "$TARGET" ]]; then
  echo "Usage: $0 {oanda|coinbase|ibkr|orchestrator|all}"
  exit 1
fi

TARGET=$(echo "$TARGET" | tr '[:upper:]' '[:lower:]')

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
REPO_ROOT="$(cd "$(dirname "$SCRIPT_PATH")/.." && pwd)"
cd "$REPO_ROOT"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

stop_broker() {
  local broker_name="$1"
  local pid_file="$REPO_ROOT/ops/state/brokers/${broker_name}.pid"
  
  if [[ ! -f "$pid_file" ]]; then
    echo -e "${YELLOW}⚠${NC} ${broker_name}: No PID file found ($pid_file)"
    return 0
  fi
  
  local pid=$(cat "$pid_file")
  
  if ! kill -0 "$pid" 2>/dev/null; then
    echo -e "${YELLOW}⚠${NC} ${broker_name}: Process $pid not running"
    rm -f "$pid_file"
    return 0
  fi
  
  echo -e "${YELLOW}→${NC} Stopping ${broker_name} (PID=$pid)..."
  
  # Send SIGTERM
  kill -TERM "$pid" 2>/dev/null || true
  
  # Wait up to 10 seconds for graceful shutdown
  local count=0
  while kill -0 "$pid" 2>/dev/null && [[ $count -lt 10 ]]; do
    sleep 1
    ((count++))
  done
  
  # Force kill if still running
  if kill -0 "$pid" 2>/dev/null; then
    echo -e "${YELLOW}⚠${NC} ${broker_name}: Graceful shutdown timeout, sending SIGKILL..."
    kill -9 "$pid" 2>/dev/null || true
    sleep 1
  fi
  
  if kill -0 "$pid" 2>/dev/null; then
    echo -e "${RED}✗${NC} ${broker_name}: Failed to stop process $pid"
    return 1
  else
    echo -e "${GREEN}✓${NC} ${broker_name}: Stopped"
    rm -f "$pid_file"
    return 0
  fi
}

stop_orchestrator() {
  local pid_file="$REPO_ROOT/ops/state/orchestrator.pid"
  
  if [[ ! -f "$pid_file" ]]; then
    echo -e "${YELLOW}⚠${NC} Orchestrator: No PID file found"
    return 0
  fi
  
  local pid=$(cat "$pid_file")
  
  if ! kill -0 "$pid" 2>/dev/null; then
    echo -e "${YELLOW}⚠${NC} Orchestrator: Process $pid not running"
    rm -f "$pid_file"
    return 0
  fi
  
  echo -e "${YELLOW}→${NC} Stopping orchestrator (PID=$pid)..."
  kill -TERM "$pid" 2>/dev/null || true
  
  local count=0
  while kill -0 "$pid" 2>/dev/null && [[ $count -lt 5 ]]; do
    sleep 1
    ((count++))
  done
  
  if kill -0 "$pid" 2>/dev/null; then
    kill -9 "$pid" 2>/dev/null || true
  fi
  
  echo -e "${GREEN}✓${NC} Orchestrator: Stopped"
  rm -f "$pid_file"
}

case "$TARGET" in
  oanda|coinbase|ibkr)
    stop_broker "$TARGET"
    ;;
  
  orchestrator)
    stop_orchestrator
    ;;
  
  all)
    echo -e "${BLUE}Stopping all brokers and orchestrator...${NC}"
    stop_broker "oanda"
    stop_broker "coinbase"
    stop_broker "ibkr"
    stop_orchestrator
    echo -e "${GREEN}✓${NC} All stopped"
    ;;
  
  *)
    echo -e "${RED}✗${NC} Invalid target: $TARGET"
    echo "Usage: $0 {oanda|coinbase|ibkr|orchestrator|all}"
    exit 1
    ;;
esac
