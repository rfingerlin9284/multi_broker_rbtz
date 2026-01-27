#!/usr/bin/env bash
# Run core safety tests which gate deployment
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTEST_BIN=".venv_pytest/bin/pytest"
if [[ ! -x "$PYTEST_BIN" ]]; then
  echo "⚠️  Pytest not found at $PYTEST_BIN - ensure you run tests in the venv (.venv_pytest)"
  exit 1
fi
export PYTHONPATH="$REPO_ROOT/MULTI_BROKER_PHOENIX"
echo "== Running core safety tests =="
$PYTEST_BIN -q tests/test_core_safety.py
echo "== Running watchdog, pnl_kill_switch and oco freeze smoke tests =="
$PYTEST_BIN -q tests/test_watchdog.py tests/test_pnl_kill_switch.py tests/test_smoke_oco_freeze.py

echo "== Running EDGE pack (fast) =="
$PYTEST_BIN -q tests/edge_pack -q

echo "✅ Core safety + EDGE tests passed"