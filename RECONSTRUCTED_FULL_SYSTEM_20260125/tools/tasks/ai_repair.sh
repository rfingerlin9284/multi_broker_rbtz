#!/usr/bin/env bash
# Trigger AI repair scan once (cooldown check, provider probe)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="${REPO:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
cd "$REPO"

# Load environment deterministically
source "${REPO}/tools/env_load.sh"

_ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }

echo "{"
echo '  "timestamp": "'$(_ts)'",'
echo '  "action": "AI_REPAIR_TRIGGER",'

# Activate venv if present
if [[ -f "$REPO/.venv/bin/activate" ]]; then
    source "$REPO/.venv/bin/activate"
fi

# Run the existing ai_repair.sh if it exists
if [[ -x "$REPO/tools/ai_repair.sh" ]]; then
    echo '  "method": "ai_repair.sh",'
    # Capture output
    OUTPUT=$("$REPO/tools/ai_repair.sh" 2>&1) || true
    # Escape for JSON
    OUTPUT_ESC=$(echo "$OUTPUT" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')
    echo "  \"output\": $OUTPUT_ESC,"
    echo '  "ok": true'
else
    # Fallback: run Python repair logic directly
    python3 - <<'PY'
import json
import os
import time
from pathlib import Path

STATE_FILE = os.getenv('AI_REPAIR_STATE_FILE', 'ops/state/ai_repair_state.json')
MIN_INTERVAL = int(os.getenv('AI_REPAIR_MIN_INTERVAL', '300'))

# Read last repair time
last_ts = 0.0
try:
    with open(STATE_FILE, 'r') as f:
        last_ts = float(json.load(f).get('last_ts', 0.0))
except:
    pass

now = time.time()
if now - last_ts < MIN_INTERVAL:
    remaining = int(MIN_INTERVAL - (now - last_ts))
    print(f'  "method": "python_direct",')
    print(f'  "skipped": true,')
    print(f'  "reason": "cooldown ({remaining}s remaining)",')
    print(f'  "ok": true')
else:
    # Perform repair: check providers and update disabled_until
    try:
        from multi_broker_phoenix.ai.seat_router import AISeatRouter
        router = AISeatRouter()
        router.refresh_health()
        snap = router.status_snapshot()
        
        # Write state
        Path(STATE_FILE).parent.mkdir(parents=True, exist_ok=True)
        with open(STATE_FILE, 'w') as f:
            json.dump({'last_ts': now, 'snapshot': snap}, f)
        
        print(f'  "method": "python_direct",')
        print(f'  "skipped": false,')
        print(f'  "repair_result": {json.dumps(snap)},')
        print(f'  "ok": true')
    except Exception as e:
        print(f'  "method": "python_direct",')
        print(f'  "error": "{e}",')
        print(f'  "ok": false')
PY
fi

echo "}"
