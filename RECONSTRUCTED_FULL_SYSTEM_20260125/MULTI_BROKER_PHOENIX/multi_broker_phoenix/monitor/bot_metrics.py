"""Simple, process-local metrics collector for headless runner.

Provides thread-safe counters and small helpers used by reporter and connectors.
"""
from __future__ import annotations
from collections import Counter, deque
import threading
import time
import json
from pathlib import Path

_lock = threading.Lock()
_counters = Counter()
_failure_reasons = Counter()
_last_trade = None
_start_ts = time.time()

# Ring of recent events (timestamp, event_str) for quick inspection
_recent = deque(maxlen=1000)


def incr(name: str, amount: int = 1):
    with _lock:
        _counters[name] += amount
        _recent.append((time.time(), name))


def add_failure(reason: str):
    with _lock:
        _failure_reasons[reason] += 1
        _recent.append((time.time(), f"FAIL:{reason}"))


def set_last_trade(symbol: str, side: str, units: int, sl: float, tp: float):
    global _last_trade
    with _lock:
        _last_trade = {
            'symbol': symbol,
            'side': side,
            'units': units,
            'sl': sl,
            'tp': tp,
            'time': time.time()
        }


def snapshot_and_reset_window(window_secs: int = 60):
    """Return a snapshot for the last window (approximate) and window totals."""
    now = time.time()
    thresh = now - window_secs
    with _lock:
        # derive last N-sec counts from recent events
        recents = [e for ts, e in _recent if ts >= thresh]
        snap = {
            'timestamp': now,
            'engine_uptime_sec': int(now - _start_ts),
            'last_60s': {
                'signals_seen': sum(1 for e in recents if e == 'signal_seen'),
                'hive_approvals': sum(1 for e in recents if e == 'hive_approval'),
                'hive_rejects': sum(1 for e in recents if e == 'hive_reject'),
                'orders_sent': sum(1 for e in recents if e == 'order_sent'),
                'orders_filled': sum(1 for e in recents if e == 'order_filled'),
                'orders_canceled_margin': sum(1 for e in recents if e == 'order_canceled_margin'),
                'orders_failed_other': sum(1 for e in recents if e == 'order_failed_other'),
            },
            'open_positions_count': None,  # filled by reporter via execution client
            'open_exposure_units_by_symbol': {},
            'realized_pl': None,
            'unrealized_pl': None,
            'top_3_failure_reasons': [],
            'last_trade_summary': _last_trade or {}
        }
        # top 3 failure reasons overall
        snap['top_3_failure_reasons'] = [k for k, _ in _failure_reasons.most_common(3)]
        return snap


def dump_report_json(path: str, payload: dict):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, 'w') as f:
        json.dump(payload, f, indent=2)


def append_history(path: str, payload: dict):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, 'a') as f:
        f.write(json.dumps(payload) + '\n')


def reset_counters():
    # not used, but available
    global _counters, _failure_reasons
    with _lock:
        _counters = Counter()
        _failure_reasons = Counter()


def get_counters():
    with _lock:
        return dict(_counters)
