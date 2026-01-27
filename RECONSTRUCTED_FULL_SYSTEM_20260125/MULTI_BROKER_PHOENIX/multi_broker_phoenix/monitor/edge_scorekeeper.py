"""Edge scorekeeper: record closed trades and compute simple stats.
"""
from __future__ import annotations
import sqlite3
import time
from pathlib import Path
from typing import Dict, Any
import json
try:
    from global_config import FEATURE_FLAGS as _FF
except Exception:
    _FF = {}

DB_PATH = Path(_FF.get('EDGE_SCOREKEEPER', {}).get('db_path', '~/.rbotzilla/edge_scorekeeper.sqlite')).expanduser()
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

def _ensure_db():
    conn = sqlite3.connect(str(DB_PATH))
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS closed_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts REAL,
                strategy TEXT,
                regime TEXT,
                score REAL,
                entry_reason TEXT,
                exit_reason TEXT,
                pnl REAL,
                duration REAL,
                spread REAL,
                atr REAL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()

_ensure_db()


def record_trade(record: Dict[str, Any]):
    conn = sqlite3.connect(str(DB_PATH))
    try:
        conn.execute('INSERT INTO closed_trades (ts,strategy,regime,score,entry_reason,exit_reason,pnl,duration,spread,atr) VALUES (?,?,?,?,?,?,?,?,?,?)', (
            time.time(),
            record.get('strategy'),
            record.get('regime'),
            float(record.get('score') or 0.0),
            json.dumps(record.get('entry_reasons') or []),
            record.get('exit_reason'),
            float(record.get('pnl') or 0.0),
            float(record.get('duration') or 0.0),
            float(record.get('spread') or 0.0),
            float(record.get('atr') or 0.0),
        ))
        conn.commit()
    finally:
        conn.close()


def compute_expectancy(strategy: str, hours: float = 24.0) -> Dict[str, Any]:
    cutoff = time.time() - hours * 3600
    conn = sqlite3.connect(str(DB_PATH))
    try:
        cur = conn.execute('SELECT pnl FROM closed_trades WHERE strategy=? AND ts>=?', (strategy, cutoff))
        rows = cur.fetchall()
        pnl_list = [r[0] for r in rows]
        wins = [p for p in pnl_list if p > 0]
        losses = [p for p in pnl_list if p <= 0]
        count = len(pnl_list)
        win_rate = (len(wins) / count) if count else 0.0
        avg_win = (sum(wins) / len(wins)) if wins else 0.0
        avg_loss = (sum(losses) / len(losses)) if losses else 0.0
        expectancy = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)
        return {'count': count, 'win_rate': win_rate, 'avg_win': avg_win, 'avg_loss': avg_loss, 'expectancy': expectancy}
    finally:
        conn.close()
