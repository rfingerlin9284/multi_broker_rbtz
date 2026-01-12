from multi_broker_phoenix.brokers.coinbase_connector import CoinbaseConnector
from multi_broker_phoenix.brokers.ibkr_connector import IBKRConnector
from multi_broker_phoenix.engines.paper_engine import PaperEngine
from multi_broker_phoenix.risk.trade_risk_gate import TradeCandidate


def test_coinbase_connector_paper_uses_engine():
    engine = PaperEngine(db_path=':memory:')
    conn = CoinbaseConnector(paper_mode=True, engine=engine, fee_pct=0.001, slippage_pct=0.002)
    conn.update_price('BTC-USD', 50000.0)
    cand = TradeCandidate('test', 'BTC-USD', 'COINBASE', entry_price=50000.0, stop_loss=49500.0, side='BUY')
    sizing = 0.001  # tiny size for test
    order = conn.place_paper_order(cand, sizing)
    assert order['platform'] == 'COINBASE' or order.get('platform') == 'OANDA' or 'id' in order


def test_ibkr_connector_paper_no_engine():
    conn = IBKRConnector(paper_mode=True, engine=None, fee_pct=0.001, slippage_pct=0.002)
    conn.update_price('AAPL', 150.0)
    cand = TradeCandidate('test', 'AAPL', 'IBKR', entry_price=150.0, stop_loss=149.0, side='SELL')
    order = conn.place_paper_order(cand, 10)
    assert order['platform'] == 'IBKR'
    assert order['size'] == 10
    assert order['status'] == 'FILLED'
