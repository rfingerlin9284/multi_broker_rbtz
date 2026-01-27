#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/ing/RICK/MULTI_BROKER_PHOENIX"

_ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }
_commit() { git -C "$ROOT" rev-parse HEAD 2>/dev/null || echo "UNKNOWN"; }
_toggles_hash() { sha256sum "$ROOT/config/toggles.env" 2>/dev/null | awk '{print $1}'; }

echo "timestamp=$(_ts)"
echo "commit=$(_commit)"
echo "toggles_hash=$(_toggles_hash)"

python3 - <<'PY'
import os, time
from datetime import datetime
from execution.oanda_practice_client import OandaPracticeClient

soft = int(os.getenv("SOFT_MAX_HOLD_SECONDS", "21600"))
hard = int(os.getenv("MAX_HOLD_SECONDS", "28800"))

client = OandaPracticeClient(
    token=os.getenv("OANDA_API_TOKEN"),
    account_id=os.getenv("OANDA_PRACTICE_ACCOUNT_ID") or os.getenv("OANDA_ACCOUNT_ID"),
    base_url=os.getenv("OANDA_API_URL", "https://api-fxpractice.oanda.com"),
)

trades = client.list_open_trades().get("trades", [])
now = datetime.utcnow()
flags = {"soft": 0, "hard": 0}

for t in trades:
    ot = t.get("openTime", "")
    tid = t.get("id")
    if not ot:
        continue
    try:
        ot = ot.split(".")[0]
        open_time = datetime.fromisoformat(ot.replace("Z", "+00:00"))
        age = (now - open_time.replace(tzinfo=None)).total_seconds()
        mark = "OK"
        if age >= hard:
            mark = "HARD"
            flags["hard"] += 1
        elif age >= soft:
            mark = "SOFT"
            flags["soft"] += 1
        print(f"trade={tid} age_sec={int(age)} flag={mark}")
    except Exception:
        continue

if flags["hard"] > 0:
    print("FAIL")
else:
    print("PASS")
PY
