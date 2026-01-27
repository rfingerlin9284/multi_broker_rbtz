import time
try:
    from multi_broker_phoenix.monitor.edge_scorekeeper import record_trade, compute_expectancy
except Exception:
    import importlib.util, os
    RP = os.path.abspath(os.path.join(os.getcwd(), 'multi_broker_phoenix', 'monitor', 'edge_scorekeeper.py'))
    spec = importlib.util.spec_from_file_location('edge_scorekeeper', RP)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    record_trade = mod.record_trade
    compute_expectancy = mod.compute_expectancy


def test_record_and_expectancy(tmp_path):
    # record a few trades
    record_trade({'strategy': 's1', 'regime': 'TREND', 'score': 80.0, 'entry_reasons': ['ok'], 'exit_reason': 'TP', 'pnl': 5.0, 'duration': 60, 'spread': 1.0, 'atr': 0.001})
    record_trade({'strategy': 's1', 'regime': 'TREND', 'score': 70.0, 'entry_reasons': ['ok'], 'exit_reason': 'SL', 'pnl': -3.0, 'duration': 30, 'spread': 1.0, 'atr': 0.001})
    res = compute_expectancy('s1', hours=24)
    assert res['count'] >= 2
    assert 'expectancy' in res
