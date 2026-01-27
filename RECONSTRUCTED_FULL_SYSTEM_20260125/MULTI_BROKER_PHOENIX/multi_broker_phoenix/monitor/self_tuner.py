"""Self-tuning loop that evaluates recent bot reports and applies safe knobs.

Runs every 10 minutes and may tighten OANDA_MAX_UNITS_* caps or disable symbols by
writing to the project's .env file (idempotent). Logs actions to logs/self_tune.log
and prints status lines for visibility.
"""
from __future__ import annotations
import time
import json
import os
from pathlib import Path
from datetime import datetime, timedelta

HISTORY_PATH = Path(__file__).resolve().parent.parent / 'logs' / 'bot_report_history.ndjson'
SELF_TUNE_LOG = Path(__file__).resolve().parent.parent / 'logs' / 'self_tune.log'
ENV_PATH = Path(__file__).resolve().parent.parent / '.env'


def _read_recent_reports(minutes: int = 10):
    now = time.time()
    res = []
    if not HISTORY_PATH.exists():
        return res
    cutoff = now - minutes * 60
    with open(HISTORY_PATH, 'r') as f:
        for line in f:
            try:
                obj = json.loads(line)
                ts = obj.get('timestamp', now)
                if ts >= cutoff:
                    res.append(obj)
            except Exception:
                continue
    return res


def _write_self_tune_log(line: str):
    SELF_TUNE_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(SELF_TUNE_LOG, 'a') as f:
        f.write(f"{datetime.now().isoformat()} {line}\n")


def _apply_env_change(key: str, before: str | None, after: str):
    # idempotent: modify .env by replacing or appending the key
    if not ENV_PATH.exists():
        ENV_PATH.write_text(f"{key}={after}\n")
        _write_self_tune_log(f"SELF_TUNE_APPLY: {key} {before or '<missing>'}->{after} reason=auto-tighten")
        return True
    changed = False
    lines = ENV_PATH.read_text().splitlines()
    out = []
    found = False
    for l in lines:
        if l.strip().startswith(f"{key}="):
            out.append(f"{key}={after}")
            found = True
            changed = True
        else:
            out.append(l)
    if not found:
        out.append(f"{key}={after}")
        changed = True
    if changed:
        ENV_PATH.write_text('\n'.join(out) + '\n')
        _write_self_tune_log(f"SELF_TUNE_APPLY: {key} {before or '<missing>'}->{after} reason=auto-tighten")
    return changed


def evaluate_and_apply(minutes: int = 10):
    reports = _read_recent_reports(minutes)
    if not reports:
        _write_self_tune_log(f"SELF_TUNE: evaluated window={minutes}m - no reports")
        print(f"SELF_TUNE: evaluated window={minutes}m")
        return

    # aggregate
    total_orders = 0
    margin_cancels = 0
    symbol_orders = {}
    for r in reports:
        l60 = r.get('last_60s', {})
        total_orders += l60.get('orders_sent', 0)
        margin_cancels += l60.get('orders_canceled_margin', 0)
        # best-effort: also inspect last_trade_summary
        last = r.get('last_trade_summary') or {}
        sym = last.get('symbol')
        if sym:
            symbol_orders[sym] = symbol_orders.get(sym, 0) + 1

    _write_self_tune_log(f"SELF_TUNE: evaluated window={minutes}m total_orders={total_orders} margin_cancels={margin_cancels}")
    print(f"SELF_TUNE: evaluated window={minutes}m")

    if total_orders == 0:
        return

    pct = (margin_cancels / total_orders) * 100
    if pct > 20:
        # tighten default caps by 10%
        key = 'OANDA_MAX_UNITS_DEFAULT'
        before = os.getenv(key) or '1000'
        try:
            new = str(max(1, int(int(before) * 0.9)))
        except Exception:
            new = '900'
        changed = _apply_env_change(key, before, new)
        if changed:
            _write_self_tune_log(f"SELF_TUNE_APPLY: tightened default cap {before}->{new} reason=margin_cancel_pct={pct:.1f}")
            print(f"SELF_TUNE_APPLY: {key} {before}->{new} reason=margin_cancel_pct={pct:.1f}")
            # restart the process by re-execing
            print("SELF_TUNE: restart requested after applying changes")
            os.execv(sys.executable, [sys.executable] + list(os.sys.argv))


def start_loop():
    import threading
    import sys

    def _loop():
        while True:
            try:
                # evaluate using configured window
                try:
                    from global_config import FEATURE_FLAGS as _FF
                    interval = int(_FF.get('OANDA_ADVANCED', {}).get('SELF_TUNER_INTERVAL_SECONDS', 600))
                except Exception:
                    interval = 600
                minutes = max(1, int(interval // 60))
                evaluate_and_apply(minutes=minutes)
            except Exception as e:
                _write_self_tune_log(f"SELF_TUNE ERROR: {e}")
            time.sleep(interval)

    t = threading.Thread(target=_loop, daemon=True, name='self_tuner')
    t.start()