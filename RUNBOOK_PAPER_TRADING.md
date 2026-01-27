# How to resume PAPER trading safely and verify trailing/time-stop

## 1) Verify AI seats (includes Ollama)

- Run the status script:
  - `tools/confirm_hive_status.sh`
- Expect Ollama to be **OK** (model present). If missing, pull the model via Ollama:
  - `ollama pull llama3.1:8b`

## 2) Start headless engine (PAPER only)

- Ensure `TRADING_MODE=PAPER` in `.env`.
- Start headless runner as usual.

## 3) Verify ExitManager tick + state

- Confirm `EXIT_MANAGER_TICK` appears in logs:
  - `grep -Rna "EXIT_MANAGER_TICK" logs/engine_headless.log | tail -20`
- Confirm state file updates:
  - `cat ops/state/exit_manager_state.json`

## 4) Verify trailing updates

- When a trade’s profit crosses the threshold, look for:
  - `TRAILING_UPDATE` in `ops/state/exit_manager_events.jsonl`

## 5) Verify time-stop behavior

- For any trade older than 8 hours (or configured), verify:
  - `TIME_STOP_CLOSE` in logs and events

## 6) Verify OCO protection and freeze logic

- Check `ops/state/oco_health.json` for missing or repaired protections.
- If OCO fails post-fill, system should flatten the trade and freeze new entries.
