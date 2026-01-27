#!/usr/bin/env python3
"""Example runner that replays a CSV and executes paper trades automatically."""
from __future__ import annotations
import argparse
from multi_broker_phoenix.data.csv_feed import CSVFeed
from multi_broker_phoenix.engines.paper_engine import PaperEngine
from multi_broker_phoenix.strategies.base import get_strategy
from multi_broker_phoenix.risk.risk_manager import RiskManager
from multi_broker_phoenix.risk.trade_risk_gate import can_open_trade


def run(csv_path: str, strategy_id: str = 'ema_scalper', speed: float = 1.0, fee_pct: float = 0.001, slippage_pct: float = 0.001, initial_equity: float = 100000.0, connector: str | None = None):
    feed = CSVFeed(csv_path)
    strategy = get_strategy(strategy_id)
    if not strategy:
        raise RuntimeError('unknown strategy')
    engine = PaperEngine(db_path='data/paper_ledger.sqlite', fee_pct=fee_pct, slippage_pct=slippage_pct, initial_equity=initial_equity)
    rm = RiskManager()
    rm.update_equity(initial_equity)
    prices = []
    # optional connector
    connector_obj = None
    if connector:
        if connector.lower() == 'coinbase':
            from multi_broker_phoenix.brokers.coinbase_connector import CoinbaseConnector
            connector_obj = CoinbaseConnector(paper_mode=True, engine=engine, fee_pct=fee_pct, slippage_pct=slippage_pct)
        elif connector.lower() == 'ibkr':
            from multi_broker_phoenix.brokers.ibkr_connector import IBKRConnector
            connector_obj = IBKRConnector(paper_mode=True, engine=engine, fee_pct=fee_pct, slippage_pct=slippage_pct)
        else:
            raise RuntimeError('unknown connector')
    for tick in feed.stream(speed=speed):
        prices.append(tick['price'])
        # keep a reasonable window
        if len(prices) > 200:
            prices = prices[-200:]
        # update connector price if present
        if connector_obj is not None:
            connector_obj.update_price(tick['symbol'], tick['price'])
            platform_name = connector_obj.__class__.__name__.split('Connector')[0].upper()
        else:
            platform_name = engine.platform
        cand = strategy.generate_candidate({'symbol': tick['symbol'], 'platform': platform_name, 'prices': prices})
        if not cand:
            continue
        dec = can_open_trade(cand, account_equity=rm.state.equity_now, rm=rm)
        if not dec.allowed:
            print('trade blocked:', dec.reason)
            continue
        # use risk manager sizing with engine fees/slippage
        sizing = rm.size_for_trade(cand, rm.state.equity_now, fee_pct=fee_pct, slippage_pct=slippage_pct)
        if not sizing.get('allowed'):
            print('sizing rejected:', sizing.get('reason'))
            continue
        # place via connector if available so connector can simulate platform-specific behavior
        if connector_obj is not None:
            order = connector_obj.place_paper_order(cand, sizing['size'])
        else:
            order = engine.place_order(cand, sizing['size'])
        print('placed order:', order)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('csv_path')
    parser.add_argument('--strategy', default='ema_scalper')
    parser.add_argument('--speed', type=float, default=100.0, help='speed multiplier for replay')
    args = parser.parse_args()
    run(args.csv_path, strategy_id=args.strategy, speed=args.speed)
