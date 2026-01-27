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
