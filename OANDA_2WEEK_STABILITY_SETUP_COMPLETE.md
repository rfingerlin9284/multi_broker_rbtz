# OANDA 2-Week Stability Setup — COMPLETE ✅

**Date:** 2026-01-25  
**Objective:** OANDA paper trading runs reliably for 2 weeks with minimal intervention

---

## ✅ What Was Done

### 1. Fixed .env Warning

**Problem:** Runner showed warning `/home/ing/RICK/.env` (wrong path)  
**Root Cause:** REPO_ROOT used `parents[3]` instead of `parents[2]`  
**Fix:** [oanda_runner.py:26](multi_broker_phoenix/runners/oanda_runner.py#L26)

```python
# Before:
REPO_ROOT = Path(__file__).resolve().parents[3]  # Too high

# After:
REPO_ROOT = Path(__file__).resolve().parents[2]  # Correct
```

### 2. Created Stability Lock Mechanism

**Purpose:** Prevent accidental code changes during 2-week run

**Files Created:**

- [tools/stability_lock.sh](tools/stability_lock.sh) — Makes critical modules read-only
- [tools/stability_unlock.sh](tools/stability_unlock.sh) — Restores write permissions (emergency only)

**What Gets Locked:**

- `multi_broker_phoenix/core/` (supervisor, gates, orchestrator, interfaces)
- `multi_broker_phoenix/risk/` (exit_manager, pnl_kill_switch, protect_loop)
- `multi_broker_phoenix/monitor/` (monitoring components)
- `multi_broker_phoenix/adapters/` (OANDA/Coinbase/IBKR connectors)
- `multi_broker_phoenix/runners/` (supervised broker engines)
- `tools/start_broker.sh`, `tools/start_full_system.sh`, etc.

**What Stays Writable:**

- `config/` (toggles, environment settings)
- `ops/state/` (heartbeats, state files)
- `logs/` (log outputs)

**Usage:**

```bash
# Lock code for 2-week stability run
./tools/stability_lock.sh

# Emergency unlock (only if critical bug found)
./tools/stability_unlock.sh
```

### 3. Created Operational Runbook

**File:** [OPS_OANDA_2WEEK_RUNBOOK.md](OPS_OANDA_2WEEK_RUNBOOK.md)

**Contents:**

- **Initial Setup**: Verify env, test import, start system, enable autonomy
- **Daily Checklist**: 2-minute status check, log review
- **Troubleshooting**: PAUSED states, gate failures, heartbeat issues, crashes
- **Maintenance Windows**: OANDA forex rollover (21:00-22:00 UTC), weekend closures
- **Emergency Recovery**: Stop/start commands
- **After 2 Weeks**: Data collection, analysis, unlock stability lock

**Quick Start:**

```bash
# Setup (one-time)
cd /home/ing/RICK/MULTI_BROKER_PHOENIX
python3 -c "from multi_broker_phoenix.runners import oanda_runner; print('✅ OK')"
./tools/start_full_system.sh
./tools/status_full_system.sh
# Enable AUTO_ARM (see runbook)
./tools/stability_lock.sh

# Daily check (2 min)
./tools/status_full_system.sh
```

### 4. Created Systemd Units (Optional — Survives Reboots)

**Purpose:** Auto-restart on crashes, survive system reboots

**Files Created:**

- [ops/systemd/rbotzilla-orchestrator.service](ops/systemd/rbotzilla-orchestrator.service)
- [ops/systemd/rbotzilla-oanda.service](ops/systemd/rbotzilla-oanda.service)
- [tools/install_systemd_units.sh](tools/install_systemd_units.sh) — Installer script

**Features:**

- Auto-restart on failure (30s delay for orchestrator, 60s for OANDA)
- Starts on boot (if enabled)
- Proper logging to journalctl + file logs
- Security hardening (NoNewPrivileges, PrivateTmp, ProtectSystem)
- Orchestrator and OANDA coordinated (OANDA requires orchestrator)

**Installation (Optional):**

```bash
# Install systemd units
sudo ./tools/install_systemd_units.sh

# Start services
sudo systemctl start rbotzilla-orchestrator
sudo systemctl start rbotzilla-oanda

# Check status
systemctl status rbotzilla-oanda

# View logs
journalctl -u rbotzilla-oanda -f
```

---

## 🎯 Next Steps for User

### Step 1: Test That .env Warning Is Fixed

```bash
cd /home/ing/RICK/MULTI_BROKER_PHOENIX
python3 -c "from multi_broker_phoenix.runners import oanda_runner; print('✅ Import OK')"
```

**Expected:** No warning about `.env` file, just `✅ Import OK`

### Step 2: Start OANDA

```bash
./tools/start_full_system.sh
```

**Expected Output:**

```
🚀 Starting RBOTzilla Full System
✓ Orchestrator started (PID=12345)
✓ OANDA broker started (PID=12346)
  State: PAUSED
```

### Step 3: Check Status

```bash
./tools/status_full_system.sh
```

**Expected:**

- Orchestrator: alive
- OANDA: PAUSED
- Gates: CONNECTIVITY ✓, LIQUIDITY ✓, OCO_READINESS ✓

### Step 4: Enable Paper Autonomy (When Ready)

**Follow runbook section:** "Initial Setup → Step 5: Enable Paper Autonomy"

Options:

- **Option A:** Via Task dropdown (if tasks exist)
- **Option B:** Manual commands:

  ```bash
  # Enable auto-arm (edit config)
  nano config/toggles.env  # Set AUTO_ARM_ON_HEALTHY=1

  # Restart
  ./tools/stop_full_system.sh
  ./tools/start_full_system.sh
  ```

### Step 5: Apply Stability Lock

```bash
./tools/stability_lock.sh
```

This makes code read-only for the 2-week run.

### Step 6: Daily Monitoring (2 min/day)

```bash
./tools/status_full_system.sh
```

See runbook for details: [OPS_OANDA_2WEEK_RUNBOOK.md](OPS_OANDA_2WEEK_RUNBOOK.md)

### Step 7: Optional — Install Systemd Units

```bash
sudo ./tools/install_systemd_units.sh
sudo systemctl start rbotzilla-orchestrator
sudo systemctl start rbotzilla-oanda
```

---

## 📋 Files Modified/Created

### Modified:

- [multi_broker_phoenix/runners/oanda_runner.py](multi_broker_phoenix/runners/oanda_runner.py#L26) — Fixed REPO_ROOT path

### Created:

- [tools/stability_lock.sh](tools/stability_lock.sh) — Lock code for 2-week stability
- [tools/stability_unlock.sh](tools/stability_unlock.sh) — Emergency unlock
- [OPS_OANDA_2WEEK_RUNBOOK.md](OPS_OANDA_2WEEK_RUNBOOK.md) — Operational procedures
- [ops/systemd/rbotzilla-orchestrator.service](ops/systemd/rbotzilla-orchestrator.service) — Systemd unit
- [ops/systemd/rbotzilla-oanda.service](ops/systemd/rbotzilla-oanda.service) — Systemd unit
- [tools/install_systemd_units.sh](tools/install_systemd_units.sh) — Systemd installer

---

## 🔐 Safety Mechanisms in Place

1. **PAUSED by Default** → System starts in PAUSED state
2. **OCO Enforcement** → No trade without TP+SL
3. **Gate System** → CONNECTIVITY, LIQUIDITY, OCO_READINESS must pass
4. **AUTO_ARM_ON_HEALTHY=0** → Manual arm required (change to 1 for autonomy)
5. **Stability Lock** → Code is read-only during 2-week run
6. **Fail-Closed Design** → Errors → PAUSED state (no crash)
7. **Broker Isolation** → OANDA only, Coinbase+IBKR disabled

---

## 📊 Success Criteria (After 2 Weeks)

- [ ] OANDA ran continuously for 14 days
- [ ] Zero manual restarts (or only due to known edge cases)
- [ ] All trades placed with valid OCO orders (TP+SL)
- [ ] Gate failures → clean PAUSED state (no crashes)
- [ ] Heartbeat updated every <30 seconds
- [ ] Daily checks took <2 minutes
- [ ] Code remained stability-locked (no emergency unlocks)

---

## 🚨 Emergency Commands

```bash
# Stop everything immediately
./tools/stop_full_system.sh

# Check what's running
ps aux | grep -E 'orchestrator|oanda_runner'

# Check recent errors
tail -100 logs/oanda/engine.log | grep ERROR

# Emergency unlock code (if critical bug found)
./tools/stability_unlock.sh
```

---

**Status:** ✅ Setup complete. Ready for testing and 2-week stability run.

**Next Action:** Test .env warning fix → Start SAFE mode → Verify gates → Enable autonomy → Lock stability → Monitor daily
