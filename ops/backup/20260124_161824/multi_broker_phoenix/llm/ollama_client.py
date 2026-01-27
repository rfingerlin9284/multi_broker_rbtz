"""Ollama client for local brain seat health + inference."""
from __future__ import annotations
import os
import logging
from typing import Dict, Any, Optional

import requests

logger = logging.getLogger(__name__)


def _ollama_url() -> str:
    return os.getenv('OLLAMA_URL', 'http://127.0.0.1:11434')


def _ollama_model() -> str:
    return os.getenv('OLLAMA_MODEL', 'llama3.1:8b')


def health(timeout: float = 2.0) -> Dict[str, Any]:
    """Check Ollama health and model availability."""
    url = _ollama_url().rstrip('/') + '/api/tags'
    model = _ollama_model()
    try:
        resp = requests.get(url, timeout=timeout)
        code = getattr(resp, 'status_code', None)
        if code != 200:
            return {'ok': False, 'status_code': code, 'reason': f'HTTP_{code}'}
        data = resp.json() if hasattr(resp, 'json') else {}
        models = data.get('models') or []
        names = [m.get('name') for m in models if isinstance(m, dict)]
        model_present = model in names
        return {
            'ok': model_present,
            'status_code': code,
            'model': model,
            'model_present': model_present,
            'available_models': names,
        }
    except Exception as e:
        return {'ok': False, 'status_code': None, 'reason': f'EXCEPTION_{str(e)}'}


def generate(prompt: str, model: Optional[str] = None, timeout: float = 10.0, **kwargs) -> Dict[str, Any]:
    """Call Ollama /api/generate."""
    url = _ollama_url().rstrip('/') + '/api/generate'
    payload = {
        'model': model or _ollama_model(),
        'prompt': prompt,
        **kwargs,
    }
    resp = requests.post(url, json=payload, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def chat(messages: list, model: Optional[str] = None, timeout: float = 10.0, **kwargs) -> Dict[str, Any]:
    """Call Ollama /api/chat."""
    url = _ollama_url().rstrip('/') + '/api/chat'
    payload = {
        'model': model or _ollama_model(),
        'messages': messages,
        **kwargs,
    }
    resp = requests.post(url, json=payload, timeout=timeout)
    resp.raise_for_status()
    return resp.json()
