#!/usr/bin/env bash
# Deterministic AI seat status - prints JSON snapshot
# Usage: tools/tasks/ai_status.sh [--no-refresh]
set -euo pipefail

REPO="${REPO:-/home/ing/RICK/MULTI_BROKER_PHOENIX}"
cd "$REPO"

# Load environment deterministically
source "${REPO}/tools/env_load.sh"

_ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }
_commit() { git -C "$REPO" rev-parse HEAD 2>/dev/null || echo "UNKNOWN"; }

echo "{"
echo '  "timestamp": "'$(_ts)'",'
echo '  "commit": "'$(_commit)'",'

# Activate venv if present
if [[ -f "$REPO/.venv/bin/activate" ]]; then
    source "$REPO/.venv/bin/activate"
fi

# Check Ollama directly first
OLLAMA_OK="false"
OLLAMA_REASON="unchecked"
if curl -fsS --max-time 2 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
    OLLAMA_OK="true"
    OLLAMA_REASON="OK"
else
    OLLAMA_REASON="API_UNREACHABLE"
fi

echo '  "ollama_direct": {"ok": '$OLLAMA_OK', "reason": "'$OLLAMA_REASON'"},'

# Run Python router status
python3 - <<'PY'
import json
import sys
try:
    # Try the newer seat router first
    from multi_broker_phoenix.ai.seat_router import AISeatRouter
    router = AISeatRouter()
    router.refresh_health()
    snap = router.status_snapshot()
    print('  "router": ' + json.dumps(snap, sort_keys=True) + ',')
    healthy = router.healthy_count()
    min_req = router.require_min
    print(f'  "healthy_count": {healthy},')
    print(f'  "min_required": {min_req},')
    verdict = "PASS" if healthy >= min_req else "FAIL"
    print(f'  "verdict": "{verdict}"')
except Exception as e:
    # Fall back to ai_router
    try:
        from ai_router.router import AIRouter
        r = AIRouter().evaluate()
        print('  "router": ' + json.dumps(r, sort_keys=True) + ',')
        verdict = "PASS" if r.get("ai_ok") else "FAIL"
        print(f'  "verdict": "{verdict}"')
    except Exception as e2:
        print(f'  "error": "Import failed: {e} / {e2}",')
        print('  "verdict": "ERROR"')
PY

echo "}"
