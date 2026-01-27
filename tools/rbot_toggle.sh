#!/usr/bin/env bash
set -euo pipefail
ROOT="/home/ing/RICK/MULTI_BROKER_PHOENIX"
TOGGLES="$ROOT/config/toggles.env"

usage() {
  echo "Usage:"
  echo "  rbot_toggle.sh set KEY VALUE"
  echo "  rbot_toggle.sh on KEY"
  echo "  rbot_toggle.sh off KEY"
  echo "  rbot_toggle.sh show"
}

cmd="${1:-}"
key="${2:-}"
val="${3:-}"

mkdir -p "$ROOT/config"
touch "$TOGGLES"

case "$cmd" in
  show)
    echo "== $TOGGLES =="
    sed -n '1,220p' "$TOGGLES"
    ;;
  set)
    [ -n "${key:-}" ] && [ -n "${val:-}" ] || { usage; exit 2; }
    tmp="$(mktemp)"
    found=0
    while IFS= read -r line || [ -n "$line" ]; do
      if [[ "$line" =~ ^${key}= ]]; then
        echo "${key}=${val}" >> "$tmp"
        found=1
      else
        echo "$line" >> "$tmp"
      fi
    done < "$TOGGLES"
    if [ "$found" -eq 0 ]; then
      echo "${key}=${val}" >> "$tmp"
    fi
    mv "$tmp" "$TOGGLES"
    echo "SET: ${key}=${val}"
    ;;
  on)
    [ -n "${key:-}" ] || { usage; exit 2; }
    "$0" set "$key" "1"
    ;;
  off)
    [ -n "${key:-}" ] || { usage; exit 2; }
    "$0" set "$key" "0"
    ;;
  *)
    usage
    exit 2
    ;;
esac
