#!/usr/bin/env bash
# Small wrapper to load the appropriate env file (per ~/.rbotzilla/mode_toggle)
# and exec the headless runner in the project directory.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENGINE_ROOT="$PROJECT_ROOT/MULTI_BROKER_PHOENIX"
MODE_FILE="$HOME/.rbotzilla/mode_toggle"
ENV_PAPER="$HOME/.rbotzilla/.env.paper"
ENV_LIVE="$HOME/.rbotzilla/.env.live"

# Default to PAPER if missing
MODE="PAPER"
if [ -f "$MODE_FILE" ]; then
  MODE=$(cat "$MODE_FILE" | tr -d '\n' | tr -d '\r' | tr '[:upper:]' '[:upper:]')
fi

if [ "$MODE" = "LIVE_REAL_MONEY" ]; then
  ENVFILE="$ENV_LIVE"
else
  ENVFILE="$ENV_PAPER"
fi

if [ ! -f "$ENVFILE" ]; then
  echo "⚠️  Env file $ENVFILE not found - refusing to overwrite environment. Exiting." >&2
  exit 1
fi

# Source environment (do not overwrite existing env vars from systemd); export all variables from file
set -a
# shellcheck disable=SC1090
. "$ENVFILE"
set +a

cd "$PROJECT_ROOT"
exec /usr/bin/env python3 "$ENGINE_ROOT/tools/run_headless.py" --mode oanda-only
