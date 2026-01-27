from __future__ import annotations
import os
import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple, List

import requests


@dataclass
class ProviderStatus:
    name: str
    ok: bool
    code: int
    reason: str
    latency_ms: int


class BrainSeatRouter:
    """
    Selects the best available 'brain seat' for decision support.
    CRITICAL RULE: trading is allowed if ANY seat is healthy.
    """

    def __init__(self):
        self.ollama_url = os.getenv("OLLAMA_URL", os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")).rstrip("/")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "llama3.1:8b")

        self.require_xai = os.getenv("REQUIRE_XAI", "0") == "1"
        self.require_deepseek = os.getenv("REQUIRE_DEEPSEEK", "0") == "1"
        self.disable_openai = os.getenv("DISABLE_OPENAI", "true").lower() == "true"

        # Soft-disable cache with backoff
        self.disabled_until: Dict[str, float] = {}

    def _disabled(self, name: str) -> bool:
        until = self.disabled_until.get(name, 0.0)
        return time.time() < until

    def soft_disable(self, name: str, seconds: int, reason: str):
        self.disabled_until[name] = time.time() + max(5, seconds)

    def health_ollama(self, timeout_s: float = 2.0) -> ProviderStatus:
        start = time.time()
        try:
            r = requests.get(f"{self.ollama_url}/api/tags", timeout=timeout_s)
            ms = int((time.time() - start) * 1000)
            if r.status_code == 200:
                return ProviderStatus("ollama", True, 200, "OK", ms)
            return ProviderStatus("ollama", False, r.status_code, "HTTP_" + str(r.status_code), ms)
        except Exception as e:
            ms = int((time.time() - start) * 1000)
            return ProviderStatus("ollama", False, 0, f"EXC:{type(e).__name__}", ms)

    def health_xai(self) -> ProviderStatus:
        start = time.time()
        base = os.getenv("XAI_BASE_URL", "https://api.x.ai").rstrip("/")
        key = os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY")
        url = f"{base}/v1/models" if not base.endswith("/v1") else f"{base}/models"
        headers = {"Authorization": f"Bearer {key}"} if key else None
        try:
            r = requests.get(url, headers=headers, timeout=3)
            ms = int((time.time() - start) * 1000)
            if r.status_code == 200:
                return ProviderStatus("grok", True, 200, "OK", ms)
            return ProviderStatus("grok", False, r.status_code, "HTTP_" + str(r.status_code), ms)
        except Exception as e:
            ms = int((time.time() - start) * 1000)
            return ProviderStatus("grok", False, 0, f"EXC:{type(e).__name__}", ms)

    def health_deepseek(self) -> ProviderStatus:
        start = time.time()
        base = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
        key = os.getenv("DEEPSEEK_API_KEY")
        url = f"{base}/v1/models" if not base.endswith("/v1") else f"{base}/models"
        headers = {"Authorization": f"Bearer {key}"} if key else None
        try:
            r = requests.get(url, headers=headers, timeout=3)
            ms = int((time.time() - start) * 1000)
            if r.status_code == 200:
                return ProviderStatus("deepseek", True, 200, "OK", ms)
            return ProviderStatus("deepseek", False, r.status_code, "HTTP_" + str(r.status_code), ms)
        except Exception as e:
            ms = int((time.time() - start) * 1000)
            return ProviderStatus("deepseek", False, 0, f"EXC:{type(e).__name__}", ms)

    def snapshot(self) -> Dict[str, dict]:
        statuses: List[ProviderStatus] = []
        statuses.append(self.health_ollama())
        if not self._disabled("grok"):
            statuses.append(self.health_xai())
        if not self._disabled("deepseek"):
            statuses.append(self.health_deepseek())

        return {s.name: {"ok": s.ok, "code": s.code, "reason": s.reason, "latency_ms": s.latency_ms} for s in statuses}

    def any_brain_ok(self) -> Tuple[bool, Dict[str, dict], Optional[str]]:
        snap = self.snapshot()

        ok_any = any(v.get("ok") for v in snap.values())
        chosen = None
        if snap.get("ollama", {}).get("ok"):
            chosen = "ollama"
        else:
            for k, v in snap.items():
                if v.get("ok"):
                    chosen = k
                    break

        return ok_any, snap, chosen
