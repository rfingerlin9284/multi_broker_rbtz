#!/usr/bin/env bash
# Test broker isolation - ensure one broker failing doesn't stop others
# Usage: ./test_isolation.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "========================================================================="
echo "BROKER ISOLATION TEST"
echo "========================================================================="
echo "This test verifies that one broker failing does not stop other brokers."
echo ""

# Check which brokers are enabled
OANDA_ENABLED="${BROKER_OANDA_ENABLED:-0}"
COINBASE_ENABLED="${BROKER_COINBASE_ENABLED:-0}"
IBKR_ENABLED="${BROKER_IBKR_ENABLED:-0}"

ENABLED_COUNT=0
[[ "$OANDA_ENABLED" == "1" ]] && ((ENABLED_COUNT++))
[[ "$COINBASE_ENABLED" == "1" ]] && ((ENABLED_COUNT++))
[[ "$IBKR_ENABLED" == "1" ]] && ((ENABLED_COUNT++))

if [[ $ENABLED_COUNT -lt 2 ]]; then
  echo -e "${RED}✗${NC} Isolation test requires at least 2 brokers enabled"
  echo "   Currently enabled: $ENABLED_COUNT"
  echo "   Set BROKER_*_ENABLED=1 for at least 2 brokers"
  exit 1
fi

echo -e "${GREEN}✓${NC} Enabled brokers: $ENABLED_COUNT (sufficient for test)"
echo ""

# Start all enabled brokers
echo "Step 1: Starting all enabled brokers..."
./tools/start_full_system.sh
sleep 5

# Check heartbeats exist
echo ""
echo "Step 2: Verifying heartbeat files exist..."
for broker in oanda coinbase ibkr; do
  ENABLED_VAR="BROKER_${broker^^}_ENABLED"
  if [[ "${!ENABLED_VAR:-0}" == "1" ]]; then
    HEARTBEAT="ops/state/brokers/${broker}.json"
    if [[ -f "$HEARTBEAT" ]]; then
      echo -e "${GREEN}✓${NC} ${broker} heartbeat exists"
    else
      echo -e "${RED}✗${NC} ${broker} heartbeat missing"
      exit 1
    fi
  fi
done

# Pick a broker to kill (prefer coinbase since it's least critical)
VICTIM_BROKER="coinbase"
if [[ "${BROKER_COINBASE_ENABLED:-0}" != "1" ]]; then
  # Fallback to IBKR if Coinbase not enabled
  if [[ "${BROKER_IBKR_ENABLED:-0}" == "1" ]]; then
    VICTIM_BROKER="ibkr"
  else
    VICTIM_BROKER="oanda"  # Last resort (proven profitable, but test needs victim)
  fi
fi

echo ""
echo "Step 3: Killing ${VICTIM_BROKER} broker process..."
PID_FILE="ops/state/brokers/${VICTIM_BROKER}.pid"
if [[ -f "$PID_FILE" ]]; then
  PID=$(cat "$PID_FILE")
  kill -9 "$PID" 2>/dev/null || true
  echo -e "${YELLOW}⚠${NC} Killed ${VICTIM_BROKER} (PID=$PID)"
else
  echo -e "${RED}✗${NC} PID file not found: $PID_FILE"
  exit 1
fi

# Wait for orchestrator to detect failure
echo ""
echo "Step 4: Waiting 15 seconds for orchestrator to detect failure..."
sleep 15

# Check that other brokers still have recent heartbeats
echo ""
echo "Step 5: Verifying other brokers still running..."
PASS=true

for broker in oanda coinbase ibkr; do
  if [[ "$broker" == "$VICTIM_BROKER" ]]; then
    continue  # Skip victim
  fi
  
  ENABLED_VAR="BROKER_${broker^^}_ENABLED"
  if [[ "${!ENABLED_VAR:-0}" != "1" ]]; then
    continue  # Skip disabled
  fi
  
  HEARTBEAT="ops/state/brokers/${broker}.json"
  if [[ ! -f "$HEARTBEAT" ]]; then
    echo -e "${RED}✗${NC} ${broker} heartbeat file disappeared"
    PASS=false
    continue
  fi
  
  # Check heartbeat age (should be < 30 seconds old)
  TIMESTAMP=$(python3 - "$HEARTBEAT" <<'PY'
import sys, json
with open(sys.argv[1]) as f:
  data = json.load(f)
  print(data.get('timestamp', ''))
PY
)
  
  if [[ -z "$TIMESTAMP" ]]; then
    echo -e "${YELLOW}⚠${NC} ${broker} heartbeat has no timestamp"
    continue
  fi
  
  AGE_SEC=$(python3 - "$TIMESTAMP" <<'PY'
import sys
from datetime import datetime
ts_str = sys.argv[1].replace('Z', '+00:00')
ts = datetime.fromisoformat(ts_str)
now = datetime.utcnow()
print(int((now - ts.replace(tzinfo=None)).total_seconds()))
PY
)
  
  if [[ $AGE_SEC -lt 30 ]]; then
    echo -e "${GREEN}✓${NC} ${broker} heartbeat recent (${AGE_SEC}s old)"
  else
    echo -e "${RED}✗${NC} ${broker} heartbeat stale (${AGE_SEC}s old)"
    PASS=false
  fi
done

echo ""
echo "Step 6: Checking if orchestrator restarted victim broker..."
sleep 45  # Wait for orchestrator restart interval (60s default)

VICTIM_PID_FILE="ops/state/brokers/${VICTIM_BROKER}.pid"
if [[ -f "$VICTIM_PID_FILE" ]]; then
  NEW_PID=$(cat "$VICTIM_PID_FILE")
  if [[ "$NEW_PID" != "$PID" ]]; then
    echo -e "${GREEN}✓${NC} Orchestrator restarted ${VICTIM_BROKER} (new PID=$NEW_PID)"
  else
    echo -e "${YELLOW}⚠${NC} ${VICTIM_BROKER} PID unchanged (may still be old)"
  fi
else
  echo -e "${YELLOW}⚠${NC} ${VICTIM_BROKER} not restarted yet (orchestrator may be slow)"
fi

# Final result
echo ""
echo "========================================================================="
if $PASS; then
  echo -e "${GREEN}✓ ISOLATION TEST PASSED${NC}"
  echo "Other brokers continued running while victim was killed."
else
  echo -e "${RED}✗ ISOLATION TEST FAILED${NC}"
  echo "One or more brokers stopped when victim was killed."
  exit 1
fi
echo "========================================================================="
