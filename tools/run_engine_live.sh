#!/usr/bin/env bash
# Start engine in LIVE mode. This script should only be run by engine_mode.sh after PIN has been validated.
set -euo pipefail
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"
export TRADING_MODE="LIVE"
exec python3 tools/run_headless.py --mode platform-paper
