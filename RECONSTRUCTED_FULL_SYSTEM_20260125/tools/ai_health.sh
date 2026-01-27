#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.."; pwd)"

_ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }
_commit() { git -C "$ROOT" rev-parse HEAD 2>/dev/null || echo "UNKNOWN"; }
_toggles_hash() { sha256sum "$ROOT/config/toggles.env" 2>/dev/null | awk '{print $1}'; }

echo "timestamp=$(_ts)"
echo "commit=$(_commit)"
echo "toggles_hash=$(_toggles_hash)"

python3 - <<'PY'
from ai_router.router import AIRouter
import json
r = AIRouter().evaluate()
print(json.dumps(r, sort_keys=True))
print("PASS" if r.get("ai_ok") else "FAIL")
PY
