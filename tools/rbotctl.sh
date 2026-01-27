#!/usr/bin/env bash
# Simple helper CLI for rbotzilla service
# Usage: rbotctl.sh start|stop|restart|status|logs|mode paper|mode live_real_money|smoke

set -euo pipefail
SERVICE_NAME="rbotzilla"
UNIT="${SERVICE_NAME}.service"

cmd="$1"
shift || true

do_systemctl(){
  sudo systemctl "$@"
}

case "$cmd" in
  start|stop|restart|status)
    do_systemctl "$cmd" "$UNIT"
    ;;
  logs)
    echo "Tailing journal: sudo journalctl -u $UNIT -f"
    sudo journalctl -u "$UNIT" -f
    ;;
  mode)
    MODE="${1:-}"
    if [ -z "$MODE" ]; then
      echo "Usage: rbotctl.sh mode paper|live_real_money"
      exit 2
    fi
    # PIN gating: check ~/.rbotzilla/control_pin if present
    PIN_FILE="$HOME/.rbotzilla/control_pin"
    if [ -f "$PIN_FILE" ]; then
      read -s -p "Enter control PIN: " PIN_INPUT
      echo
      PIN_EXPECTED=$(cat "$PIN_FILE" | tr -d '\n' | tr -d '\r')
      if [ "$PIN_INPUT" != "$PIN_EXPECTED" ]; then
        echo "Incorrect PIN"
        exit 3
      fi
    else
      echo "⚠️  No PIN file at $PIN_FILE - proceeding without PIN (set to enable gating)"
    fi

    if [ "$MODE" = "paper" ]; then
      echo "PAPER" > "$HOME/.rbotzilla/mode_toggle"
      echo "Set mode to PAPER"
    elif [ "$MODE" = "live_real_money" ]; then
      echo "LIVE_REAL_MONEY" > "$HOME/.rbotzilla/mode_toggle"
      echo "Set mode to LIVE_REAL_MONEY"
    else
      echo "Unknown mode: $MODE"
      exit 2
    fi
    # Restart service to pick up new mode
    do_systemctl restart "$UNIT"
    ;;
  smoke)
    if [ -x "./tools/run_core_safety.sh" ]; then
      ./tools/run_core_safety.sh
    else
      echo "run_core_safety.sh not found or not executable"
      exit 2
    fi
    ;;
  *)
    echo "Usage: $0 start|stop|restart|status|logs|mode paper|mode live_real_money|smoke"
    exit 2
    ;;
esac
