try:
    from execution.regime import classify
except Exception:
    # Fallback to loading by path if import fails under pytest
    import importlib.util, os
    RP = os.path.abspath(os.path.join(os.getcwd(), 'execution', 'regime.py'))
    spec = importlib.util.spec_from_file_location('edge_regime', RP)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    classify = mod.classify


def test_classify_insufficient():
    res = classify([], {'ema_short_period':12,'ema_long_period':26,'adx_trend_threshold':20,'chaop_atr_threshold':0.00005})
    assert res['regime'] == 'CHAOP'


def test_classify_trend():
    # create synthetic trending prices
    prices = [1.0 + i*0.001 for i in range(40)]
    res = classify(prices, {'ema_short_period':12,'ema_long_period':26,'adx_trend_threshold':5,'chaop_atr_threshold':0.00005})
    assert res['regime'] in ('TREND','RANGE')
