#!/usr/bin/env bash
set -euo pipefail

REPO="/home/ing/RICK/MULTI_BROKER_PHOENIX"
TOOLS="$REPO/tools"
STATE_DIR="$REPO/ops/state"

# Accept PIN as:
# 1) arg1
# 2) env RBOTZILLA_GUARD_PIN
PIN="${1:-${RBOTZILLA_GUARD_PIN:-}}"

# Find the preflight PASS marker (support a few names)
PASS_FILE=""
for f in \
  "$STATE_DIR/oanda_preflight.pass" \
  "$STATE_DIR/preflight_oanda.pass" \
  "$STATE_DIR/oanda_preflight.PASS" \
; do
  [[ -f "$f" ]] && PASS_FILE="$f" && break
done

if [[ -z "$PASS_FILE" ]]; then
  echo "❌ Error: No preflight PASS marker found in $STATE_DIR"
  echo "   Run: ./tools/start_full_system.sh (it auto-runs preflight)"
  exit 1
fi

# Freshness check (default 10 minutes)
MAX_AGE_SEC="${MAX_AGE_SEC:-600}"
NOW="$(date +%s)"
MTIME="$(stat -c %Y "$PASS_FILE" 2>/dev/null || echo 0)"
AGE="$(( NOW - MTIME ))"

if (( AGE > MAX_AGE_SEC )); then
  echo "❌ Preflight PASS is too old (${AGE}s). Re-run start_full_system.sh to refresh."
  exit 1
fi

echo "✅ Fresh preflight PASS detected (${AGE}s old). Arming trading..."

# Must have guardctl
if [[ ! -x "$TOOLS/guardctl.sh" ]]; then
  echo "❌ Error: $TOOLS/guardctl.sh missing or not executable"
  exit 1
fi

# Prompt for PIN if not provided
if [[ -z "$PIN" ]]; then
  # Terminal prompt (for manual runs)
  read -r -s -p "Enter Guard PIN: " PIN
  echo
fi

# Basic sanity: digits only (don’t be strict about length)
if [[ ! "$PIN" =~ ^[0-9]+$ ]]; then
  echo "❌ Error: PIN must be numeric"
  exit 1
fi

# Unlock
"$TOOLS/guardctl.sh" unlock "$PIN"

echo "✅ ARMED: Guard unlocked, trading enabled."
