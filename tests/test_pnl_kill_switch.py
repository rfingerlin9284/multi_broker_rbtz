import os
import types
import pytest

from multi_broker_phoenix.monitor import pnl_kill_switch


class DummyOandaConnector:
    def __init__(self, token='t', account='a', base='https://api-fxpractice.oanda.com'):
        self.token = token
        self.account_id = account
        self.base_url = base
        self.http = None


class DummyClient:
    def __init__(self, realized=0.0, unrealized=-300.0, trades=None):
        self._realized = realized
        self._unrealized = unrealized
        self._trades = trades or [{'instrument': 'EUR_USD'}]

    def get_account_summary(self):
        return {'account': {'realizedPL': self._realized, 'unrealizedPL': self._unrealized}}

    def list_open_trades(self):
        return {'trades': [{'instrument': 'EUR_USD', 'unrealizedPL': self._unrealized}]}

    def close_all_positions(self):
        return {'EUR_USD': {'success': True}}


def test_run_pnl_once_triggers(monkeypatch, tmp_path):
    # Provide dummy client via monkeypatching OandaPracticeClient
    dc = DummyClient(realized=0.0, unrealized=-300.0)

    class FakeClientFactory:
        def __init__(self, *a, **k):
            pass

        def __call__(self, *a, **k):
            return dc

    monkeypatch.setattr('multi_broker_phoenix.monitor.pnl_kill_switch.OandaPracticeClient', FakeClientFactory)

    oc = DummyOandaConnector()
    state = pnl_kill_switch.run_pnl_once(oc)
    assert state['triggered'] is True
    assert state['total_loss'] <= -220


def test_run_pnl_once_no_trigger(monkeypatch):
    dc = DummyClient(realized=0.0, unrealized=-50.0)

    class FakeClientFactory:
        def __init__(self, *a, **k):
            pass

        def __call__(self, *a, **k):
            return dc

    monkeypatch.setattr('multi_broker_phoenix.monitor.pnl_kill_switch.OandaPracticeClient', FakeClientFactory)
    oc = DummyOandaConnector()
    state = pnl_kill_switch.run_pnl_once(oc)
    assert state['triggered'] is False
    assert state['total_loss'] > -220
