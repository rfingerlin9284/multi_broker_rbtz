#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
REPO="$(cd "$(dirname "$SCRIPT_PATH")/.." && pwd)"
STATE_DIR="$REPO/ops/state"
STAMP_OK="$STATE_DIR/preflight_oanda.ok"
STAMP_JSON="$STATE_DIR/preflight_oanda.json"

# Canonical runtime paths (prefer repo-local, fallback to legacy paths)
ENGINE_LOG="$REPO/logs/oanda/engine.log"
ENGINE_LOG_LEGACY="/home/ing/RICK/logs/oanda/engine.log"
HB_PRIMARY="$REPO/ops/state/brokers/oanda.json"
HB_LEGACY="/home/ing/RICK/ops/state/brokers/oanda.json"

mkdir -p "$STATE_DIR"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

pass() { echo -e "${GREEN}✅ PASS${NC} $*"; }
warn() { echo -e "${YELLOW}⚠️  WARN${NC} $*"; }
fail() { echo -e "${RED}❌ FAIL${NC} $*"; }

FAILS=0
STEP() { echo -e "\n— $*"; }

STEP "Preflight: Python import sanity"
if python3 -c "import multi_broker_phoenix; from multi_broker_phoenix.core.interfaces import OCOOrder; o=OCOOrder(symbol='EUR_USD',entry_side='BUY',entry_quantity=1,take_profit_price=1.1,stop_loss_price=1.0); assert o.validate()[0]" >/dev/null 2>&1; then
  pass "Core imports + OCOOrder validate"
else
  fail "Python imports/OCOOrder failed"
  FAILS=$((FAILS+1))
fi

STEP "Preflight: OANDA runner process present"
# Wait up to 60s for runner to appear (start_full_system.sh triggers orchestrator → start_broker)
found_pid=""
for i in $(seq 1 60); do
  found_pid="$(pgrep -f "multi_broker_phoenix.runners.oanda_runner" | head -n 1 || true)"
  [[ -n "$found_pid" ]] && break
  sleep 1
done
if [[ -n "$found_pid" ]]; then
  pass "OANDA runner PID=$found_pid"
else
  fail "OANDA runner not detected after 60s"
  FAILS=$((FAILS+1))
fi

STEP "Preflight: Heartbeat file updates"
HB=""
if [[ -f "$HB_PRIMARY" ]]; then HB="$HB_PRIMARY"; fi
if [[ -z "$HB" && -f "$HB_LEGACY" ]]; then HB="$HB_LEGACY"; fi

if [[ -n "$HB" ]]; then
  pass "Heartbeat exists: $HB"
else
  fail "Heartbeat missing (expected $HB1 or $HB2)"
  FAILS=$((FAILS+1))
fi

STEP "Preflight: Log checks (no known fatal regressions)"
if [[ -f "$ENGINE_LOG" ]]; then
  pass "Engine log exists: $ENGINE_LOG"
  # Last 600 lines should NOT include these classic faceplants
  tail -n 600 "$ENGINE_LOG" | grep -qi "ModuleNotFoundError: No module named 'multi_broker_phoenix'" && { fail "ModuleNotFoundError detected"; FAILS=$((FAILS+1)); } || pass "No ModuleNotFoundError"
  tail -n 600 "$ENGINE_LOG" | grep -qi "attribute 'token'" && { fail "Token AttributeError detected"; FAILS=$((FAILS+1)); } || pass "No token AttributeError"
  tail -n 600 "$ENGINE_LOG" | grep -q "Gate checks: ✅ ALL PASS" && pass "Gate checks show ALL PASS" || { warn "No 'Gate checks: ✅ ALL PASS' found yet (may be early)"; }
elif [[ -f "$ENGINE_LOG_LEGACY" ]]; then
  ENGINE_LOG="$ENGINE_LOG_LEGACY"
  pass "Engine log exists: $ENGINE_LOG"
  tail -n 600 "$ENGINE_LOG" | grep -qi "ModuleNotFoundError: No module named 'multi_broker_phoenix'" && { fail "ModuleNotFoundError detected"; FAILS=$((FAILS+1)); } || pass "No ModuleNotFoundError"
  tail -n 600 "$ENGINE_LOG" | grep -qi "attribute 'token'" && { fail "Token AttributeError detected"; FAILS=$((FAILS+1)); } || pass "No token AttributeError"
  tail -n 600 "$ENGINE_LOG" | grep -q "Gate checks: ✅ ALL PASS" && pass "Gate checks show ALL PASS" || { warn "No 'Gate checks: ✅ ALL PASS' found yet (may be early)"; }
else
  fail "Engine log missing: $ENGINE_LOG (and legacy path)"
  FAILS=$((FAILS+1))
fi

STEP "Preflight: PROTECT_LOOP healthy (errors=0)"
if [[ -f "$ENGINE_LOG" ]]; then
  last_ticks="$(tail -n 800 "$ENGINE_LOG" | grep -E "PROTECT_LOOP_TICK" | tail -n 5 || true)"
  if [[ -z "$last_ticks" ]]; then
    warn "No PROTECT_LOOP_TICK lines found yet (may be early)"
  else
    bad="$(echo "$last_ticks" | grep -v "errors=0" || true)"
    if [[ -z "$bad" ]]; then
      pass "Last PROTECT_LOOP ticks show errors=0"
    else
      fail "Some recent PROTECT_LOOP ticks show errors≠0"
      echo "$bad" | sed -n '1,8p'
      FAILS=$((FAILS+1))
    fi
  fi
fi

echo
if [[ "$FAILS" -eq 0 ]]; then
  pass "PRE-FLIGHT: ALL TESTS PASSED"
  now_iso="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  now_epoch="$(date +%s)"
  cat > "$STAMP_JSON" <<JSON
{
  "broker": "oanda",
  "result": "PASS",
  "timestamp_utc": "$now_iso",
  "epoch": $now_epoch
}
JSON
  echo "$now_epoch" > "$STAMP_OK"
  echo
  echo -e "${GREEN}✅ OK TO ARM:${NC} Run 'RBOTzilla: 🟢 Arm OANDA (Enable Trading)' task"
  exit 0
else
  fail "PRE-FLIGHT: FAILED ($FAILS failures). NOT OK TO ARM."
  now_iso="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  now_epoch="$(date +%s)"
  cat > "$STAMP_JSON" <<JSON
{
  "broker": "oanda",
  "result": "FAIL",
  "timestamp_utc": "$now_iso",
  "epoch": $now_epoch,
  "failures": $FAILS
}
JSON
  rm -f "$STAMP_OK" >/dev/null 2>&1 || true
  exit 1
fi
