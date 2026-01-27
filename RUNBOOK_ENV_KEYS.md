# RBOTzilla Environment Key Management Runbook

## Problem This Solves

**Env Drift:** The bot "loses keys" or "acts different day-to-day" because different launch paths load different env files inconsistently.

**Root Cause:** Multiple env files (.env, toggles.env, shell exports, systemd env) create silent conflicts where duplicates override each other unpredictably.

**Solution:** Single deterministic env loading pipeline with separation of secrets and toggles.

---

## Architecture

### Three-Tier Environment Loading

```
1. config/toggles.env      (committed, non-secret, enables/disables features)
   ↓
2. ops/secrets.env         (gitignored, contains API keys/tokens)
   ↓ (overrides)
3. Runtime                 (loaded by tools/env_load.sh in deterministic order)
```

**Rule:** Secrets OVERRIDE toggles. Later values win.

---

## Files

| File                              | Purpose                             | Git Status    | Permissions |
| --------------------------------- | ----------------------------------- | ------------- | ----------- |
| `config/toggles.env`              | Feature flags, non-secret config    | ✅ Committed  | 600         |
| `config/secrets.env.example`      | Template for secrets (NO real keys) | ✅ Committed  | 644         |
| `ops/secrets.env`                 | **YOUR ACTUAL KEYS**                | ❌ Gitignored | 600         |
| `~/.config/rbotzilla/secrets.env` | Alternative location (optional)     | ❌ Gitignored | 600         |
| `tools/env_load.sh`               | Single source of truth loader       | ✅ Committed  | 755         |
| `tools/env_doctor.sh`             | Drift detector                      | ✅ Committed  | 755         |
| `tools/bootstrap_secrets.sh`      | One-command key recovery            | ✅ Committed  | 755         |

---

## How to Bootstrap (First Time or After Key Loss)

### Scenario 1: Engine Is Running (Recover from Live Process)

```bash
cd /home/ing/RICK/MULTI_BROKER_PHOENIX
bash tools/bootstrap_secrets.sh
```

**What it does:**

1. Finds running engine PID
2. Reads `/proc/<PID>/environ`
3. Extracts whitelisted keys (OANDA*\*, XAI*\*, etc.)
4. Writes to `ops/secrets.env` (chmod 600)
5. **NEVER prints secret values**
6. Runs `env_doctor` to verify

**Output (presence-only):**

```
✅ Created ops/secrets.env
   Source: running_engine_pid_3108717
   Keys extracted: 6

PRESENCE CHECK (no values shown):
  OANDA_API_TOKEN = [SET]
  OANDA_ACCOUNT_ID = [SET]
  XAI_API_KEY = [SET]
  ...
```

### Scenario 2: Engine Not Running (Migrate from .env)

```bash
bash tools/bootstrap_secrets.sh
```

**What it does:**

1. Checks if `.env` exists
2. Copies whitelisted keys to `ops/secrets.env`
3. **NEVER prints secret values**

### Scenario 3: No Keys Anywhere (Fresh Start)

```bash
bash tools/bootstrap_secrets.sh
```

**What it does:**

1. Creates `ops/secrets.env` with empty placeholders
2. Prints loud warning: **"YOU MUST MANUALLY FILL IN YOUR KEYS"**

Then edit manually:

```bash
nano ops/secrets.env
# Fill in your actual keys
chmod 600 ops/secrets.env
```

---

## How to Verify Environment

### Check for Drift / Duplicates / Missing Keys

```bash
bash tools/env_doctor.sh
```

**Exit codes:**

- `0` = OK (no issues)
- `2` = Duplicates found
- `3` = Missing required keys
- `4` = Both duplicates + missing keys

**Output Example (healthy):**

```
=========================================
 RBOTzilla Environment Doctor
=========================================

FOUND:
  toggles  = /home/ing/RICK/MULTI_BROKER_PHOENIX/config/toggles.env
  secrets  = /home/ing/RICK/MULTI_BROKER_PHOENIX/ops/secrets.env

HASHES:
  toggles  = 9ac43cbaeb5f1b2d5e81d41cfd33d53678c05409f66aa0e5c77189b6d575c79b
  secrets  = a1b2c3d4e5f67890abcdef1234567890abcdef1234567890abcdef1234567890

REQUIRED KEYS (presence only):
  OANDA_API_TOKEN = [SET]
  OANDA_ACCOUNT_ID = [SET]
  OLLAMA_URL = [SET]

=========================================
✅ STATUS: OK
=========================================
```

**Output Example (duplicates detected):**

```
DUPLICATES DETECTED ⚠️
  The following keys are defined in BOTH toggles and secrets:
    - XAI_API_KEY
    - DEEPSEEK_API_KEY
  (Secrets will override toggles, but duplicates cause confusion.)

⚠️  STATUS: DUPLICATES FOUND
```

**Fix:** Remove duplicates from `config/toggles.env` (secrets should be in `ops/secrets.env` only).

---

## How Runtime Scripts Load Environment

Every script sources `tools/env_load.sh` at the top:

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Load environment deterministically
source "${ROOT}/tools/env_load.sh"

# ... rest of script
```

**Scripts patched:**

- `tools/rbot_status.sh`
- `tools/rbot_start.sh`
- `tools/confirm_hive_status.sh`
- `tools/task_runner.sh`
- `tools/tasks/ai_status.sh`
- `tools/tasks/exit_status.sh`
- `tools/tasks/ai_repair.sh`

---

## Secrets Location Priority

`tools/env_load.sh` searches in this order:

1. `ops/secrets.env` (repo-local, preferred)
2. `~/.config/rbotzilla/secrets.env` (user-level)
3. `/etc/rbotzilla/secrets.env` (system-level)

**First found wins.** If none exist, toggles-only is used (secrets will be missing).

---

## State Files (Observability)

### ops/state/env_state.json

Written by `tools/env_load.sh` every time it runs:

```json
{
  "last_loaded_utc": "2026-01-23T18:30:45Z",
  "toggles_path": "/home/ing/RICK/MULTI_BROKER_PHOENIX/config/toggles.env",
  "secrets_path_used": "/home/ing/RICK/MULTI_BROKER_PHOENIX/ops/secrets.env",
  "sha256_toggles": "9ac43cbaeb5f1b2d5e81d41cfd33d53678c05409f66aa0e5c77189b6d575c79b",
  "sha256_secrets": "a1b2c3d4...",
  "required_keys_presence": {
    "OANDA_API_TOKEN": true,
    "OANDA_ACCOUNT_ID": true,
    "XAI_API_KEY": false,
    ...
  },
  "duplicates_detected": []
}
```

**Use case:** Debug "which file was actually loaded?" without printing secrets.

### ops/state/env_doctor_last.json

Written by `tools/env_doctor.sh`:

```json
{
  "timestamp_utc": "2026-01-23T18:31:00Z",
  "duplicates": ["XAI_API_KEY"],
  "missing_keys": [],
  "exit_code": 2
}
```

---

## Common Scenarios

### 1. "Keys worked yesterday, missing today"

**Cause:** Different script launched bot, loaded different env file.

**Fix:**

```bash
bash tools/bootstrap_secrets.sh  # Recover from running PID or .env
bash tools/env_doctor.sh         # Verify
```

### 2. "Duplicate key warnings"

**Cause:** Same key defined in both `config/toggles.env` and `ops/secrets.env`.

**Fix:**

1. Remove from `config/toggles.env` (secrets belong in `ops/secrets.env`)
2. Run `bash tools/env_doctor.sh` to confirm

### 3. "I rotated API keys, bot still uses old ones"

**Cause:** Keys cached in running engine process.

**Fix:**

```bash
# Update ops/secrets.env with new keys
nano ops/secrets.env

# Restart engine (forces reload)
bash tools/rbot_stop.sh
bash tools/rbot_start.sh
```

### 4. "Engine is using STALE environment / env drift still happening"

**Symptom:** You've fixed env files on disk (env_doctor says OK), but the running engine still sees old/wrong values.

**Root Cause:** The running engine process inherited env at startup (before your fixes). It's living in a "childhood trauma" snapshot.

**The 3-Layer Truth Model:**

1. **Layer 1 (files on disk):** `.env`, `config/toggles.env`, `ops/secrets.env` ✅ You fixed this
2. **Layer 2 (your shell):** When you run `source tools/env_load.sh` ✅ Also fixed
3. **Layer 3 (running engine process):** `os.getenv()` reads `/proc/<PID>/environ` ❌ **STALE**

**Canonical Fix (Restart Under Deterministic Env):**

```bash
bash tools/prime_session_recover.sh
```

**What it does:**

1. Validates env files with `env_doctor` (HARD FAIL if bad)
2. Sources `tools/env_load.sh` (deterministic pipeline)
3. Shows allowlist-only env snapshot (NO secret values printed)
4. Stops old engine (TERM → wait → KILL if needed)
5. Starts engine **under env_load.sh** (inherits correct env)
6. Waits up to 60s for proof-of-life ticks:
   - `EXIT_MANAGER_TICK` (positions can be closed)
   - `PROTECT_LOOP_TICK` (max hold enforced)
7. Shows last 140 log lines
8. Writes machine-readable report: `ops/state/prime_session_recover.json`

**Verdict:**

- ✅ **PASS:** Both ticks detected
- ❌ **FAIL:** Missing ticks → fix exits/protect loop first

**What "good" looks like:**

```
✅ VERDICT: PASS
   - Engine restarted under deterministic env
   - Exit manager is alive
   - Protect loop is alive
```

**VS Code Task:**

- Open Command Palette (`Ctrl+Shift+P`)
- Run Task → `[CRITICAL] PRIME SESSION RECOVER`

### 5. "Lost ops/secrets.env, engine still running"

**Recovery:**

```bash
bash tools/bootstrap_secrets.sh
# Extracts from /proc/<PID>/environ automatically
```

---

## Testing

### Manual Test: Duplicate Detection

```bash
# Add duplicate key to toggles
echo "OANDA_API_TOKEN=dummy" >> config/toggles.env

# Run doctor
bash tools/env_doctor.sh
# Expect: exit 2, duplicate warning

# Remove duplicate
sed -i '/OANDA_API_TOKEN/d' config/toggles.env
```

### Automated Tests

```bash
python3 -m pytest tests/test_env_loader.py -v
```

---

## Security

**NEVER:**

- Print secret values in logs, stdout, debug output
- Commit `ops/secrets.env` or `.env` with real keys
- Share screenshots with keys visible

**ALWAYS:**

- Use `[SET]`/`[EMPTY]` for presence-only reporting
- chmod 600 secrets files
- Use file hashes instead of contents for debugging

---

## Troubleshooting

### "env_load.sh: command not found"

**Cause:** Script not executable or wrong path.

**Fix:**

```bash
chmod +x /home/ing/RICK/MULTI_BROKER_PHOENIX/tools/env_load.sh
```

### "Permission denied: ops/secrets.env"

**Cause:** Permissions too restrictive.

**Fix:**

```bash
chmod 600 /home/ing/RICK/MULTI_BROKER_PHOENIX/ops/secrets.env
```

### "env_doctor shows MISSING_KEYS but keys are set"

**Cause:** Keys in wrong file (e.g., in .env but not ops/secrets.env).

**Fix:**

```bash
bash tools/bootstrap_secrets.sh  # Migrate to correct location
```

---

## Migration from Old System

If you previously relied on `.env` alone:

1. Run `bash tools/bootstrap_secrets.sh` to create `ops/secrets.env`
2. (Optional) Remove secrets from `.env` to prevent confusion
3. Verify with `bash tools/env_doctor.sh`
4. Restart bot to use new loading pipeline

**No service interruption required if engine is running during migration.**

---

## Summary

| Command                               | Purpose                                      |
| ------------------------------------- | -------------------------------------------- |
| `bash tools/bootstrap_secrets.sh`     | ONE COMMAND to restore/create secrets        |
| `bash tools/env_doctor.sh`            | Verify env health (duplicates, missing keys) |
| `bash tools/prime_session_recover.sh` | Restart engine under deterministic env       |
| `cat ops/state/env_state.json`        | See what was loaded (no secret values)       |
| `nano ops/secrets.env`                | Manually edit keys (chmod 600)               |

**Remember:** Secrets live in `ops/secrets.env`, toggles in `config/toggles.env`. Never mix them.

---

## Quick Reference: Prime Session Recover

**When to use:** Engine is using stale env, env_doctor says OK but behavior is wrong, after rotating keys.

**One-liner:**

```bash
bash tools/prime_session_recover.sh
```

**What you'll see:**

```
========================================
 RBOTzilla Prime Session Recover
========================================

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

**Report location:**

```bash
cat ops/state/prime_session_recover.json
```

**Validate report schema:**

```bash
python3 tests/test_prime_session_recover_report.py
```

**VS Code Task:**

Command Palette → Run Task → `[CRITICAL] PRIME SESSION RECOVER`
