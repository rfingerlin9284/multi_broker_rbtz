import os
import types
import time

import pytest

from multi_broker_phoenix.monitor import watchdog


class DummyOanda:
    def __init__(self, ok: bool = True):
        self._ok = ok

    def verify_credentials(self):
        return {'success': bool(self._ok)}


class DummyResp:
    def __init__(self, status_code=200, text='OK'):
        self.status_code = status_code
        self.text = text


def test_resolve_ai_health_urls_xai_and_deepseek(monkeypatch):
    # Clean env
    monkeypatch.delenv('GROK_HEALTH_URL', raising=False)
    monkeypatch.delenv('XAI_API_URL', raising=False)
    monkeypatch.delenv('DEEPSEEK_HEALTH_URL', raising=False)

    # XAI key present -> expect xai_base + /v1/models
    monkeypatch.setenv('XAI_API_KEY', 'xai-test-key')
    monkeypatch.setenv('XAI_BASE_URL', 'https://api.x.ai/v1')

    # DeepSeek key present -> expect https://api.deepseek.com/v1/models
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'ds-test-key')

    grok_url, deepseek_url = watchdog.resolve_ai_health_urls()
    assert grok_url is not None and grok_url.endswith('/v1/models')
    assert deepseek_url == 'https://api.deepseek.com/v1/models'


def test_run_watchdog_once_ok_and_auth_fail(monkeypatch):
    # Prepare dummy oanda connector OK
    oanda_ok = DummyOanda(ok=True)

    # Simulate requests.get:
    calls = {}

    def fake_get_ok(url, timeout=5, headers=None):
        calls['last'] = (url, headers)
        return DummyResp(status_code=200)

    # When both endpoints return 200 -> watchdog ok
    monkeypatch.setenv('XAI_API_KEY', 'xai-test-key')
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'ds-test-key')
    monkeypatch.setenv('XAI_BASE_URL', 'https://api.x.ai/v1')
    monkeypatch.setenv('MIN_BRAIN_SEATS', '1')

    monkeypatch.setattr(watchdog.requests, 'get', fake_get_ok)

    gx, dx = watchdog.resolve_ai_health_urls()
    state = watchdog.run_watchdog_once(oanda_ok, gx, dx)
    assert state['ok'] is True
    assert watchdog.trading_allowed() is True
    assert state['details']['grok']['ok'] is True
    assert state['details']['deepseek']['ok'] is True

    # Now simulate DeepSeek returning 401 -> AUTH_FAIL (still OK if another seat healthy)
    def fake_get_deepseek_401(url, timeout=5, headers=None):
        if 'deepseek' in url:
            return DummyResp(status_code=401)
        return DummyResp(status_code=200)

    monkeypatch.setattr(watchdog.requests, 'get', fake_get_deepseek_401)
    state2 = watchdog.run_watchdog_once(oanda_ok, gx, dx)
    assert state2['ok'] is True
    assert watchdog.trading_allowed() is True
    assert state2['details']['deepseek']['code'] == 401
    assert state2['details']['deepseek']['reason'] == 'AUTH_FAIL'

    # If OANDA creds fail, also freeze
    oanda_fail = DummyOanda(ok=False)
    monkeypatch.setattr(watchdog.requests, 'get', fake_get_ok)
    state3 = watchdog.run_watchdog_once(oanda_fail, gx, dx)
    assert state3['ok'] is False
    assert watchdog.trading_allowed() is False
    assert state3['details']['oanda']['ok'] is False


if __name__ == '__main__':
    pytest.main([__file__])
