from pathlib import Path
from multi_broker_phoenix.risk.platform_breaker import set_platform_enabled, is_platform_enabled

def test_platform_breaker_roundtrip(tmp_path: Path):
    p = tmp_path / "platform_breakers.json"
    assert is_platform_enabled("oanda", p) is True
    set_platform_enabled("oanda", False, reason="test_off", path=p)
    assert is_platform_enabled("oanda", p) is False
    set_platform_enabled("oanda", True, reason="test_on", path=p)
    assert is_platform_enabled("oanda", p) is True
