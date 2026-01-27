import importlib
from multi_broker_phoenix.strategies.base import get_strategy, STRATEGY_REGISTRY

# ensure the bullish_regime module is imported so it registers itself
importlib.import_module('multi_broker_phoenix.strategies.bullish_regime')


def test_bullish_regime_delegates_to_holy_grail():
    holy = get_strategy('holy_grail')
    bull = get_strategy('bullish_regime')
    assert holy is not None
    assert bull is not None
    prices = list(1.0 + 0.001 * i for i in range(20))
    market = {'symbol': 'SYM-B', 'platform': 'OANDA', 'prices': prices}
    cand_h = holy.generate_candidate(market)
    cand_b = bull.generate_candidate(market)
    # Both should produce equivalent candidates (or both None)
    if cand_h is None:
        assert cand_b is None
    else:
        assert cand_b is not None
        assert cand_h.symbol == cand_b.symbol
        assert cand_h.side == cand_b.side
        assert cand_h.entry_price == cand_b.entry_price
        assert cand_h.stop_loss == cand_b.stop_loss


def test_bullish_regime_missing_delegate_returns_none(monkeypatch):
    # Temporarily remove holy_grail from registry
    orig = STRATEGY_REGISTRY.pop('holy_grail', None)
    try:
        bull = get_strategy('bullish_regime')
        assert bull is not None
        prices = [1.0, 1.02, 1.03]
        cand = bull.generate_candidate({'symbol': 'X', 'platform': 'OANDA', 'prices': prices})
        assert cand is None
    finally:
        if orig is not None:
            STRATEGY_REGISTRY['holy_grail'] = orig


def test_bullish_regime_self_reference_guard(monkeypatch):
    # Simulate a mis-registration where holy_grail points at bullish_regime
    bull = get_strategy('bullish_regime')
    assert bull is not None
    orig = STRATEGY_REGISTRY.get('holy_grail')
    # inject self into registry
    STRATEGY_REGISTRY['holy_grail'] = bull
    try:
        prices = [1.0, 1.01, 1.02]
        cand = bull.generate_candidate({'symbol': 'SELF', 'platform': 'OANDA', 'prices': prices})
        assert cand is None
    finally:
        # restore original registry value
        if orig is not None:
            STRATEGY_REGISTRY['holy_grail'] = orig
        else:
            STRATEGY_REGISTRY.pop('holy_grail', None)
