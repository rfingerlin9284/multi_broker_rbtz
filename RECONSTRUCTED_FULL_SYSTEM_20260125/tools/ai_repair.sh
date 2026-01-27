#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.."; pwd)"
STATE="$ROOT/ops/state/ai_repair_state.json"
COOLDOWN_MIN="${AI_REPAIR_COOLDOWN_MIN:-10}"

_ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }
_commit() { git -C "$ROOT" rev-parse HEAD 2>/dev/null || echo "UNKNOWN"; }
_toggles_hash() { sha256sum "$ROOT/config/toggles.env" 2>/dev/null | awk '{print $1}'; }

mask() {
  local v="$1"
  if [[ -z "$v" ]]; then
    echo "<empty>"
  else
    echo "${v:0:4}...${v: -4}"
  fi
}

echo "timestamp=$(_ts)"
echo "commit=$(_commit)"
echo "toggles_hash=$(_toggles_hash)"

python3 - <<PY
import json, time, os
from ai_router.providers.xai_provider import XAIProvider
from ai_router.providers.deepseek_provider import DeepSeekProvider

x = XAIProvider()
d = DeepSeekProvider()

xs = x.health()
ds = d.health()

state = {
  "updated_at": time.time(),
  "cooldown_min": int(os.getenv("AI_REPAIR_COOLDOWN_MIN", "10")),
  "disabled_until": {},
  "reasons": {}
}

if xs.get("code") == 404:
  state["disabled_until"]["grok"] = time.time() + state["cooldown_min"] * 60
  state["reasons"]["grok"] = "HTTP_404"

if ds.get("code") == 401:
  state["disabled_until"]["deepseek"] = time.time() + state["cooldown_min"] * 60
  state["reasons"]["deepseek"] = "AUTH_FAIL"

os.makedirs(os.path.dirname("$STATE"), exist_ok=True)
with open("$STATE", "w") as f:
  json.dump(state, f, indent=2)

print(json.dumps({"grok": xs, "deepseek": ds, "state": state}, sort_keys=True))
PY

echo "XAI_BASE_URL=${XAI_BASE_URL:-<unset>}"
echo "XAI_MODEL=${XAI_MODEL:-<unset>}"
echo "XAI_API_KEY=$(mask "${XAI_API_KEY:-}")"
echo "DEEPSEEK_BASE_URL=${DEEPSEEK_BASE_URL:-<unset>}"
echo "DEEPSEEK_MODEL=${DEEPSEEK_MODEL:-<unset>}"
echo "DEEPSEEK_API_KEY=$(mask "${DEEPSEEK_API_KEY:-}")"

echo "PASS"
