import os
import pytest

from multi_broker_phoenix.brokers.oanda_connector import OANDAConnector
from multi_broker_phoenix.monitor import watchdog


class FakeClient:
    def __init__(self, *a, **k):
        pass

    def create_order_market(self, instrument, units, sl_price, tp_price, client_tag=None):
        # Simulate order create but missing SL/TP attachments in create response
        return {'orderCreateTransaction': {'id': '12345', 'instrument': instrument}, 'success': True}

    def get_account_summary(self):
        # Provide margin fields to avoid preflight skipping in tests
        return {'account': {'realizedPL': 0.0, 'unrealizedPL': 0.0, 'marginAvailable': 1000.0, 'marginUsed': 0.0, 'balance': 10000.0}}

    def list_open_trades(self):
        return {'trades': []}

    def close_all_positions(self):
        return {}


class FakeClientFactory:
    def __init__(self, *a, **k):
        pass

    def __call__(self, *a, **k):
        return FakeClient()


def test_oco_missing_triggers_freeze(monkeypatch):
    # Ensure watchdog is un-frozen initially
    try:
        from multi_broker_phoenix.monitor.watchdog import _set_trading_allowed as _wd_set
        _wd_set(True)
    except Exception:
        pass

    # Monkeypatch OandaPracticeClient to our fake
    monkeypatch.setattr('multi_broker_phoenix.monitor.pnl_kill_switch.OandaPracticeClient', FakeClientFactory)
    # Create a fake execution.oanda_practice_client module in sys.modules so runtime imports succeed
    import types, sys
    fake_exec = types.ModuleType('execution')
    fake_sub = types.ModuleType('execution.oanda_practice_client')
    fake_sub.OandaPracticeClient = FakeClientFactory
    fake_exec.oanda_practice_client = fake_sub
    monkeypatch.setitem(sys.modules, 'execution', fake_exec)
    monkeypatch.setitem(sys.modules, 'execution.oanda_practice_client', fake_sub)

    # Create connector and candidate
    os.environ['OANDA_API_TOKEN'] = 'fake'
    os.environ['OANDA_ACCOUNT_ID'] = 'acct'

    conn = OANDAConnector(token=os.getenv('OANDA_API_TOKEN'), account_id=os.getenv('OANDA_ACCOUNT_ID'), practice_mode=True, http_client=None)

    class Cand:
        symbol = 'EUR_USD'
        side = 'BUY'
        stop_loss = 0.99
        take_profit = 1.01
        client_tag = 'smoke'

    res = conn.place_paper_order(Cand(), units=100)
    assert res.get('watchdog_freeze') == 'OCO_MISSING'
    assert watchdog.trading_allowed() is False

    # Cleanup: unfreeze
    try:
        from multi_broker_phoenix.monitor.watchdog import _set_trading_allowed as _wd_set
        _wd_set(True)
    except Exception:
        pass


def test_trailing_repair_attempt_succeeds(monkeypatch):
    """Simulate a missing trailing stop that can be repaired by creating one."""
    # Ensure watchdog is un-frozen initially
    try:
        from multi_broker_phoenix.monitor.watchdog import _set_trading_allowed as _wd_set
        _wd_set(True)
    except Exception:
        pass

    class FakeClient2(FakeClient):
        def create_order_market(self, instrument, units, sl_price, tp_price, client_tag=None):
            # Simulate order fill with SL/TP attachments present but no trailing stop
            return {
                'orderCreateTransaction': {
                    'id': '12345',
                    'instrument': instrument,
                    'takeProfitOnFill': {'price': str(tp_price)},
                    'stopLossOnFill': {'price': str(sl_price)},
                },
                'orderFillTransaction': {'tradeOpened': {'tradeID': 'T123'}},
                'success': True,
            }

        def list_open_trades(self):
            # Return a trade without trailingStopLoss
            return {'trades': [{'tradeID': 'T123', 'instrument': 'EUR_USD'}]}

        def create_trailing_stop(self, instrument, trade_id, distance):
            # Simulate successful trailing stop creation
            return {'orderCreateTransaction': {'id': 'trail-1'}}

    class FakeClientFactory2(FakeClientFactory):
        def __call__(self, *a, **k):
            return FakeClient2()

    # Monkeypatch OandaPracticeClient to our fake that supports trailing repair
    monkeypatch.setattr('multi_broker_phoenix.monitor.pnl_kill_switch.OandaPracticeClient', FakeClientFactory2)
    # Create a fake execution.oanda_practice_client module in sys.modules so runtime imports succeed
    import types, sys
    fake_exec = types.ModuleType('execution')
    fake_sub = types.ModuleType('execution.oanda_practice_client')
    fake_sub.OandaPracticeClient = FakeClientFactory2
    fake_exec.oanda_practice_client = fake_sub
    monkeypatch.setitem(sys.modules, 'execution', fake_exec)
    monkeypatch.setitem(sys.modules, 'execution.oanda_practice_client', fake_sub)

    # Create connector and candidate
    os.environ['OANDA_API_TOKEN'] = 'fake'
    os.environ['OANDA_ACCOUNT_ID'] = 'acct'

    conn = OANDAConnector(token=os.getenv('OANDA_API_TOKEN'), account_id=os.getenv('OANDA_ACCOUNT_ID'), practice_mode=True, http_client=None)

    class Cand2:
        symbol = 'EUR_USD'
        side = 'BUY'
        stop_loss = 0.99
        take_profit = 1.01
        client_tag = 'smoke'
        trailing_distance = 10.0

    res = conn.place_paper_order(Cand2(), units=100)
    # Repair should succeed and not freeze the system
    assert res.get('watchdog_freeze') is None
    assert watchdog.trading_allowed() is True

    # Cleanup: unfreeze (idempotent)
    try:
        from multi_broker_phoenix.monitor.watchdog import _set_trading_allowed as _wd_set
        _wd_set(True)
    except Exception:
        pass
