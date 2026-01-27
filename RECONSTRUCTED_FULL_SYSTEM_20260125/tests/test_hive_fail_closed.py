import os
import pytest

from multi_broker_phoenix.engines.real_trading_engine import RealTradingEngine

class DummyBroker:
    __class__.__name__ = "DummyBroker"


def test_real_trading_engine_fail_closed_when_no_real_hive(monkeypatch):
    # Force LIVE trading mode and ensure no XAI/DEEPSEEK keys
    monkeypatch.setenv('TRADING_MODE', 'LIVE')
    monkeypatch.delenv('XAI_API_KEY', raising=False)
    monkeypatch.delenv('DEEPSEEK_API_KEY', raising=False)
    monkeypatch.setenv('ALLOW_PAPER_WITHOUT_HIVE', '0')

    with pytest.raises(RuntimeError):
        RealTradingEngine(DummyBroker(), initial_capital=10000)


def test_real_trading_engine_allows_simple_hive_in_paper_when_flag_set(monkeypatch):
    monkeypatch.setenv('TRADING_MODE', 'PAPER')
    monkeypatch.delenv('XAI_API_KEY', raising=False)
    monkeypatch.delenv('DEEPSEEK_API_KEY', raising=False)
    monkeypatch.setenv('ALLOW_PAPER_WITHOUT_HIVE', '1')

    # Should not raise
    engine = RealTradingEngine(DummyBroker(), initial_capital=10000)
    assert engine.use_simple_hive is True
