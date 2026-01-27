# Prime Session Recover - Implementation Complete

## What Was Built

A deterministic, idempotent "Prime Session Recover" system that restarts the engine under the correct environment pipeline and verifies proof-of-life before allowing trading.

## Files Created

### 1. [tools/prime_session_recover.sh](tools/prime_session_recover.sh)

**Purpose:** Canonical way to restart engine when env drift is suspected.

**Key Features:**

- ✅ Validates env with `env_doctor` (HARD FAIL if duplicates/missing keys)
- ✅ Shows allowlist-only env snapshots (NEVER prints secrets)
- ✅ Compares running engine env vs deterministic env
- ✅ Stops old engine gracefully (TERM → wait → KILL)
- ✅ Starts engine under `tools/env_load.sh` (inherits correct env)
- ✅ Waits 60s for proof-of-life ticks (`EXIT_MANAGER_TICK`, `PROTECT_LOOP_TICK`)
- ✅ Shows last 140 log lines + critical events
- ✅ Writes JSON report to `ops/state/prime_session_recover.json`
- ✅ Exit code 0 for PASS, 1 for FAIL

**Usage:**

```bash
bash tools/prime_session_recover.sh [mode]
# mode defaults to 'oanda-only'
```

### 2. [tests/test_prime_session_recover_report.py](tests/test_prime_session_recover_report.py)

**Purpose:** Validate JSON report schema.

**Tests:**

- ✅ Required top-level keys exist and have correct types
- ✅ `proof_of_life` sub-structure validated
- ✅ `verdict` is 'PASS' or 'FAIL'
- ✅ Pretty-prints report summary

**Usage:**

```bash
python3 tests/test_prime_session_recover_report.py
```

### 3. [.vscode/tasks.json](.vscode/tasks.json)

**Added Task:**

- Label: `[CRITICAL] PRIME SESSION RECOVER — restart engine under env_load.sh`
- Command: `/home/ing/RICK/MULTI_BROKER_PHOENIX/tools/prime_session_recover.sh`
- Presentation: Dedicated panel, always reveal, auto-focus

**Run via:**

- Command Palette (`Ctrl+Shift+P`)
- Run Task → `[CRITICAL] PRIME SESSION RECOVER`

### 4. [RUNBOOK_ENV_KEYS.md](RUNBOOK_ENV_KEYS.md)

**Updated Sections:**

- Added **Scenario 4**: "Engine is using STALE environment / env drift still happening"
- Added **Quick Reference: Prime Session Recover** at end
- Updated **Summary** table with new command

---

## The 3-Layer Truth Model (Now Documented)

### Layer 1: Files on Disk

- `.env`, `config/toggles.env`, `ops/secrets.env`
- ✅ Fixed by removing duplicates
- ✅ Validated by `env_doctor`

### Layer 2: Shell Environment

- When you run `source tools/env_load.sh`
- ✅ Fixed by deterministic loading pipeline
- ✅ All scripts patched to source `env_load.sh`

### Layer 3: Running Process Environment

- What `watchdog.py` sees via `os.getenv()`
- Reads `/proc/<PID>/environ` (childhood trauma snapshot)
- ❌ **STALE until prime_session_recover.sh restarts engine**

---

## Proof-of-Life Requirements

The script will NOT report `PASS` until BOTH ticks are detected in logs:

1. **EXIT_MANAGER_TICK** → Positions can be closed (no zombie holds)
2. **PROTECT_LOOP_TICK** → Max hold hours enforced (6-8hr safety net)

**Why this matters:**

- If exits aren't running, you can end up with zombie positions
- If protect loop isn't running, max hold enforcement fails
- Both MUST be alive before allowing new entries

---

---

## What "Good" Looks Like

### Terminal Output

```
=========================================
 RBOTzilla Prime Session Recover
=========================================

✅ env_doctor PASS
✅ Sourced tools/env_load.sh
✅ Started engine pid=123456
✅ Both ticks detected!
  EXIT_MANAGER_TICK: ✅ FOUND
  PROTECT_LOOP_TICK: ✅ FOUND

✅ VERDICT: PASS
   - Engine restarted under deterministic env
   - Exit manager is alive
   - Protect loop is alive
```

### JSON Report

```json
{
  "timestamp": "2026-01-24T04:30:00-05:00",
  "repo": "/home/ing/RICK/MULTI_BROKER_PHOENIX",
  "mode": "oanda-only",
  "pid": 123456,
  "old_pid": "3108717",
  "log_file": "/home/ing/RICK/MULTI_BROKER_PHOENIX/logs/engine_headless.log",
  "proof_of_life": {
    "EXIT_MANAGER_TICK": true,
    "PROTECT_LOOP_TICK": true
  },
  "verdict": "PASS"
}
```

---

## Why This Stops "Env Drift" Permanently

### Before (Broken)

1. User fixes `.env` on disk
2. Runs `env_doctor` → ✅ OK
3. Engine still sees old env (living in `/proc/<PID>/environ` snapshot)
4. User confused: "I fixed it but it's still wrong!"
5. Repeat ×∞

### After (Fixed)

1. User runs `prime_session_recover.sh`
2. Script validates env files (HARD FAIL if bad)
3. Script restarts engine **under env_load.sh**
4. Engine inherits correct, deterministic env at startup
5. Script verifies exits/protect loops are alive
6. User gets machine-readable proof before proceeding

**No more split-reality loops.**

---

## Integration with Existing Tools

### Bootstrap Secrets (Key Recovery)

```bash
bash tools/bootstrap_secrets.sh  # Create/restore secrets
bash tools/env_doctor.sh         # Verify no duplicates/drift
bash tools/prime_session_recover.sh  # Restart under clean env
```

### AI Health (Quorum Verification)

```bash
bash tools/tasks/ai_status.sh    # Check brain seats
# Should show: verdict=PASS, ollama healthy=true
```

---

## Systemd Service Upgrade (Next Level)

For production: run engine as systemd service instead of manual nohup.

**Benefits:**

- ✅ Auto-restart on crash
- ✅ Logs to journald (auto-rotate)
- ✅ Explicit env loading via systemd unit
- ✅ No more babysitting with screen/tmux

**Example unit snippet:**

```ini
[Unit]
Description=RBOTzilla Trading Engine
After=network.target

[Service]
Type=simple
User=ing
WorkingDirectory=/home/ing/RICK/MULTI_BROKER_PHOENIX
EnvironmentFile=/home/ing/RICK/MULTI_BROKER_PHOENIX/ops/secrets.env
ExecStartPre=/bin/bash /home/ing/RICK/MULTI_BROKER_PHOENIX/tools/env_load.sh
ExecStart=/home/ing/RICK/MULTI_BROKER_PHOENIX/.venv/bin/python3 -u tools/run_headless.py --mode oanda-only
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
```

---

## Verification Commands

### Before Running Recovery

```bash
# 1. Check env files are clean
bash tools/env_doctor.sh

# 2. Check AI health
bash tools/tasks/ai_status.sh
```

### Run Recovery

```bash
bash tools/prime_session_recover.sh
```

### After Recovery

```bash
# 1. Validate JSON report schema
python3 tests/test_prime_session_recover_report.py

# 2. Check report verdict
cat ops/state/prime_session_recover.json | grep verdict

# 3. View last log entries
tail -100 logs/engine_headless.log
```

---

## Summary

| What                  | Status | Location                                     |
| --------------------- | ------ | -------------------------------------------- |
| Recovery Script       | ✅     | `tools/prime_session_recover.sh`             |
| VS Code Task          | ✅     | `.vscode/tasks.json`                         |
| Report Schema Test    | ✅     | `tests/test_prime_session_recover_report.py` |
| Runbook Documentation | ✅     | `RUNBOOK_ENV_KEYS.md`                        |
| Proof-of-Life         | ✅     | Requires EXIT + PROTECT ticks                |
| Secret Safety         | ✅     | NEVER prints secret values                   |
| Exit Codes            | ✅     | 0=PASS, 1=FAIL                               |

**Status:** Production Ready ✅

**Next Action for User:**

```bash
cd /home/ing/RICK/MULTI_BROKER_PHOENIX
bash tools/prime_session_recover.sh
```

Then wait for `✅ VERDICT: PASS` before proceeding.
