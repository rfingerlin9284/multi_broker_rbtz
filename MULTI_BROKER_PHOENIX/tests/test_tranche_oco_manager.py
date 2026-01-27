import pytest
from multi_broker_phoenix.engines.tranche_oco_manager import TrancheOCOTradeManager
from multi_broker_phoenix.engines.paper_engine import PaperEngine
from multi_broker_phoenix.strategies.fabio_aaa_full import FabioAAAFull


def test_manager_only_for_fabio_or_tranche():
    pe = PaperEngine(db_path=':memory:')
    mgr = TrancheOCOTradeManager(pe)
    s = FabioAAAFull()
    # create fake candidate-like object without tranche_plan
    class C: pass
    c = C()
    c.strategy_id = 'random'
    assert not mgr.supports_candidate(c)

    # now with tranche_plan attr
    c.tranche_plan = [{'pct_allocation':0.5,'stop_price':90,'take_price':120}]
    assert mgr.supports_candidate(c)

    # Fabio strategy object returns supporting
    cand = s.generate_candidate({'prices':[100+i*0.5 for i in range(30)], 'symbol':'BTC-USD','platform':'COINBASE'})
    assert cand is not None
    assert mgr.supports_candidate(cand)


def test_tranche_execution_flow():
    pe = PaperEngine(db_path=':memory:')
    mgr = TrancheOCOTradeManager(pe)
    s = FabioAAAFull()
    prices = [100.0 + i*0.5 for i in range(30)]
    cand = s.generate_candidate({'prices': prices, 'symbol':'BTC-USD', 'platform':'COINBASE'})
    assert cand is not None
    # Start plan with total USD 10000 -> convert to units
    total_usd = 10000.0
    res = mgr.execute_tranche_plan(cand, total_usd)
    assert res and 'plan_id' in res
    # initial placed order exists in paper DB
    placed = res['placed']
    assert placed and placed['status'] == 'FILLED'
    plan_id = res['plan_id']

    # Simulate market: reach first take price
    first_take = cand.tranche_plan[0]['take_price']
    ev = mgr.simulate_market_tick(first_take)
    # should include a take and a move_stop_to_breakeven events
    assert any(e['event'] == 'take' for e in ev)
    assert any(e['event'] == 'move_stop_to_breakeven' for e in ev)

    # Simulate reaching second take
    second_take = cand.tranche_plan[1]['take_price']
    ev2 = mgr.simulate_market_tick(second_take)
    assert any(e['event'] == 'take' for e in ev2)

    # Simulate reaching third take: completes
    third_take = cand.tranche_plan[2]['take_price']
    ev3 = mgr.simulate_market_tick(third_take)
    assert any(e['event'] == 'take' for e in ev3) or any(e['event']=='completed' for e in ev3)

    # Finally manager should have no active plans
    assert plan_id not in mgr.active_plans
