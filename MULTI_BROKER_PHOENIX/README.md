# MULTI_BROKER_PHOENIX

A consolidated, safety-first multi-broker trading framework built around the RBOTZILLA Charter.

## Key guarantees
- **Platform breakers** (per-venue kill switches)
- **Execution gate** (global gate integrating risk state)
- **Trade risk gate** (halts/brakes, platform caps, open-risk caps, triage filtering, sizing via stop distance)
- **OCO-first mindset**: brokers/engines are expected to place orders with a stop-loss.

## Repo layout
- `multi_broker_phoenix/foundation/` Charter and governance rules
- `multi_broker_phoenix/risk/` Gates, breakers, and risk state/policy
- `multi_broker_phoenix/brokers/` Broker connectors (OANDA / Coinbase / IBKR)
- `multi_broker_phoenix/engines/` Per-venue engines
- `multi_broker_phoenix/config/` Non-secret config policies and toggles
- `tests/` Pytest suite validating core gate behavior
- `tools/` Versioning/locking helpers + git hooks

## Running tests
```bash
python -m pip install -r requirements.txt
pytest -q
```

## Examples 🔧

- A small example that runs a registered strategy against synthetic price data is available at `examples/run_strategy_example.py`.

Usage:
```bash
. .venv/bin/activate
python examples/run_strategy_example.py
```

- **Paper-replay runner (CSV)**: replay a CSV of market ticks and execute paper trades automatically with safe risk checks and a persistent ledger.

Usage (example):
```bash
. .venv/bin/activate
python examples/run_paper_replay.py path/to/market_ticks.csv --strategy holy_grail --speed 100
```

This will show placed paper orders and write them to `data/paper_ledger.sqlite`. Execution type is explicit and stored with each trade as `execution_type` (one of `SIMULATED`, `PLATFORM_PAPER`, `LIVE_REAL`).

OANDA quick validation (example):
```bash
export OANDA_API_TOKEN=...
export OANDA_ACCOUNT_ID=...
./tools/validate_oanda.sh --info
# to place a practice order (interactive double-confirm):
./tools/validate_oanda.sh --place-order EUR_USD 1 --confirm
```

Config (env):
- `TRADING_MODE` = `SIMULATED` | `PAPER` | `LIVE` (default `PAPER`).
- `PAPER_VIA_PLATFORM` = `1` or `0` (default `0`) — when `1` and the connector supports platform paper, trades will be routed to the platform's paper account.
- `ALLOW_LIVE_REAL` = `1` or `0` (default `0`) — must be set to `1` to enable any real-money live trades.

Defaults are safe: **paper (client-side) trading is enabled by default and real-money live trading is disabled** unless you explicitly opt in via `ALLOW_LIVE_REAL`.

## Versioning + read-only workflow (archive-first)
Edits must follow:
1. Archive current active file into `older_versions/` with `_v###` suffix
2. Promote an edited `.new` file
3. Lock active file as read-only

Use:
```bash
tools/version_and_lock.sh path/to/file.py
```

Enable hooks:
```bash
git config core.hooksPath .githooks
chmod +x .githooks/pre-commit tools/version_and_lock.sh
```
