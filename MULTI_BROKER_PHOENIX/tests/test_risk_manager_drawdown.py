from multi_broker_phoenix.risk.risk_manager import RiskManager

def test_drawdown_ladder_triage_and_halt(tmp_path):
    cfg = tmp_path / "risk_config.yaml"
    cfg.write_text("""drawdown_ladder:
  - name: NORMAL
    dd_min: 0.0
    dd_max: 0.10
    base_risk_per_trade_pct: 0.01
    max_open_risk_pct: 0.05
    max_trades_per_platform: 3
    allow_new_trades: true
    triage_mode: false
  - name: TRIAGE
    dd_min: 0.10
    dd_max: 0.30
    base_risk_per_trade_pct: 0.005
    max_open_risk_pct: 0.03
    max_trades_per_platform: 2
    allow_new_trades: true
    triage_mode: true
  - name: HALTED
    dd_min: 0.30
    dd_max: 1.0
    base_risk_per_trade_pct: 0.0
    max_open_risk_pct: 0.0
    max_trades_per_platform: 0
    allow_new_trades: false
    triage_mode: true
pnl_brakes:
  daily_loss_limit_pct: -3.0
  weekly_loss_limit_pct: -8.0
default_risk_per_trade_pct: 0.0075
max_total_open_risk_pct: 0.05
""")
    rm = RiskManager(config_path=str(cfg))
    rm.update_equity(1000.0)
    assert rm.state.policy.name == "NORMAL"
    rm.update_equity(850.0)
    assert rm.state.policy.name == "TRIAGE"
    assert rm.state.triage_mode is True
    rm.update_equity(650.0)
    assert rm.state.policy.name == "HALTED"
    assert rm.is_trading_allowed() is False
