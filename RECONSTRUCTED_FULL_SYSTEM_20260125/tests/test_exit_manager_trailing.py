import os
from multi_broker_phoenix.risk.exit_manager import ExitManager


def test_trailing_stop_updates_when_profit_exceeds_threshold(monkeypatch):
    # Configure trailing to trigger quickly
    monkeypatch.setenv('EXIT_ENABLE_TRAILING', 'true')
    monkeypatch.setenv('EXIT_TRAILING_START_PIPS', '20')
    monkeypatch.setenv('EXIT_TRAILING_DISTANCE_PIPS', '10')

    captured = {}

    class FakeConnector:
        def modify_trade(self, trade_id, stopLoss=None, **kwargs):
            captured['trade_id'] = trade_id
            captured['stopLoss'] = stopLoss
            return {'ok': True}

    em = ExitManager(FakeConnector())

    pos = {
        'id': 'T1',
        'instrument': 'EUR_USD',
        'side': 'long',
        'averagePrice': 1.2000,
        'stopLossOrder': {'price': 1.1990},
    }

    updated = em._apply_trailing_stop(pos, profit_pips=25.0, current_price=1.2025)

    assert updated is True
    assert captured['trade_id'] == 'T1'
    # Entry 1.2000 + (25-10) pips = 1.2015
    assert float(captured['stopLoss']['price']) == 1.2015


def test_time_stop_close_when_age_exceeds_max(monkeypatch):
    monkeypatch.setenv('EXIT_ENABLE_TIME_STOP', 'true')
    monkeypatch.setenv('EXIT_MAX_HOLD_HOURS', '8')
    monkeypatch.setenv('MAX_HOLD_SECONDS', '28800')

    closed = {'id': None}

    class FakeConnector:
        def close_trade(self, trade_id):
            closed['id'] = trade_id
            return {'ok': True}

    em = ExitManager(FakeConnector())

    pos = {
        'id': 'T2',
        'instrument': 'EUR_USD',
        'side': 'long',
        'averagePrice': 1.2000,
        'stopLossOrder': {'price': 1.1990},
    }

    # 9 hours old
    result = em._apply_time_stop(pos, age_sec=9 * 3600, hard=True)
    assert result is True
    assert closed['id'] == 'T2'
