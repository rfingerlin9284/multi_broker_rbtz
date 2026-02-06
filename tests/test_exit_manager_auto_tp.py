import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from multi_broker_phoenix.risk.exit_manager import ExitManager
from datetime import datetime, timedelta


def make_position(entry=1.2000, sl=1.1990, instrument='EUR_USD', trade_id='T_AUTO_1'):
    return {
        'id': trade_id,
        'trade_id': trade_id,
        'instrument': instrument,
        'averagePrice': entry,
        'price': entry,
        'openTime': (datetime.utcnow() - timedelta(minutes=5)).isoformat() + 'Z',
        'stop_loss': sl,
        'take_profit': None,
        'side': 'long',
        'strategy': 'ema_scalper',
    }


class FakeConnector:
    def __init__(self):
        self.created_tp = None

    def get_positions(self):
        return [make_position()]

    def get_prices(self, pairs):
        # Return price that gives 12 pips profit (entry 1.2000 -> 1.2012)
        return {pairs[0]: 1.2012}

    def create_take_profit(self, trade_id, price, instrument=None):
        self.created_tp = float(price)
        return {'success': True}


def test_auto_tp_creation():
    conn = FakeConnector()
    em = ExitManager(conn)
    # Ensure auto-tp enabled and trigger below current profit
    em.config['ENABLE_AUTO_TP'] = True
    em.config['AUTO_TP_TRIGGER_PIPS'] = 10.0

    res = em.check_all_positions()
    assert res.get('auto_tp_created', 0) == 1, f"Expected auto TP created, got {res}"
    assert conn.created_tp is not None
    # Expected TP = entry + (entry - sl) * 1.0 = 1.2000 + 0.0010 = 1.2010
    assert abs(conn.created_tp - 1.2010) < 1e-8


if __name__ == '__main__':
    print('Running ExitManager Auto-TP quick test...')
    test_auto_tp_creation()
    print('✅ auto TP test passed')