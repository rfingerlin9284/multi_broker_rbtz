try:
    from multi_broker_phoenix.tools.backtest import Backtester
except Exception:
    # Fall back to explicit file-based import (helps when test discovery
    # uses a different sys.path or package root)
    import importlib.util, pathlib
    backtest_path = pathlib.Path(__file__).resolve().parents[1] / 'multi_broker_phoenix' / 'tools' / 'backtest.py'
    spec = importlib.util.spec_from_file_location('mbp_tools_backtest', str(backtest_path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    Backtester = module.Backtester


def test_backtester_runs():
    # use a simple uptrend to produce buy signals and positive returns
    prices = [1.0 + 0.001 * i for i in range(50)]
    bt = Backtester('holy_grail')
    stats = bt.run(prices, symbol='SYM', platform='OANDA')
    assert 'trades' in stats
    assert stats['trades'] >= 0
    assert 'total_return' in stats
