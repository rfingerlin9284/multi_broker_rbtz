import json
from multi_broker_phoenix.api.app import app, RM, ENGINE


def test_preview_missing_candidate():
    client = app.test_client()
    rv = client.post('/actions/test-order/preview', json={})
    assert rv.status_code == 400


def test_preview_and_confirm_simulated():
    client = app.test_client()
    # set equity high so sizing allowed
    RM.update_equity(100000.0)
    cand = {'candidate': {'symbol': 'SYM', 'platform': 'COINBASE', 'entry_price': 100.0, 'stop_loss': 99.0, 'side': 'BUY'}}
    rv = client.post('/actions/test-order/preview', json=cand)
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['allowed'] is True
    # confirm
    ENGINE.clear_trades()
    rv2 = client.post('/actions/test-order/confirm', json={**cand, 'mode': 'simulated'})
    assert rv2.status_code == 200
    d2 = rv2.get_json()
    assert d2['status'] == 'ok'
    # check audit table exists
    rows = ENGINE.list_trades()
    assert len(rows) >= 1


def test_confirm_blocked_by_oanda_creds_missing(monkeypatch):
    client = app.test_client()
    cand = {'candidate': {'symbol': 'EUR_USD', 'platform': 'OANDA', 'entry_price': 1.0, 'stop_loss': 0.99, 'side': 'BUY'}}
    ENGINE.clear_trades()
    rv = client.post('/actions/test-order/confirm', json={**cand, 'mode': 'platform_paper'})
    assert rv.status_code == 403
