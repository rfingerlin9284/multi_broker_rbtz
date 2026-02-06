import os
import time
import json
import types
import sys
from pathlib import Path
# Ensure repo root is in path for local test execution
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.run_headless import TradingStrategyScanner, AutonomousTradingEngine, tp_guard


def make_candles_with_cross():
    # create 60 candles where the last values increase sharply to trigger EMA cross
    candles = []
    for i in range(60):
        if i < 57:
            base = 10.0
        elif i == 57:
            base = 10.0
        elif i == 58:
            base = 1.0
        else:
            base = 1000.0
        candles.append({'close': base, 'high': base + 0.1, 'low': base - 0.1})
    return candles


def test_generate_signals_enrichment():
    catalog = {
        'ema_scalper': {'name': 'EMA Scalper', 'allow_stop_only': True, 'tags': ['scalp'], 'win_rate_pct': 85}
    }
    scanner = TradingStrategyScanner(catalog=catalog)
    scanner.enabled_strategies = ['ema_scalper']
    candles = make_candles_with_cross()
    sigs = scanner.generate_signals('EUR_USD', candles)
    # Expect at least one signal and that it's enriched
    assert any(s['strategy'] == 'ema_scalper' for s in sigs), f"No ema_scalper signal found: {sigs}"
    found = next(s for s in sigs if s['strategy'] == 'ema_scalper')
    assert found.get('allow_stop_only') is True
    assert 'catalog' in found and found['catalog']['name'] == 'EMA Scalper'


class DummyOrderExecutor:
    def __init__(self):
        self.last_oco = None

    def place_oco(self, oco):
        self.last_oco = oco
        return True


def test_execute_trade_sl_only_flow(monkeypatch):
    # Prepare engine
    eng = AutonomousTradingEngine(mode='paper')
    # Monkeypatch tp_guard to always strip TP (simulate policy)
    monkeypatch.setattr('tools.run_headless.tp_guard', lambda *_: None)

    # Set OCO class and order executor
    class FakeOCO:
        def __init__(self, symbol, entry_side, entry_quantity, take_profit_price, stop_loss_price, client_tag):
            self.symbol = symbol
            self.entry_side = entry_side
            self.entry_quantity = entry_quantity
            self.take_profit_price = take_profit_price
            self.stop_loss_price = stop_loss_price
            self.client_tag = client_tag

    eng.OCOOrder = FakeOCO
    eng.order_executor = DummyOrderExecutor()
    # Mock price fetcher
    eng.candle_fetcher.get_price = lambda pair: {'bid': 1.20000, 'ask': 1.20010}

    # Ensure quality sizing disabled for determinism
    eng.enable_quality_sizing = False
    eng.max_units = 10000

    os.environ['STOP_ONLY_SIZE_MULT'] = '0.5'

    # Disable AI Hive to avoid rejection during unit test
    os.environ['ENABLE_AI_HIVE'] = 'false'
    signal = {'strategy': 'ema_scalper', 'pair': 'EUR_USD', 'side': 'BUY', 'confidence': 0.8, 'allow_stop_only': True}
    res = eng.execute_trade(signal)
    # After execution, order executor should have recorded an OCO with tp=None
    assert eng.order_executor.last_oco is not None
    oco = eng.order_executor.last_oco
    assert oco.take_profit_price is None
    expected_qty = int(eng.max_units * float(os.getenv('STOP_ONLY_SIZE_MULT', '0.5')))
    assert int(oco.entry_quantity) == expected_qty
    assert oco.client_tag and oco.client_tag.startswith('sl_only_')


if __name__ == '__main__':
    # Quick local sanity run without pytest
    print('Running quick checks...')
    test_generate_signals_enrichment()
    print('✅ generate_signals_enrichment passed')
    # For execute_trade test, emulate monkeypatch by directly overriding tp_guard
    import tools.run_headless as rh
    rh.tp_guard = lambda *args, **kwargs: None
    test_execute_trade_sl_only_flow(monkeypatch=types.SimpleNamespace(setattr=lambda *a, **k: None))
    print('✅ execute_trade_sl_only_flow passed')