STRATEGY_FABIO_AAA_FULL INTEGRATION
===================================

Purpose
-------
Record of discovery and injection plan for adding the FABIO_AAA_FULL strategy into RBOTzilla.

Discovery Summary (key files & why)
-----------------------------------
- Strategy registry / loader
  - `multi_broker_phoenix/strategies/base.py` (exports `get_strategy`, `list_strategies`) — where new strategy entries should be discoverable via `get_strategy` and `list_strategies`.
  - `.env` / `.env.example` contains `DEFAULT_STRATEGY` variable — used by `tools/run_headless.py` and engine startup.

- Base Strategy interface
  - `multi_broker_phoenix/strategies/base.py` — base class and helper interfaces. Follow existing convention (generate_candidate / generate_setup pattern).

- Scanner loop / strategy fan-out
  - `tools/run_headless.py` — runs strategies across market universe and calls Hive. Also used by `live_extreme_engine.py` and `live_session_engine.py` which orchestrate runtime selection.
  - `live_extreme_engine.py` / `live_session_engine.py` — call `get_strategy` and run `generate_candidate` for each instrument.

- Order placement path
  - `multi_broker_phoenix/engines/paper_engine.py` — paper order insertion SQL and logging.
  - `multi_broker_phoenix/brokers/coinbase_safe_connector.py` and `multi_broker_phoenix/brokers/ibkr_connector.py` (or coinbase connectors) — live broker integration points.

- OCO enforcement / watchdog
  - `hive_real/hive_schema.py` — canonical Hive schema classes `OCOBracket` and OCO validation rules.
  - `hive_real/orchestrator_v2.py` — `_validate_oco` implements OCO enforcement and raises failures if OCO is missing or invalid.
  - `hive_real/data_gate.py` sets `oco_required` autofill default.

- Hive / consensus modules / seats
  - `hive_real/api_ai_hive.py` — real AI Hive wrapper and usage.
  - `hive_real/orchestrator_v2.py` — orchestrates AI calls and validates outputs (OCO, schema, etc.).
  - `rick_hive/rick_hive_mind.py`, `rick_hive/rick_hive_browser.py` — local Hive seats and browser-driven seats; these are where new Seat classes or seat adapters should be added.

- Bot-Eye renderer & Activity feed
  - `hive_real/ui_renderer.py` — human formatting for Hive outputs; add brief, Bot-Eye style narration here.
  - `rick_hive/rick_hive_browser.py` & `hive_real/hive_web_interface.py` — places to expose strategy narration and diagnostics via Web UI, SSE or logs.

- OCO enforcement tests
  - `hive_real/test_orchestrator_v2.py` — includes tests for OCO validation; add tests for multi-tranche OCO behavior here.

Injection Points (where files will be added/updated)
--------------------------------------------------
1) New strategy module
   - `multi_broker_phoenix/strategies/fabio_aaa_full.py` — implements `FABIO_AAA_FULL` strategy class with `generate_candidate` or `generate_setup` method following base strategy API.

2) Engines & helpers (new modules)
   - `multi_broker_phoenix/strategies/engines/profile_engine.py`
   - `multi_broker_phoenix/strategies/engines/orderflow_engine.py`
   - `multi_broker_phoenix/strategies/engines/liquidity_wall_engine.py`
   - `multi_broker_phoenix/strategies/engines/vwap_stddev_engine.py`
   - `multi_broker_phoenix/strategies/engines/range_bar.py` (RangeBarBuilder)
   - Keep these in `multi_broker_phoenix/strategies/engines/` to be encapsulated and importable by the strategy implementation; provide proxy-mode fallbacks when needed.

3) Universe Hunter
   - `multi_broker_phoenix/strategies/universe_hunter.py` — top-N ranker that computes AAA_SETUP_SCORE and returns top candidates.

4) Hive seats / mapping
   - Extend `rick_hive` or `hive_real` seats: add `SeatProfile`, `SeatOrderFlow`, `SeatLiquidity`, `SeatVWAP`, `SeatRiskOCO` as seat adapters that return PASS/FAIL + score.

5) Trade manager
   - `multi_broker_phoenix/execution/tranche_oco_manager.py` — ensures 3-tranche OCO creation and lifecycle management. Hook into existing broker connectors for order placement (Coinbase, OANDA, IBKR).

6) Diagnostics & CLI
   - `tools/diagnostics_fabio.py` — CLI entry for dry-run, top-5 scan, and Hive votes printing; integrate into `tools/run_headless.py` testing flows.

7) Tests
   - `tests/test_fabio_profile.py`, `tests/test_fabio_orderflow.py`, `tests/test_fabio_liquidity.py`, `tests/test_fabio_integration.py`

Configuration & Defaults
------------------------
- Add defaults to `.env.example` and `.env`:
  - DEFAULT_STRATEGY=FABIO_AAA_FULL (update optional)
  - FABIO_AAA_REQUIRE_FULL_MODE=true (safety)
  - FABIO_AAA_TOP_N=5

- Register strategy with `multi_broker_phoenix/strategies/base.py` list or automatic discovery pattern.

Docs + How to Run Diagnostics
-----------------------------
- Add this file: `DOCS/STRATEGY_FABIO_AAA_FULL_INTEGRATION.md` (this file).
- Diagnostic command (dry-run):
  - `python tools/diagnostics_fabio.py --dry-run --top 5`
  - Or integrate into `tools/run_headless.py` via `--strategy FABIO_AAA_FULL --diagnostics`

Notes / Constraints Observed
---------------------------
- OCO enforcement and Hive gating already exist and will be used - DO NOT override OCO rules.
- Hive uses strict JSON schema (`hive_real/hive_schema.py`) — ensure strategy outputs conform to `HiveOutput` structure and 'oco' fields are valid.
- Use existing Hive seats if possible (rick_hive) or add new deterministic seats that return PASS/FAIL with reasoning strings.
- Keep all changes idempotent and add unit tests and integration dry runs before activating as default.

Next Steps (short)
------------------
1) Create the new strategy stub file with state machine and docstrings (PR to snapshot branch).
2) Implement RangeBarBuilder and engine stubs (with proxy-mode returns).
3) Implement UniverseHunter and basic Hive seat adapters.
4) Add TrancheOCOTradeManager and tests; ensure OCO validation passes.
5) Add diagnostics CLI and integration tests.
6) Register strategy and update `.env.example` defaults (enable by default only after integration tests pass).

Contact / Owner
---------------
- Changes will be added to branch: `latest-near-perfect-autonomous-engine` (snapshot branch for the current work).  
- I'll prepare the PR and tests; please review and I will iterate.
