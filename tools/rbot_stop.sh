#!/usr/bin/env bash
set -euo pipefail
ROOT="/home/ing/RICK/MULTI_BROKER_PHOENIX"
PIDFILE="$ROOT/logs/engine.pid"

if [ -f "$PIDFILE" ]; then
  pid="$(cat "$PIDFILE" || true)"
  if [ -n "${pid:-}" ] && kill -0 "$pid" 2>/dev/null; then
    kill "$pid" || true
    sleep 0.5
    if kill -0 "$pid" 2>/dev/null; then
      kill -9 "$pid" || true
    fi
    echo "STOPPED: pid=$pid"
  else
    echo "Not running (stale pidfile)."
  fi
  rm -f "$PIDFILE"
else
  echo "Not running (no pidfile)."
fi

pkill -f "MULTI_BROKER_PHOENIX/tools/run_headless.py" >/dev/null 2>&1 || true
