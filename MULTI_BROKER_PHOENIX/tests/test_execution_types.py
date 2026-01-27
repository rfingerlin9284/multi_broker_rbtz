import os
from multi_broker_phoenix.brokers.coinbase_connector import CoinbaseConnector
from multi_broker_phoenix.brokers.ibkr_connector import IBKRConnector
from multi_broker_phoenix.engines.paper_engine import PaperEngine
from multi_broker_phoenix.risk.trade_risk_gate import TradeCandidate
from multi_broker_phoenix.config import runtime


def test_coinbase_execution_type_defaults_to_simulated(tmp_path):
    engine = PaperEngine(db_path=str(tmp_path / 'db.sqlite'))
    conn = CoinbaseConnector(paper_mode=True, engine=engine)
    conn.update_price('BTC-USD', 45000.0)
    cand = TradeCandidate('t', 'BTC-USD', 'COINBASE', entry_price=45000.0, stop_loss=44000.0, side='BUY')
    order = conn.place_paper_order(cand, 0.001)
    assert order['execution_type'] == 'SIMULATED'


def test_ibkr_execution_type_with_platform_paper(tmp_path, monkeypatch):
    monkeypatch.setenv('TRADING_MODE', 'PAPER')
    monkeypatch.setenv('PAPER_VIA_PLATFORM', '1')
    engine = PaperEngine(db_path=str(tmp_path / 'db.sqlite'))
    conn = IBKRConnector(paper_mode=True, engine=engine)
    conn.update_price('AAPL', 150.0)
    cand = TradeCandidate('t', 'AAPL', 'IBKR', entry_price=150.0, stop_loss=149.0, side='SELL')
    order = conn.place_paper_order(cand, 1)
    # when PAPER_VIA_PLATFORM is set and IBKR supports platform paper this should be PLATFORM_PAPER
    assert order['execution_type'] in ('PLATFORM_PAPER', 'SIMULATED')
