# RBOTZILLA VS Code Agent Charter (Repo-Local)

## Goal
Operate this repo as an autonomous OANDA PRACTICE trading system using the existing start/stop automation and existing code. Keep the system stable, observable, and safe.

## Non-negotiables
1) OANDA PRACTICE only (no live).
2) No Coinbase. No IBKR.
3) No browser seat.
4) No OpenAI usage.
5) Use only the existing repo tooling:
   - tools/rbot_start.sh
   - tools/rbot_stop.sh
   - tools/rbot_status.sh
   - tools/RUN_OANDA_PRACTICE_NOW.sh
   - config/toggles.env
   - .vscode/tasks.json
6) Never print secrets. Use [SET]/[EMPTY] only.
7) Never edit trading logic, strategies, SL/TP rules. If something requires that, stop and report.

## What “autonomous + reliable” means here
- Engine stays running headless.
- OANDA practice connection stays healthy.
- If something breaks (process dead, auth fail, connectivity fail), do:
  1) Alert the user (local log + terminal)
  2) Attempt safe repair (config/env/process/deps only)
  3) Verify integrity (hash verify + compileall)
  4) Restart and confirm recovery
  5) If not recoverable quickly: stop engine and alert clearly (fail closed).

## Narration requirements (simple English)
Every major event should be narrated plainly, like:
- “OANDA is connected and authenticated.”
- “Scanning 5 symbols. Strategies enabled: X, Y, Z.”
- “Signal found on USD_JPY (strength: 0.78). Sending to Hive for a vote.”
- “Hive vote failed (timeout). Trade blocked. Retrying…”
- “Order placed in OANDA practice. Stop loss: __. Take profit: __. Trailing will activate when profit > __.”

## Allowed changes
- tools/*
- config/*
- .vscode/*
- monitoring/watchdog scripts
- logging / narration layer

## Forbidden changes
- Any file that decides entries/exits or SL/TP
- Any strategy rule logic
- Any risk sizing logic

## Minimum verification after any change
- python3 -m compileall
- rbot_status.sh
- tail log for 60 seconds and show key milestones (no secrets)

