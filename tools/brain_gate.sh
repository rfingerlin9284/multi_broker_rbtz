#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/ing/RICK/MULTI_BROKER_PHOENIX"
CMD="${1:-}"
shift || true

_ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }
_commit() { git -C "$ROOT" rev-parse HEAD 2>/dev/null || echo "UNKNOWN"; }
_toggles_hash() { sha256sum "$ROOT/config/toggles.env" 2>/dev/null | awk '{print $1}'; }

print_header() {
  echo "timestamp=$(_ts)"
  echo "commit=$(_commit)"
  echo "toggles_hash=$(_toggles_hash)"
}

case "$CMD" in
  brain_health)
    print_header
    python3 - <<'PY'
from llm_gate.ollama_gate import health_check
import json
res = health_check()
print(json.dumps(res, sort_keys=True))
print("PASS" if res.get("ok") else "FAIL")
PY
    ;;
  brain_ask)
    print_header
    prompt="$*"
    if [[ -z "$prompt" ]]; then
      echo "FAIL"
      exit 2
    fi
    python3 - <<PY
from llm_gate.ollama_gate import generate
import json
res = generate("""$prompt""")
print(json.dumps(res, sort_keys=True))
print("PASS" if res.get("ok") else "FAIL")
PY
    ;;
  *)
    echo "Usage: brain_gate.sh brain_health | brain_ask \"prompt...\""
    exit 2
    ;;
esac
