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
