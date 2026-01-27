from multi_broker_phoenix.strategies.base import get_strategy
from multi_broker_phoenix.risk.trade_risk_gate import can_open_trade
from multi_broker_phoenix.risk.risk_manager import RiskManager


def _prepare_rm_for_symbol(rm: RiskManager, symbol: str):
    rm.update_equity(100000.0)
    rm.state.regime_by_symbol[symbol] = {'trend': 'BULL', 'vol': 'NORMAL'}


def test_ema_scalper_positive():
    s = get_strategy('ema_scalper')
    assert s is not None
    prices = [1.0 + i * 0.001 for i in range(30)]  # smooth uptrend
    cand = s.generate_candidate({'symbol': 'EURUSD', 'platform': 'OANDA', 'prices': prices})
    assert cand is not None
    rm = RiskManager()
    _prepare_rm_for_symbol(rm, 'EURUSD')
    dec = can_open_trade(cand, account_equity=100000.0, rm=rm)
    assert dec.allowed


def test_institutional_sd_positive():
    s = get_strategy('institutional_sd')
    assert s is not None
    # volatility: sharp moves
    prices = [1.0, 1.02, 0.98, 1.03, 0.95, 1.05, 1.02, 1.06, 1.08]
    cand = s.generate_candidate({'symbol': 'BTC-USD', 'platform': 'COINBASE', 'prices': prices})
    assert cand is not None
    rm = RiskManager()
    _prepare_rm_for_symbol(rm, 'BTC-USD')
    dec = can_open_trade(cand, account_equity=100000.0, rm=rm)
    assert dec.allowed


def test_trap_reversal_positive():
    s = get_strategy('trap_reversal')
    assert s is not None
    prices = [1.0, 1.05, 1.01]  # spike then revert
    cand = s.generate_candidate({'symbol': 'SYM', 'platform': 'OANDA', 'prices': prices})
    assert cand is not None
    rm = RiskManager()
    _prepare_rm_for_symbol(rm, 'SYM')
    dec = can_open_trade(cand, account_equity=100000.0, rm=rm)
    assert dec.allowed


def test_holy_grail_positive():
    s = get_strategy('holy_grail')
    assert s is not None
    prices = list(1.0 + 0.001 * i for i in range(20))
    cand = s.generate_candidate({'symbol': 'SYM2', 'platform': 'OANDA', 'prices': prices})
    assert cand is not None
    rm = RiskManager()
    _prepare_rm_for_symbol(rm, 'SYM2')
    dec = can_open_trade(cand, account_equity=100000.0, rm=rm)
    assert dec.allowed


def test_ema_with_params():
    s = get_strategy('ema_scalper')
    params = {'short_span': 3, 'long_span': 8, 'min_move_pct': 0.0001}
    prices = [1.0 + 0.0005 * i for i in range(30)]
    cand = s.generate_candidate({'symbol': 'EURUSD', 'platform': 'OANDA', 'prices': prices, 'params': params})
    assert cand is not None
    rm = RiskManager()
    _prepare_rm_for_symbol(rm, 'EURUSD')
    dec = can_open_trade(cand, account_equity=100000.0, rm=rm)
    assert dec.allowed
