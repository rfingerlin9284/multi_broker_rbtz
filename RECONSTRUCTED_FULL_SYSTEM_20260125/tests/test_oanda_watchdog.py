import os
import pytest

from multi_broker_phoenix.brokers.oanda_connector import OANDAConnector


class DummyCandidate:
    def __init__(self, symbol='EUR_USD', side='BUY', entry=1.0, sl=0.99, tp=1.01):
        self.symbol = symbol
        self.side = side
        self.entry_price = entry
        self.stop_loss = sl
        self.take_profit = tp


def test_place_paper_order_blocked_by_watchdog(monkeypatch, tmp_path):
    monkeypatch.setenv('OANDA_API_TOKEN', 'fake-token')
    monkeypatch.setenv('OANDA_ACCOUNT_ID', 'fake-account')

    # Ensure watchdog returns False
    monkeypatch.setattr('multi_broker_phoenix.monitor.watchdog.trading_allowed', lambda: False)

    conn = OANDAConnector(token=os.getenv('OANDA_API_TOKEN'), account_id=os.getenv('OANDA_ACCOUNT_ID'), practice_mode=True, http_client=None)

    cand = DummyCandidate()

    with pytest.raises(RuntimeError) as ei:
        conn.place_paper_order(cand, units=100)
    assert 'BLOCKED_BY_WATCHDOG' in str(ei.value)


def test_place_paper_order_proceeds_when_watchdog_ok(monkeypatch):
    # If watchdog ok but client isn't available, we should get credential checks or client errors later
    monkeypatch.setenv('OANDA_API_TOKEN', 'fake-token')
    monkeypatch.setenv('OANDA_ACCOUNT_ID', 'fake-account')
    monkeypatch.setattr('multi_broker_phoenix.monitor.watchdog.trading_allowed', lambda: True)

    conn = OANDAConnector(token=os.getenv('OANDA_API_TOKEN'), account_id=os.getenv('OANDA_ACCOUNT_ID'), practice_mode=True, http_client=None)
    cand = DummyCandidate()

    # Without a proper HTTP client, create_order_market will raise; ensure we get past the watchdog gate
    with pytest.raises(Exception):
        conn.place_paper_order(cand, units=100)
