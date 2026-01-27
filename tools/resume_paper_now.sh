#!/usr/bin/env bash
[[ -f tools/env_load.sh ]] && source tools/env_load.sh || true
export PYTHONPATH="${PWD}/DEPLOYMENT_PACKAGE:${PWD}:${PWD}/MULTI_BROKER_PHOENIX:${PYTHONPATH:-}"
# RBOTzilla Resume Paper Trading Now
#
# Purpose: Restart engine under deterministic env pipeline to resume PAPER trading.
#
# RULES:
# - NEVER prints secrets
# - Fails hard if env_doctor fails
# - Verifies proof-of-life ticks before declaring success
# - Keeps TRADING_MODE=PAPER
#
# Usage: bash tools/resume_paper_now.sh

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${RBOT_LOG_DIR:-$REPO/logs}"
LOG_FILE="${RBOT_LOG_FILE:-$LOG_DIR/engine_headless.log}"
STATE_DIR="$REPO/ops/state"
REPORT_JSON="$STATE_DIR/resume_paper_now.json"

ts() { date -Iseconds 2>/dev/null || date '+%Y-%m-%dT%H:%M:%S%z'; }
say() { echo "[$(ts)] $*"; }
die() { say "❌ $*"; exit 1; }

cd "$REPO" || die "repo not found: $REPO"
mkdir -p "$LOG_DIR" "$STATE_DIR"

say "========================================="
say " RBOTzilla Resume PAPER Trading"
say "========================================="
say ""

# 0) venv
if [[ -f "$REPO/.venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$REPO/.venv/bin/activate"
  say "✅ venv activated"
fi
say ""

# 1) env doctor - HARD FAIL if bad
say "========================================="
say " Step 1: Environment Validation"
say "========================================="
if ! bash tools/env_doctor.sh; then
  EXIT_CODE=$?
  say ""
  say "❌ env_doctor FAILED (exit code: $EXIT_CODE)"
  say "   Fix with: bash tools/bootstrap_secrets.sh"
  say "   Then retry: bash tools/resume_paper_now.sh"
  exit "$EXIT_CODE"
fi
say ""

# 2) load deterministic env
say "========================================="
say " Step 2: Load Deterministic Environment"
say "========================================="
[[ -x "tools/env_load.sh" ]] || die "tools/env_load.sh not executable"

# shellcheck disable=SC1091
source "tools/env_load.sh"
say "✅ Sourced tools/env_load.sh"

# Verify TRADING_MODE is PAPER
TRADING_MODE="${TRADING_MODE:-UNKNOWN}"
if [[ "$TRADING_MODE" != "PAPER" ]]; then
  die "TRADING_MODE=$TRADING_MODE (expected PAPER). Refusing to proceed."
fi
say "✅ TRADING_MODE=$TRADING_MODE (safe)"
say ""

# 3) bootstrap secrets (no-op if already exists, no secrets printed)
say "========================================="
say " Step 3: Bootstrap Secrets (if needed)"
say "========================================="
if [[ ! -f "ops/secrets.env" ]]; then
  say "⚠️  ops/secrets.env not found, running bootstrap..."
  bash tools/bootstrap_secrets.sh || die "bootstrap_secrets.sh failed"
else
  say "✅ ops/secrets.env exists"
fi
say ""

# 4) locate and stop old engine
say "========================================="
say " Step 4: Stop Old Engine"
say "========================================="
OLD_PID=""
for f in "ops/state/engine.pid" "engine.pid"; do
  if [[ -f "$f" ]]; then
    OLD_PID=$(cat "$f" 2>/dev/null || true)
    [[ -n "$OLD_PID" ]] && break
  fi
done

if [[ -z "$OLD_PID" ]]; then
  OLD_PID=$(pgrep -f "run_headless\.py.*--mode" | head -n1 || true)
fi

if [[ -n "$OLD_PID" ]] && ps -p "$OLD_PID" >/dev/null 2>&1; then
  say "Found running engine pid=$OLD_PID"
  say "Stopping (TERM → wait → KILL if needed)..."
  
  kill -TERM "$OLD_PID" 2>/dev/null || true
  
  for i in {1..30}; do
    if ps -p "$OLD_PID" >/dev/null 2>&1; then
      sleep 1
      [[ $((i % 5)) -eq 0 ]] && say "  waiting... ($i/30)"
    else
      say "✅ Process $OLD_PID terminated gracefully"
      break
    fi
  done
  
  if ps -p "$OLD_PID" >/dev/null 2>&1; then
    say "⚠️  Still alive after 30s; sending KILL"
    kill -KILL "$OLD_PID" 2>/dev/null || true
    sleep 1
  fi
else
  say "No running engine pid found"
fi

# Cleanup any stray processes
pkill -f "tools/run_headless\.py --mode oanda-only" 2>/dev/null || true
pkill -f "run_headless\.py --mode oanda-only" 2>/dev/null || true

sleep 2
say "✅ Stop phase complete"
say ""

# 5) start engine under deterministic env
say "========================================="
say " Step 5: Start Engine (PAPER mode)"
say "========================================="

RUN_HEADLESS=""
if [[ -f "MULTI_BROKER_PHOENIX/tools/run_headless.py" ]]; then
  RUN_HEADLESS="MULTI_BROKER_PHOENIX/tools/run_headless.py"
elif [[ -f "tools/run_headless.py" ]]; then
  RUN_HEADLESS="tools/run_headless.py"
else
  die "Could not find run_headless.py"
fi

# Re-source to ensure launched engine inherits correct env
# shellcheck disable=SC1091
source "tools/env_load.sh"

# Set PYTHONPATH to prefer deployment package (complete module set), then repo root
export PYTHONPATH="${PWD}/DEPLOYMENT_PACKAGE:${PWD}:${PWD}/MULTI_BROKER_PHOENIX:${PYTHONPATH:-}"

say "Launching: python3 -u $RUN_HEADLESS --mode oanda-only"
say "Log file: $LOG_FILE"
say "PYTHONPATH: $PYTHONPATH"

nohup python3 -u "$RUN_HEADLESS" --mode oanda-only >>"$LOG_FILE" 2>&1 &
NEW_PID=$!

echo "$NEW_PID" > "ops/state/engine.pid"
say "✅ Started engine pid=$NEW_PID"
say "   Waiting 10s for initialization..."
sleep 10
say ""

# 6) verify engine is alive
say "========================================="
say " Step 6: Verify Engine Process"
say "========================================="
if ps -p "$NEW_PID" >/dev/null 2>&1; then
  say "✅ Engine process $NEW_PID is alive"
else
  say "❌ Engine process $NEW_PID died immediately"
  say ""
  say "Last 50 log lines:"
  tail -50 "$LOG_FILE" || true
  exit 1
fi
say ""

# 7) proof-of-life: verify critical ticks
say "========================================="
say " Step 7: Proof-of-Life Verification"
say "========================================="
say "Waiting up to 60s for evidence of:"
say "  - WATCHDOG_UNFREEZE or trading_allowed"
say "  - EXIT_MANAGER_TICK"
say "  - PROTECT_LOOP_TICK"
say ""

watchdog_ok=0
exit_tick_ok=0
protect_tick_ok=0

deadline=$((SECONDS+60))
while (( SECONDS < deadline )); do
  if [[ -f "$LOG_FILE" ]]; then
    # Check for watchdog unfreeze or trading allowed
    if tail -n 500 "$LOG_FILE" 2>/dev/null | grep -qi "WATCHDOG.*UNFREEZE\|trading.*allowed"; then
      watchdog_ok=1
    fi
    
    # Check for exit manager tick
    if tail -n 500 "$LOG_FILE" 2>/dev/null | grep -q "EXIT_MANAGER_TICK"; then
      exit_tick_ok=1
    fi
    
    # Check for protect loop tick
    if tail -n 500 "$LOG_FILE" 2>/dev/null | grep -q "PROTECT_LOOP_TICK"; then
      protect_tick_ok=1
    fi
    
    # Break early if all found
    if [[ $watchdog_ok -eq 1 && $exit_tick_ok -eq 1 && $protect_tick_ok -eq 1 ]]; then
      say "✅ All critical ticks detected!"
      break
    fi
  fi
  sleep 2
done

say ""
say "Results:"
say "  Watchdog/Trading: $([[ $watchdog_ok -eq 1 ]] && echo '✅ OK' || echo '❌ MISSING')"
say "  EXIT_MANAGER_TICK: $([[ $exit_tick_ok -eq 1 ]] && echo '✅ FOUND' || echo '❌ MISSING')"
say "  PROTECT_LOOP_TICK: $([[ $protect_tick_ok -eq 1 ]] && echo '✅ FOUND' || echo '❌ MISSING')"
say ""

# 8) show recent log context
say "========================================="
say " Step 8: Recent Log Context"
say "========================================="
say "Last 100 log lines:"
say "---"
tail -n 100 "$LOG_FILE" 2>/dev/null | head -100 || say "(log not readable)"
say "---"
say ""

say "Critical events (last 100 matches):"
say "---"
grep -a "WATCHDOG.*FREEZE\|EXIT_MANAGER_TICK\|PROTECT_LOOP_TICK\|AttributeError\|ERROR\|Traceback" "$LOG_FILE" 2>/dev/null | tail -100 || say "(no matches)"
say "---"
say ""

# 9) determine verdict
verdict="FAIL"
if [[ $exit_tick_ok -eq 1 && $protect_tick_ok -eq 1 ]]; then
  verdict="PASS"
fi

say "========================================="
say " Step 9: Verdict"
say "========================================="
if [[ "$verdict" == "PASS" ]]; then
  say "✅ VERDICT: PASS"
  say "   - Engine restarted under deterministic env"
  say "   - Exit manager is alive"
  say "   - Protect loop is alive"
  say "   - PAPER trading infrastructure operational"
else
  say "❌ VERDICT: FAIL"
  say "   - Missing required proof-of-life ticks"
  say "   - Review logs above for errors"
fi
say ""

# 10) get env_state.json sha for report
ENV_STATE_SHA="unknown"
if [[ -f "ops/state/env_state.json" ]]; then
  ENV_STATE_SHA=$(sha256sum "ops/state/env_state.json" 2>/dev/null | cut -d' ' -f1 || echo "unknown")
fi

# 11) write report
say "========================================="
say " Step 10: Write Report"
say "========================================="

python3 - <<PY
import json, time, os, sys

report = {
  "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
  "repo": "$REPO",
  "mode": "oanda-only",
  "trading_mode": "$TRADING_MODE",
  "engine_pid": int("$NEW_PID"),
  "old_pid": "$OLD_PID" if "$OLD_PID" else None,
  "log_file": "$LOG_FILE",
  "env_state_sha256": "$ENV_STATE_SHA",
  "proof_of_life": {
    "watchdog_tick_seen": bool($watchdog_ok),
    "exit_tick_seen": bool($exit_tick_ok),
    "protect_tick_seen": bool($protect_tick_ok),
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

# 12) final instructions
say "========================================="
say " NEXT ACTIONS"
say "========================================="

if [[ "$verdict" == "PASS" ]]; then
  say "✅ Engine is healthy and operational"
  say ""
  say "PAPER trading is now active."
else
  say "❌ Engine started but proof-of-life verification FAILED"
  say ""
  say "Do not proceed until:"
  say "  1. EXIT_MANAGER_TICK appears in logs"
  say "  2. PROTECT_LOOP_TICK appears in logs"
  say "  3. No AttributeError or credential errors"
  say ""
  say "Review logs above and fix issues first."
fi

say ""
say "Report: $REPORT_JSON"
say "========================================="

if [[ "$verdict" == "PASS" ]]; then
  exit 0
else
  exit 1
fi
