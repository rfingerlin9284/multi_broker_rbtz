from execution.oanda_practice_client import OandaPracticeClient, PRACTICE_API_URL


class FakeHTTP:
    def __init__(self):
        self.last = None

    def put(self, url, headers=None, timeout=None, **kwargs):
        self.last = ("put", url, kwargs)
        class Resp:
            status_code = 200
            def raise_for_status(self):
                return None
            def json(self):
                return {"ok": True}
        return Resp()

    def post(self, url, headers=None, timeout=None, **kwargs):
        self.last = ("post", url, kwargs)
        class Resp:
            status_code = 200
            def raise_for_status(self):
                return None
            def json(self):
                return {"ok": True}
        return Resp()

    def get(self, url, headers=None, timeout=None, **kwargs):
        self.last = ("get", url, kwargs)
        class Resp:
            status_code = 200
            def raise_for_status(self):
                return None
            def json(self):
                return {"ok": True}
        return Resp()


def test_close_position_uses_put():
    http = FakeHTTP()
    client = OandaPracticeClient(
        token="test_token",
        account_id="test_account",
        base_url=PRACTICE_API_URL,
        http_client=http,
    )
    client.close_position("EUR_USD")
    assert http.last is not None
    method, url, kwargs = http.last
    assert method == "put"
    assert "/positions/EUR_USD/close" in url
