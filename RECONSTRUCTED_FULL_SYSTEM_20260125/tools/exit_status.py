#!/usr/bin/env python3
"""Deterministic exit/heartbeat status snapshot."""
from __future__ import annotations
import os
import json
import time
from pathlib import Path


def _age(path: str):
    p = Path(path)
    if not p.exists():
        return None
    return time.time() - p.stat().st_mtime


def _read_json(path: str):
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception:
        return None


def main() -> int:
    exit_state = os.getenv('HEARTBEAT_EXIT_STATE_FILE', 'ops/state/exit_manager.json')
    protect_state = os.getenv('HEARTBEAT_PROTECT_STATE_FILE', 'ops/state/protect_loop.json')
    max_skew = int(os.getenv('HEARTBEAT_MAX_SKEW_SEC', '180'))

    ages = {
        "exit_manager": _age(exit_state),
        "protect_loop": _age(protect_state),
    }

    stale = [k for k, v in ages.items() if v is None or v > max_skew]

    payload = {
        "ok": len(stale) == 0,
        "max_skew_sec": max_skew,
        "ages_sec": ages,
        "stale": stale,
        "exit_manager_state": _read_json(exit_state),
        "protect_loop_state": _read_json(protect_state),
    }

    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
