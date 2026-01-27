#!/usr/bin/env python3
"""Deterministic AI seat status snapshot."""
from __future__ import annotations
import json
import argparse


def main() -> int:
    parser = argparse.ArgumentParser(description="AI seat status")
    parser.add_argument("--no-refresh", action="store_true", help="Do not run live health checks")
    args = parser.parse_args()

    try:
        from multi_broker_phoenix.ai.seat_router import AISeatRouter
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}))
        return 1

    router = AISeatRouter()
    if args.no_refresh:
        snapshot = router.status_snapshot()
    else:
        router.refresh_health()
        snapshot = router.status_snapshot()

    print(json.dumps({"ok": True, "status": snapshot}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
