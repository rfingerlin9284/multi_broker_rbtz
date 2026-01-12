from pathlib import Path
import tempfile
from multi_broker_phoenix.engines.paper_engine import PaperEngine
from multi_broker_phoenix.risk.trade_risk_gate import TradeCandidate


def test_paper_engine_writes_sqlite(tmp_path: Path):
    db = tmp_path / 'ledger.sqlite'
    engine = PaperEngine(db_path=str(db), fee_pct=0.001, slippage_pct=0.002)
    cand = TradeCandidate('test_strategy', 'SYM', 'OANDA', entry_price=1.2345, stop_loss=1.2300, side='BUY')
    order = engine.place_order(cand, size=1000.0)
    assert 'id' in order
    assert order['fees'] >= 0
    rows = engine.list_trades()
    assert len(rows) == 1
    r = rows[0]
    assert r['id'] == order['id']
    assert r['symbol'] == 'SYM'
    # execution_type defaults to SIMULATED in absence of runtime or explicit param
    assert r.get('execution_type') == 'SIMULATED'
