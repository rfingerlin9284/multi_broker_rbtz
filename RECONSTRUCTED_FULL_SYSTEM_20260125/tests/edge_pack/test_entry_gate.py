import time
from execution.entry_gate import EntryGate


class Cand:
    def __init__(self, symbol, entry_price=None):
        self.symbol = symbol
        self.entry_price = entry_price


def test_spread_skip():
    c = Cand('EUR_USD')
    market = {'bid': 1.1000, 'ask': 1.1005, 'spread_pips': 5.0, 'prices': [1.1, 1.1002, 1.1004]}
    res = EntryGate.evaluate(c, market)
    assert res['allow'] is False
    assert 'SKIP_SPREAD' in res['reasons']


def test_low_vol_skip(monkeypatch):
    import execution.entry_gate as eg
    monkeypatch.setitem(eg._FF.setdefault('ENTRY_GATE', {}), 'atr_low_threshold', 0.00001)
    c = Cand('EUR_USD')
    prices = [1.1000 + (i * 0.000001) for i in range(20)]
    market = {'bid': 1.1000, 'ask': 1.1001, 'prices': prices}
    res = EntryGate.evaluate(c, market)
    assert res['allow'] is False
    assert 'SKIP_LOW_VOL' in res['reasons']


def test_spike_detector(monkeypatch):
    import execution.entry_gate as eg
    monkeypatch.setitem(eg._FF.setdefault('ENTRY_GATE', {}), 'spike_detector_multiplier', 2.0)
    c = Cand('EUR_USD')
    prices = [1.1000, 1.1001, 1.1002, 1.1030]
    recent_ranges = [abs(prices[i] - prices[i-1]) for i in range(1, len(prices))]
    market = {'bid': 1.1030, 'ask': 1.1031, 'prices': prices, 'recent_ranges': recent_ranges}
    res = EntryGate.evaluate(c, market)
    assert res['allow'] is False
    assert 'SKIP_EVENT_SPIKE' in res['reasons']


def test_cooldown(monkeypatch):
    import execution.entry_gate as eg
    monkeypatch.setitem(eg._FF.setdefault('ENTRY_GATE', {}), 'cooldown_seconds', 3600)
    c = Cand('EUR_USD')
    market = {'bid': 1.1000, 'ask': 1.1001, 'prices': [1.1, 1.1002, 1.1004]}
    EntryGate.mark_close('EUR_USD')
    # immediate evaluate should be blocked by cooldown default
    res = EntryGate.evaluate(c, market)
    assert res['allow'] is False
    assert 'SKIP_COOLDOWN' in res['reasons']
