# OANDA Execution Path Map

1. **Startup script**: `tools/start_extreme_validated.py`

   - Entry point when launching the validated Extreme Trading Engine.
   - Loads `.env`, configures logging, prints banners, and calls `connect_oanda_practice()`.
   - `connect_oanda_practice()` instantiates `multi_broker_phoenix.brokers.oanda_connector.OANDAConnector` with `practice_mode=True` and calls `get_last_price()` / `verify_credentials()` to confirm connectivity.
   - After connectors are ready, the script builds strategy references (`ExtremeCompoundingEngine`, `ZombieTradeKiller`) and enters `main_trading_loop()`.

2. **Main trading loop**: `tools/start_extreme_validated.py#main_trading_loop`

   - Iterates through the set of brokers (`coinbase`, `oanda`, `ibkr`) and loads signals from strategies (`multi_broker_phoenix.strategies.base.get_strategy`).
   - For OANDA, it checks symbols such as `EUR_USD`, `GBP_USD`, `USD_JPY` and uses the connector’s `get_last_price()` to feed the engines.
   - Strategy evaluations eventually produce trade candidates that are dispatched to the brokers' connectors for `place_order()` calls.

3. **OANDA connector**: `multi_broker_phoenix/brokers/oanda_connector.py`

   - `OANDAConnector.place_paper_order()` and `_post_order()` build the REST payload, enforce trial-based retries, and submit to practice endpoints (`https://api-fxpractice.oanda.com`).
   - Responses include SL/TP details if provided, and the connector returns `success` metadata to the calling engine.
   - The connector exposes helpers such as `verify_credentials()` and `get_last_price()` for health checks.

4. **Strategy & engine execution**
   - The engine uses `ExtremeCompoundingEngine.place_order()` (not shown here) to merge risk sizing, SL/TP rules, and menu-driven bot approvals before calling the connector.
   - The final execution path is: `start_extreme_validated.py` → `ExtremeCompoundingEngine` / strategy modules → `OANDAConnector` → OANDA practice REST API.
