"""Simple experiment harness to sweep strategies over synthetic scenarios.

Generates several price series types (uptrend, downtrend, sideways, random walk,
volatility spike) and runs the repository `Backtester` for each registered
strategy over multiple random seeds. Outputs a CSV `artifacts/strategy_sweep.csv`
with aggregated metrics and prints a short ranking.
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


def gen_uptrend(length: int = 500, drift: float = 0.0005, vol: float = 0.002, seed: int | None = None) -> List[float]:
    rnd = random.Random(seed)
    p = 1.0
    series = []
    for _ in range(length):
        p *= 1.0 + drift + rnd.uniform(-vol, vol)
        series.append(p)
    return series


def gen_downtrend(length: int = 500, drift: float = -0.0005, vol: float = 0.002, seed: int | None = None) -> List[float]:
    return gen_uptrend(length=length, drift=drift, vol=vol, seed=seed)


def gen_sideways(length: int = 500, vol: float = 0.002, seed: int | None = None) -> List[float]:
    rnd = random.Random(seed)
    p = 1.0
    series = []
    for _ in range(length):
        p *= 1.0 + rnd.uniform(-vol, vol)
        series.append(p)
    return series


def gen_random_walk(length: int = 500, vol: float = 0.002, seed: int | None = None) -> List[float]:
    rnd = random.Random(seed)
    p = 1.0
    series = []
    for _ in range(length):
        p += rnd.uniform(-vol, vol)
        p = max(0.0001, p)
        series.append(p)
    return series


def gen_volatility_spike(length: int = 500, base_vol: float = 0.001, spike_vol: float = 0.05, spike_at: int | None = None, seed: int | None = None) -> List[float]:
    rnd = random.Random(seed)
    p = 1.0
    series = []
    if spike_at is None:
        spike_at = length // 2
    for i in range(length):
        vol = spike_vol if abs(i - spike_at) < 3 else base_vol
        p *= 1.0 + rnd.uniform(-vol, vol)
        series.append(p)
    return series


SCENARIOS = {
    'uptrend': gen_uptrend,
    'downtrend': gen_downtrend,
    'sideways': gen_sideways,
    'random_walk': gen_random_walk,
    'vol_spike': gen_volatility_spike,
}


def run_sweep(seeds_per_scenario: int = 10, length: int = 500) -> None:
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
                seed = 1000 + s
                series = gen(length, seed=seed)
                stats = bt.run(series)
                stats_acc['total_return'] += stats['total_return']
                stats_acc['win_rate'] += stats['win_rate']
                stats_acc['max_drawdown'] += stats['max_drawdown']
                stats_acc['trades'] += stats['trades']
                runs += 1
            # average
            avg_total_return = stats_acc['total_return'] / runs
            avg_win_rate = stats_acc['win_rate'] / runs
            avg_max_dd = stats_acc['max_drawdown'] / runs
            avg_trades = stats_acc['trades'] / runs
            # score: higher is better (total_return / max_drawdown); small dd boosted by eps
            score = avg_total_return / (avg_max_dd + 1e-9)
            rows.append({
                'strategy': strat,
                'scenario': scenario_name,
                'avg_total_return': avg_total_return,
                'avg_win_rate': avg_win_rate,
                'avg_max_drawdown': avg_max_dd,
                'avg_trades': avg_trades,
                'score': score,
            })

    out_csv = os.path.join(OUTPUT_DIR, 'strategy_sweep.csv')
    with open(out_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    # print top performers
    rows_sorted = sorted(rows, key=lambda r: r['score'], reverse=True)
    print('\nTop 10 strategy-scenario combos by score:')
    for r in rows_sorted[:10]:
        print(f"{r['strategy']:20} {r['scenario']:12} score={r['score']:.4f} ret={r['avg_total_return']:.4f} dd={r['avg_max_drawdown']:.4f} wr={r['avg_win_rate']:.3f} trades={r['avg_trades']:.1f}")


if __name__ == '__main__':
    run_sweep()
