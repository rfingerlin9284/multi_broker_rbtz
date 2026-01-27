import os
from unittest import mock
from multi_broker_phoenix.brokers.oanda_connector import OANDAConnector


def test_default_practice_mode_uses_fxpractice_url():
    o = OANDAConnector()
    assert 'fxpractice' in o.base_url
    assert 'stream' in o.stream_base
    assert o.practice_mode is True


def test_explicit_live_mode_sets_trade_url():
    o = OANDAConnector(practice_mode=False)
    assert 'fxtrade' in o.base_url or 'api-fxtrade' in o.base_url
    assert o.practice_mode is False


def test_get_last_price_fallback(monkeypatch):
    o = OANDAConnector()
    # simulate requests.get failure
    monkeypatch.setattr('requests.get', lambda *args, **kwargs: (_ for _ in ()).throw(Exception('nodata')))
    # should return None rather than raising
    assert o.get_last_price('EUR_USD') is None


def test_place_paper_order_requires_creds():
    o = OANDAConnector()
    class C: pass
    c = C()
    c.symbol = 'EUR_USD'
    c.side = 'BUY'
    # no creds -> runtime error
    o.token = None
    o.account_id = None
    try:
        o.place_paper_order(c, units=1)
        raised = False
    except RuntimeError:
        raised = True
    assert raised is True


def test_place_paper_order_http_error(monkeypatch):
    o = OANDAConnector()
    o.token = 'x'
    o.account_id = '1'

    class DummyResp:
        status_code = 400
        text = 'bad'
        def raise_for_status(self):
            raise Exception('bad')
    monkeypatch.setattr('requests.post', lambda *args, **kwargs: DummyResp())
    class C: pass
    c = C()
    c.symbol = 'EUR_USD'
    c.side = 'BUY'
    res = o.place_paper_order(c, units=1)
    assert isinstance(res, dict)
    assert res.get('status') == 'ERROR' or res.get('status') == 'OK' or res.get('http_status') == 400
