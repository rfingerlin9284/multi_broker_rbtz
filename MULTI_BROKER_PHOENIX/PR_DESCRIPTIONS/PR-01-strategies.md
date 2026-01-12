Title: Enhance strategies with RSI filters and EMA params

Summary:
- Parameterized `ema_scalper` earlier; this PR adds:
  - `HolyGrail`: RSI confirmation filter (configurable via `params['rsi_period']`)
  - `_rsi` helper and unit tests
  - Small doc notes and example usage

Files changed (intent):
- `multi_broker_phoenix/strategies/base.py` (new helper `_rsi`, holy_grail changes)
- `tests/test_holy_grail_rsi.py` (new tests)

Rationale:
- Avoid opening trend-following trades into overbought/oversold extremes.
- Provide easy-to-tune parameterization for strategy testing.
