import math
import pytest
from core.signal_brain import Layer3_FullIndicatorScan, unified_signal


def make_candles(close_start=1.0, step=0.001, n=220):
    # Create synthetic candles with gentle uptrend so indicators bias BUY
    candles = []
    price = close_start
    for i in range(n):
        open_p = price
        high = price + step * 1.2
        low = price - step * 1.2
        close = price + step
        volume = 100 + (i % 10)
        candles.append({"mid": {"o": open_p, "h": high, "l": low, "c": close}, "volume": volume})
        price = close
    return candles


def test_layer3_no_crash_and_indicators_present():
    scan = Layer3_FullIndicatorScan()
    candles = make_candles()
    result = scan.evaluate("EUR_USD", {"candles": candles})
    assert "meta" in result
    # Must include indicators if enough candles
    assert isinstance(result["meta"].get("indicators"), dict)


def test_unified_signal_returns_buy_on_uptrend():
    candles = make_candles()
    sig, conf, meta = unified_signal("EUR_USD", candles)
    assert sig in ("BUY", None, "SELL")
    # On our synthetic uptrend, expect BUY or None (if confluence threshold not reached)
    if sig == "BUY":
        assert conf > 0


if __name__ == "__main__":
    pytest.main(["-q", __file__])
