# Autonomous System Runner

This entry point ties together the entire RBOTzilla ecosystem: the autonomous hive agent, real broker connectors (Coinbase, OANDA, IBKR), and the live strategy/quality stack. Running this module launches a single loop that feeds live (or practice) prices into the AI hunter, gates every trade through the quality engine, and executes orders via broker adapters that honor the safety limits you already configured.

## Key facts

- Implements the `startup_autonomous_hive_agent()` bootstrapping flow.
- Exchanges are represented via `BrokerExecutionAdapter`, so `QualityFirstTradingEngine` can always call `place_order(...)`.
- A `MarketDataCollector` keeps every strategy honest by delivering fresh snapshots and price history from each connector.
- Logging mirrors the familiar console output from the hive documentation while also exposing iteration-level results.

## How to run

1. Populate the usual secrets in `.env` (`OPENAI_API_KEY`, broker credentials, etc.). The existing `.env` file already includes placeholders for RBOTzilla-specific keys such as `COINBASE_API_KEY`, `OANDA_API_TOKEN`, and `IBKR_*`.
2. Adjust the symbol feed if you want to cover more markets via `FEED_SYMBOLS` (comma-separated, e.g. `BTC-USD,ETH-USD,EUR_USD`).
3. Tune the polling cadence with `HEADLESS_POLL_SECONDS` (default: 60 seconds).
4. Execute the runner with:

   ```bash
   python -m multi_broker_phoenix.autonomous_system_runner
   ```

   The module will log each iteration's market snapshot and strategies executed. The loop runs until you hit `Ctrl+C` or an unrecoverable error occurs.

## Notes

- The `AutonomousSystemRunner` honors your `AUTONOMOUS_DEFAULT_*_USD` overrides so the quality engine and adapters share the same notional sizing targets.
- If a connector (Coinbase, OANDA, IBKR) fails to initialize because of missing credentials, the runner still starts but logs the missing adapter and skips that broker.
- Missing AI API keys simply cause the AI setup hunter to return no setups, which is still safe—you'll see repeated "no setup" logs until the keys are restored.
- For real-money testing, make sure `TRADING_MODE=LIVE` with the required confirm flags before turning off paper mode per broker.
