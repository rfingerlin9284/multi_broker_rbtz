#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/ing/RICK/MULTI_BROKER_PHOENIX"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_DIR="$ROOT/ops/backups/$TS"
MANIFEST="$ROOT/ops/state/patch_manifest.json"
SELFTEST_OUT="$ROOT/ops/state/selftest_last.log"

mkdir -p "$BACKUP_DIR"
mkdir -p "$ROOT/ops/state"

backup_file() {
  local f="$1"
  if [[ -f "$f" ]]; then
    (cd "$ROOT" && cp --parents "${f#$ROOT/}" "$BACKUP_DIR")
  fi
}

# Backup targets
backup_file "$ROOT/MULTI_BROKER_PHOENIX/multi_broker_phoenix/monitor/watchdog.py"
backup_file "$ROOT/multi_broker_phoenix/risk/exit_manager.py"
backup_file "$ROOT/multi_broker_phoenix/risk/protect_loop.py"
backup_file "$ROOT/tools/task_runner.sh"
backup_file "$ROOT/.vscode/tasks.json"
backup_file "$ROOT/config/toggles.env"
backup_file "$ROOT/tools/brain_gate.sh"
backup_file "$ROOT/tools/brain_health.sh"
backup_file "$ROOT/tools/ai_health.sh"
backup_file "$ROOT/tools/ai_repair.sh"
backup_file "$ROOT/tools/holdtime_audit.sh"
backup_file "$ROOT/ops/selftest_ai_brain_gate.sh"
backup_file "$ROOT/llm_gate/ollama_gate.py"
backup_file "$ROOT/ai_router/router.py"
backup_file "$ROOT/ai_router/providers/ollama_provider.py"
backup_file "$ROOT/ai_router/providers/xai_provider.py"
backup_file "$ROOT/ai_router/providers/deepseek_provider.py"
backup_file "$ROOT/multi_broker_phoenix/hive/brain_seat_router.py"
backup_file "$ROOT/multi_broker_phoenix/monitor/ai_repair_agent.py"

mkdir -p "$ROOT/llm_gate"
mkdir -p "$ROOT/ai_router/providers"
mkdir -p "$ROOT/ops"
mkdir -p "$ROOT/tools"
mkdir -p "$ROOT/.vscode"

cat <<'EOF' > "$ROOT/llm_gate/__init__.py"
"""Local LLM gate modules."""
EOF

cat <<'EOF' > "$ROOT/llm_gate/ollama_gate.py"
from __future__ import annotations
import json
import os
import time
from typing import Dict, Any

import requests

STATE_FILE = os.getenv("BRAIN_HEALTH_STATE_FILE", "ops/state/brain_health.json")
OLLAMA_URL = os.getenv("OLLAMA_URL", os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")).rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
OLLAMA_TIMEOUT_S = float(os.getenv("OLLAMA_TIMEOUT_S", "6"))
OLLAMA_RETRY = int(os.getenv("OLLAMA_RETRY", "1"))


def _write_state(payload: Dict[str, Any]) -> None:
    try:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, "w") as f:
            json.dump(payload, f, indent=2)
    except Exception:
        pass


def health_check() -> Dict[str, Any]:
    start = time.time()
    ok = False
    reason = "UNKNOWN"
    code = 0
    models = []
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=OLLAMA_TIMEOUT_S)
        code = r.status_code
        if r.status_code == 200:
            ok = True
            reason = "OK"
            data = r.json()
            models = [m.get("name") for m in data.get("models", []) if m.get("name")]
        else:
            reason = f"HTTP_{r.status_code}"
    except Exception as e:
        reason = f"EXC:{type(e).__name__}"
    latency_ms = int((time.time() - start) * 1000)
    payload = {
        "ok": ok,
        "code": code,
        "reason": reason,
        "latency_ms": latency_ms,
        "model": OLLAMA_MODEL,
        "url": OLLAMA_URL,
        "models": models,
        "timestamp": time.time(),
    }
    _write_state(payload)
    return payload


def generate(prompt: str, system_prompt: str | None = None) -> Dict[str, Any]:
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }
    if system_prompt:
        payload["system"] = system_prompt

    last_error = None
    for _ in range(OLLAMA_RETRY + 1):
        start = time.time()
        try:
            r = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=OLLAMA_TIMEOUT_S)
            latency_ms = int((time.time() - start) * 1000)
            if r.status_code != 200:
                last_error = f"HTTP_{r.status_code}"
                continue
            data = r.json()
            text = data.get("response", "")
            return {
                "ok": True,
                "response": text,
                "latency_ms": latency_ms,
            }
        except Exception as e:
            last_error = f"EXC:{type(e).__name__}"
    return {
        "ok": False,
        "error": last_error or "UNKNOWN",
        "response": "",
        "latency_ms": 0,
    }
EOF

cat <<'EOF' > "$ROOT/ai_router/__init__.py"
"""AI provider router."""
EOF

cat <<'EOF' > "$ROOT/ai_router/providers/__init__.py"
"""AI provider implementations."""
EOF

cat <<'EOF' > "$ROOT/ai_router/providers/ollama_provider.py"
from __future__ import annotations
from typing import Dict, Any

from llm_gate.ollama_gate import health_check as _health, generate as _generate


class OllamaProvider:
    name = "ollama"

    def health(self) -> Dict[str, Any]:
        return _health()

    def generate(self, prompt: str, system_prompt: str | None = None) -> Dict[str, Any]:
        return _generate(prompt, system_prompt=system_prompt)
EOF

cat <<'EOF' > "$ROOT/ai_router/providers/xai_provider.py"
from __future__ import annotations
import os
import time
from typing import Dict, Any

import requests


class XAIProvider:
    name = "grok"

    def __init__(self):
        self.base_url = os.getenv("XAI_BASE_URL", "https://api.x.ai").rstrip("/")
        self.model = os.getenv("XAI_MODEL", "grok-4-latest")
        self.key = os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY")

    def enabled(self) -> bool:
        return bool(self.key)

    def health(self) -> Dict[str, Any]:
        if not self.key:
            return {"ok": False, "code": 0, "reason": "NO_KEY", "latency_ms": 0}
        start = time.time()
        url = f"{self.base_url}/v1/models" if not self.base_url.endswith("/v1") else f"{self.base_url}/models"
        headers = {"Authorization": f"Bearer {self.key}"}
        try:
            r = requests.get(url, headers=headers, timeout=4)
            latency_ms = int((time.time() - start) * 1000)
            if r.status_code == 200:
                return {"ok": True, "code": 200, "reason": "OK", "latency_ms": latency_ms}
            return {"ok": False, "code": r.status_code, "reason": f"HTTP_{r.status_code}", "latency_ms": latency_ms}
        except Exception as e:
            latency_ms = int((time.time() - start) * 1000)
            return {"ok": False, "code": 0, "reason": f"EXC:{type(e).__name__}", "latency_ms": latency_ms}

    def generate(self, prompt: str, system_prompt: str | None = None) -> Dict[str, Any]:
        if not self.key:
            return {"ok": False, "error": "NO_KEY", "response": ""}
        url = f"{self.base_url}/v1/chat/completions" if not self.base_url.endswith("/v1") else f"{self.base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt or "You are a trading analyst."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
        }
        try:
            start = time.time()
            r = requests.post(url, headers=headers, json=payload, timeout=15)
            latency_ms = int((time.time() - start) * 1000)
            if r.status_code != 200:
                return {"ok": False, "error": f"HTTP_{r.status_code}", "response": "", "latency_ms": latency_ms}
            data = r.json()
            content = data["choices"][0]["message"]["content"]
            return {"ok": True, "response": content, "latency_ms": latency_ms}
        except Exception as e:
            return {"ok": False, "error": f"EXC:{type(e).__name__}", "response": ""}
EOF

cat <<'EOF' > "$ROOT/ai_router/providers/deepseek_provider.py"
from __future__ import annotations
import os
import time
from typing import Dict, Any

import requests


class DeepSeekProvider:
    name = "deepseek"

    def __init__(self):
        self.base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        self.key = os.getenv("DEEPSEEK_API_KEY")

    def enabled(self) -> bool:
        return bool(self.key)

    def health(self) -> Dict[str, Any]:
        if not self.key:
            return {"ok": False, "code": 0, "reason": "NO_KEY", "latency_ms": 0}
        start = time.time()
        url = f"{self.base_url}/v1/models" if not self.base_url.endswith("/v1") else f"{self.base_url}/models"
        headers = {"Authorization": f"Bearer {self.key}"}
        try:
            r = requests.get(url, headers=headers, timeout=4)
            latency_ms = int((time.time() - start) * 1000)
            if r.status_code == 200:
                return {"ok": True, "code": 200, "reason": "OK", "latency_ms": latency_ms}
            return {"ok": False, "code": r.status_code, "reason": f"HTTP_{r.status_code}", "latency_ms": latency_ms}
        except Exception as e:
            latency_ms = int((time.time() - start) * 1000)
            return {"ok": False, "code": 0, "reason": f"EXC:{type(e).__name__}", "latency_ms": latency_ms}

    def generate(self, prompt: str, system_prompt: str | None = None) -> Dict[str, Any]:
        if not self.key:
            return {"ok": False, "error": "NO_KEY", "response": ""}
        url = f"{self.base_url}/v1/chat/completions" if not self.base_url.endswith("/v1") else f"{self.base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt or "You are a trading analyst."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
        }
        try:
            start = time.time()
            r = requests.post(url, headers=headers, json=payload, timeout=15)
            latency_ms = int((time.time() - start) * 1000)
            if r.status_code != 200:
                return {"ok": False, "error": f"HTTP_{r.status_code}", "response": "", "latency_ms": latency_ms}
            data = r.json()
            content = data["choices"][0]["message"]["content"]
            return {"ok": True, "response": content, "latency_ms": latency_ms}
        except Exception as e:
            return {"ok": False, "error": f"EXC:{type(e).__name__}", "response": ""}
EOF

cat <<'EOF' > "$ROOT/ai_router/router.py"
from __future__ import annotations
import json
import os
import time
from typing import Dict, Any, Optional

from ai_router.providers.ollama_provider import OllamaProvider
from ai_router.providers.xai_provider import XAIProvider
from ai_router.providers.deepseek_provider import DeepSeekProvider

STATE_FILE = os.getenv("AI_REPAIR_STATE_FILE", "ops/state/ai_repair_state.json")


def _read_state() -> Dict[str, Any]:
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def _disabled_until(name: str) -> float:
    st = _read_state()
    return float(st.get("disabled_until", {}).get(name, 0.0) or 0.0)


def _is_disabled(name: str) -> bool:
    return time.time() < _disabled_until(name)


class AIRouter:
    def __init__(self):
        self.require_ai = os.getenv("REQUIRE_AI", "0").lower() in ("1", "true", "yes")
        self.min_seats = int(os.getenv("AI_MIN_HEALTHY_SEATS", "1"))
        self.local_required = os.getenv("AI_LOCAL_REQUIRED", "0").lower() in ("1", "true", "yes")
        self.cloud_optional = os.getenv("AI_CLOUD_OPTIONAL", "1").lower() in ("1", "true", "yes")
        self.fail_open_cloud = os.getenv("AI_FAIL_OPEN_ON_CLOUD_ERRORS", "1").lower() in ("1", "true", "yes")

        self.ollama = OllamaProvider()
        self.xai = XAIProvider()
        self.deepseek = DeepSeekProvider()

    def snapshot(self) -> Dict[str, Dict[str, Any]]:
        statuses: Dict[str, Dict[str, Any]] = {}
        statuses["ollama"] = self.ollama.health()

        if not _is_disabled("grok") and self.xai.enabled():
            statuses["grok"] = self.xai.health()
        else:
            statuses["grok"] = {"ok": False, "code": 0, "reason": "DISABLED", "latency_ms": 0}

        if not _is_disabled("deepseek") and self.deepseek.enabled():
            statuses["deepseek"] = self.deepseek.health()
        else:
            statuses["deepseek"] = {"ok": False, "code": 0, "reason": "DISABLED", "latency_ms": 0}

        return statuses

    def evaluate(self) -> Dict[str, Any]:
        snap = self.snapshot()
        local_ok = bool(snap.get("ollama", {}).get("ok"))
        cloud_ok = any(
            s.get("ok") for k, s in snap.items() if k in ("grok", "deepseek")
        )
        healthy_count = sum(1 for s in snap.values() if s.get("ok"))

        if not self.require_ai:
            ai_ok = True
        else:
            if self.local_required:
                ai_ok = local_ok and healthy_count >= self.min_seats
            else:
                ai_ok = healthy_count >= self.min_seats

        chosen = "ollama" if local_ok else None
        if chosen is None:
            for k in ("grok", "deepseek"):
                if snap.get(k, {}).get("ok"):
                    chosen = k
                    break

        return {
            "ai_ok": ai_ok,
            "local_ok": local_ok,
            "cloud_ok": cloud_ok,
            "chosen": chosen,
            "healthy_count": healthy_count,
            "min_seats": self.min_seats,
            "snapshot": snap,
        }

    def ask(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        order = ["ollama", "grok", "deepseek"]
        providers = {
            "ollama": self.ollama,
            "grok": self.xai,
            "deepseek": self.deepseek,
        }

        for name in order:
            if _is_disabled(name):
                continue
            prov = providers[name]
            if hasattr(prov, "enabled") and not prov.enabled():
                continue
            res = prov.generate(prompt, system_prompt=system_prompt)
            if res.get("ok"):
                return {"ok": True, "provider": name, "response": res.get("response", ""), "latency_ms": res.get("latency_ms", 0)}
        return {"ok": False, "provider": None, "response": ""}
EOF

cat <<'EOF' > "$ROOT/tools/brain_gate.sh"
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
EOF

cat <<'EOF' > "$ROOT/tools/brain_health.sh"
#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/ing/RICK/MULTI_BROKER_PHOENIX"
"$ROOT/tools/brain_gate.sh" brain_health
EOF

cat <<'EOF' > "$ROOT/tools/ai_health.sh"
#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/ing/RICK/MULTI_BROKER_PHOENIX"

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
EOF

cat <<'EOF' > "$ROOT/tools/ai_repair.sh"
#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/ing/RICK/MULTI_BROKER_PHOENIX"
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
EOF

cat <<'EOF' > "$ROOT/tools/holdtime_audit.sh"
#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/ing/RICK/MULTI_BROKER_PHOENIX"

_ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }
_commit() { git -C "$ROOT" rev-parse HEAD 2>/dev/null || echo "UNKNOWN"; }
_toggles_hash() { sha256sum "$ROOT/config/toggles.env" 2>/dev/null | awk '{print $1}'; }

echo "timestamp=$(_ts)"
echo "commit=$(_commit)"
echo "toggles_hash=$(_toggles_hash)"

python3 - <<'PY'
import os, time
from datetime import datetime
from execution.oanda_practice_client import OandaPracticeClient

soft = int(os.getenv("SOFT_MAX_HOLD_SECONDS", "21600"))
hard = int(os.getenv("MAX_HOLD_SECONDS", "28800"))

client = OandaPracticeClient(
    token=os.getenv("OANDA_API_TOKEN"),
    account_id=os.getenv("OANDA_PRACTICE_ACCOUNT_ID") or os.getenv("OANDA_ACCOUNT_ID"),
    base_url=os.getenv("OANDA_API_URL", "https://api-fxpractice.oanda.com"),
)

trades = client.list_open_trades().get("trades", [])
now = datetime.utcnow()
flags = {"soft": 0, "hard": 0}

for t in trades:
    ot = t.get("openTime", "")
    tid = t.get("id")
    if not ot:
        continue
    try:
        ot = ot.split(".")[0]
        open_time = datetime.fromisoformat(ot.replace("Z", "+00:00"))
        age = (now - open_time.replace(tzinfo=None)).total_seconds()
        mark = "OK"
        if age >= hard:
            mark = "HARD"
            flags["hard"] += 1
        elif age >= soft:
            mark = "SOFT"
            flags["soft"] += 1
        print(f"trade={tid} age_sec={int(age)} flag={mark}")
    except Exception:
        continue

if flags["hard"] > 0:
    print("FAIL")
else:
    print("PASS")
PY
EOF

cat <<'EOF' > "$ROOT/ops/selftest_ai_brain_gate.sh"
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
EOF

cat <<'EOF' > "$ROOT/config/toggles.env"
# RBOTZILLA Toggle Controls (SAFE: no secrets)
# 1 = ON, 0 = OFF

# Core switches
ENABLE_ENGINE=1
ENABLE_HIVE=1

# Brokers
ENABLE_OANDA=1
ENABLE_COINBASE=0
ENABLE_IBKR=0

# Modes supported by run_headless.py
# auto | multi-asset | platform-paper | simulate | oanda-only | coinbase-only | ibkr-only
HEADLESS_MODE=oanda-only

# Trading mode gates (PAPER = OANDA practice)
TRADING_MODE=PAPER
PRACTICE_TRADING_ALLOWED=1
ALLOW_PRACTICE_ORDERS=1
CONFIRM_PRACTICE_ORDER=0

# AI requirements (NO OpenAI / NO browser hive)
REQUIRE_XAI=1
REQUIRE_DEEPSEEK=1
DISABLE_OPENAI=true
DISABLE_BROWSER_HIVE=true

# AI Router gate (local always-on)
REQUIRE_AI=1
AI_MIN_HEALTHY_SEATS=1
AI_LOCAL_REQUIRED=1
AI_CLOUD_OPTIONAL=1
AI_FAIL_OPEN_ON_CLOUD_ERRORS=1

# Optional: reduce noise
SIMPLIFY_MODE=1
HIVE_ONLY_ON_SIGNAL=1
AI_MAX_CALLS_PER_SYMBOL=1
AI_MAX_CALLS_PER_SCAN=10

# Paper order helpers
PAPER_AUTO_BRACKET=1
PAPER_SL_PIPS=20
PAPER_TP_PIPS=40
PAPER_TRAIL_PIPS=12
EOF

cat <<'EOF' > "$ROOT/.vscode/tasks.json"
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "[ANY] RBOTZILLA STATUS — prints toggles+PID; outputs stdout",
      "type": "shell",
      "command": "/home/ing/RICK/MULTI_BROKER_PHOENIX/tools/task_runner.sh",
      "args": [
        "RBOTZILLA_STATUS",
        "/home/ing/RICK/MULTI_BROKER_PHOENIX/tools/rbot_status.sh"
      ],
      "problemMatcher": []
    },
    {
      "label": "[ANY] BRAIN HEALTH — local LLM health; outputs stdout",
      "type": "shell",
      "command": "/home/ing/RICK/MULTI_BROKER_PHOENIX/tools/task_runner.sh",
      "args": [
        "BRAIN_HEALTH",
        "/home/ing/RICK/MULTI_BROKER_PHOENIX/tools/brain_health.sh"
      ],
      "problemMatcher": []
    },
    {
      "label": "[ANY] AI HEALTH — router snapshot; outputs stdout",
      "type": "shell",
      "command": "/home/ing/RICK/MULTI_BROKER_PHOENIX/tools/task_runner.sh",
      "args": [
        "AI_HEALTH",
        "/home/ing/RICK/MULTI_BROKER_PHOENIX/tools/ai_health.sh"
      ],
      "problemMatcher": []
    },
    {
      "label": "[ANY] AI REPAIR — cloud cooldown; outputs stdout",
      "type": "shell",
      "command": "/home/ing/RICK/MULTI_BROKER_PHOENIX/tools/task_runner.sh",
      "args": [
        "AI_REPAIR",
        "/home/ing/RICK/MULTI_BROKER_PHOENIX/tools/ai_repair.sh"
      ],
      "problemMatcher": []
    },
    {
      "label": "[ANY] HOLDTIME AUDIT — open positions age; outputs stdout",
      "type": "shell",
      "command": "/home/ing/RICK/MULTI_BROKER_PHOENIX/tools/task_runner.sh",
      "args": [
        "HOLDTIME_AUDIT",
        "/home/ing/RICK/MULTI_BROKER_PHOENIX/tools/holdtime_audit.sh"
      ],
      "problemMatcher": []
    }
  ]
}
EOF

cat <<'EOF' > "$ROOT/tools/task_runner.sh"
#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: task_runner.sh <task_name> <command...>"
  exit 2
fi

task_name="$1"
shift

ROOT="/home/ing/RICK/MULTI_BROKER_PHOENIX"
LOG_ROOT="$ROOT/ops/task_runs/$task_name"
mkdir -p "$LOG_ROOT"

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
log_file="$LOG_ROOT/${stamp}.log"
summary_file="$LOG_ROOT/${stamp}.summary.txt"
json_file="$LOG_ROOT/${stamp}.json"

# Defensive: if task name is passed twice, drop the duplicate
if [[ "${1:-}" == "$task_name" && -n "${2:-}" ]]; then
  shift
fi

cmd_display="$*"

# Capture called script hash (best-effort)
script_path="${1:-}"
script_hash=""
if [[ -n "$script_path" && -f "$script_path" ]]; then
  script_hash="$(python3 - "$script_path" <<'PY'
import hashlib
import sys
path = sys.argv[1]
try:
    data = open(path, 'rb').read()
    print(hashlib.sha256(data).hexdigest())
except Exception:
    print('')
PY
)"
fi

# Capture git commit if available
commit=""
if command -v git >/dev/null 2>&1 && git -C "$ROOT" rev-parse --git-dir >/dev/null 2>&1; then
  commit="$(git -C "$ROOT" rev-parse HEAD 2>/dev/null || true)"
fi

# Capture toggles snapshot hash (no secrets)
toggles_hash=""
if [[ -f "$ROOT/config/toggles.env" ]]; then
  toggles_hash="$(python3 - <<'PY'
import hashlib
p = '/home/ing/RICK/MULTI_BROKER_PHOENIX/config/toggles.env'
try:
    data = open(p, 'rb').read()
    print(hashlib.sha256(data).hexdigest())
except Exception:
    print('')
PY
)"
fi

# Run command and capture output
set +e
{
  echo "=== TASK RUNNER START ==="
  echo "task_name=${task_name}"
  echo "timestamp=${stamp}"
  echo "command=${cmd_display}"
  echo "script_path=${script_path}"
  echo "script_hash=${script_hash}"
  echo "commit=${commit}"
  echo "toggles_hash=${toggles_hash}"
  echo "=========================="
  "$@"
} 2>&1 | tee "$log_file"
exit_code=${PIPESTATUS[0]}
set -e

# Summary: last 200 lines
if [[ -f "$log_file" ]]; then
  tail -n 200 "$log_file" > "$summary_file" || true
fi

summary_hash="$(python3 - "$task_name" "$stamp" <<'PY'
import hashlib
import sys
task = sys.argv[1]
stamp = sys.argv[2]
p = f'/home/ing/RICK/MULTI_BROKER_PHOENIX/ops/task_runs/{task}/{stamp}.summary.txt'
try:
  data = open(p, 'rb').read()
  print(hashlib.sha256(data).hexdigest())
except Exception:
  print('')
PY
)"

# Find last successful run
prev_summary=""
prev_hash=""
python3 - "$task_name" <<'PY'
import json, glob, os
import sys
root = f"/home/ing/RICK/MULTI_BROKER_PHOENIX/ops/task_runs/{sys.argv[1]}"
paths = sorted(glob.glob(os.path.join(root, '*.json')))
last = None
for p in paths[::-1]:
    try:
        with open(p) as f:
            d = json.load(f)
        if d.get('exit_code') == 0:
            last = d
            break
    except Exception:
        continue
if last:
  print(last.get('summary_file',''))
  print(last.get('summary_hash',''))
PY
> "$LOG_ROOT/.prev_summary.tmp" || true

if [[ -f "$LOG_ROOT/.prev_summary.tmp" ]]; then
  prev_summary="$(sed -n '1p' "$LOG_ROOT/.prev_summary.tmp")"
  prev_hash="$(sed -n '2p' "$LOG_ROOT/.prev_summary.tmp")"
  rm -f "$LOG_ROOT/.prev_summary.tmp"
fi

# Write JSON metadata
python3 - <<PY
import json
out = {
  'task_name': '$task_name',
  'timestamp': '$stamp',
  'command': '$cmd_display',
  'script_path': '$script_path',
  'script_hash': '$script_hash',
  'exit_code': $exit_code,
  'commit': '$commit',
  'toggles_hash': '$toggles_hash',
  'log_file': '$log_file',
  'summary_file': '$summary_file',
  'summary_hash': '$summary_hash'
}
with open('$json_file','w') as f:
  json.dump(out, f, indent=2)
PY

# Compare to baseline
if [[ -n "$prev_hash" && -n "$summary_hash" ]]; then
  if [[ "$prev_hash" == "$summary_hash" ]]; then
    echo "✅ SAME AS BASELINE"
  else
    echo "⚠️ DIFFERENT FROM BASELINE (summary diff below)"
    if [[ -f "$prev_summary" && -f "$summary_file" ]]; then
      diff -u "$prev_summary" "$summary_file" || true
    fi
  fi
else
  echo "⚠️ BASELINE NOT FOUND (first successful run establishes baseline)"
fi

exit $exit_code
EOF

cat <<'EOF' > "$ROOT/multi_broker_phoenix/risk/exit_manager.py"
"""Exit Manager - Profit-aware exit logic for RBOTzilla.

This module provides intelligent exit management with:
1. Profit Lock: Move SL to breakeven when trade reaches +X pips
2. Trailing Stop: Dynamic trailing after profit threshold
3. Time Stop: Close trades open beyond max duration
4. Partial TP: Scale out at intermediate targets

Key Features:
- Integrates with OANDA API to modify orders
- Respects existing OCO structures
- Emits events for audit trail
- Configurable thresholds via env vars
"""
from __future__ import annotations
import os
import time
import logging
import threading
from typing import Dict, Any, Optional, List
from datetime import datetime
import json

logger = logging.getLogger(__name__)

# State file for observability
STATE_FILE = os.getenv('EXIT_MANAGER_STATE_FILE', 'ops/state/exit_manager.json')
EVENT_LOG = os.getenv('EXIT_MANAGER_EVENT_LOG', 'ops/state/exit_manager_events.jsonl')


# -----------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------
DEFAULT_CONFIG = {
  # Profit lock: move SL to breakeven after X pips profit
  'PROFIT_LOCK_PIPS': float(os.getenv('EXIT_PROFIT_LOCK_PIPS', '15.0')),

  # Trailing stop: start trailing after X pips profit
  'TRAILING_START_PIPS': float(os.getenv('EXIT_TRAILING_START_PIPS', '20.0')),
  'TRAILING_DISTANCE_PIPS': float(os.getenv('EXIT_TRAILING_DISTANCE_PIPS', '10.0')),

  # Time stop: close trades open longer than X hours
  'MAX_TRADE_HOURS': float(os.getenv('EXIT_MAX_TRADE_HOURS', '48.0')),

  # Hard/soft max hold (seconds)
  'SOFT_MAX_HOLD_SECONDS': int(os.getenv('SOFT_MAX_HOLD_SECONDS', '21600')),
  'MAX_HOLD_SECONDS': int(os.getenv('MAX_HOLD_SECONDS', '28800')),

  # Profit giveback rule (pips-based trigger; name kept for config compatibility)
  'PROFIT_LOCK_TRIGGER_PCT': float(os.getenv('PROFIT_LOCK_TRIGGER_PCT', '0.20')),
  'GIVEBACK_PCT': float(os.getenv('GIVEBACK_PCT', '0.50')),

  # Partial TP: take X% at first target
  'PARTIAL_TP_PERCENT': float(os.getenv('EXIT_PARTIAL_TP_PERCENT', '50.0')),
  'PARTIAL_TP_PIPS': float(os.getenv('EXIT_PARTIAL_TP_PIPS', '25.0')),

  # Check interval (seconds)
  'CHECK_INTERVAL_SECS': int(os.getenv('EXIT_CHECK_INTERVAL', '30')),

  # Enable/disable features
  'ENABLE_PROFIT_LOCK': os.getenv('EXIT_ENABLE_PROFIT_LOCK', 'true').lower() == 'true',
  'ENABLE_TRAILING': os.getenv('EXIT_ENABLE_TRAILING', 'true').lower() == 'true',
  'ENABLE_TIME_STOP': os.getenv('EXIT_ENABLE_TIME_STOP', 'true').lower() == 'true',
  'ENABLE_PARTIAL_TP': os.getenv('EXIT_ENABLE_PARTIAL_TP', 'false').lower() == 'true',
}


def get_config() -> Dict[str, Any]:
  """Return current exit manager configuration."""
  return {
    'PROFIT_LOCK_PIPS': float(os.getenv('EXIT_PROFIT_LOCK_PIPS', DEFAULT_CONFIG['PROFIT_LOCK_PIPS'])),
    'TRAILING_START_PIPS': float(os.getenv('EXIT_TRAILING_START_PIPS', DEFAULT_CONFIG['TRAILING_START_PIPS'])),
    'TRAILING_DISTANCE_PIPS': float(os.getenv('EXIT_TRAILING_DISTANCE_PIPS', DEFAULT_CONFIG['TRAILING_DISTANCE_PIPS'])),
    'MAX_TRADE_HOURS': float(os.getenv('EXIT_MAX_TRADE_HOURS', DEFAULT_CONFIG['MAX_TRADE_HOURS'])),
    'SOFT_MAX_HOLD_SECONDS': int(os.getenv('SOFT_MAX_HOLD_SECONDS', DEFAULT_CONFIG['SOFT_MAX_HOLD_SECONDS'])),
    'MAX_HOLD_SECONDS': int(os.getenv('MAX_HOLD_SECONDS', DEFAULT_CONFIG['MAX_HOLD_SECONDS'])),
    'PROFIT_LOCK_TRIGGER_PCT': float(os.getenv('PROFIT_LOCK_TRIGGER_PCT', DEFAULT_CONFIG['PROFIT_LOCK_TRIGGER_PCT'])),
    'GIVEBACK_PCT': float(os.getenv('GIVEBACK_PCT', DEFAULT_CONFIG['GIVEBACK_PCT'])),
    'PARTIAL_TP_PERCENT': float(os.getenv('EXIT_PARTIAL_TP_PERCENT', DEFAULT_CONFIG['PARTIAL_TP_PERCENT'])),
    'PARTIAL_TP_PIPS': float(os.getenv('EXIT_PARTIAL_TP_PIPS', DEFAULT_CONFIG['PARTIAL_TP_PIPS'])),
    'CHECK_INTERVAL_SECS': int(os.getenv('EXIT_CHECK_INTERVAL', DEFAULT_CONFIG['CHECK_INTERVAL_SECS'])),
    'ENABLE_PROFIT_LOCK': os.getenv('EXIT_ENABLE_PROFIT_LOCK', str(DEFAULT_CONFIG['ENABLE_PROFIT_LOCK'])).lower() == 'true',
    'ENABLE_TRAILING': os.getenv('EXIT_ENABLE_TRAILING', str(DEFAULT_CONFIG['ENABLE_TRAILING'])).lower() == 'true',
    'ENABLE_TIME_STOP': os.getenv('EXIT_ENABLE_TIME_STOP', str(DEFAULT_CONFIG['ENABLE_TIME_STOP'])).lower() == 'true',
    'ENABLE_PARTIAL_TP': os.getenv('EXIT_ENABLE_PARTIAL_TP', str(DEFAULT_CONFIG['ENABLE_PARTIAL_TP'])).lower() == 'true',
  }


# -----------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------
def pip_size(pair: str) -> float:
  """Return pip size for a currency pair."""
  pair_upper = pair.upper().replace('-', '_').replace('/', '_')
  if pair_upper.endswith('JPY') or '_JPY' in pair_upper:
    return 0.01
  return 0.0001


def current_profit_pips(position: Dict[str, Any], current_price: float) -> float:
  """Calculate current profit in pips for a position."""
  pair = position.get('instrument', '')
  entry_price = float(position.get('averagePrice', position.get('price', 0)))
  side = position.get('side', 'long').lower()

  if not pair or entry_price == 0:
    return 0.0

  pip = pip_size(pair)

  if side == 'long':
    return (current_price - entry_price) / pip
  else:  # short
    return (entry_price - current_price) / pip


def _ensure_state_dir(path: str) -> None:
  """Ensure state directory exists for the given file path."""
  try:
    import pathlib
    pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
  except Exception:
    pass


def _log_event(event_type: str, details: Dict[str, Any]):
  """Append event to durable event log."""
  try:
    event = {
      'timestamp': datetime.utcnow().isoformat() + 'Z',
      'type': event_type,
      **details
    }
    _ensure_state_dir(EVENT_LOG)
    with open(EVENT_LOG, 'a') as f:
      f.write(json.dumps(event) + '\n')
  except Exception as e:
    logger.warning(f"Failed to log exit event: {e}")


def _write_state(state: Dict[str, Any]):
  """Write state to file for observability."""
  try:
    state['updated_at'] = datetime.utcnow().isoformat() + 'Z'
    _ensure_state_dir(STATE_FILE)
    with open(STATE_FILE, 'w') as f:
      json.dump(state, f, indent=2)
  except Exception as e:
    logger.warning(f"Failed to write exit manager state: {e}")


# -----------------------------------------------------------------
# Exit Manager Class
# -----------------------------------------------------------------
class ExitManager:
  """Manages intelligent exits for open positions."""

  def __init__(self, connector, account_id: str = None):
    """Initialize Exit Manager."""
    self.connector = connector
    self.account_id = account_id or getattr(connector, 'account_id', None)
    self.config = get_config()
    self._running = False
    self._thread = None
    self._lock = threading.Lock()

    # Track which positions have had profit lock applied
    self._profit_locked: Dict[str, bool] = {}

    # Track trailing stop high-water marks
    self._trailing_hwm: Dict[str, float] = {}

    # Track peak profit for giveback logic
    self._max_profit_pips: Dict[str, float] = {}

    logger.info(f"ExitManager initialized with config: {self.config}")

  def start_background_monitor(self):
    """Start background thread that monitors positions."""
    if self._running:
      logger.warning("ExitManager already running")
      return

    self._running = True
    self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
    self._thread.start()
    logger.info("ExitManager background monitor started")

  def stop(self):
    """Stop the background monitor."""
    self._running = False
    if self._thread:
      self._thread.join(timeout=5.0)
    logger.info("ExitManager stopped")

  def _monitor_loop(self):
    """Main monitoring loop."""
    while self._running:
      try:
        result = self.check_all_positions()
        logger.info("EXIT_MANAGER_TICK positions=%d", result.get('checked', 0))
        _log_event('EXIT_MANAGER_TICK', {
          'checked': result.get('checked', 0),
          'profit_locks': result.get('profit_locks', 0),
          'trailing_updates': result.get('trailing_updates', 0),
          'time_closes': result.get('time_closes', 0),
          'hard_time_closes': result.get('hard_time_closes', 0),
          'profit_giveback_exits': result.get('profit_giveback_exits', 0),
          'profit_giveback_tightens': result.get('profit_giveback_tightens', 0),
        })
      except Exception as e:
        logger.error(f"ExitManager check error: {e}")

      time.sleep(self.config['CHECK_INTERVAL_SECS'])

  def check_all_positions(self) -> Dict[str, Any]:
    """Check all open positions and apply exit logic."""
    actions = {
      'checked': 0,
      'profit_locks': 0,
      'trailing_updates': 0,
      'time_closes': 0,
      'hard_time_closes': 0,
      'soft_time_warnings': 0,
      'profit_giveback_exits': 0,
      'profit_giveback_tightens': 0,
      'errors': []
    }

    try:
      positions = self._get_positions()
      prices = self._get_prices([p.get('instrument') for p in positions])

      for pos in positions:
        pos_id = pos.get('id', pos.get('trade_id', 'unknown'))
        pair = pos.get('instrument', '')

        if not pair or pair not in prices:
          continue

        current_price = prices[pair]
        profit_pips = current_profit_pips(pos, current_price)
        age_sec = self._position_age_seconds(pos)

        actions['checked'] += 1

        # Hard time stop
        if age_sec is not None and age_sec >= self.config['MAX_HOLD_SECONDS']:
          if self._apply_time_stop(pos, age_sec, hard=True):
            actions['hard_time_closes'] += 1
            continue

        # Soft time stop warning / tighten
        if age_sec is not None and age_sec >= self.config['SOFT_MAX_HOLD_SECONDS']:
          if self._apply_soft_hold(pos, profit_pips, current_price, age_sec):
            actions['soft_time_warnings'] += 1

        # Profit Lock
        if self.config['ENABLE_PROFIT_LOCK']:
          if self._apply_profit_lock(pos, profit_pips, current_price):
            actions['profit_locks'] += 1

        # Trailing Stop
        if self.config['ENABLE_TRAILING']:
          if self._apply_trailing_stop(pos, profit_pips, current_price):
            actions['trailing_updates'] += 1

        # Soft time stop (legacy)
        if self.config['ENABLE_TIME_STOP']:
          if self._apply_time_stop(pos, age_sec, hard=False):
            actions['time_closes'] += 1

        # Profit giveback prevention
        giveback = self._apply_profit_giveback(pos, profit_pips, current_price)
        if giveback == 'EXIT':
          actions['profit_giveback_exits'] += 1
        elif giveback == 'TIGHTEN':
          actions['profit_giveback_tightens'] += 1

    except Exception as e:
      actions['errors'].append(str(e))
      logger.error(f"check_all_positions error: {e}")

    _write_state({
      'last_check': actions,
      'profit_locked': list(self._profit_locked.keys()),
      'trailing_hwm': self._trailing_hwm,
      'max_profit_pips': self._max_profit_pips,
    })

    return actions

  def _get_positions(self) -> List[Dict[str, Any]]:
    """Get open positions from connector."""
    try:
      if hasattr(self.connector, 'get_open_trades'):
        return self.connector.get_open_trades() or []
      if hasattr(self.connector, 'get_positions'):
        return self.connector.get_positions() or []
      logger.warning("No position retrieval method found on connector")
      return []
    except Exception as e:
      logger.error(f"Failed to get positions: {e}")
      return []

  def _get_prices(self, pairs: List[str]) -> Dict[str, float]:
    """Get current prices for pairs."""
    prices = {}
    try:
      unique_pairs = list(set(p for p in pairs if p))
      if not unique_pairs:
        return prices

      if hasattr(self.connector, 'get_prices'):
        raw = self.connector.get_prices(unique_pairs)
        for pair, data in (raw or {}).items():
          if isinstance(data, dict):
            bid = float(data.get('bid', 0))
            ask = float(data.get('ask', 0))
            prices[pair] = (bid + ask) / 2 if bid and ask else 0
          else:
            prices[pair] = float(data)
      elif hasattr(self.connector, 'get_current_price'):
        for pair in unique_pairs:
          p = self.connector.get_current_price(pair)
          if p:
            prices[pair] = float(p)
    except Exception as e:
      logger.error(f"Failed to get prices: {e}")

    return prices

  def _position_age_seconds(self, pos: Dict[str, Any]) -> Optional[float]:
    open_time_str = pos.get('openTime', '')
    if not open_time_str:
      return None
    try:
      open_time_str = open_time_str.split('.')[0]
      open_time = datetime.fromisoformat(open_time_str.replace('Z', '+00:00'))
      now = datetime.utcnow()
      return (now - open_time.replace(tzinfo=None)).total_seconds()
    except Exception:
      return None

  def _apply_profit_lock(self, pos: Dict[str, Any], profit_pips: float, current_price: float) -> bool:
    pos_id = pos.get('id', pos.get('trade_id', 'unknown'))
    if self._profit_locked.get(pos_id):
      return False
    if profit_pips < self.config['PROFIT_LOCK_PIPS']:
      return False

    entry_price = float(pos.get('averagePrice', pos.get('price', 0)))
    side = pos.get('side', 'long').lower()
    pair = pos.get('instrument', '')
    if entry_price == 0:
      return False

    pip = pip_size(pair)
    spread_buffer = pip * 2
    if side == 'long':
      new_sl = entry_price + spread_buffer
    else:
      new_sl = entry_price - spread_buffer

    current_sl = float(pos.get('stopLossOrder', {}).get('price', 0))
    if current_sl > 0:
      if side == 'long' and new_sl <= current_sl:
        return False
      if side == 'short' and new_sl >= current_sl:
        return False

    try:
      success = self._modify_trade_sl(pos_id, new_sl)
      if success:
        self._profit_locked[pos_id] = True
        _log_event('PROFIT_LOCK', {
          'position_id': pos_id,
          'pair': pair,
          'side': side,
          'entry': entry_price,
          'profit_pips': profit_pips,
          'new_sl': new_sl,
          'old_sl': current_sl,
        })
        logger.info(f"Profit lock applied: {pos_id} {pair} SL → {new_sl}")
        return True
    except Exception as e:
      logger.error(f"Failed to apply profit lock for {pos_id}: {e}")
    return False

  def _apply_trailing_stop(self, pos: Dict[str, Any], profit_pips: float, current_price: float) -> bool:
    pos_id = pos.get('id', pos.get('trade_id', 'unknown'))
    pair = pos.get('instrument', '')
    side = pos.get('side', 'long').lower()
    if profit_pips < self.config['TRAILING_START_PIPS']:
      return False

    hwm = self._trailing_hwm.get(pos_id, 0)
    if profit_pips > hwm:
      self._trailing_hwm[pos_id] = profit_pips
      hwm = profit_pips

    pip = pip_size(pair)
    trailing_dist = self.config['TRAILING_DISTANCE_PIPS'] * pip
    entry_price = float(pos.get('averagePrice', pos.get('price', 0)))

    if side == 'long':
      hwm_price = entry_price + (hwm * pip)
      new_sl = hwm_price - trailing_dist
    else:
      hwm_price = entry_price - (hwm * pip)
      new_sl = hwm_price + trailing_dist

    current_sl = float(pos.get('stopLossOrder', {}).get('price', 0))
    if current_sl > 0:
      if side == 'long' and new_sl <= current_sl:
        return False
      if side == 'short' and new_sl >= current_sl:
        return False

    try:
      success = self._modify_trade_sl(pos_id, new_sl)
      if success:
        _log_event('TRAILING_UPDATE', {
          'position_id': pos_id,
          'pair': pair,
          'side': side,
          'profit_pips': profit_pips,
          'hwm_pips': hwm,
          'new_sl': new_sl,
          'old_sl': current_sl,
        })
        logger.info(f"Trailing SL updated: {pos_id} {pair} SL → {new_sl}")
        return True
    except Exception as e:
      logger.error(f"Failed to update trailing SL for {pos_id}: {e}")
    return False

  def _apply_soft_hold(self, pos: Dict[str, Any], profit_pips: float, current_price: float, age_sec: float) -> bool:
    pos_id = pos.get('id', pos.get('trade_id', 'unknown'))
    pair = pos.get('instrument', '')
    side = pos.get('side', 'long').lower()
    entry_price = float(pos.get('averagePrice', pos.get('price', 0)))
    if entry_price == 0:
      return False

    logger.warning(f"TIME_STOP_SOFT position_id={pos_id} age_sec={int(age_sec)}")
    _log_event('TIME_STOP_SOFT', {'position_id': pos_id, 'age_sec': age_sec})

    # Tighten stop to breakeven when possible
    if profit_pips <= 0:
      return True

    pip = pip_size(pair)
    buffer = pip * 2
    if side == 'long':
      new_sl = entry_price + buffer
    else:
      new_sl = entry_price - buffer

    current_sl = float(pos.get('stopLossOrder', {}).get('price', 0))
    if current_sl > 0:
      if side == 'long' and new_sl <= current_sl:
        return True
      if side == 'short' and new_sl >= current_sl:
        return True

    try:
      success = self._modify_trade_sl(pos_id, new_sl)
      if success:
        logger.info(f"TIME_STOP_SOFT tighten SL: {pos_id} {pair} SL → {new_sl}")
    except Exception:
      pass
    return True

  def _apply_time_stop(self, pos: Dict[str, Any], age_sec: Optional[float], hard: bool = False) -> bool:
    pos_id = pos.get('id', pos.get('trade_id', 'unknown'))
    if age_sec is None:
      return False
    max_sec = self.config['MAX_HOLD_SECONDS'] if hard else self.config['MAX_TRADE_HOURS'] * 3600.0
    if age_sec < max_sec:
      return False

    success = self._close_trade(pos_id)
    if success:
      reason = 'HARD_MAX_HOLD' if hard else 'SOFT_MAX_HOLD'
      _log_event('TIME_STOP_EXIT', {
        'position_id': pos_id,
        'pair': pos.get('instrument', ''),
        'age_sec': age_sec,
        'reason': reason,
      })
      logger.info(f"TIME_STOP_EXIT: position_id={pos_id} age_sec={int(age_sec)} reason={reason}")
      return True
    return False

  def _apply_profit_giveback(self, pos: Dict[str, Any], profit_pips: float, current_price: float) -> Optional[str]:
    pos_id = pos.get('id', pos.get('trade_id', 'unknown'))
    pair = pos.get('instrument', '')
    side = pos.get('side', 'long').lower()
    trigger = float(self.config['PROFIT_LOCK_TRIGGER_PCT'])
    giveback = float(self.config['GIVEBACK_PCT'])

    peak = self._max_profit_pips.get(pos_id, profit_pips)
    if profit_pips > peak:
      peak = profit_pips
      self._max_profit_pips[pos_id] = peak

    if peak < trigger:
      return None

    if profit_pips > peak * (1 - giveback):
      return None

    # Giveback triggered
    action = None
    if self._close_trade(pos_id):
      action = 'EXIT'
    else:
      # tighten stop near current price
      pip = pip_size(pair)
      if side == 'long':
        new_sl = current_price - (pip * 2)
      else:
        new_sl = current_price + (pip * 2)
      try:
        if self._modify_trade_sl(pos_id, new_sl):
          action = 'TIGHTEN'
      except Exception:
        action = None

    if action:
      _log_event('PROFIT_LOCK', {
        'position_id': pos_id,
        'pair': pair,
        'peak_pips': peak,
        'now_pips': profit_pips,
        'action': action,
      })
      logger.info(f"PROFIT_LOCK: peak={peak:.2f} now={profit_pips:.2f} action={action}")
    return action

  def _modify_trade_sl(self, trade_id: str, new_sl: float) -> bool:
    try:
      if hasattr(self.connector, 'modify_trade'):
        result = self.connector.modify_trade(trade_id, stopLoss={'price': str(new_sl)})
        return result is not None
      if hasattr(self.connector, 'update_stop_loss'):
        return self.connector.update_stop_loss(trade_id, new_sl)
      logger.warning("No trade modification method found on connector")
      return False
    except Exception as e:
      logger.error(f"modify_trade_sl error: {e}")
      return False

  def _close_trade(self, trade_id: str) -> bool:
    try:
      if hasattr(self.connector, 'close_trade'):
        result = self.connector.close_trade(trade_id)
        return result is not None
      if hasattr(self.connector, 'close_position'):
        return self.connector.close_position(trade_id)
      logger.warning("No trade close method found on connector")
      return False
    except Exception as e:
      logger.error(f"close_trade error: {e}")
      return False

  def cleanup_closed_positions(self, open_position_ids: List[str]):
    with self._lock:
      closed = [pid for pid in self._profit_locked if pid not in open_position_ids]
      for pid in closed:
        del self._profit_locked[pid]

      closed = [pid for pid in self._trailing_hwm if pid not in open_position_ids]
      for pid in closed:
        del self._trailing_hwm[pid]

      closed = [pid for pid in self._max_profit_pips if pid not in open_position_ids]
      for pid in closed:
        del self._max_profit_pips[pid]


# -----------------------------------------------------------------
# Module-level convenience functions
# -----------------------------------------------------------------
_exit_manager: Optional[ExitManager] = None


def start_exit_manager(connector, account_id: str = None) -> ExitManager:
  """Start the global exit manager instance."""
  global _exit_manager
  if _exit_manager is not None:
    _exit_manager.stop()
  _exit_manager = ExitManager(connector, account_id)
  _exit_manager.start_background_monitor()
  return _exit_manager


def stop_exit_manager():
  """Stop the global exit manager."""
  global _exit_manager
  if _exit_manager:
    _exit_manager.stop()
    _exit_manager = None


def get_exit_manager() -> Optional[ExitManager]:
  """Get the global exit manager instance."""
  return _exit_manager


if __name__ == '__main__':
  print("Exit Manager Configuration:")
  for k, v in get_config().items():
    print(f"  {k}: {v}")
EOF

cat <<'EOF' > "$ROOT/multi_broker_phoenix/risk/protect_loop.py"
"""Protect Loop - Unified protection cycle for autonomous trading.

This module provides a single entry point that runs all protection
checks in one cycle:
1. OCO reconciliation (verify/repair SL/TP)
2. Exit manager check (profit lock, trailing, time stop)
3. Broker health verification

Events emitted:
- PROTECT_LOOP_TICK: Each cycle completion (proves loop is running)
- Plus all events from OCO reconciler and exit manager
"""
from __future__ import annotations
import os
import time
import logging
import threading
import json
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# State file for observability
STATE_FILE = os.getenv('PROTECT_STATE_FILE', 'ops/state/protect_loop.json')


def _ensure_state_dir():
  """Ensure state directory exists."""
  import pathlib
  pathlib.Path(STATE_FILE).parent.mkdir(parents=True, exist_ok=True)


def _write_state(state: Dict[str, Any]) -> None:
  """Write state to JSON file."""
  try:
    _ensure_state_dir()
    state['updated_at'] = datetime.utcnow().isoformat() + 'Z'
    with open(STATE_FILE, 'w') as f:
      json.dump(state, f, indent=2, default=str)
  except Exception as e:
    logger.warning(f'Failed to write protect loop state: {e}')


def _log_event(event_type: str, details: Dict[str, Any]) -> None:
  """Log event to durable narration stream."""
  try:
    from multi_broker_phoenix.monitor.pnl_kill_switch import _log_event as durable_log
    durable_log(event_type, details)
  except Exception:
    logger.info(f'PROTECT_EVENT: {event_type} {details}')


def run_protect_once(connector, account_id: str = None) -> Dict[str, Any]:
  """Run a single protection cycle."""
  ts = time.time()
  results = {
    'timestamp': ts,
    'oco': None,
    'exit_manager': None,
    'broker_health': None,
    'errors': [],
  }

  try:
    from multi_broker_phoenix.risk.oco_reconcile import run_oco_reconcile_once
    from execution.oanda_practice_client import OandaPracticeClient

    oco_client = OandaPracticeClient(
      token=connector.token,
      account_id=account_id or connector.account_id,
      base_url=connector.base_url,
      http_client=getattr(connector, 'http', None)
    )
    results['oco'] = run_oco_reconcile_once(oco_client)
  except Exception as e:
    results['errors'].append(f'OCO reconcile error: {e}')
    logger.error(f'Protect loop OCO error: {e}')

  try:
    from multi_broker_phoenix.risk.exit_manager import get_exit_manager
    em = get_exit_manager()
    if em:
      results['exit_manager'] = em.check_all_positions()
    else:
      results['exit_manager'] = {'skipped': True, 'reason': 'not_initialized'}
  except Exception as e:
    results['errors'].append(f'Exit manager error: {e}')
    logger.error(f'Protect loop exit manager error: {e}')

  try:
    from multi_broker_phoenix.risk.broker_health import get_health_state
    results['broker_health'] = get_health_state()
  except ImportError:
    results['broker_health'] = {'skipped': True, 'reason': 'module_not_available'}
  except Exception as e:
    results['errors'].append(f'Broker health error: {e}')
    logger.error(f'Protect loop broker health error: {e}')

  _log_event('PROTECT_LOOP_TICK', {
    'timestamp': ts,
    'oco_ok': results.get('oco', {}).get('ok', 0) if results.get('oco') else 0,
    'oco_missing': results.get('oco', {}).get('missing', 0) if results.get('oco') else 0,
    'oco_repaired': results.get('oco', {}).get('repaired', 0) if results.get('oco') else 0,
    'exit_profit_locks': results.get('exit_manager', {}).get('profit_locks', 0) if results.get('exit_manager') else 0,
    'broker_healthy': results.get('broker_health', {}).get('healthy', False) if results.get('broker_health') else False,
    'errors': len(results['errors']),
  })
  logger.info('PROTECT_LOOP_TICK timestamp=%s errors=%s', ts, len(results['errors']))

  _write_state(results)
  return results


_protect_thread: Optional[threading.Thread] = None
_stop_event = threading.Event()


def start_protect_loop(connector, interval_sec: int = None, account_id: str = None) -> threading.Thread:
  global _protect_thread, _stop_event

  interval = interval_sec or int(os.getenv('PROTECT_LOOP_INTERVAL', '30'))

  _stop_event.clear()

  def _run():
    logger.info(f'Protect loop started (interval={interval}s)')
    while not _stop_event.is_set():
      try:
        run_protect_once(connector, account_id)
      except Exception as e:
        logger.exception(f'Protect loop error: {e}')
      _stop_event.wait(interval)
    logger.info('Protect loop stopped')

  _protect_thread = threading.Thread(target=_run, daemon=True, name='protect_loop')
  _protect_thread.start()
  return _protect_thread


def stop_protect_loop() -> None:
  global _stop_event
  _stop_event.set()
  if _protect_thread and _protect_thread.is_alive():
    _protect_thread.join(timeout=5)


def get_protect_state() -> Dict[str, Any]:
  try:
    with open(STATE_FILE, 'r') as f:
      return json.load(f)
  except Exception:
    return {}


if __name__ == '__main__':
  print("Protect Loop module loaded successfully")
  print(f"State file: {STATE_FILE}")
EOF

cat <<'EOF' > "$ROOT/MULTI_BROKER_PHOENIX/multi_broker_phoenix/monitor/watchdog.py"
"""Always-on connection watchdog for brokers and AI services."""
from __future__ import annotations
import threading
import time
import requests
import logging
import os
import subprocess
import json
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

try:
  from ai_router.router import AIRouter
except Exception:
  AIRouter = None

logger = logging.getLogger(__name__)

WATCHDOG_STATE: Dict[str, Any] = {
  'ok': True,
  'last_check': None,
  'details': {}
}

_TRADING_ALLOWED = True
_RECONNECT_CALLBACKS: list = []


def _log_event(event_type: str, details: Dict[str, Any]):
  try:
    from multi_broker_phoenix.monitor import pnl_kill_switch as pk
    pk._log_event(event_type, details)
  except Exception:
    try:
      logger.info('EVENT: %s %s', event_type, details)
    except Exception:
      pass


def register_reconnect_callback(cb):
  try:
    if callable(cb):
      _RECONNECT_CALLBACKS.append(cb)
      return True
  except Exception:
    pass
  return False


def unregister_reconnect_callback(cb):
  try:
    if cb in _RECONNECT_CALLBACKS:
      _RECONNECT_CALLBACKS.remove(cb)
      return True
  except Exception:
    pass
  return False


def trading_allowed() -> bool:
  return _TRADING_ALLOWED


def _set_trading_allowed(val: bool):
  global _TRADING_ALLOWED
  _TRADING_ALLOWED = bool(val)


def _check_oanda(oanda_connector) -> bool:
  try:
    r = oanda_connector.verify_credentials()
    return r.get('success', False)
  except Exception:
    return False


def _check_endpoint(url: str, timeout: float = 5.0, headers: Optional[Dict[str, str]] = None) -> Tuple[bool, Optional[int], Optional[str]]:
  try:
    r = requests.get(url, timeout=timeout, headers=headers)
    code = getattr(r, 'status_code', None)
    if code == 200:
      return True, code, 'OK'
    if code in (401, 403):
      return False, code, 'AUTH_FAIL'
    return False, code, f'HTTP_{code}'
  except Exception as e:
    return False, None, f'EXCEPTION_{str(e)}'


def _state_age_seconds(path: str) -> Optional[float]:
  try:
    p = Path(path)
    if not p.exists():
      return None
    return time.time() - p.stat().st_mtime
  except Exception:
    return None


def heartbeat_status() -> Dict[str, Any]:
  max_skew = int(os.getenv('HEARTBEAT_MAX_SKEW_SEC', '180'))
  enforce_missing = os.getenv('HEARTBEAT_ENFORCE_MISSING', '0').lower() in ('1', 'true', 'yes')
  exit_state = os.getenv('HEARTBEAT_EXIT_STATE_FILE', 'ops/state/exit_manager.json')
  protect_state = os.getenv('HEARTBEAT_PROTECT_STATE_FILE', 'ops/state/protect_loop.json')
  watchdog_state = os.getenv('HEARTBEAT_WATCHDOG_STATE_FILE', 'ops/state/watchdog.json')

  ages = {
    'exit_manager': _state_age_seconds(exit_state),
    'protect_loop': _state_age_seconds(protect_state),
    'watchdog': _state_age_seconds(watchdog_state),
  }

  stale = []
  for k, age in ages.items():
    if age is None and not enforce_missing:
      continue
    if age is None or age > max_skew:
      stale.append(k)

  return {
    'ok': len(stale) == 0,
    'max_skew_sec': max_skew,
    'enforce_missing': enforce_missing,
    'ages_sec': ages,
    'stale': stale,
  }


def _write_watchdog_state() -> None:
  path = os.getenv('HEARTBEAT_WATCHDOG_STATE_FILE', 'ops/state/watchdog.json')
  try:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, 'w') as f:
      f.write(str(int(time.time())))
  except Exception:
    pass


def _failsafe_flatten(oanda_connector, reason: str, details: Dict[str, Any]) -> bool:
  try:
    from execution.oanda_practice_client import OandaPracticeClient
    client = OandaPracticeClient(
      token=oanda_connector.token,
      account_id=oanda_connector.account_id,
      base_url=oanda_connector.base_url,
      http_client=getattr(oanda_connector, 'http', None)
    )
    res = client.close_all_positions()
    _log_event('HEARTBEAT_FAILSAFE_FLATTEN', {'reason': reason, 'details': details, 'result': res})
    _set_trading_allowed(False)
    return True
  except Exception as e:
    _log_event('HEARTBEAT_FAILSAFE_ERROR', {'reason': reason, 'error': str(e)})
    try:
      _set_trading_allowed(False)
    except Exception:
      pass
    return False


def _maybe_run_repair(ai_details: Dict[str, Any]) -> None:
  if os.getenv('AI_REPAIR_ENABLED', '1').lower() not in ('1', 'true', 'yes'):
    return
  state_file = os.getenv('AI_REPAIR_LAST_FILE', 'ops/state/ai_repair_last.json')
  min_interval = int(os.getenv('AI_REPAIR_MIN_INTERVAL', '300'))
  now = time.time()

  last_ts = 0.0
  try:
    with open(state_file, 'r') as f:
      last_ts = float(json.load(f).get('last_ts', 0.0))
  except Exception:
    last_ts = 0.0

  if now - last_ts < min_interval:
    return

  script = '/home/ing/RICK/MULTI_BROKER_PHOENIX/tools/ai_repair.sh'
  try:
    res = subprocess.run([script], check=False, capture_output=True, text=True)
    with open(state_file, 'w') as f:
      json.dump({'last_ts': now, 'exit_code': res.returncode}, f)
    _log_event('AI_REPAIR_TRIGGER', {'exit_code': res.returncode})
  except Exception as e:
    _log_event('AI_REPAIR_ERROR', {'error': str(e)})


def _log_freeze_change(ok: bool, details: Dict[str, Any]):
  ts = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
  if not ok:
    logger.critical('WATCHDOG FREEZE %s - details=%s', ts, details)
  else:
    logger.info('WATCHDOG UNFREEZE %s - details=%s', ts, details)


def run_watchdog_once(oanda_connector, grok_url: Optional[str], deepseek_url: Optional[str], invoke_callbacks_async: bool = True) -> Dict[str, Any]:
  details: Dict[str, Any] = {}
  ok = True

  try:
    o_ok = _check_oanda(oanda_connector)
    details['oanda'] = {'ok': bool(o_ok)}
    if not o_ok:
      ok = False
  except Exception as e:
    details['oanda'] = {'ok': False, 'reason': str(e)}
    ok = False
    logger.exception('Watchdog OANDA check failed: %s', e)

  require_ai = os.getenv('REQUIRE_AI', '0').lower() in ('1', 'true', 'yes')
  ai_ok = True
  local_ok = False
  cloud_ok = False
  if require_ai:
    try:
      if AIRouter is None:
        raise RuntimeError('AIRouter unavailable')
      router = AIRouter()
      evals = router.evaluate()
      ai_ok = bool(evals.get('ai_ok'))
      local_ok = bool(evals.get('local_ok'))
      cloud_ok = bool(evals.get('cloud_ok'))
      details['ai_seats'] = evals
      if local_ok and not cloud_ok:
        _maybe_run_repair(evals)
    except Exception as e:
      details['ai_seats'] = {'ok': False, 'reason': str(e)}
      ai_ok = False

    if not ai_ok:
      ok = False

  hb = heartbeat_status()
  details['heartbeat'] = hb
  if not hb.get('ok', True):
    ok = False
    if os.getenv('HEARTBEAT_FAILSAFE_FLATTEN', '1').lower() in ('1', 'true', 'yes'):
      try:
        _failsafe_flatten(oanda_connector, 'HEARTBEAT_STALE', hb)
      except Exception:
        pass

  action = 'ALLOW' if ok else 'FREEZE'
  logger.info('WATCHDOG: ai_ok=%s local_ok=%s cloud_ok=%s action=%s', ai_ok, local_ok, cloud_ok, action)

  prev_ok = WATCHDOG_STATE.get('ok', True)
  WATCHDOG_STATE['ok'] = ok
  WATCHDOG_STATE['last_check'] = time.time()
  WATCHDOG_STATE['details'] = details

  if not ok:
    _set_trading_allowed(False)
  else:
    _set_trading_allowed(True)

  _write_watchdog_state()

  if not prev_ok and ok:
    try:
      _log_event('WATCHDOG_UNFREEZE', {'details': details, 'timestamp': WATCHDOG_STATE.get('last_check')})
    except Exception:
      logger.exception('Watchdog: failed to record WATCHDOG_UNFREEZE event')

    try:
      for cb in list(_RECONNECT_CALLBACKS):
        try:
          if invoke_callbacks_async:
            threading.Thread(target=lambda c=cb: c(oanda_connector), daemon=True).start()
          else:
            c = cb
            c(oanda_connector)
        except Exception:
          logger.exception('Watchdog: failed to start/invoke reconnect callback')
    except Exception:
      logger.exception('Watchdog: failed to invoke reconnect callbacks')
  elif not ok and prev_ok:
    try:
      _log_event('WATCHDOG_FREEZE', {'details': details, 'timestamp': WATCHDOG_STATE.get('last_check')})
    except Exception:
      logger.exception('Watchdog: failed to record WATCHDOG_FREEZE event')

  _log_event('WATCHDOG_TICK', {'details': details, 'timestamp': WATCHDOG_STATE.get('last_check')})
  _log_freeze_change(ok, details)

  return dict(WATCHDOG_STATE)


def _run_watchdog(oanda_connector, grok_url: str | None, deepseek_url: str | None, interval: int = 15):
  while True:
    try:
      run_watchdog_once(oanda_connector, grok_url, deepseek_url)
    except Exception:
      logger.exception('Watchdog iteration failed')
    time.sleep(interval)


def start_watchdog(oanda_connector, grok_url: str | None = None, deepseek_url: str | None = None, interval: int = 15):
  t = threading.Thread(target=_run_watchdog, args=(oanda_connector, grok_url, deepseek_url, interval), daemon=True, name='watchdog')
  t.start()
  return t
EOF

chmod +x "$ROOT/tools/brain_gate.sh" "$ROOT/tools/brain_health.sh" "$ROOT/tools/ai_health.sh" "$ROOT/tools/ai_repair.sh" "$ROOT/tools/holdtime_audit.sh"
chmod +x "$ROOT/ops/selftest_ai_brain_gate.sh"
chmod +x "$ROOT/tools/task_runner.sh"

# Run self-tests
set +e
bash "$ROOT/ops/selftest_ai_brain_gate.sh" | tee "$SELFTEST_OUT"
SELFTEST_CODE=${PIPESTATUS[0]}
set -e

# Write manifest
python3 - <<PY
import hashlib, json
files = [
  "$ROOT/llm_gate/ollama_gate.py",
  "$ROOT/ai_router/router.py",
  "$ROOT/ai_router/providers/ollama_provider.py",
  "$ROOT/ai_router/providers/xai_provider.py",
  "$ROOT/ai_router/providers/deepseek_provider.py",
  "$ROOT/ops/selftest_ai_brain_gate.sh",
  "$ROOT/tools/brain_gate.sh",
  "$ROOT/tools/brain_health.sh",
  "$ROOT/tools/ai_health.sh",
  "$ROOT/tools/ai_repair.sh",
  "$ROOT/tools/holdtime_audit.sh",
  "$ROOT/config/toggles.env",
  "$ROOT/tools/task_runner.sh",
  "$ROOT/.vscode/tasks.json",
  "$ROOT/multi_broker_phoenix/risk/exit_manager.py",
  "$ROOT/multi_broker_phoenix/risk/protect_loop.py",
  "$ROOT/MULTI_BROKER_PHOENIX/multi_broker_phoenix/monitor/watchdog.py",
]

def sha(path):
  try:
    with open(path, "rb") as f:
      return hashlib.sha256(f.read()).hexdigest()
  except Exception:
    return ""

manifest = {"generated_at": "$TS", "files": {p: sha(p) for p in files}}
with open("$MANIFEST", "w") as f:
  json.dump(manifest, f, indent=2)
PY

if [[ $SELFTEST_CODE -eq 0 ]]; then
  echo "✅ PATCH PASS"
  exit 0
else
  echo "❌ PATCH FAIL"
  exit 1
fi
