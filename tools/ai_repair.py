#!/usr/bin/env python3
"""Deterministic AI seat repair runner."""
from __future__ import annotations
import json


def main() -> int:
    try:
        from multi_broker_phoenix.ai.repair_agent import ProviderRepairAgent
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}))
        return 1

    agent = ProviderRepairAgent()
    result = agent.run_once()
    print(json.dumps({"ok": True, "result": result}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
