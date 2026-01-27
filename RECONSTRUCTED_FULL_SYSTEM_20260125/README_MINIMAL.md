# Minimal + Diagnostics (Headless)

This folder contains a trimmed, headless-only build focused on autonomous operation, self‑healing, and monitoring.

## Start (OANDA practice, headless)
- `tools/RUN_OANDA_PAPER.sh`

## Stop
- `tools/STOP_ENGINE.sh`

## Health & Monitoring
- AI router health: `tools/ai_health.sh`
- LLM brain health: `tools/brain_health.sh`
- Exit/position status: `tools/tasks/exit_status.sh`
- OCO audit: `tools/oco_audit.sh`
- Holdtime audit: `tools/holdtime_audit.sh`

## Environment
- Load/validate env: `tools/env_load.sh`, `tools/env_preflight.py`, `tools/env_doctor.sh`
- Required keys: `RUNBOOK_ENV_KEYS.md`

Notes:
- This stays fully headless (CLI only).
- No existing `.env` files were modified.
