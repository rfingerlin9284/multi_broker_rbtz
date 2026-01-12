# RUN OANDA PRACTICE (No Simulation Path)

This guide focuses on the **practice-only execution path** that bypasses any mock or dry-run wiring and drills straight into real OANDA practice orders with enforced OCO brackets.

## Required Environment Variables

| Variable                           | Description                                                                               |
| ---------------------------------- | ----------------------------------------------------------------------------------------- |
| `OANDA_API_TOKEN` or `OANDA_TOKEN` | Bearer token for your OANDA practice account (must belong to `api-fxpractice.oanda.com`). |
| `OANDA_ACCOUNT_ID`                 | Practice account ID.                                                                      |
| `OANDA_ENV` (optional)             | Use `practice` to remind operators, but the client prefers `api-fxpractice`.              |
| `OANDA_API_URL` (optional)         | Override default, but it **must** start with `https://api-fxpractice.oanda.com`.          |
| `OANDA_STREAM_URL` (optional)      | Override streaming endpoint (defaults to the practice stream).                            |

Point the above keys into your `.env` or export them directly before executing anything in this workflow.

## Supporting Scripts

- **OANDA**
  - Connectivity check: `python3 scripts/oanda_practice_smoke_test.py` verifies account connectivity and prints the account summary in raw JSON.
  - Tiny trade test: `python3 scripts/oanda_practice_tiny_trade_test.py` places a single-unit market order with a strict SL/TP bracket, then logs the response plus `/openTrades`.
- **IBKR**
  - Connectivity check: `python3 scripts/ibkr_practice_smoke_test.py` — attempts to connect to TWS/IB Gateway (paper port 4002) and returns an account summary if available; falls back to simulated connector if not.
  - Tiny trade test: `python3 scripts/ibkr_practice_tiny_trade_test.py` — places a tiny paper order via TWS/IB Gateway when available; otherwise runs a simulated order if the simple connector is present and seeded with a price.
- **Coinbase**
  - Nano trade test: `python3 scripts/coinbase_nano_trade_test.py` — uses Coinbase public API for live market prices and places a simulated nano order by default. To opt-in to a live tiny order, set `COINBASE_ALLOW_REAL=true` and ensure API credentials are configured (use carefully).

> Both scripts rely on `execution/oanda_practice_client.py`, which hardcodes the practice API host, refuses live hosts, and enforces a stop-loss + take-profit on every order.

## Full Engine Run (practice-only)

Assuming you have validated OANDA practice credentials, start the validated engine with:

```
bash tools/start_extreme_validated.py
```

The script:

1. Loads `.env`
2. Connects to practice OANDA via `multi_broker_phoenix.brokers.oanda_connector.OANDAConnector(practice_mode=True)`
3. Runs `ExtremeCompoundingEngine`/`ZombieTradeKiller` logic before delegating to the connector for real practice orders.

## What to Watch For

- The new practice client logs: `OANDA Practice client initialized | account=... | base_url=https://api-fxpractice.oanda.com` on startup.
- Tiny trade test prints the order payload and the open trade snapshot to confirm the insert.
- If any command fails, double-check that `OANDA_API_TOKEN`, `OANDA_ACCOUNT_ID`, and `OANDA_API_URL` (if set) reference the practice account and that your IP is whitelisted in OANDA practice if required.
