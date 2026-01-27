"""Runtime state manager (persists transient runtime disables)"""
from __future__ import annotations
import json
from pathlib import Path

RUNTIME_PATH = Path.home() / '.rbotzilla' / 'runtime_state.json'
RUNTIME_PATH.parent.mkdir(parents=True, exist_ok=True)


def load_runtime_state() -> dict:
    if not RUNTIME_PATH.exists():
        return {}
    try:
        with open(RUNTIME_PATH, 'r') as f:
            return json.load(f)
    except Exception:
        return {}


def save_runtime_state(obj: dict):
    with open(RUNTIME_PATH, 'w') as f:
        json.dump(obj, f)
