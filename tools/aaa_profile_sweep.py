#!/usr/bin/env python3
"""AAA Profile Robustness Sweep

Runs `fabio_aaa_full` across multiple risk profiles (conservative, mild, high)
and multiple random seeds for each extreme scenario, then writes per-profile
CSV artifacts and a combined summary.
"""
from __future__ import annotations
import csv
import os
import statistics
from pathlib import Path
from typing import Dict, Any, List

# Import run_extreme_backtest and EXTREME_SCENARIOS directly from file paths (no package install needed)
import importlib.util
PROJECT_INNER = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'MULTI_BROKER_PHOENIX', 'tools'))

spec = importlib.util.spec_from_file_location('mbp_extreme_backtest', os.path.join(PROJECT_INNER, 'extreme_backtest.py'))
mbp_extreme = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mbp_extreme)
run_extreme_backtest = mbp_extreme.run_extreme_backtest

spec2 = importlib.util.spec_from_file_location('mbp_extreme_market_simulator', os.path.join(PROJECT_INNER, 'extreme_market_simulator.py'))
mbp_scen = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(mbp_scen)
EXTREME_SCENARIOS = mbp_scen.EXTREME_SCENARIOS

# Profiles
PROFILES = {
    'conservative': {'base_risk_pct': 1.0, 'max_leverage_param': 1.0, 'kelly_fraction': 0.25},
    'mild': {'base_risk_pct': 2.5, 'max_leverage_param': 2.0, 'kelly_fraction': 0.5},
    'high': {'base_risk_pct': 5.0, 'max_leverage_param': 5.0, 'kelly_fraction': 0.75},
}

OUTPUT_DIR = Path(__file__).resolve().parents[1] / 'MULTI_BROKER_PHOENIX' / 'artifacts'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def run_profile_sweep(strategy: str = 'fabio_aaa_full', seeds: int = 10, length: int = 500):
    runs = []
    for profile_name, params in PROFILES.items():
        rows = []
        print(f"\n▶ Running profile: {profile_name} (seeds={seeds})")
        for seed in range(seeds):
            for scenario_name, scenario_gen in EXTREME_SCENARIOS.items():
                price_series = scenario_gen(length=length, seed=seed)
                result = run_extreme_backtest(
                    strategy,
                    price_series,
                    scenario_name,
                    base_risk_pct=params['base_risk_pct'],
                    max_leverage_param=params['max_leverage_param'],
                    kelly_fraction=params['kelly_fraction'],
                    starting_balance=10000.0
                )
                # add metadata
                result.update({'profile': profile_name, 'seed': seed})
                rows.append(result)
        # write per-profile csv
        outfile = OUTPUT_DIR / f'aaa_profile_sweep_{profile_name}.csv'
        if rows:
            with outfile.open('w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=sorted(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)
        print(f"  ▸ Saved {len(rows)} runs to {outfile}")
        runs.extend(rows)

    # combined summary
    summary = []
    by_profile: Dict[str, List[Dict[str, Any]]] = {}
    for r in runs:
        by_profile.setdefault(r['profile'], []).append(r)

    for profile, list_r in by_profile.items():
        vals = [float(x.get('total_return_pct', 0.0)) for x in list_r]
        trades = [int(x.get('trades', 0)) for x in list_r]
        wins = [float(x.get('win_rate', 0.0)) for x in list_r]
        summary.append({
            'profile': profile,
            'runs': len(list_r),
            'mean_return_pct': statistics.mean(vals),
            'median_return_pct': statistics.median(vals),
            'stdev_return_pct': statistics.stdev(vals) if len(vals) > 1 else 0.0,
            'mean_trades': statistics.mean(trades) if trades else 0.0,
            'mean_win_pct': statistics.mean(wins) if wins else 0.0,
        })

    summary_file = OUTPUT_DIR / 'aaa_profile_sweep_summary.csv'
    with summary_file.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=sorted(summary[0].keys()))
        writer.writeheader()
        writer.writerows(summary)

    print('\nSummary:')
    for s in summary:
        print(f" - {s['profile']}: mean_return={s['mean_return_pct']:.2f}% median={s['median_return_pct']:.2f}% stdev={s['stdev_return_pct']:.2f}% mean_trades={s['mean_trades']:.1f} mean_win%={s['mean_win_pct']:.1f}%")


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--strategy', default='fabio_aaa_full')
    ap.add_argument('--seeds', type=int, default=10)
    ap.add_argument('--length', type=int, default=500)
    args = ap.parse_args()
    run_profile_sweep(strategy=args.strategy, seeds=args.seeds, length=args.length)
