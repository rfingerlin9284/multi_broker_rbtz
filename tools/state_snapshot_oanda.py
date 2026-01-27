#!/usr/bin/env python3
"""State snapshot helper for OANDA FIFO investigations.

Outputs a markdown snapshot for a given instrument and time window using:
1) Local logs (engine_headless.log, logs/oanda/engine.log)
2) OANDA REST (open trades, positions, pending orders, transactions)

Never prints API tokens.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import requests
except Exception:
    requests = None


DEFAULT_LOGS = [
    "/home/ing/RICK/MULTI_BROKER_PHOENIX/logs/engine_headless.log",
    "/home/ing/RICK/MULTI_BROKER_PHOENIX/logs/oanda/engine.log",
]

TIME_RE = re.compile(r"'time':\s*'([^']+Z)'")
INSTR_RE = re.compile(r"'instrument':\s*'([^']+)'")
TRADE_OPEN_RE = re.compile(r"'tradeOpened':\s*\{'price':\s*'([^']+)',\s*'tradeID':\s*'([^']+)'\,\s*'units':\s*'([^']+)'")
FIFO_RE = re.compile(r"FIFO_VIOLATION_SAFEGUARD_VIOLATION")


def _parse_time(ts: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


def _read_log_lines(path: str) -> List[str]:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.readlines()
    except Exception:
        return []


def _filter_window(ts: Optional[datetime], start: datetime, end: datetime) -> bool:
    if ts is None:
        return False
    return start <= ts <= end


def _extract_fifo_lines(lines: List[str], instrument: str, start: datetime, end: datetime) -> List[str]:
    hits = []
    for line in lines:
        if instrument not in line:
            continue
        if not FIFO_RE.search(line):
            continue
        ts_match = TIME_RE.search(line)
        ts = _parse_time(ts_match.group(1)) if ts_match else None
        if ts and _filter_window(ts, start, end):
            hits.append(line.rstrip("\n"))
    return hits


def _extract_trade_opens(lines: List[str], instrument: str, before: datetime) -> List[Dict[str, Any]]:
    trades = []
    for line in lines:
        if instrument not in line:
            continue
        if "tradeOpened" not in line:
            continue
        ts_match = TIME_RE.search(line)
        ts = _parse_time(ts_match.group(1)) if ts_match else None
        if ts and ts <= before:
            m = TRADE_OPEN_RE.search(line)
            if not m:
                continue
            price, trade_id, units = m.group(1), m.group(2), m.group(3)
            trades.append({
                "time": ts.isoformat().replace("+00:00", "Z"),
                "trade_id": trade_id,
                "units": units,
                "price": price,
                "raw": line.rstrip("\n"),
            })
    return trades


def _get_env(name: str) -> Optional[str]:
    v = os.getenv(name)
    return v if v else None


def _http_get(url: str, token: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if requests is None:
        raise RuntimeError("requests not installed")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    resp = requests.get(url, headers=headers, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


def _oanda_fetch(account_id: str, token: str, base_url: str, start: datetime, end: datetime) -> Dict[str, Any]:
    base = base_url.rstrip("/")
    return {
        "open_trades": _http_get(f"{base}/v3/accounts/{account_id}/openTrades", token),
        "open_positions": _http_get(f"{base}/v3/accounts/{account_id}/openPositions", token),
        "pending_orders": _http_get(f"{base}/v3/accounts/{account_id}/pendingOrders", token),
        "transactions": _http_get(
            f"{base}/v3/accounts/{account_id}/transactions",
            token,
            params={
                "from": start.isoformat().replace("+00:00", "Z"),
                "to": end.isoformat().replace("+00:00", "Z"),
            },
        ),
    }


def _filter_instrument(items: List[Dict[str, Any]], instrument: str) -> List[Dict[str, Any]]:
    return [i for i in items if i.get("instrument") == instrument]


def _safe_json(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=False)


def main() -> int:
    ap = argparse.ArgumentParser(description="OANDA state snapshot helper")
    ap.add_argument("--instrument", required=True)
    ap.add_argument("--from", dest="start", required=True)
    ap.add_argument("--to", dest="end", required=True)
    ap.add_argument("--log", action="append", default=[])
    ap.add_argument("--no-oanda", action="store_true")
    args = ap.parse_args()

    instrument = args.instrument
    start = _parse_time(args.start)
    end = _parse_time(args.end)
    if not start or not end:
        print("Invalid --from/--to; use ISO8601 with Z")
        return 2

    logs = args.log or DEFAULT_LOGS

    # Log-derived snapshot
    log_lines: List[str] = []
    for lp in logs:
        log_lines.extend(_read_log_lines(lp))

    fifo_lines = _extract_fifo_lines(log_lines, instrument, start, end)
    trade_opens = _extract_trade_opens(log_lines, instrument, start)

    print("# OANDA State Snapshot (log-derived)")
    print(f"- Instrument: {instrument}")
    print(f"- Window: {start.isoformat().replace('+00:00', 'Z')} .. {end.isoformat().replace('+00:00', 'Z')}")
    print("\n## FIFO cancel lines (log-derived)")
    if fifo_lines:
        for line in fifo_lines:
            print(f"- {line}")
    else:
        print("- (none found in logs)")

    print("\n## Trade opens before window (log-derived)")
    if trade_opens:
        for t in trade_opens:
            print(f"- time={t['time']} tradeID={t['trade_id']} units={t['units']} price={t['price']}")
    else:
        print("- (none found in logs)")

    if args.no_oanda:
        print("\n## OANDA live snapshot")
        print("- Skipped (--no-oanda)")
        return 0

    token = _get_env("OANDA_API_TOKEN") or _get_env("OANDA_TOKEN")
    account_id = _get_env("OANDA_ACCOUNT_ID")
    base_url = _get_env("OANDA_API_URL") or "https://api-fxpractice.oanda.com"

    if not token or not account_id:
        print("\n## OANDA live snapshot")
        print("- Unavailable (missing OANDA_API_TOKEN/OANDA_TOKEN or OANDA_ACCOUNT_ID)")
        return 0

    try:
        data = _oanda_fetch(account_id, token, base_url, start, end)
    except Exception as exc:
        print("\n## OANDA live snapshot")
        print(f"- Error querying OANDA: {exc}")
        return 1

    open_trades = _filter_instrument(data.get("open_trades", {}).get("trades", []), instrument)
    open_positions = _filter_instrument(data.get("open_positions", {}).get("positions", []), instrument)
    pending_orders = _filter_instrument(data.get("pending_orders", {}).get("orders", []), instrument)
    transactions = _filter_instrument(data.get("transactions", {}).get("transactions", []), instrument)

    print("\n## OANDA live snapshot")
    print("### Open trades (filtered)")
    print(_safe_json(open_trades) if open_trades else "[]")

    print("\n### Open positions (filtered)")
    print(_safe_json(open_positions) if open_positions else "[]")

    print("\n### Pending orders (filtered)")
    print(_safe_json(pending_orders) if pending_orders else "[]")

    print("\n### Transactions in window (filtered)")
    print(_safe_json(transactions) if transactions else "[]")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
