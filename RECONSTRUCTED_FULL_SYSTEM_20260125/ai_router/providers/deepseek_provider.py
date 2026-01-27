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
