#!/usr/bin/env bash
set -euo pipefail
pkill -f "MULTI_BROKER_PHOENIX/tools/run_headless.py" >/dev/null 2>&1 || true
echo "Stopped headless runner."
