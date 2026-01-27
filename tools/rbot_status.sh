#!/usr/bin/env bash
set -euo pipefail
ROOT="/home/ing/RICK/MULTI_BROKER_PHOENIX"

# Load environment deterministically
source "${ROOT}/tools/env_load.sh"
TOGGLES="$ROOT/config/toggles.env"
ENVFILE="$ROOT/.env"

echo "== TOGGLES =="
if [ -f "$TOGGLES" ]; then
  grep -E '^(ENABLE_|HEADLESS_MODE=|TRADING_MODE=|PRACTICE_TRADING_ALLOWED=|ALLOW_PRACTICE_ORDERS=|CONFIRM_PRACTICE_ORDER=|REQUIRE_|DISABLE_)' "$TOGGLES" || true
else
  echo "Missing: $TOGGLES"
fi

echo
echo "== KEYS (presence only, no secrets) =="
if [ -f "$ENVFILE" ]; then
  awk -F= '/^(XAI_API_KEY|DEEPSEEK_API_KEY|OPENAI_API_KEY|GROK_API_KEY)=/ {print $1"=" (length($2)>0 ? "[SET]" : "[EMPTY]")}' "$ENVFILE" || true
else
  echo "Missing: $ENVFILE"
fi

echo
echo "== OANDA CREDENTIALS =="
if [ -f "$ENVFILE" ]; then
  awk -F= '/^(OANDA_API_TOKEN|OANDA_ACCOUNT_ID|OANDA_API_URL)=/ {print $1"=" (length($2)>0 ? "[SET]" : "[EMPTY]")}' "$ENVFILE" || true
else
  echo "Missing: $ENVFILE"
fi

echo
echo "== OANDA BROKER PID =="
OANDA_PIDFILE="$ROOT/ops/state/brokers/oanda.pid"
if [ -f "$OANDA_PIDFILE" ]; then
  oanda_pid="$(cat "$OANDA_PIDFILE" || true)"
  if [ -n "${oanda_pid:-}" ] && kill -0 "$oanda_pid" 2>/dev/null; then
    echo "RUNNING: pid=$oanda_pid"
  else
    echo "STALE PIDFILE (not running): $OANDA_PIDFILE"
  fi
else
  echo "Not running (no oanda pidfile)."
fi
