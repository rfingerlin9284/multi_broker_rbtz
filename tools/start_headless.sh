#!/usr/bin/env bash
set -euo pipefail

# Simple helper to start the headless runner in the repository.
# This script assumes you have a venv at .venv and have installed requirements.

if [ ! -f ".venv/bin/activate" ]; then
  echo "Virtualenv not found. Create one: python3 -m venv .venv && . .venv/bin/activate && pip install -r MULTI_BROKER_PHOENIX/requirements.txt"
  exit 1
fi

. .venv/bin/activate
export PYTHONPATH="$PWD/MULTI_BROKER_PHOENIX:$PYTHONPATH"

# Run a simple headless runner that will start connectors and loop over price updates.
# Use mode=live or replay via env vars or args.
python - <<'PY'
from multi_broker_phoenix.tools.run_headless import run_headless
run_headless()
PY
