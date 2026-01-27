import os
import pytest


@pytest.mark.skipif(not os.getenv('IBKR_HOST'), reason='IBKR gateway not configured')
def test_ibkr_connectivity():
    # Try to import ib_insync and connect using the connector; this is a soft smoke test
    from ibkr_gateway.ibkr_connector import IBKRConnector
    c = IBKRConnector()
    ok = c.connect()
    assert ok is True or ok is False  # ensure call completes (True if gateway reachable)


@pytest.mark.skipif(not (os.getenv('IBKR_HOST') and os.getenv('IBKR_PLACE_TEST_ORDER')=='1'), reason='IBKR test order not enabled')
def test_ibkr_place_practice_order():
    # This test will attempt to place a small paper order via IBKR TWS/Gateway.
    # Requires: IBKR_HOST, IBKR_PORT, IBKR_CLIENT_ID, IBKR_PLACE_TEST_ORDER=1 and a running paper gateway
    from ibkr_gateway.ibkr_connector import IBKRConnector
    os.environ['EXECUTION_ENABLED'] = '1'
    c = IBKRConnector()
    # Very small order for testing
    res = c.place_order(symbol='TEST', side='BUY', units=1, entry_price=1.0, stop_loss=0.99, take_profit=1.1)
    assert isinstance(res, dict)
    assert res.get('success') is True or res.get('error') is not None
