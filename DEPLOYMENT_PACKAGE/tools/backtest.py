"""Very small backtester for smoke-testing strategies.

It executes a strategy over a price series and simulates simple stop-loss exits.
Returns a summary with total return, win-rate, and max drawdown.
"""
from __future__ import annotations
from typing import Dict, Any, List
from multi_broker_phoenix.strategies.base import get_strategy


class Backtester:
    def __init__(self, strategy_id: str):
        self.strategy_id = strategy_id
        self.strategy = get_strategy(strategy_id)
        if not self.strategy:
            raise ValueError('unknown strategy')

    def run(self, price_series: List[float], symbol: str = 'SYM', platform: str = 'OANDA') -> Dict[str, Any]:
        eq = 1.0
        peak = eq
        max_dd = 0.0
        trades = []
        pos = None
        for i in range(len(price_series)):
            prices = price_series[: i+1]
            cand = self.strategy.generate_candidate({'symbol': symbol, 'platform': platform, 'prices': prices})
            if cand and pos is None:
                # open
                pos = {
                    'entry': cand.entry_price,
                    'stop': cand.stop_loss,
                    'side': cand.side,
                    'open_index': i,
                }
            # if position open, check stop
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
        # close any open at last price
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
