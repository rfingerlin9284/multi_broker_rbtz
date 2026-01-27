#!/usr/bin/env bash
set -euo pipefail
ROOT="/home/ing/RICK/MULTI_BROKER_PHOENIX"
cd "$ROOT"
source "$ROOT/.venv/bin/activate"

# Always run OANDA-only mode (NO platform-paper)
exec tools/py_venv.sh -u MULTI_BROKER_PHOENIX/tools/run_headless.py --mode oanda-only
