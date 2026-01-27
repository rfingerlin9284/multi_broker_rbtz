#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/ing/RICK/MULTI_BROKER_PHOENIX"
VENV="$ROOT/.venv"
ENVFILE="$ROOT/.env"
TOGGLES="$ROOT/config/toggles.env"
LOGDIR="$ROOT/logs"
ENGINE_LOG="$LOGDIR/engine_headless.log"
PIDFILE="$LOGDIR/engine.pid"
PYTHON_ENTRY="$ROOT/MULTI_BROKER_PHOENIX/tools/run_headless.py"
REQUIRED_KEYS=("OANDA_API_TOKEN" "OANDA_ACCOUNT_ID" "OANDA_API_URL")

echo "[PHASE 4] OANDA practice run helper"
echo "Runner entrypoint: python3 $PYTHON_ENTRY --mode oanda-only"
echo ".env loaded from: $ENVFILE"
echo "toggles file: $TOGGLES"

echo "Ensuring venv exists..."
if [ ! -d "$VENV" ]; then
  python3 -m venv "$VENV"
  echo "  → Created virtualenv at $VENV"
fi
# shellcheck disable=SC1090
source "$VENV/bin/activate"
echo "Activating $VENV"

if [ ! -f "$ENVFILE" ]; then
  echo "ERROR: Missing $ENVFILE. Please copy from .env.example and supply credentials."
  exit 1
fi

echo "Validating OANDA credentials..."
missing=()
for key in "${REQUIRED_KEYS[@]}"; do
  if ! grep -E -q "^${key}=[[:space:]]*[^[:space:]]" "$ENVFILE"; then
    missing+=("$key")
  fi
done

if [ ${#missing[@]} -gt 0 ]; then
  echo "ERROR: Missing required OANDA config lines in $ENVFILE"
  for key in "${missing[@]}"; do
    hint="  ${key}=<your-${key,,}>"
    if [ "$key" = "OANDA_API_URL" ]; then
      hint="  ${key}=https://api-fxpractice.oanda.com"
    fi
    echo "$hint"
  done
  exit 2
fi

echo "Enforcing toggles for OANDA-only practice..."
for pair in \
  "ENABLE_ENGINE=1" \
  "ENABLE_OANDA=1" \
  "ENABLE_COINBASE=0" \
  "ENABLE_IBKR=0" \
  "HEADLESS_MODE=oanda-only" \
  "TRADING_MODE=PAPER" \
  "PRACTICE_TRADING_ALLOWED=1" \
  "ALLOW_PRACTICE_ORDERS=1" \
  "CONFIRM_PRACTICE_ORDER=0" \
  "DISABLE_OPENAI=true" \
  "DISABLE_BROWSER_HIVE=true"; do
  key="${pair%%=*}"
  value="${pair#*=}"
  "$ROOT/tools/rbot_toggle.sh" set "$key" "$value" >/dev/null
done

echo "Starting OANDA practice engine via tools/rbot_start.sh..."
"$ROOT/tools/rbot_start.sh"

echo "Running status check..."
"$ROOT/tools/rbot_status.sh"

echo "Tailing logs for 60 seconds..."
mkdir -p "$LOGDIR"
touch "$ENGINE_LOG"
timeout 60 tail -n 200 -F "$ENGINE_LOG"

echo -n "ENGINE RUNNING"
if [ -f "$PIDFILE" ]; then
  pid="$(cat "$PIDFILE" || true)"
  if [ -n "${pid:-}" ]; then
    echo " pid=$pid"
    exit 0
  fi
fi
echo " (pid not found)"
exit 0
