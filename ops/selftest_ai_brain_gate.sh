#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/ing/RICK/MULTI_BROKER_PHOENIX"

run_step() {
  local name="$1"
  shift
  echo "=== $name ==="
  "$@"
}

run_step "Ollama health" python3 - <<'PY'
from llm_gate.ollama_gate import health_check
res = health_check()
print(res)
if not res.get("ok"):
    raise SystemExit(1)
PY

run_step "Ollama generate" python3 - <<'PY'
from llm_gate.ollama_gate import generate
res = generate("Return the word OK")
print(res)
if not res.get("ok") or not res.get("response"):
    raise SystemExit(1)
PY

run_step "AI router local ok" python3 - <<'PY'
from ai_router.router import AIRouter
r = AIRouter().evaluate()
print(r)
if not r.get("local_ok"):
    raise SystemExit(1)
if not r.get("ai_ok"):
    raise SystemExit(1)
PY

run_step "AI router allow with cloud failures" bash -c '
export REQUIRE_AI=1
export AI_MIN_HEALTHY_SEATS=1
export AI_LOCAL_REQUIRED=1
export AI_CLOUD_OPTIONAL=1
export AI_FAIL_OPEN_ON_CLOUD_ERRORS=1
export XAI_BASE_URL=http://127.0.0.1:9
export DEEPSEEK_BASE_URL=http://127.0.0.1:9
python3 - <<"PY"
from ai_router.router import AIRouter
r = AIRouter().evaluate()
print(r)
if not r.get("local_ok"):
    raise SystemExit(1)
if not r.get("ai_ok"):
    raise SystemExit(1)
PY
'

echo "✅ SELFTEST PASS"
