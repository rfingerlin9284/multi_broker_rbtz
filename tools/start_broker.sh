#!/usr/bin/env bash
# Start a specific broker
# Usage: ./start_broker.sh {oanda|coinbase|ibkr}

set -euo pipefail

BROKER_NAME="${1:-}"

if [[ -z "$BROKER_NAME" ]]; then
  echo "Usage: $0 {oanda|coinbase|ibkr}"
  exit 1
fi

BROKER_NAME=$(echo "$BROKER_NAME" | tr '[:upper:]' '[:lower:]')

if [[ ! "$BROKER_NAME" =~ ^(oanda|coinbase|ibkr)$ ]]; then
  echo "Error: Invalid broker name '$BROKER_NAME'. Must be one of: oanda, coinbase, ibkr"
  exit 1
fi

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
REPO_ROOT="$(cd "$(dirname "$SCRIPT_PATH")/.." && pwd)"
cd "$REPO_ROOT"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}Starting ${BROKER_NAME} broker...${NC}"

# Load environment
if [[ -f "tools/env_load.sh" ]]; then
  source tools/env_load.sh
else
  echo -e "${RED}✗${NC} env_load.sh not found"
  exit 1
fi

# Check if broker is enabled
ENABLED_VAR="BROKER_${BROKER_NAME^^}_ENABLED"
ENABLED="${!ENABLED_VAR:-0}"

if [[ "$ENABLED" != "1" ]]; then
  echo -e "${YELLOW}⚠${NC} Broker $BROKER_NAME is DISABLED (${ENABLED_VAR}=${ENABLED})"
  echo -e "   Set ${ENABLED_VAR}=1 in environment to enable"
  exit 1
fi

# Ensure directories
mkdir -p "$REPO_ROOT/ops/state/brokers"
mkdir -p "$REPO_ROOT/logs/${BROKER_NAME}"

# Start broker engine
# This is a placeholder - actual implementation depends on broker engine structure
# For now, create a simple wrapper that starts the appropriate engine

BROKER_PID_FILE="$REPO_ROOT/ops/state/brokers/${BROKER_NAME}.pid"
BROKER_LOG="$REPO_ROOT/logs/${BROKER_NAME}/engine.log"

# Prevent duplicate broker processes
if [[ -f "$BROKER_PID_FILE" ]]; then
  EXISTING_PID=$(cat "$BROKER_PID_FILE" || true)
  if [[ -n "$EXISTING_PID" ]] && kill -0 "$EXISTING_PID" 2>/dev/null; then
    echo -e "${YELLOW}⚠${NC} ${BROKER_NAME} broker already running (PID=$EXISTING_PID)"
    echo -e "   Log: $BROKER_LOG"
    exit 0
  fi
fi

# Ensure Python can find multi_broker_phoenix package
# Support both /home/ing/RICK and /home/ing/RICK/MULTI_BROKER_PHOENIX as REPO_ROOT
if [[ -d "$REPO_ROOT/multi_broker_phoenix" ]]; then
  export PYTHONPATH="$REPO_ROOT:${PYTHONPATH:-}"
elif [[ -d "$REPO_ROOT/MULTI_BROKER_PHOENIX/multi_broker_phoenix" ]]; then
  export PYTHONPATH="$REPO_ROOT/MULTI_BROKER_PHOENIX:${PYTHONPATH:-}"
else
  echo -e "${RED}✗${NC} Cannot find multi_broker_phoenix package"
  exit 1
fi

case "$BROKER_NAME" in
  oanda)
    # Start OANDA supervised runner
    nohup python3 -m multi_broker_phoenix.runners.oanda_runner >> "$BROKER_LOG" 2>&1 &
    echo $! > "$BROKER_PID_FILE"
    ;;
  
  coinbase)
    # Start Coinbase supervised runner
    nohup python3 -m multi_broker_phoenix.runners.coinbase_runner >> "$BROKER_LOG" 2>&1 &
    echo $! > "$BROKER_PID_FILE"
    ;;
  
  ibkr)
    # Start IBKR supervised runner
    nohup python3 -m multi_broker_phoenix.runners.ibkr_runner >> "$BROKER_LOG" 2>&1 &
    echo $! > "$BROKER_PID_FILE"
    ;;
esac

PID=$(cat "$BROKER_PID_FILE")
echo -e "${GREEN}✓${NC} ${BROKER_NAME} broker started (PID=$PID)"
echo -e "   Log: $BROKER_LOG"
echo -e "   Heartbeat: ops/state/brokers/${BROKER_NAME}.json"
