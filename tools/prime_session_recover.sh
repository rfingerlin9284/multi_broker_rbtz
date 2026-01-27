#!/usr/bin/env bash
# RBOTzilla Prime Session Recover
# 
# Purpose: Restart engine under deterministic env pipeline with proof-of-life verification.
# 
# CRITICAL RULES:
# 1. NEVER prints secrets (strict allowlist only)
# 2. Fails hard if env_doctor fails or proof-of-life missing
# 3. Writes machine-readable report to ops/state/prime_session_recover.json
#
# Usage:
#   bash tools/prime_session_recover.sh [MODE]
#   MODE defaults to 'oanda-only' if not specified

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="${1:-${RBOT_MODE:-oanda-only}}"

LOG_DIR="${RBOT_LOG_DIR:-$REPO/logs}"
LOG_FILE="${RBOT_LOG_FILE:-$LOG_DIR/engine_headless.log}"
STATE_DIR="$REPO/ops/state"
REPORT_JSON="$STATE_DIR/prime_session_recover.json"

# Only show safe keys; never dump full env (it will contain secrets).
ALLOWLIST_REGEX='^(REQUIRE_(XAI|DEEPSEEK|OPENAI|OLLAMA|SEATS_MIN|AI)|MIN_BRAIN_SEATS|TRADING_MODE|HEADLESS_MODE|ENABLE_(ENGINE|HIVE|OANDA))='

ts() { date -Iseconds 2>/dev/null || date '+%Y-%m-%dT%H:%M:%S%z'; }
say() { echo "[$(ts)] $*"; }
die() { say "❌ $*"; exit 1; }

cd "$REPO" || die "repo not found: $REPO"
mkdir -p "$LOG_DIR" "$STATE_DIR"

say "========================================="
say " RBOTzilla Prime Session Recover"
say "========================================="
say "repo=$REPO"
say "mode=$MODE"
say "log=$LOG_FILE"
say "report=$REPORT_JSON"
say ""

# 0) venv (optional)
if [[ -f "$REPO/.venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$REPO/.venv/bin/activate"
  say "✅ venv activated"
else
  say "⚠️  venv not found (continuing without it)"
fi
say ""

# 1) env sanity - HARD FAIL if env_doctor fails
say "========================================="
say " Step 1: Environment Doctor"
say "========================================="
[[ -x "tools/env_doctor.sh" ]] || die "tools/env_doctor.sh not found/executable"

if bash tools/env_doctor.sh; then
  say "✅ env_doctor PASS"
else
  EXIT_CODE=$?
  say "❌ env_doctor FAIL (exit code: $EXIT_CODE)"
  say ""
  say "STOP: Environment has duplicates or missing required keys."
  say "Fix with: bash tools/bootstrap_secrets.sh"
  say "Then re-run: bash tools/prime_session_recover.sh"
  exit "$EXIT_CODE"
fi
say ""

# 2) deterministic env snapshot (safe allowlist only)
say "========================================="
say " Step 2: Load Deterministic Environment"
say "========================================="
[[ -x "tools/env_load.sh" ]] || die "tools/env_load.sh not found/executable"

# shellcheck disable=SC1091
source "tools/env_load.sh"
say "✅ Sourced tools/env_load.sh"
say ""
say "Deterministic env snapshot (allowlist only):"
env | grep -E "$ALLOWLIST_REGEX" | sort || say "  (no matching keys)"
say ""

# 3) locate running engine pid (pidfile → pgrep fallback)
say "========================================="
say " Step 3: Locate Running Engine"
say "========================================="
PID=""
for f in "ops/state/engine.pid" "engine.pid"; do
  if [[ -f "$f" ]]; then
    PID="$(cat "$f" 2>/dev/null || true)"
    [[ -n "$PID" ]] && break
  fi
done

if [[ -z "$PID" ]]; then
  PID="$(pgrep -f "run_headless\.py.*--mode" | head -n1 || true)"
fi

if [[ -n "$PID" ]] && ps -p "$PID" >/dev/null 2>&1; then
  say "Found running engine pid=$PID"
  say ""
  say "Engine env snapshot (allowlist only; may be STALE):"
  # /proc/<pid>/environ includes secrets. Never print it raw. Filter strictly.
  tr '\0' '\n' <"/proc/${PID}/environ" 2>/dev/null | grep -E "$ALLOWLIST_REGEX" | sort || say "  (no matching keys)"
else
  say "No running engine pid found (or pid not alive)."
  PID=""
fi
say ""

# 4) AI status (optional)
say "========================================="
say " Step 4: AI Health Check"
say "========================================="
if [[ -x "tools/tasks/ai_status.sh" ]]; then
  bash tools/tasks/ai_status.sh || say "⚠️  ai_status.sh failed (continuing)"
elif [[ -f "tools/ai_status.py" ]]; then
  python3 tools/ai_status.py || say "⚠️  ai_status.py failed (continuing)"
else
  say "⚠️  ai_status script not found (skipping)"
fi
say ""

# 5) stop old engine (best effort)
say "========================================="
say " Step 5: Stop Old Engine"
say "========================================="
if [[ -n "$PID" ]]; then
  say "Stopping engine pid=$PID (TERM → wait → KILL if needed)"
  kill -TERM "$PID" 2>/dev/null || true
  
  for i in {1..30}; do
    if ps -p "$PID" >/dev/null 2>&1; then
      sleep 1
      [[ $((i % 5)) -eq 0 ]] && say "  waiting... ($i/30)"
    else
      say "✅ Process $PID terminated gracefully"
      break
    fi
  done
  
  if ps -p "$PID" >/dev/null 2>&1; then
    say "⚠️  Still alive after 30s; sending KILL"
    kill -KILL "$PID" 2>/dev/null || true
    sleep 1
  fi
else
  say "No running engine pid to stop"
fi

# Also kill any narrow matches of the exact mode
pkill -f "tools/run_headless\.py --mode ${MODE}" 2>/dev/null || true
pkill -f "run_headless\.py --mode ${MODE}" 2>/dev/null || true

# Wait a moment for cleanup
sleep 2
say "✅ Stop phase complete"
say ""

# 6) start engine under deterministic env pipeline
say "========================================="
say " Step 6: Start Engine Under env_load.sh"
say "========================================="

RUN_HEADLESS=""
if [[ -f "tools/run_headless.py" ]]; then
  RUN_HEADLESS="tools/run_headless.py"
elif [[ -f "MULTI_BROKER_PHOENIX/tools/run_headless.py" ]]; then
  RUN_HEADLESS="MULTI_BROKER_PHOENIX/tools/run_headless.py"
else
  die "Could not find run_headless.py (looked in tools/ and MULTI_BROKER_PHOENIX/tools/)"
fi

# Re-source env_load so the launched engine inherits the correct deterministic env.
# shellcheck disable=SC1091
source "tools/env_load.sh"

say "Launching: python3 -u $RUN_HEADLESS --mode $MODE"
say "Log file: $LOG_FILE"

nohup python3 -u "$RUN_HEADLESS" --mode "$MODE" >>"$LOG_FILE" 2>&1 &
NEWPID=$!

# Write PID file
echo "$NEWPID" > "ops/state/engine.pid"

say "✅ Started engine pid=$NEWPID"
say "   Waiting 5s for initialization..."
sleep 5
say ""

# 7) proof-of-life: require exit + protect loop ticks
need1="EXIT_MANAGER_TICK"
need2="PROTECT_LOOP_TICK"
found1=0
found2=0

say "========================================="
say " Step 7: Proof-of-Life Verification"
say "========================================="
say "Waiting up to 60s for:"
say "  - $need1"
say "  - $need2"
say ""

deadline=$((SECONDS+60))
while (( SECONDS < deadline )); do
  if [[ -f "$LOG_FILE" ]]; then
    tail -n 500 "$LOG_FILE" 2>/dev/null | grep -q "$need1" && found1=1 || true
    tail -n 500 "$LOG_FILE" 2>/dev/null | grep -q "$need2" && found2=1 || true
    
    if [[ $found1 -eq 1 && $found2 -eq 1 ]]; then
      say "✅ Both ticks detected!"
      break
    fi
  fi
  sleep 2
done

say ""
say "Results:"
say "  EXIT_MANAGER_TICK: $([[ $found1 -eq 1 ]] && echo '✅ FOUND' || echo '❌ MISSING')"
say "  PROTECT_LOOP_TICK: $([[ $found2 -eq 1 ]] && echo '✅ FOUND' || echo '❌ MISSING')"
say ""

# 8) show recent log context
say "========================================="
say " Step 8: Recent Log Context"
say "========================================="
say "Last 140 log lines:"
say "---"
tail -n 140 "$LOG_FILE" 2>/dev/null || say "(log file not readable)"
say "---"
say ""

say "Critical events (last 100 matches):"
say "---"
grep -E "WATCHDOG_UNFREEZE|WATCHDOG.*FREEZE|$need1|$need2|_TRADING_ALLOWED|QUARANTINE|AUTH.*FAIL|ERROR|Traceback" "$LOG_FILE" 2>/dev/null | tail -100 || say "(no matches)"
say "---"
say ""

# 9) verdict
verdict="FAIL"
[[ $found1 -eq 1 && $found2 -eq 1 ]] && verdict="PASS"

say "========================================="
say " Step 9: Verdict"
say "========================================="
if [[ "$verdict" == "PASS" ]]; then
  say "✅ VERDICT: PASS"
  say "   - Engine restarted under deterministic env"
  say "   - Exit manager is alive"
  say "   - Protect loop is alive"
else
  say "❌ VERDICT: FAIL"
  say "   - Missing required proof-of-life ticks"
fi
say ""

# 10) write report JSON (no jq required)
say "========================================="
say " Step 10: Write Report"
say "========================================="

python3 - <<PY
import json, time, os, sys

report = {
  "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
  "repo": "$REPO",
  "mode": "$MODE",
  "pid": int("$NEWPID"),
  "old_pid": "$PID" if "$PID" else None,
  "log_file": "$LOG_FILE",
  "proof_of_life": {
    "EXIT_MANAGER_TICK": bool($found1),
    "PROTECT_LOOP_TICK": bool($found2),
  },
  "verdict": "$verdict",
}

path = "$REPORT_JSON"
os.makedirs(os.path.dirname(path), exist_ok=True)

try:
  with open(path, "w") as f:
    json.dump(report, f, indent=2)
  print(f"✅ Report written: {path}")
except Exception as e:
  print(f"❌ Failed to write report: {e}", file=sys.stderr)
  sys.exit(1)
PY

say ""

# 11) next actions
say "========================================="
say " NEXT ACTIONS"
say "========================================="
say ""
say "Report saved to: $REPORT_JSON"
say ""

if [[ "$verdict" == "PASS" ]]; then
  say "========================================="
  say " ✅ RECOVERY COMPLETE"
  say "========================================="
  exit 0
else
  say "========================================="
  say " ❌ RECOVERY INCOMPLETE"
  say "========================================="
  say "Engine started but proof-of-life verification failed."
  say "Review logs and fix issues before proceeding."
  exit 1
fi
