from multi_broker_phoenix.strategies.base import get_strategy
from multi_broker_phoenix.risk.risk_manager import RiskManager
from multi_broker_phoenix.engines.mock_engine import MockEngine
from multi_broker_phoenix.risk.trade_risk_gate import can_open_trade


def test_engine_fees_and_slippage_reduce_size():
    s = get_strategy('ema_scalper')
    prices = [1.0 + i * 0.001 for i in range(30)]
    cand = s.generate_candidate({'symbol': 'EURUSD', 'platform': 'OANDA', 'prices': prices})
    assert cand is not None
    rm = RiskManager()
    rm.update_equity(100000.0)
    rm.state.regime_by_symbol['EURUSD'] = {'trend': 'BULL', 'vol': 'NORMAL'}

    # compute sizing without fees/slippage
    sizing_clean = rm.size_for_trade(cand, 100000.0, fee_pct=0.0, slippage_pct=0.0)
    # compute sizing with fees/slippage
    sizing_costly = rm.size_for_trade(cand, 100000.0, fee_pct=0.001, slippage_pct=0.001)
    assert sizing_clean['size'] > sizing_costly['size']

    # now place an order via engine with fees & slippage
    dec = can_open_trade(cand, account_equity=100000.0, rm=rm)
    engine = MockEngine('OANDA', fee_pct=0.001, slippage_pct=0.001)
    order = engine.place_order(cand, sizing_costly['size'])
    assert 'fees' in order
    assert order['fees'] >= 0
    assert order['fill_price'] != order['entry']
