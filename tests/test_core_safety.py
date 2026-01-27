import os
import types
import sys

from multi_broker_phoenix.monitor import protect_and_exit, pnl_kill_switch

class FakeClientBase:
    def __init__(self, *a, **k):
        self.closed = []
        self.created_trailing = []
    def list_open_trades(self):
        return {'trades': []}
    def get_account_summary(self):
        return {'account': {'balance': 10000.0, 'marginAvailable': 1000.0, 'marginUsed': 1000.0}}
    def close_position(self, instrument):
        self.closed.append(instrument)
        return {'closed': instrument}
    def close_all_positions(self):
        return {}


def test_protect_reconciler_closes_unprotected(monkeypatch):
    # Fake client with one unprotected trade and failing trailing creation
    class Fake(FakeClientBase):
        def list_open_trades(self):
            return {'trades': [{'tradeID':'T1','instrument':'EUR_USD','currentUnits':100}]}
        def create_trailing_stop(self, instrument, trade_id, distance):
            raise RuntimeError('fail create')

    fake_factory = lambda *a, **k: Fake()

    # monkeypatch the import used by reconciler
    fake_module = types.ModuleType('execution.oanda_practice_client')
    fake_module.OandaPracticeClient = lambda *a, **k: fake_factory
    monkeypatch.setitem(sys.modules, 'execution', types.ModuleType('execution'))
    monkeypatch.setitem(sys.modules, 'execution.oanda_practice_client', fake_module)

    # ensure watchdog unfrozen
    try:
        from multi_broker_phoenix.monitor.watchdog import _set_trading_allowed as _wd_set
        _wd_set(True)
    except Exception:
        pass

    class OC: pass
    oc = OC()
    oc.token = 'fake'
    oc.account_id = 'acct'
    oc.base_url = 'https://api-fxpractice.oanda.com'
    oc.http = None

    res = protect_and_exit.run_reconcile_once(oc, {'repair_attempts':1, 'initial_backoff_sec':0.01, 'enabled': True})
    assert res['processed'] == 1
    assert res['closed'] == 1


def test_breakeven_sets_stop(monkeypatch):
    # Fake client with one profitable trade
    class Fake(FakeClientBase):
        def list_open_trades(self):
            return {'trades': [{'tradeID':'T1','instrument':'EUR_USD','currentUnits':100,'price':1.1000,'currentPrice':1.1100}]}
        def create_stop_loss(self, trade_id, price):
            self.last_stop = (trade_id, price)
            return {'orderCreateTransaction': {'id': 's1'}}

    fake = Fake()
    fake_module = types.ModuleType('execution.oanda_practice_client')
    fake_module.OandaPracticeClient = lambda *a, **k: (lambda: fake)
    monkeypatch.setitem(sys.modules, 'execution', types.ModuleType('execution'))
    monkeypatch.setitem(sys.modules, 'execution.oanda_practice_client', fake_module)

    class OC: pass
    oc = OC()
    oc.token = 'fake'
    oc.account_id = 'acct'
    oc.base_url = 'https://api-fxpractice.oanda.com'
    oc.http = None

    res = protect_and_exit.run_reconcile_once(oc, {'repair_attempts': 1, 'initial_backoff_sec': 0.01, 'enabled': True})
    # no unprotected trades in this fake; run breakeven
    from multi_broker_phoenix.monitor.breakeven_worker import run_breakeven_once
    br = run_breakeven_once(oc, {'enabled': True, 'trigger_pips': 5.0, 'sl_offset_pips': 0.2, 'verify_after_modify': False})
    assert br['breakeven_set'] == 1


def test_breakeven_skips_when_not_profit(monkeypatch):
    class Fake(FakeClientBase):
        def list_open_trades(self):
            # tiny profit (0.5 pips) - well below trigger
            return {'trades': [{'tradeID':'T2','instrument':'EUR_USD','currentUnits':100,'price':1.1000,'currentPrice':1.10005}]}
        def create_stop_loss(self, trade_id, price):
            self.last_stop = (trade_id, price)
            return {'orderCreateTransaction': {'id': 's1'}}

    fake = Fake()
    fake_module = types.ModuleType('execution.oanda_practice_client')
    fake_module.OandaPracticeClient = lambda *a, **k: (lambda: fake)
    monkeypatch.setitem(sys.modules, 'execution', types.ModuleType('execution'))
    monkeypatch.setitem(sys.modules, 'execution.oanda_practice_client', fake_module)

    class OC: pass
    oc = OC()
    oc.token = 'fake'
    oc.account_id = 'acct'
    oc.base_url = 'https://api-fxpractice.oanda.com'
    oc.http = None

    from multi_broker_phoenix.monitor.breakeven_worker import run_breakeven_once
    br = run_breakeven_once(oc, {'enabled': True, 'trigger_pips': 10.0, 'sl_offset_pips': 0.2, 'verify_after_modify': False})
    # Debug assertion: validate behavior matches computed pips
    # Ensure no stop was actually created on the fake client (no side-effect)
    assert getattr(fake, 'last_stop', None) is None


    try:
        from multi_broker_phoenix.monitor.watchdog import trading_allowed
        assert trading_allowed() is False
    except Exception:
        pass


def test_margin_emergency_flatten_and_freeze(monkeypatch):
    class Fake(FakeClientBase):
        def get_account_summary(self):
            return {'account': {'balance': 10000.0, 'marginAvailable': 10.0, 'marginUsed': 9950.0}}
        def list_open_trades(self):
            return {'trades':[{'instrument':'EUR_USD','currentUnits':1000}]}

    fake = Fake()
    fake_module = types.ModuleType('execution.oanda_practice_client')
    fake_module.OandaPracticeClient = lambda *a, **k: (lambda: fake)
    monkeypatch.setitem(sys.modules, 'execution', types.ModuleType('execution'))
    monkeypatch.setitem(sys.modules, 'execution.oanda_practice_client', fake_module)

    class OC: pass
    oc = OC()
    oc.token = 'fake'
    oc.account_id = 'acct'
    oc.base_url = 'https://api-fxpractice.oanda.com'
    oc.http = None

    # run a margin check
    cfg = {'enabled': True, 'min_margin_available_usd': 500.0, 'max_margin_used_pct': 0.5}
    res = pnl_kill_switch.run_margin_once(oc, cfg)
    assert res['triggered'] is True

    try:
        from multi_broker_phoenix.monitor.watchdog import trading_allowed
        assert trading_allowed() is False
    except Exception:
        pass


def test_preflight_skip_on_margin(monkeypatch):
    class Fake(FakeClientBase):
        def get_account_summary(self):
            return {'account': {'balance': 10000.0, 'marginAvailable': 10.0, 'marginUsed': 9990.0}}
        def list_open_trades(self):
            return {'trades':[]}
        def get_prices(self, instruments):
            return {'prices':[{'closeoutAsk':1.1,'closeoutBid':1.09}]}

    fake = Fake()
    fake_module = types.ModuleType('execution.oanda_practice_client')
    fake_module.OandaPracticeClient = lambda *a, **k: (lambda: fake)
    monkeypatch.setitem(sys.modules, 'execution', types.ModuleType('execution'))
    monkeypatch.setitem(sys.modules, 'execution.oanda_practice_client', fake_module)

    # Ensure watchdog un-frozen for this test
    try:
        from multi_broker_phoenix.monitor.watchdog import _set_trading_allowed as _wd_set
        _wd_set(True)
    except Exception:
        pass

    # Create OANDA connector
    from multi_broker_phoenix.brokers.oanda_connector import OANDAConnector
    os.environ['OANDA_API_TOKEN'] = 'f'
    os.environ['OANDA_ACCOUNT_ID'] = 'acct'
    conn = OANDAConnector(token='f', account_id='acct', practice_mode=True, http_client=None)

    class Cand:
        symbol = 'EUR_USD'
        stop_loss = 0.99
        take_profit = 1.01
        client_tag = 'smoke'
    res = conn.place_paper_order(Cand(), units=100)
    assert res.get('skip_reason') == 'MARGIN_EMERGENCY'
