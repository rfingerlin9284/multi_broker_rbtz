#!/usr/bin/env python3
"""Simple example: run a registered strategy against synthetic data.

Usage:
  . .venv/bin/activate
  python examples/run_strategy_example.py
"""
from multi_broker_phoenix.strategies.base import get_strategy
from multi_broker_phoenix.risk.trade_risk_gate import can_open_trade
from multi_broker_phoenix.risk.risk_manager import RiskManager


def run():
    prices = [1.0 + 0.001 * i for i in range(30)]
    s = get_strategy('ema_scalper')
    cand = s.generate_candidate({'symbol': 'EURUSD', 'platform': 'OANDA', 'prices': prices})
    print('strategy:', getattr(s, '__class__', s))
    print('candidate:', cand)
    rm = RiskManager()
    rm.update_equity(100000.0)
    rm.state.regime_by_symbol['EURUSD'] = {'trend': 'BULL', 'vol': 'NORMAL'}
    dec = can_open_trade(cand, account_equity=100000.0, rm=rm) if cand else None
    print('decision:', dec)


if __name__ == '__main__':
    run()
