"""Sweep stop-loss multipliers for selected strategies and scenarios."""
from __future__ import annotations
import csv
import os
import random
from typing import List, Dict, Any

from multi_broker_phoenix.strategies.base import list_strategies
from tools.backtest import Backtester
from tools.strategy_sweep import SCENARIOS

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'artifacts')
os.makedirs(OUTPUT_DIR, exist_ok=True)


class StopScalingBacktester(Backtester):
    def run(self, price_series: List[float], stop_scale: float = 1.0, symbol: str = 'SYM', platform: str = 'OANDA') -> Dict[str, Any]:
        # copy of Backtester.run but scale stop distance from entry
        eq = 1.0
        peak = eq
        max_dd = 0.0
        trades = []
        pos = None
        for i in range(len(price_series)):
            prices = price_series[: i+1]
            cand = self.strategy.generate_candidate({'symbol': symbol, 'platform': platform, 'prices': prices})
            if cand and pos is None:
                entry = cand.entry_price
                stop = cand.stop_loss
                # scale stop away from entry
                stop_adj = entry + (stop - entry) * float(stop_scale)
                pos = {
                    'entry': entry,
                    'stop': stop_adj,
                    'side': cand.side,
                    'open_index': i,
                }
            if pos is not None:
                current = price_series[i]
                if pos['side'] == 'BUY' and current <= pos['stop']:
                    ret = (current - pos['entry']) / pos['entry']
                    trades.append(ret)
                    eq *= (1 + ret)
                    pos = None
                elif pos['side'] == 'SELL' and current >= pos['stop']:
                    ret = (pos['entry'] - current) / pos['entry']
                    trades.append(ret)
                    eq *= (1 + ret)
                    pos = None
            peak = max(peak, eq)
            max_dd = max(max_dd, (peak - eq) / peak)
        if pos is not None:
            last = price_series[-1]
            if pos['side'] == 'BUY':
                ret = (last - pos['entry']) / pos['entry']
            else:
                ret = (pos['entry'] - last) / pos['entry']
            trades.append(ret)
            eq *= (1 + ret)
        total_return = eq - 1.0
        wins = [t for t in trades if t > 0]
        stats = {
            'trades': len(trades),
            'total_return': total_return,
            'win_rate': (len(wins) / len(trades)) if trades else 0.0,
            'max_drawdown': max_dd,
            'avg_trade_return': (sum(trades) / len(trades)) if trades else 0.0,
        }
        return stats


def run_stop_sweep(strategies: List[str] | None = None, scenarios: List[str] | None = None,
                   stop_scales: List[float] = None, seeds_per_scenario: int = 20, length: int = 1000):
    if strategies is None:
        strategies = ['ema_scalper', 'holy_grail', 'institutional_sd']
    if scenarios is None:
        scenarios = ['vol_spike', 'uptrend', 'downtrend']
    if stop_scales is None:
        stop_scales = [0.5, 0.75, 1.0, 1.5, 2.0, 3.0]

    rows: List[Dict[str, Any]] = []
    for strat in strategies:
        sbt = StopScalingBacktester(strat)
        for scenario_name in scenarios:
            gen = SCENARIOS[scenario_name]
            for scale in stop_scales:
                stats_acc = {'total_return': 0.0, 'win_rate': 0.0, 'max_drawdown': 0.0, 'trades': 0}
                runs = 0
                for s in range(seeds_per_scenario):
                    seed = 50000 + s
                    series = gen(length, seed=seed)
                    stats = sbt.run(series, stop_scale=scale)
                    stats_acc['total_return'] += stats['total_return']
                    stats_acc['win_rate'] += stats['win_rate']
                    stats_acc['max_drawdown'] += stats['max_drawdown']
                    stats_acc['trades'] += stats['trades']
                    runs += 1
                avg_total_return = stats_acc['total_return'] / runs
                avg_win_rate = stats_acc['win_rate'] / runs
                avg_max_dd = stats_acc['max_drawdown'] / runs
                avg_trades = stats_acc['trades'] / runs
                score = avg_total_return / max(avg_max_dd, 0.001)
                rows.append({
                    'strategy': strat,
                    'scenario': scenario_name,
                    'stop_scale': scale,
                    'avg_total_return': avg_total_return,
                    'avg_win_rate': avg_win_rate,
                    'avg_max_drawdown': avg_max_dd,
                    'avg_trades': avg_trades,
                    'score': score,
                })

    out_csv = os.path.join(OUTPUT_DIR, 'stop_sweep.csv')
    with open(out_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    # print best settings per strategy
    for strat in strategies:
        strat_rows = [r for r in rows if r['strategy'] == strat]
        best = sorted(strat_rows, key=lambda r: r['score'], reverse=True)[0]
        print(f"Best for {strat}: scenario={best['scenario']}, stop_scale={best['stop_scale']} score={best['score']:.4f} ret={best['avg_total_return']:.4f} dd={best['avg_max_drawdown']:.4f} trades={best['avg_trades']:.1f}")


if __name__ == '__main__':
    run_stop_sweep()