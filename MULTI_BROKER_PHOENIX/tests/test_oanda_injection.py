from multi_broker_phoenix.brokers.oanda_connector import OANDAConnector


class FakeResp:
    def __init__(self, json_data=None, status_code=200, text=''):
        self._json = json_data or {}
        self.status_code = status_code
        self.text = text

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception('http error')


class FakeHTTP:
    def __init__(self):
        self.get_calls = []
        self.post_calls = []

    def get(self, url, **kwargs):
        self.get_calls.append((url, kwargs))
        # return a price response
        return FakeResp({'prices': [{'closeoutBid': '1.10', 'closeoutAsk': '1.12'}]}, status_code=200)

    def post(self, url, **kwargs):
        self.post_calls.append((url, kwargs))
        # return an order create response
        return FakeResp({'orderCreateTransaction': {'id': 'abc123'}}, status_code=201)


def test_oanda_uses_injected_http_client():
    fake = FakeHTTP()
    o = OANDAConnector(http_client=fake)
    p = o.get_last_price('EUR_USD')
    assert p == 1.11
    assert len(fake.get_calls) == 1
    class C: pass
    c = C()
    c.symbol = 'EUR_USD'
    c.side = 'BUY'
    # set dummy creds so the method proceeds to HTTP post
    o.token = 'DUMMY'
    o.account_id = 'DUMMY'
    res = o.place_paper_order(c, units=1)
    assert res.get('id') == 'abc123'
    assert len(fake.post_calls) == 1


def test_oanda_default_client_is_requests_when_none():
    # When no http_client passed, .http should be the requests module
    o = OANDAConnector()
    import requests
    assert o.http is requests
