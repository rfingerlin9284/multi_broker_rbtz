"""Advanced experiment harness

Adds simple transaction-cost adjustment and minimum-trade filter and uses a
more stable scoring metric to avoid explosion when max drawdown is near zero.
"""
from __future__ import annotations
import csv
import os
import random
from typing import List, Dict, Any

from multi_broker_phoenix.strategies.base import list_strategies
from tools.backtest import Backtester

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'artifacts')
os.makedirs(OUTPUT_DIR, exist_ok=True)

# reuse scenario generators from strategy_sweep to keep things simple
from tools.strategy_sweep import SCENARIOS, gen_uptrend


def stable_score(avg_ret: float, avg_dd: float) -> float:
    # use small floor to avoid huge values for near-zero drawdown
    dd_floor = max(avg_dd, 0.001)
    return avg_ret / dd_floor


def run_advanced(seeds_per_scenario: int = 50, length: int = 1000, trade_cost: float = 0.0002, min_trades: int = 3) -> None:
    strategies = list(list_strategies().keys())
    if not strategies:
        print('No strategies registered; import module to register strategies and try again.')
        return

    rows: List[Dict[str, Any]] = []
    for strat in strategies:
        bt = Backtester(strat)
        for scenario_name, gen in SCENARIOS.items():
            stats_acc = {'total_return': 0.0, 'win_rate': 0.0, 'max_drawdown': 0.0, 'trades': 0}
            runs = 0
            for s in range(seeds_per_scenario):
                seed = 10000 + s
                series = gen(length, seed=seed)
                stats = bt.run(series)
                # adjust total return approximately for trade cost
                adj_total_return = stats['total_return'] - (stats['trades'] * trade_cost)
                stats_acc['total_return'] += adj_total_return
                stats_acc['win_rate'] += stats['win_rate']
                stats_acc['max_drawdown'] += stats['max_drawdown']
                stats_acc['trades'] += stats['trades']
                runs += 1
            avg_total_return = stats_acc['total_return'] / runs
            avg_win_rate = stats_acc['win_rate'] / runs
            avg_max_dd = stats_acc['max_drawdown'] / runs
            avg_trades = stats_acc['trades'] / runs
            score = stable_score(avg_total_return, avg_max_dd)
            rows.append({
                'strategy': strat,
                'scenario': scenario_name,
                'avg_total_return': avg_total_return,
                'avg_win_rate': avg_win_rate,
                'avg_max_drawdown': avg_max_dd,
                'avg_trades': avg_trades,
                'score': score,
            })

    out_csv = os.path.join(OUTPUT_DIR, 'strategy_sweep_adv.csv')
    with open(out_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    # filter by min trades to avoid sparse-trade artifacts
    filtered = [r for r in rows if r['avg_trades'] >= min_trades]
    filtered_sorted = sorted(filtered, key=lambda r: r['score'], reverse=True)

    print(f"\nTop 10 combos (min_trades={min_trades}) by stable score:")
    for r in filtered_sorted[:10]:
        print(f"{r['strategy']:20} {r['scenario']:12} score={r['score']:.4f} ret={r['avg_total_return']:.4f} dd={r['avg_max_drawdown']:.4f} wr={r['avg_win_rate']:.3f} trades={r['avg_trades']:.1f}")


if __name__ == '__main__':
    run_advanced()