#!/usr/bin/env bash
# Confirm that REAL HIVE browser/API seats are available and responding.
# Writes JSON result to ./hive_confirm.json and exits 0 on success.

set -euo pipefail
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

python3 - <<'PY'
from hive_real.test_real_ai import test_real_ai_connections
import json,sys
try:
    result = test_real_ai_connections()
    with open('hive_confirm.json','w') as f:
        f.write(json.dumps(result, indent=2))
    # Also write authoritative hive state to ops/state/hive.json
    import os
    os.makedirs('ops/state', exist_ok=True)
    hive_state = {
        'hive_confirmed': bool([v for v in result.get('votes', []) if v.get('ai') in ('ChatGPT','Grok','DeepSeek')]),
        'timestamp': time.time(),
        'result': result
    }
    with open('ops/state/hive.json','w') as f:
        f.write(json.dumps(hive_state, indent=2))
    # Success if any real AI responded
    real_ais = [v['ai'] for v in result.get('votes', []) if v.get('ai') in ('ChatGPT','Grok','DeepSeek')]
    if real_ais:
        print("✅ Real Hive confirmed:", ', '.join(real_ais))
        sys.exit(0)
    else:
        print("❌ No real AI responses detected. See hive_confirm.json and ops/state/hive.json for details.")
        sys.exit(2)
except Exception as e:
    print("❌ Hive confirmation failed:", e)
    sys.exit(3)
PY
