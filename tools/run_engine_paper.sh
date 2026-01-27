#!/usr/bin/env bash
# Start the headless paper engine (depends on broker-link)
set -euo pipefail
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"
# Use existing runner with mode set to platform-paper to prefer real connectors in PAPER
export TRADING_MODE="PAPER"
exec python3 tools/run_headless.py --mode platform-paper
