from multi_broker_phoenix.risk.risk_manager import RiskManager
from multi_broker_phoenix.risk.trade_risk_gate import TradeCandidate, can_open_trade

def test_trade_risk_gate_requires_regime():
    rm = RiskManager()
    rm.update_equity(1000.0)
    cand = TradeCandidate(strategy_id="ema_scalper", symbol="EUR_USD", platform="OANDA", entry_price=1.1000, stop_loss=1.0950, side="LONG")
    dec = can_open_trade(cand, account_equity=1000.0, rm=rm)
    assert dec.allowed is False
    assert dec.reason == "missing_regime"

def test_trade_risk_gate_sizes_by_stop_distance():
    rm = RiskManager()
    rm.update_equity(1000.0)
    rm.state.regime_by_symbol["EUR_USD"] = {"trend":"BULL","vol":"NORMAL"}
    cand = TradeCandidate(strategy_id="ema_scalper", symbol="EUR_USD", platform="OANDA", entry_price=1.1000, stop_loss=1.0950, side="LONG")
    dec = can_open_trade(cand, account_equity=1000.0, rm=rm)
    assert dec.allowed is True
    assert dec.size > 0
    assert 1000 < dec.size < 3000
