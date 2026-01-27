from multi_broker_phoenix.engines.paper_engine import PaperEngine
from multi_broker_phoenix.tools.reconcile_ibkr import reconcile


def test_reconcile_basic(tmp_path):
    # Prepare ledger with one matching trade and one extra
    engine = PaperEngine(db_path=str(tmp_path / 'db.sqlite'))
    # Create two trades in ledger
    class C: pass
    c1 = C(); c1.entry_price = 100.0; c1.side = 'BUY'; c1.symbol = 'ABC'; c1.strategy_id = 's1'; c1.stop_loss = 99.0
    engine.place_order(c1, 1.0, execution_type='PLATFORM_PAPER')
    c2 = C(); c2.entry_price = 50.0; c2.side = 'SELL'; c2.symbol = 'XYZ'; c2.strategy_id = 's2'; c2.stop_loss = 51.0
    engine.place_order(c2, 2.0, execution_type='PLATFORM_PAPER')

    ledger = engine.list_trades()

    # Platform has one matching trade (use same id as ledger first entry) and one extra
    platform = []
    # match first ledger trade by id
    platform.append({'id': ledger[0]['id'], 'symbol': 'ABC', 'side': 'BUY', 'size': ledger[0]['size'], 'fill_price': ledger[0]['fill_price']})
    platform.append({'id': 'PLAT-EXTRA-1', 'symbol': 'FOO', 'side': 'BUY', 'size': 1.0, 'fill_price': 10.0})

    rpt = reconcile(platform, ledger)
    assert len(rpt['matched']) == 1
    assert len(rpt['only_platform']) == 1
    assert len(rpt['only_ledger']) == 1
    assert len(rpt['mismatched']) == 0
