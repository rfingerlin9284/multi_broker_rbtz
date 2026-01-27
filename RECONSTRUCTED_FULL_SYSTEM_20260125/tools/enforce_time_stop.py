#!/usr/bin/env python3
"""Deterministic time-stop enforcement for OANDA trades."""
from __future__ import annotations
import os
import json
from datetime import datetime


def _parse_open_time(open_time_str: str) -> datetime:
    open_time_str = open_time_str.split('.')[0]
    return datetime.fromisoformat(open_time_str.replace('Z', '+00:00'))


def main() -> int:
    token = os.getenv('OANDA_API_TOKEN')
    account_id = os.getenv('OANDA_PRACTICE_ACCOUNT_ID') or os.getenv('OANDA_ACCOUNT_ID')
    base_url = os.getenv('OANDA_API_URL', 'https://api-fxpractice.oanda.com')
    hard_max_hours = float(os.getenv('HARD_MAX_TRADE_HOURS', '8.0'))

    if not token or not account_id:
        print(json.dumps({"ok": False, "error": "Missing OANDA_API_TOKEN or OANDA_ACCOUNT_ID"}))
        return 1

    try:
        from execution.oanda_practice_client import OandaPracticeClient
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}))
        return 1

    client = OandaPracticeClient(token=token, account_id=account_id, base_url=base_url)
    trades = client.list_open_trades().get('trades', [])

    now = datetime.utcnow()
    closed = []
    skipped = []

    for t in trades:
        trade_id = t.get('id') or t.get('tradeID') or t.get('trade_id')
        instrument = t.get('instrument')
        open_time_str = t.get('openTime') or ''
        if not trade_id or not instrument or not open_time_str:
            skipped.append({"trade_id": trade_id, "reason": "missing_fields"})
            continue
        try:
            open_time = _parse_open_time(open_time_str)
            hours_open = (now - open_time.replace(tzinfo=None)).total_seconds() / 3600
        except Exception:
            skipped.append({"trade_id": trade_id, "reason": "bad_open_time"})
            continue
        if hours_open >= hard_max_hours:
            try:
                client.close_position(instrument)
                closed.append({"trade_id": trade_id, "instrument": instrument, "hours_open": round(hours_open, 4)})
            except Exception as e:
                skipped.append({"trade_id": trade_id, "reason": f"close_failed:{e}"})
        else:
            skipped.append({"trade_id": trade_id, "reason": "under_limit"})

    print(json.dumps({
        "ok": True,
        "hard_max_hours": hard_max_hours,
        "closed": closed,
        "skipped": skipped,
        "open_trades": len(trades)
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
