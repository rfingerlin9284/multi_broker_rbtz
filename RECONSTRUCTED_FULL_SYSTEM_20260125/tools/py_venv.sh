#!/usr/bin/env bash
set -euo pipefail

# Wrapper to ensure we always run using the workspace virtualenv when present,
# and to auto-protect against broken `.env` files (duplicate keys, missing keys).

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

VENV_PY="$ROOT_DIR/.venv/bin/python3"
if [[ -x "$VENV_PY" ]]; then
  PY="$VENV_PY"
else
  PY="$(command -v python3)"
fi

# Auto-fix .env duplicates (keeps last occurrence active). Never prints secrets.
"$PY" "$ROOT_DIR/tools/env_preflight.py" --fix --quiet || true

exec "$PY" "$@"
