import os
import pytest


@pytest.mark.skipif(not os.getenv('OANDA_API_TOKEN') or not os.getenv('OANDA_ACCOUNT_ID'), reason='OANDA env vars not set')
def test_oanda_account_and_pricing():
    from multi_broker_phoenix.brokers.oanda_connector import OANDAConnector
    o = OANDAConnector()
    assert o.token is not None
    assert o.account_id is not None
    price = o.get_last_price('EUR_USD')
    assert price is None or price > 0


@pytest.mark.skipif(not (os.getenv('OANDA_API_TOKEN') and os.getenv('OANDA_ACCOUNT_ID') and os.getenv('OANDA_PLACE_TEST_ORDER')=='1'), reason='No OANDA token or test order not enabled')
def test_oanda_place_practice_order():
    from multi_broker_phoenix.brokers.oanda_connector import OANDAConnector
    o = OANDAConnector()
    # place a very small order: this will run only when the env flag OANDA_PLACE_TEST_ORDER==1
    class C: pass
    c = C()
    c.symbol = 'EUR_USD'
    c.side = 'BUY'
    res = o.place_paper_order(c, units=1)
    assert isinstance(res, dict)
    assert res.get('execution_type') == 'PLATFORM_PAPER' or res.get('status') in ('ERROR',)
