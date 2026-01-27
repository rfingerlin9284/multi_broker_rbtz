import os
import unittest
from datetime import datetime, timedelta

from multi_broker_phoenix.risk.exit_manager import ExitManager


class DummyConnector:
    def __init__(self):
        self.closed = []

    def close_trade(self, trade_id):
        self.closed.append(trade_id)
        return {"closed": trade_id}


class ExitManagerHardTimeStopTest(unittest.TestCase):
    def setUp(self):
        self._env = dict(os.environ)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)

    def test_hard_time_stop_closes_even_if_soft_disabled(self):
        os.environ["HARD_MAX_TRADE_HOURS"] = "1.0"
        os.environ["EXIT_ENABLE_TIME_STOP"] = "false"

        connector = DummyConnector()

        class EM(ExitManager):
            def _get_positions(self):
                open_time = (datetime.utcnow() - timedelta(hours=2)).isoformat() + "Z"
                return [{
                    "id": "T1",
                    "instrument": "EUR_USD",
                    "side": "long",
                    "averagePrice": "1.1000",
                    "openTime": open_time,
                }]

            def _get_prices(self, pairs):
                return {"EUR_USD": 1.1005}

        em = EM(connector)
        result = em.check_all_positions()

        self.assertEqual(result.get("hard_time_closes"), 1)
        self.assertIn("T1", connector.closed)


if __name__ == "__main__":
    unittest.main()
