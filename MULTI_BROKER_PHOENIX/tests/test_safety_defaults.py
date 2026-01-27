import os
from multi_broker_phoenix.config.runtime import resolve_execution_type, paper_via_platform
from multi_broker_phoenix.api.app import app


def test_paper_via_platform_default_is_true(monkeypatch):
    # Ensure env-sourced behavior: if env var not set, default should be True
    monkeypatch.delenv('PAPER_VIA_PLATFORM', raising=False)
    assert paper_via_platform() is True


def test_resolve_execution_type_returns_platform_paper_for_oanda(monkeypatch):
    # With TRADING_MODE unset (defaults to PAPER) and PAPER_VIA_PLATFORM true, OANDA should be PLATFORM_PAPER
    monkeypatch.delenv('TRADING_MODE', raising=False)
    monkeypatch.delenv('PAPER_VIA_PLATFORM', raising=False)
    et = resolve_execution_type('OANDA', supports_platform_paper=True)
    assert et == 'PLATFORM_PAPER'


def test_platforms_endpoint_reports_oanda_creds_missing(monkeypatch):
    # Force app.OANDA to None to simulate missing creds/connector
    import multi_broker_phoenix.api.app as api_app
    api_app.OANDA = None
    client = api_app.app.test_client()
    rv = client.get('/platforms')
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['platforms']['OANDA']['creds_present'] is False
    assert data['platforms']['OANDA']['effective_execution_type'] == 'PLATFORM_PAPER'


def test_preview_returns_platform_paper_by_default(monkeypatch):
    # Confirm preview returns PLATFORM_PAPER execution_type for OANDA
    import multi_broker_phoenix.api.app as api_app
    client = api_app.app.test_client()
    cand = {'candidate': {'symbol': 'EUR_USD', 'platform': 'OANDA', 'entry_price': 1.0, 'stop_loss': 0.99, 'side': 'BUY'}}
    rv = client.post('/actions/test-order/preview', json=cand)
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['execution_type'] == 'PLATFORM_PAPER'
