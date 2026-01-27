#!/usr/bin/env python3
"""Performance stats reporter for existing artifacts.

Reads CSVs under MULTI_BROKER_PHOENIX/artifacts/ and prints clean summaries:
- Extreme backtests (profit/return/win-rate per strategy/scenario)
- Strategy sweeps (avg returns/win-rates across regimes)

This is intentionally dependency-free (no pandas).

Examples:
  python tools/report_stats.py
  python tools/report_stats.py --strategy fabio_aaa_full
  python tools/report_stats.py --artifacts /path/to/artifacts
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


def _as_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        s = str(x).strip()
        if s == "":
            return default
        return float(s)
    except Exception:
        return default


def _as_int(x: Any, default: int = 0) -> int:
    try:
        if x is None:
            return default
        s = str(x).strip()
        if s == "":
            return default
        return int(float(s))
    except Exception:
        return default


def _read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _print_table(headers: List[str], rows: List[List[str]]) -> None:
    if not rows:
        print("(no rows)")
        return
    widths = [len(h) for h in headers]
    for r in rows:
        for i, cell in enumerate(r):
            widths[i] = max(widths[i], len(cell))

    def fmt_row(r: List[str]) -> str:
        return "  ".join(cell.ljust(widths[i]) for i, cell in enumerate(r))

    print(fmt_row(headers))
    print("  ".join("-" * w for w in widths))
    for r in rows:
        print(fmt_row(r))


def report_extreme(artifacts_dir: Path, strategy_filter: Optional[str], extreme_filename: str) -> None:
    p = artifacts_dir / extreme_filename
    if not p.exists():
        print(f"- {extreme_filename} not found under {artifacts_dir}")
        return

    rows = _read_csv(p)
    if strategy_filter:
        rows = [r for r in rows if (r.get("strategy") or "") == strategy_filter]

    # Per-row report (top by return)
    rows_sorted = sorted(rows, key=lambda r: _as_float(r.get("total_return_pct"), -1e9), reverse=True)

    print("\n== EXTREME BACKTEST (top 15 by return) ==")
    top = []
    for r in rows_sorted[:15]:
        strat = r.get("strategy", "?")
        scen = r.get("scenario", "?")
        ret = _as_float(r.get("total_return_pct"))
        win = _as_float(r.get("win_rate"))
        trades = _as_int(r.get("trades"))
        end_bal = _as_float(r.get("ending_balance"))
        profit = end_bal - _as_float(r.get("starting_balance"), 10000.0)
        top.append([
            strat,
            scen,
            f"{ret:.2f}%",
            f"{profit:+.2f}",
            f"{win:.1f}%",
            str(trades),
        ])

    _print_table(["strategy", "scenario", "return", "profit($)", "win%", "trades"], top)

    # Aggregate per strategy
    agg: Dict[str, Dict[str, float]] = defaultdict(
        lambda: {
            "n": 0,
            "ret_sum": 0.0,
            "profit_sum": 0.0,
            "trades": 0.0,
            "wins_est": 0.0,
        }
    )
    for r in rows:
        strat = r.get("strategy", "?")
        end_bal = _as_float(r.get("ending_balance"))
        start_bal = _as_float(r.get("starting_balance"), 10000.0)
        trades = _as_int(r.get("trades"))
        win_rate_pct = _as_float(r.get("win_rate"))
        agg[strat]["n"] += 1
        agg[strat]["ret_sum"] += _as_float(r.get("total_return_pct"))
        agg[strat]["profit_sum"] += (end_bal - start_bal)
        agg[strat]["trades"] += trades
        agg[strat]["wins_est"] += trades * (win_rate_pct / 100.0)

    summary = []
    for strat, a in sorted(agg.items(), key=lambda kv: kv[1]["ret_sum"] / max(1.0, kv[1]["n"]), reverse=True):
        n = int(a["n"])
        total_trades = int(a["trades"])
        weighted_win = (a["wins_est"] / a["trades"]) * 100.0 if a["trades"] > 0 else 0.0
        summary.append([
            strat,
            str(n),
            f"{(a['ret_sum'] / max(1, n)):.2f}%",
            f"{(a['profit_sum'] / max(1, n)):+.2f}",
            f"{weighted_win:.1f}%",
            str(total_trades),
        ])

    print("\n== EXTREME BACKTEST (avg per strategy) ==")
    _print_table(["strategy", "scenarios", "avg_return", "avg_profit($)", "win%(weighted)", "trades"], summary)


def report_sweep_adv(artifacts_dir: Path, strategy_filter: Optional[str]) -> None:
    p = artifacts_dir / "strategy_sweep_adv.csv"
    if not p.exists():
        print(f"- strategy_sweep_adv.csv not found under {artifacts_dir}")
        return

    rows = _read_csv(p)
    if strategy_filter:
        rows = [r for r in rows if (r.get("strategy") or "") == strategy_filter]

    # group by strategy+regime
    grp: Dict[Tuple[str, str], Dict[str, float]] = defaultdict(lambda: {"n": 0, "ret_sum": 0.0, "win_sum": 0.0})
    for r in rows:
        strat = r.get("strategy", "?")
        regime = r.get("scenario", r.get("regime", "?")) or "?"
        key = (strat, regime)
        grp[key]["n"] += 1
        grp[key]["ret_sum"] += _as_float(r.get("total_return")) * 100.0 if "total_return" in r else _as_float(r.get("total_return_pct"))
        grp[key]["win_sum"] += _as_float(r.get("win_rate")) * 100.0 if _as_float(r.get("win_rate")) <= 1.0 else _as_float(r.get("win_rate"))

    print("\n== STRATEGY SWEEP ADV (avg by strategy+scenario) ==")
    out_rows: List[List[str]] = []
    for (strat, regime), a in sorted(grp.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        n = int(a["n"])
        out_rows.append([
            strat,
            regime,
            str(n),
            f"{(a['ret_sum'] / max(1, n)):.2f}%",
            f"{(a['win_sum'] / max(1, n)):.1f}%",
        ])

    _print_table(["strategy", "scenario", "runs", "avg_return", "avg_win%"], out_rows)


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    default_artifacts = repo_root / "MULTI_BROKER_PHOENIX" / "artifacts"

    ap = argparse.ArgumentParser(description="Report win-rate/profit stats from artifacts")
    ap.add_argument("--artifacts", type=Path, default=default_artifacts, help="Artifacts directory")
    ap.add_argument("--strategy", default=None, help="Filter to a single strategy id")
    ap.add_argument("--extreme-file", default="extreme_backtest_results.csv",
                    help="Extreme backtest results filename inside artifacts/")
    args = ap.parse_args()

    artifacts_dir: Path = args.artifacts
    if not artifacts_dir.exists():
        print(f"Artifacts dir not found: {artifacts_dir}")
        return 2

    report_extreme(artifacts_dir, args.strategy, args.extreme_file)
    report_sweep_adv(artifacts_dir, args.strategy)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
