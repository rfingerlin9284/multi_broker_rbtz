#!/usr/bin/env python3
"""Demo: strategy -> risk gate -> mock engine flow

Usage:
  . .venv/bin/activate
  python examples/run_execution_demo.py
"""
from multi_broker_phoenix.strategies.base import get_strategy
from multi_broker_phoenix.risk.risk_manager import RiskManager
from multi_broker_phoenix.risk.trade_risk_gate import can_open_trade
from multi_broker_phoenix.engines.mock_engine import MockEngine


def run_demo():
    prices = [1.0 + 0.001 * i for i in range(30)]
    s = get_strategy('ema_scalper')
    cand = s.generate_candidate({'symbol': 'EURUSD', 'platform': 'OANDA', 'prices': prices})
    print('candidate:', cand)
    rm = RiskManager()
    rm.update_equity(100000.0)
    rm.state.regime_by_symbol['EURUSD'] = {'trend': 'BULL', 'vol': 'NORMAL'}
    if cand:
        dec = can_open_trade(cand, account_equity=100000.0, rm=rm)
        print('decision:', dec)
        if dec.allowed:
            engine = MockEngine('OANDA')
            order = engine.place_order(cand, dec.size)
            print('order placed:', order)


if __name__ == '__main__':
    run_demo()
