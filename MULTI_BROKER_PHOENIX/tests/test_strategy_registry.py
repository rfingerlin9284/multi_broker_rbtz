from multi_broker_phoenix.strategies.base import list_strategies, get_strategy


def test_list_strategies_contains_expected():
    d = list_strategies()
    # core strategies should be present
    assert 'holy_grail' in d
    assert 'ema_scalper' in d


def test_get_strategy_returns_instance():
    s = get_strategy('holy_grail')
    assert s is not None
    assert s.__class__.__name__ == 'HolyGrail'
