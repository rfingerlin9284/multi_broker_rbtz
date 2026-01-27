import pytest
from multi_broker_phoenix.strategies.base import get_strategy, list_strategies


def test_strategy_registered():
    strategies = list_strategies()
    assert 'fabio_aaa_full' in strategies


def test_generate_candidate_none_on_small_history():
    s = get_strategy('fabio_aaa_full')
    assert s is not None
    cand = s.generate_candidate({'prices': [1.0, 1.01, 1.02]})
    assert cand is None


def test_generate_candidate_returns_candidate_with_tranches():
    s = get_strategy('fabio_aaa_full')
    # Build synthetic price series with clear momentum
    prices = [100.0 + i*0.5 for i in range(30)]
    market_data = {'prices': prices, 'symbol':'BTC-USD', 'platform':'COINBASE'}
    cand = s.generate_candidate(market_data)
    assert cand is not None
    assert cand.strategy_id == 'fabio_aaa_full'
    assert hasattr(cand, 'tranche_plan')
    plan = getattr(cand, 'tranche_plan')
    assert isinstance(plan, list)
    assert len(plan) == 3
    # primary stop equals candidate.stop_loss
    assert pytest.approx(plan[0]['stop_price'], rel=1e-6) == cand.stop_loss
    assert hasattr(cand, 'charter')
    assert 'require_full_mode_inputs' in cand.charter
