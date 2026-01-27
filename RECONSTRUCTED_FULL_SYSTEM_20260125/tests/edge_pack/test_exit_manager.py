try:
    from execution.exit_manager import run_quick_cut_once
except Exception:
    import importlib.util, os
    RP = os.path.abspath(os.path.join(os.getcwd(), 'execution', 'exit_manager.py'))
    spec = importlib.util.spec_from_file_location('edge_exit_manager', RP)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    run_quick_cut_once = mod.run_quick_cut_once


class FakeClient:
    def __init__(self, *a, **k):
        pass

    def list_open_trades(self):
        # One small trade that opened 10 seconds ago with -5 USD unrealized
        return {'trades': [{'tradeID': 't1', 'instrument': 'EUR_USD', 'openTimeTs': __import__('time').time() - 10, 'unrealizedPL': -5.0}]}

    def close_position(self, inst):
        return {'closed': inst}


class FakeConnector:
    token = 'x'
    account_id = '1'
    base_url = 'https://api'
    http = None


def test_quick_cut(monkeypatch):
    # patch client class import path used in exit manager
    import sys, types
    fake_mod = types.SimpleNamespace(OandaPracticeClient=lambda *a, **k: FakeClient())
    sys.modules['execution.oanda_practice_client'] = fake_mod
    res = run_quick_cut_once(FakeConnector(), {'enabled': True, 'max_loss_usd': 3.0, 'max_age_seconds': 60})
    # cleanup
    try:
        del sys.modules['execution.oanda_practice_client']
    except Exception:
        pass
    assert 'closed' in res
    assert len(res['closed']) >= 1
