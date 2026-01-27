#!/usr/bin/env bash
# Test gate failure handling - ensure gates work and broker PAUSEs correctly
# Usage: ./test_gates.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "========================================================================="
echo "GATE FAILURE TEST"
echo "========================================================================="
echo "This test verifies gates fail appropriately and broker PAUSEs."
echo ""

# Test 1: Invalid API credentials (CONNECTIVITY gate should fail)
echo "Test 1: CONNECTIVITY gate with invalid credentials..."
echo "   (Simulated - would require temporarily breaking .env)"
echo -e "${YELLOW}⚠${NC} Manual test: Set invalid OANDA_API_TOKEN and verify broker stays PAUSED"
echo ""

# Test 2: OCO_READINESS gate  (Coinbase should FAIL without emulated OCO)
echo "Test 2: OCO_READINESS gate for Coinbase..."

if [[ "${BROKER_COINBASE_ENABLED:-0}" == "1" ]]; then
  COINBASE_EMULATED="${COINBASE_EMULATED_OCO:-false}"
  
  if [[ "$COINBASE_EMULATED" == "true" ]]; then
    echo -e "${YELLOW}⚠${NC} Coinbase has emulated OCO enabled"
    echo "   OCO_READINESS gate may PASS (test inconclusive)"
  else
    echo -e "${GREEN}✓${NC} Coinbase emulated OCO disabled"
    echo "   Checking if broker stays PAUSED..."
    
    # Check heartbeat state
    sleep 10
    HEARTBEAT="ops/state/brokers/coinbase.json"
    
    if [[ -f "$HEARTBEAT" ]]; then
      STATE=$(python3 - "$HEARTBEAT" <<'PY'
import sys, json
with open(sys.argv[1]) as f:
  data = json.load(f)
  print(data.get('state', 'unknown'))
PY
)
      
      if [[ "$STATE" == "PAUSED" ]]; then
        echo -e "${GREEN}✓${NC} Coinbase broker is PAUSED (expected due to OCO gate failure)"
      elif [[ "$STATE" == "STARTING" ]]; then
        echo -e "${YELLOW}⚠${NC} Coinbase broker still STARTING (wait longer)"
      else
        echo -e "${RED}✗${NC} Coinbase broker is $STATE (should be PAUSED)"
      fi
    else
      echo -e "${YELLOW}⚠${NC} Coinbase heartbeat not found (broker may not be running)"
    fi
  fi
else
  echo -e "${YELLOW}⚠${NC} Coinbase broker disabled (skipping OCO test)"
fi

echo ""

# Test 3: Check gate results in heartbeat files
echo "Test 3: Inspecting gate_status in heartbeat files..."
for broker in oanda coinbase ibkr; do
  ENABLED_VAR="BROKER_${broker^^}_ENABLED"
  if [[ "${!ENABLED_VAR:-0}" != "1" ]]; then
    continue
  fi
  
  HEARTBEAT="ops/state/brokers/${broker}.json"
  if [[ ! -f "$HEARTBEAT" ]]; then
    echo -e "${YELLOW}⚠${NC} ${broker}: No heartbeat file"
    continue
  fi
  
  python3 - "$broker" "$HEARTBEAT" <<'PY'
import sys, json
broker = sys.argv[1]
with open(sys.argv[2]) as f:
  data = json.load(f)
  gates = data.get('gate_status', {})
  
  print(f"\n{broker.upper()} gate results:")
  for gate_name, result in gates.items():
    status = "✅ PASS" if result.get('passed') else "❌ FAIL"
    reason = result.get('reason', 'OK')
    print(f"   {status} {gate_name}: {reason}")
PY

done

echo ""
echo "========================================================================="
echo -e "${GREEN}✓ GATE TEST COMPLETE${NC}"
echo "Review output above to verify gate behavior matches expectations."
echo "========================================================================="
