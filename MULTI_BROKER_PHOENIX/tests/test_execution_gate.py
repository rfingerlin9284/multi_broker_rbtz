from multi_broker_phoenix.risk.execution_gate import can_place_order, set_risk_manager
from multi_broker_phoenix.risk.risk_manager import RiskManager

def test_execution_gate_respects_env_disable(monkeypatch):
    monkeypatch.setenv("EXECUTION_ENABLED", "0")
    assert can_place_order(platform="oanda") is False
    monkeypatch.setenv("EXECUTION_ENABLED", "1")
    assert can_place_order(platform="oanda") is True

def test_execution_gate_requires_strategy_context_in_triage(monkeypatch, tmp_path):
    cfg = tmp_path / "risk_config.yaml"
    cfg.write_text("""drawdown_ladder:
  - name: TRIAGE
    dd_min: 0.0
    dd_max: 1.0
    base_risk_per_trade_pct: 0.005
    max_open_risk_pct: 0.03
    max_trades_per_platform: 2
    allow_new_trades: true
    triage_mode: true
default_risk_per_trade_pct: 0.0075
max_total_open_risk_pct: 0.05
pnl_brakes: { daily_loss_limit_pct: -3.0, weekly_loss_limit_pct: -8.0 }
""")
    rm = RiskManager(config_path=str(cfg))
    rm.update_equity(1000.0)
    set_risk_manager(rm)
    monkeypatch.setenv("EXECUTION_ENABLED", "1")
    assert can_place_order(platform="oanda") is False
    assert can_place_order(strategy_name="ema_scalper", pack_name="pack_b", platform="oanda") is True
