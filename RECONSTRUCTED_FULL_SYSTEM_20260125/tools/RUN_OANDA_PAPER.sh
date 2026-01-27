#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENGINE_ROOT="$ROOT/MULTI_BROKER_PHOENIX"
cd "$ROOT"
source "$ROOT/.venv/bin/activate"

# Always run OANDA-only mode (NO platform-paper)
exec tools/py_venv.sh -u "$ENGINE_ROOT/tools/run_headless.py" --mode oanda-only
