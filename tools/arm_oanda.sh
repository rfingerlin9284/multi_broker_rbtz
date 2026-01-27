#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
REPO="$(cd "$(dirname "$SCRIPT_PATH")/.." && pwd)"
STATE_DIR="$REPO/ops/state"

# Find the preflight PASS marker (support a few names)
PASS_FILE=""
for f in \
  "$STATE_DIR/preflight_oanda.ok" \
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
echo "✅ ARMED: Trading enabled."
