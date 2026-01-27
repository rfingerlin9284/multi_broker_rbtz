#!/usr/bin/env bash
# Manage engine trading mode (PAPER <-> LIVE) with PIN-gated enable
set -euo pipefail
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"
PIN_FILE="$HOME/.rbotzilla/live_pin.txt"

usage(){
  cat <<EOF
Usage: $0 status|enable --pin <PIN>|disable

Commands:
  status          Show current TRADING_MODE
  enable --pin    Enable LIVE mode (requires PIN stored in $PIN_FILE)
  disable         Set TRADING_MODE=PAPER

EOF
}

if [ "$#" -lt 1 ]; then
  usage
  exit 2
fi

CMD="$1"; shift
case "$CMD" in
  status)
    echo "TRADING_MODE=$(grep -E '^TRADING_MODE=' "$ENV_FILE" || true)" || true
    ;;
  enable)
    if [ "$#" -lt 2 ] || [ "$1" != "--pin" ]; then
      echo "Missing --pin argument"; usage; exit 2
    fi
    PIN="$2"
    if [ ! -f "$PIN_FILE" ]; then
      echo "PIN file missing: $PIN_FILE"; exit 1
    fi
    SAVED_PIN="$(cat "$PIN_FILE" | tr -d '\n')"
    if [ "$PIN" != "$SAVED_PIN" ]; then
      echo "Invalid PIN"; exit 1
    fi
    # Update .env and authoritative ops/state/mode.json
    if grep -q '^TRADING_MODE=' "$ENV_FILE"; then
      sed -i 's/^TRADING_MODE=.*/TRADING_MODE=LIVE/' "$ENV_FILE"
    else
      echo 'TRADING_MODE=LIVE' >> "$ENV_FILE"
    fi
    # Write authoritative mode file
    mkdir -p "$PROJECT_ROOT/ops/state"
    python3 - <<PY
import json, time
open('$PROJECT_ROOT/ops/state/mode.json','w').write(json.dumps({'mode':'LIVE','ts':time.time()}))
PY
    echo "TRADING_MODE set to LIVE in $ENV_FILE and ops/state/mode.json"

    # Enable live service and restart broker-link so it picks up LIVE env
    echo "Enabling rbotzilla-engine-live.service and restarting broker-link"
    sudo systemctl enable --now rbotzilla-engine-live.service
    sudo systemctl disable --now rbotzilla-engine-paper.service || true
    sudo systemctl restart rbotzilla-broker-link.service || true
    ;;
  disable)
    if grep -q '^TRADING_MODE=' "$ENV_FILE"; then
      sed -i 's/^TRADING_MODE=.*/TRADING_MODE=PAPER/' "$ENV_FILE"
    else
      echo 'TRADING_MODE=PAPER' >> "$ENV_FILE"
    fi
    mkdir -p "$PROJECT_ROOT/ops/state"
    python3 - <<PY
import json, time
open('$PROJECT_ROOT/ops/state/mode.json','w').write(json.dumps({'mode':'PAPER','ts':time.time()}))
PY
    echo "TRADING_MODE set to PAPER in $ENV_FILE and ops/state/mode.json"

    echo "Disabling live service and enabling paper engine"
    sudo systemctl disable --now rbotzilla-engine-live.service || true
    sudo systemctl enable --now rbotzilla-engine-paper.service || true
    sudo systemctl restart rbotzilla-broker-link.service || true
    ;;
  *)
    usage; exit 2
    ;;
esac
