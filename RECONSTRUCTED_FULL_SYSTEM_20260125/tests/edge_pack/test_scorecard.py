try:
    from execution.scorecard import score_signal
except Exception:
    import importlib.util, os
    RP = os.path.abspath(os.path.join(os.getcwd(), 'execution', 'scorecard.py'))
    spec = importlib.util.spec_from_file_location('edge_scorecard', RP)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    score_signal = mod.score_signal


def test_scorecard_pass():
    features = {'htf_alignment': 1.0, 'structure': 1.0, 'momentum': 1.0, 'volatility_sanity': 1.0, 'spread_sanity': 1.0, 'risk_feasibility': 1.0}
    res = score_signal(features, {'weights': {'htf_alignment':0.25,'structure':0.25,'momentum':0.2,'volatility_sanity':0.15,'spread_sanity':0.05,'risk_feasibility':0.1}, 'min_score_threshold':70})
    assert res['passed'] is True
    assert res['score'] >= 70


def test_scorecard_fail():
    features = {'htf_alignment': 0.0, 'structure': 0.4, 'momentum': 0.2, 'volatility_sanity': 0.4, 'spread_sanity': 1.0, 'risk_feasibility': 1.0}
    res = score_signal(features, {'weights': {'htf_alignment':0.25,'structure':0.25,'momentum':0.2,'volatility_sanity':0.15,'spread_sanity':0.05,'risk_feasibility':0.1}, 'min_score_threshold':70})
    assert res['passed'] is False
    assert res['score'] < 70