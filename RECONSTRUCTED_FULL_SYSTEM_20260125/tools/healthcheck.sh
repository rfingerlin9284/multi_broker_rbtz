#!/usr/bin/env bash
# Simple GO/NO-GO healthcheck for core services and broker link heartbeat
set -euo pipefail
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STATE_DIR="$PROJECT_ROOT/ops/state"
HB_FILE="$STATE_DIR/broker_link.json"
ENGINE_HB="$STATE_DIR/engine_heartbeat.json"

# Helper
fail(){ echo "FAIL: $1"; exit 2; }
pass(){ echo "PASS: $1"; }

# 1) systemd services
for svc in rbotzilla-broker-link rbotzilla-engine-paper; do
  if ! systemctl is-active --quiet $svc; then
    fail "$svc inactive"
  else
    pass "$svc active"
  fi
done

# 2) Broker link heartbeat
if [ ! -f "$HB_FILE" ]; then
  fail "broker state missing: $HB_FILE"
fi
age=$(python3 - <<PY
import json,time
s=json.load(open('$HB_FILE'))
print(int(time.time()- (s.get('last_heartbeat') or 0)))
PY
)
if [ "$age" -gt 120 ]; then
  fail "broker last_heartbeat too old: ${age}s"
else
  pass "broker last_heartbeat recent: ${age}s"
fi

# 3) Engine heartbeat
if [ ! -f "$ENGINE_HB" ]; then
  fail "engine heartbeat missing: $ENGINE_HB"
fi
eng_age=$(python3 - <<PY
import json,time
s=json.load(open('$ENGINE_HB'))
print(int(time.time()- (s.get('ts') or 0)))
PY
)
if [ "$eng_age" -gt 60 ]; then
  fail "engine heartbeat too old: ${eng_age}s"
else
  pass "engine heartbeat recent: ${eng_age}s"
fi

# 4) Mode check (paper default)
mode=$(python3 - <<PY
import json,os
p='$PROJECT_ROOT/ops/state/mode.json'
if not os.path.exists(p):
    print('PAPER')
else:
    print(json.load(open(p)).get('mode','PAPER'))
PY
)
if [ "$mode" != "PAPER" ]; then
  echo "WARN: mode=$mode (expected PAPER)."; exit 1
else
  pass "mode=$mode"
fi

# 5) Hive check if live
if [ "$mode" = "LIVE" ]; then
  if [ ! -f "$PROJECT_ROOT/ops/state/hive.json" ]; then
    fail "live mode but hive.json missing"
  fi
  hive_ok=$(python3 - <<PY
import json
s=json.load(open('$PROJECT_ROOT/ops/state/hive.json'))
print('1' if s.get('hive_confirmed') else '0')
PY
)
  if [ "$hive_ok" != "1" ]; then
    fail "HIVE confirmation failed"
  else
    pass "HIVE confirmation OK"
  fi
fi

echo "ALL CHECKS PASSED"
exit 0
