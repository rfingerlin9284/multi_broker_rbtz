# OANDA 2-Week Operational Runbook

**Purpose:** Run OANDA paper trading reliably and autonomously for 2 weeks with minimal intervention.

**Status:** Stability-locked. Code changes disabled unless critical bug found.

---

## Daily Checklist (2 minutes max)

### Morning Check (once per day)

```bash
cd /home/ing/RICK/MULTI_BROKER_PHOENIX
./tools/status_full_system.sh
```

**Expected Output:**

```
✓ Orchestrator: alive (PID=12345)
✓ OANDA: ACTIVE (heartbeat 3s ago)
  - Guard: UNLOCKED  - Auto-arm: enabled
  - Gates: CONNECTIVITY ✓ | LIQUIDITY ✓ | OCO_READINESS ✓
  - Positions: 2 open
✓ Coinbase: DISABLED
✓ Ibkr: DISABLED
```

**If something looks wrong:**

1. Check logs: `tail -f logs/oanda/engine.log`
2. Check heartbeat: `cat ops/state/brokers/oanda.json`
3. See "Troubleshooting" section below

---## Initial Setup (One-Time)

### Step 1: Verify Environment

```bash
cd /home/ing/RICK/MULTI_BROKER_PHOENIX

# Check that .env exists with OANDA credentials
ls -la .env

# Verify toggles
cat config/toggles.env | grep -E 'BROKER_(OANDA|COINBASE|IBKR)_ENABLED'
```

Expected:

```
BROKER_OANDA_ENABLED=1
BROKER_COINBASE_ENABLED=0
BROKER_IBKR_ENABLED=0
```

### Step 2: Test Import (Verify Code Works)

```bash
python3 -c "from multi_broker_phoenix.runners import oanda_runner; print('✅ OK')"
```

Should print: `✅ OK`

### Step 3: Start in SAFE Mode (Guard Locked)

```bash
# Via Task dropdown (preferred):
# Task → RBOTZILLA: Start Full System (SAFE)

# Or via terminal:
./tools/start_full_system.sh
```

Expected output:

```
🚀 Starting RBOTzilla Full System (SAFE MODE)
✓ Orchestrator started (PID=12345)
✓ OANDA broker started (PID=12346)
   State: PAUSED (guard locked)
   Log: logs/oanda/engine.log
```

### Step 4: Verify Gates Pass

```bash
./tools/status_full_system.sh
```

Check:

- `CONNECTIVITY gate: ✓ passed`
- `LIQUIDITY gate: ✓ passed`
- `OCO_READINESS gate: ✓ passed`

If any gate fails, see "Gate Failures" troubleshooting section.

### Step 5: Enable Paper Autonomy

**Option A: Via Task Dropdown (Preferred)**

1. Task → `RBOTzilla: 🚀 Start + Preflight + Arm OANDA`
2. Edit `config/toggles.env` → set `AUTO_ARM_ON_HEALTHY=1`

**Option B: Via Terminal**

```bash
# Enable auto-arm
sed -i 's/AUTO_ARM_ON_HEALTHY=0/AUTO_ARM_ON_HEALTHY=1/' config/toggles.env

# Restart system
./tools/stop_full_system.sh
./tools/start_full_system.sh
```

**Verify autonomy is active:**

```bash
./tools/status_full_system.sh
```

Should show:

```
✓ OANDA: ACTIVE (not PAUSED)
  - AI Hive: REQUIRED for approvals
  - Auto-arm: enabled
```

### Step 6: Apply Stability Lock

```bash
./tools/stability_lock.sh
```

This makes code read-only for 2 weeks (prevents accidental changes).

---

## Normal Operations

### Daily Check (2 minutes)

1. Run `./tools/status_full_system.sh`
2. Verify OANDA state is ACTIVE (or PAUSED with valid reason)
3. Check heartbeat age (should be <30 seconds)
4. Check for errors in `ops/state/brokers/oanda.json`

### View Live Logs

```bash
# Via Task dropdown:
# Task → RBOTZILLA: Tail OANDA Logs

# Or via terminal:
tail -f logs/oanda/engine.log
```

### Restart OANDA Only (Without Stopping Orchestrator)

```bash
# Via Task dropdown:
# Task → RBOTZILLA: Stop OANDA
# Task → RBOTZILLA: Start OANDA

# Or via terminal:
./tools/stop_broker.sh oanda
./tools/start_broker.sh oanda
```

### Restart Full System

```bash
# Via Task dropdown:
# Task → RBOTZILLA: Stop Full System
# Task → RBOTZILLA: Start Full System (SAFE)

# Or via terminal:
./tools/stop_full_system.sh
./tools/start_full_system.sh
```

---

## Understanding Broker States

| State        | Meaning                 | Action Required                                |
| ------------ | ----------------------- | ---------------------------------------------- |
| **STARTING** | Broker initializing     | Wait 10-30 seconds                             |
| **PAUSED**   | Healthy but not trading | Check reason (gate failed? auto-arm disabled?) |
| **ACTIVE**   | Trading enabled         | Normal operation                               |
| **FAILED**   | Circuit breaker tripped | Check logs, fix issue, restart                 |

### PAUSED Reasons (Common)

- `gate_failed: CONNECTIVITY`: OANDA API auth issue → check credentials in .env
- `gate_failed: OCO_READINESS`: OCO capability check failed → check logs for details
- `manual_arm_required`: AUTO_ARM_ON_HEALTHY=0 → either enable auto-arm or manually arm
- `ai_hive_unavailable`: AI Hive not responding → check API keys

---

## Troubleshooting

### Problem: CONNECTIVITY gate failed

**Symptoms:** Status shows `CONNECTIVITY gate: ✗ failed (auth error)`

**Solutions:**

1. Check OANDA credentials in `.env`:

   ```bash
   grep OANDA .env
   ```

   Verify `OANDA_API_TOKEN` and `OANDA_ACCOUNT_ID` are correct.

2. Test auth manually:

   ```bash
   python3 -c "from execution.oanda_practice_client import OandaPracticeClient; \
               c = OandaPracticeClient(); print(c.get_account_summary())"
   ```

3. If auth is valid but gate still fails, check logs:
   ```bash
   tail -100 logs/oanda/engine.log | grep -i connectivity
   ```

### Problem: OCO_READINESS gate failed

**Symptoms:** Status shows `OCO_READINESS gate: ✗ failed`

**Solutions:**

1. Check if OANDA adapter supports OCO:

   ```bash
   python3 -c "from multi_broker_phoenix.adapters.oanda_adapter import OandaAdapter; \
               a = OandaAdapter(); h = a.health_check(); print(f'OCO capable: {h.oco_capable}')"
   ```

   Should print: `OCO capable: True`

2. Check logs for specific error:

   ```bash
   tail -100 logs/oanda/engine.log | grep -i oco
   ```

3. If OCO is truly not working, system will fail-closed (PAUSED). This is correct safety behavior.

### Problem: No positions opening even though ACTIVE

**Possible Causes:**

1. Strategy not generating signals → check signal brain logs
2. Risk limits hit → check position count vs max positions
3. OCO verification failing silently → check logs for "OCO verification failed"

**Debug Commands:**

```bash
# Check current positions
python3 -c "from multi_broker_phoenix.adapters.oanda_adapter import OandaAdapter; \
            a = OandaAdapter(); print(a.get_positions())"

# Check recent signal attempts
grep "signal generated\|trade allowed\|OCO placed" logs/oanda/engine.log | tail -20
```

### Problem: Heartbeat stopped updating

**Symptoms:** Status shows "heartbeat age: 120s" or "heartbeat: stale"

**Solution:**

1. Check if process is alive:

   ```bash
   cat ops/state/brokers/oanda.pid
   ps aux | grep $(cat ops/state/brokers/oanda.pid)
   ```

2. If process is dead, restart:

   ```bash
   ./tools/start_broker.sh oanda
   ```

3. If process is alive but heartbeat stale, check for deadlock in logs:
   ```bash
   tail -100 logs/oanda/engine.log
   ```

### Problem: Process crashes repeatedly (FAILED state)

**Symptoms:** Status shows OANDA state: FAILED, fail_count: 5+

**Solution:**

1. Check recent error in heartbeat:

   ```bash
   cat ops/state/brokers/oanda.json | grep last_error
   ```

2. Check crash logs:

   ```bash
   tail -200 logs/oanda/engine.log | grep -i "error\|exception\|traceback" -A 5
   ```

3. Fix the underlying issue, then restart:

   ```bash
   ./tools/stop_broker.sh oanda
   ./tools/start_broker.sh oanda
   ```

4. If issue persists, **unlock stability lock** to make code fixes:
   ```bash
   ./tools/stability_unlock.sh
   # Make minimal fix
   ./tools/stability_lock.sh
   ```

---

## Weekend / Maintenance Windows

### OANDA Maintenance Windows (Forex Rollover)

- **Daily:** 21:00-22:00 UTC (5pm-6pm ET) - Forex rollover
- **Weekend:** Friday 22:00 UTC → Sunday 22:00 UTC - Markets closed

**Expected Behavior:**

- During rollover: OANDA may go PAUSED with reason `maintenance_window`
- During weekend: Spreads may be wide, liquidity gate may fail
- **This is normal.** System will auto-recover when market conditions improve.

**No action required** unless PAUSED state persists >1 hour after maintenance window ends.

---

## Systemd Integration (Optional - Survives Reboots)

If systemd units are installed, service runs automatically on boot.

### Check Service Status

```bash
systemctl status rbotzilla-orchestrator
systemctl status rbotzilla-oanda
```

### View Service Logs

```bash
journalctl -u rbotzilla-oanda -f
```

### Restart Services

```bash
sudo systemctl restart rbotzilla-oanda
```

### Install Systemd Units (First Time)

```bash
./tools/install_systemd_units.sh
```

---

## After 2 Weeks

### Data Collection

1. **Copy logs for analysis:**

   ```bash
   tar -czf oanda_2week_logs_$(date +%Y%m%d).tar.gz logs/oanda/
   ```

2. **Copy heartbeat history:**

   ```bash
   cp -r ops/state/brokers oanda_2week_state_$(date +%Y%m%d)/
   ```

3. **Analyze:**
   - Total trades placed
   - Win rate
   - OCO verification success rate
   - Gate failure frequency / reasons
   - Average position hold time
   - P&L (paper)

### Unlock Stability Lock

```bash
./tools/stability_unlock.sh
```

### Plan Next Iteration

Based on 2-week data:

- Identify reliability issues that need fixes
- Plan next round of improvements
- Consider enabling Coinbase/IBKR (if OANDA was stable)

---

## Quick Reference

### Start Commands

```bash
./tools/start_full_system.sh          # Start orchestrator + enabled brokers (SAFE)
./tools/start_broker.sh oanda         # Start OANDA only
```

### Status Commands

```bash
./tools/status_full_system.sh         # Full system status
cat ops/state/brokers/oanda.json      # OANDA heartbeat details
./tools/check_status.sh               # Quick healthcheck (if exists)
```

### Log Commands

```bash
tail -f logs/oanda/engine.log         # Follow live log
grep "ERROR\|OCO" logs/oanda/engine.log | tail -50  # Recent errors/OCO events
```

### Control Commands

```bash
./tools/stop_full_system.sh           # Stop everything
./tools/stop_broker.sh oanda          # Stop OANDA only
./tools/restart_broker.sh oanda       # Restart OANDA (if script exists)
```

### Stability Lock Commands

```bash
./tools/stability_lock.sh             # Lock code (2-week stability mode)
./tools/stability_unlock.sh           # Unlock code (for fixes only)
```

---

## Emergency Contacts / Resources

- **Logs:** `logs/oanda/engine.log`
- **Heartbeat:** `ops/state/brokers/oanda.json`
- **Config:** `config/toggles.env`, `.env`
- **Documentation:** `INTEGRATION_COMPLETE.md`, `SYSTEM_STATUS.md`

---

**Last Updated:** 2026-01-25  
**Baseline:** Stability-locked for 2-week OANDA paper trading run
