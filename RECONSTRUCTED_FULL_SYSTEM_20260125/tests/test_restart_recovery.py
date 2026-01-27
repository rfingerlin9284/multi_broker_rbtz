import time
from multi_broker_phoenix.monitor.protect_and_exit import start_up_reconcile, DEFAULT_RECONCILE_CONFIG


class FakeClient:
    def __init__(self, *a, **k):
        pass

    def list_open_trades(self):
        return {'trades': []}

    def get_account_summary(self):
        return {'account': {'unrealizedPL': 0.0, 'realizedPL': 0.0, 'marginAvailable': 10000.0, 'marginUsed': 0.0, 'balance': 10000.0}}

    def close_all_positions(self):
        return {'closed': True}


def fake_client_factory(*a, **k):
    return FakeClient()


def test_startup_reconcile_pass(monkeypatch):
    # Patch the OandaPracticeClient used by protect_and_exit's runtime
    monkeypatch.setattr('multi_broker_phoenix.monitor.protect_and_exit.OandaPracticeClient', fake_client_factory)
    # Use a minimal fake oanda connector with required attrs
    class FakeConnector:
        token = 'x'
        account_id = '1'
        base_url = 'https://api'
        http = None

    res = start_up_reconcile(FakeConnector(), DEFAULT_RECONCILE_CONFIG)
    assert res.get('passed') is True


def test_startup_reconcile_fail_on_pnl_trigger(monkeypatch):
    # Patch client to return huge negative unrealized to trigger PNL kill
    class BadClient(FakeClient):
        def get_account_summary(self):
            return {'account': {'unrealizedPL': -1000.0, 'realizedPL': 0.0, 'marginAvailable': 10000.0, 'marginUsed': 0.0, 'balance': 10000.0}}

    monkeypatch.setattr('multi_broker_phoenix.monitor.protect_and_exit.OandaPracticeClient', lambda *a, **k: BadClient())
    monkeypatch.setattr('multi_broker_phoenix.monitor.pnl_kill_switch.OandaPracticeClient', lambda *a, **k: BadClient())
    monkeypatch.setattr('multi_broker_phoenix.monitor.breakeven_worker.OandaPracticeClient', lambda *a, **k: BadClient())

    class FakeConnector:
        token = 'x'
        account_id = '1'
        base_url = 'https://api'
        http = None

    res = start_up_reconcile(FakeConnector(), DEFAULT_RECONCILE_CONFIG)
    assert res.get('passed') is False
