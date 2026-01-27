Title: Engine fees/slippage model and RiskManager sizing

Summary:
- Add fees & slippage config to `MockEngine` and include `fees` and `fill_price` in orders.
- Add `RiskManager.size_for_trade()` that accounts for fees/slippage and regime multipliers.
- Add tests verifying sizing is reduced by fees/slippage and engine returns fees.

Files changed (intent):
- `multi_broker_phoenix/engines/mock_engine.py`
- `multi_broker_phoenix/risk/risk_manager.py`
- `tests/test_fees_and_sizing.py`

Rationale:
- Realistic testing needs to account for execution costs and their impact on sizing.
- Centralized sizing in RiskManager ensures consistent policy enforcement.
