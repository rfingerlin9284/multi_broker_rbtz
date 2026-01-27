from multi_broker_phoenix.strategies.base import get_strategy


def test_holy_grail_rsi_filter_allows_trend():
    s = get_strategy('holy_grail')
    # craft a rising price series with moderate RSI
    prices = [1.0, 1.001, 1.002, 1.003, 1.004, 1.005, 1.006, 1.007, 1.008, 1.009, 1.010, 1.011, 1.012, 1.013, 1.014]
    cand = s.generate_candidate({'symbol': 'SYM', 'platform': 'OANDA', 'prices': prices})
    assert cand is not None


def test_holy_grail_rsi_blocks_extreme():
    s = get_strategy('holy_grail')
    # artificially create very high RSI by strong gains
    prices = [1.0]
    for i in range(30):
        prices.append(prices[-1] * 1.02)
    cand = s.generate_candidate({'symbol': 'SYM', 'platform': 'OANDA', 'prices': prices})
    assert cand is None
