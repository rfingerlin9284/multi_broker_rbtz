from multi_broker_phoenix.strategies.base import get_strategy
from multi_broker_phoenix.engines.mock_engine import MockEngine
from multi_broker_phoenix.risk.risk_manager import RiskManager
from multi_broker_phoenix.risk.trade_risk_gate import can_open_trade


def test_strategy_to_engine_flow():
    s = get_strategy('ema_scalper')
    prices = [1.0 + i * 0.001 for i in range(30)]
    cand = s.generate_candidate({'symbol': 'EURUSD', 'platform': 'OANDA', 'prices': prices})
    assert cand is not None
    rm = RiskManager()
    rm.update_equity(100000.0)
    rm.state.regime_by_symbol['EURUSD'] = {'trend': 'BULL', 'vol': 'NORMAL'}
    dec = can_open_trade(cand, account_equity=100000.0, rm=rm)
    assert dec.allowed
    engine = MockEngine('OANDA')
    order = engine.place_order(cand, size=dec.size)
    assert order['status'] == 'FILLED'
    assert order['size'] == dec.size
    assert order['symbol'] == 'EURUSD'
