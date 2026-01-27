2026-01-22: Watchdog & HIVE safety/autonomy updates

- watchdog.py
  - Added durable event logging calls for WATCHDOG_FREEZE and WATCHDOG_UNFREEZE via \_log_event
  - Added `unregister_reconnect_callback(cb)` helper
  - Added `invoke_callbacks_async` optional arg to `run_watchdog_once` (default: True). When False, callbacks are invoked synchronously (useful for deterministic tests and immediate recovery handling)

- tests/test_watchdog_reconnect.py
  - Updated test to invoke callbacks synchronously and assert immediate invocation
  - Added test to verify WATCHDOG_UNFREEZE event is emitted (via monkeypatched \_log_event)

- run_headless.py
  - On watchdog reconnect, register a callback to run `tools/confirm_hive.sh` when `TRADING_MODE=LIVE` to keep system fail-closed unless real HIVE seats respond

- tools/confirm_hive.sh
  - Utility added earlier to verify real AI hive seats and write `hive_confirm.json`

- tasks.yaml
  - Added `HIVE_RECONNECT_CONFIRM` acceptance task

Motivation: Improve deterministic, testable watchdog behavior, emit durable audit events for state transitions, and ensure HIVE confirmation runs on recovery to keep live systems fail-closed if AI seats are not healthy.
