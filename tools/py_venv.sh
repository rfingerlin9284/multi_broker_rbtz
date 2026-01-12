#!/usr/bin/env bash
set -euo pipefail

# ═══════════════════════════════════════════════════════════════════════════════
# 🐍 RBOTZILLA PYTHON WRAPPER
# ═══════════════════════════════════════════════════════════════════════════════
# Wrapper to ensure we always run using the workspace virtualenv and correct paths.
# Auto-protects against broken `.env` files (duplicate keys, missing keys).
#
# Usage:
#   ./tools/py_venv.sh script.py [args...]
#   ./tools/py_venv.sh -c "python code"
# ═══════════════════════════════════════════════════════════════════════════════

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Set PYTHONPATH to include core directories
export PYTHONPATH="${ROOT_DIR}/RBOTZILLA_CORE_EXTRACT:${ROOT_DIR}/hive_real:${ROOT_DIR}:${PYTHONPATH:-}"

# Use venv if available, otherwise system python
VENV_PY="$ROOT_DIR/.venv/bin/python3"
if [[ -x "$VENV_PY" ]]; then
  PY="$VENV_PY"
else
  PY="$(command -v python3)"
fi

# Auto-fix .env duplicates (keeps last occurrence active). Never prints secrets.
"$PY" "$ROOT_DIR/tools/env_preflight.py" --fix --quiet 2>/dev/null || true

exec "$PY" "$@"
