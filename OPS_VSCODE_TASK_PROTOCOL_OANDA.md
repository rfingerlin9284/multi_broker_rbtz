# OANDA Daily Operations Protocol

**Purpose:** Single-page guide for running OANDA autonomous trading via VS Code Tasks.

**Repo:** `/home/ing/RICK/MULTI_BROKER_PHOENIX`

---

## Daily Workflow (Click Tasks in Order)

### Morning Startup

1. **"OANDA DAILY: 1) Start"**
   - Starts orchestrator + OANDA runner
   - OANDA-only mode (Coinbase/IBKR disabled)

2. **"OANDA DAILY: 2) Status (Heartbeat + Gates)"**
   - Check broker health
   - Verify heartbeat updates
   - Confirm all gates PASS

3. **"OANDA DAILY: 3) Tail Logs (engine.log)"**
   - Watch real-time engine activity
   - Verify protect_loop running (errors=0)
   - Confirms token fix is working

4. **"OANDA DAILY: 4) Enable Trading (paper)"**
   - Enables trading (paper mode)
   - System now accepts AI signals

### Monitoring

- Use Task #2 (Status) every 30-60 minutes
- Use Task #3 (Tail Logs) to watch live activity
- Check `/home/ing/RICK/ops/state/brokers/oanda.json` for heartbeat

### Evening Shutdown

5. **"OANDA DAILY: 5) Stop OANDA (Clean)"**
   - Graceful shutdown
   - Waits for positions to close (if any)

6. **"OANDA DAILY: 6) Disable Trading"**
   - Disables trading (safety)
   - Use before any maintenance

---

## Key Files

| Path                                                | Purpose                                  |
| --------------------------------------------------- | ---------------------------------------- |
| `/home/ing/RICK/ops/state/brokers/oanda.json`       | Heartbeat (state, fail_count, timestamp) |
| `/home/ing/RICK/logs/oanda/engine.log`              | Main engine log                          |
| `/home/ing/RICK/logs/orchestrator/orchestrator.log` | Orchestrator log                         |

---

## Troubleshooting

**Problem:** Status shows "not running"

- **Fix:** Run Task #1 (Start SAFE)

**Problem:** Gates show FAIL

- **Fix:** Check logs with Task #3, review error messages

**Problem:** Token AttributeError

- **Fix:** This was permanently fixed (commit 224c20e). If you still see it, check branch.

**Problem:** Heartbeat file not updating

- **Fix:** Restart with Task #5 (Stop) then Task #1 (Start)

---

## Terminal Equivalents

```bash
# Start (OANDA-only)
cd /home/ing/RICK/MULTI_BROKER_PHOENIX
BROKER_OANDA_ENABLED=1 \
BROKER_COINBASE_ENABLED=0 \
BROKER_IBKR_ENABLED=0 \
AUTO_ARM_ON_HEALTHY=0 \
./tools/start_full_system.sh

# Status
./tools/status_full_system.sh

# Tail logs
tail -f /home/ing/RICK/logs/oanda/engine.log

# Enable trading
./tools/arm_oanda.sh

# Stop OANDA
./tools/stop_broker.sh oanda

# Disable trading
./tools/stop_broker.sh oanda
```

---

## Help Script

Run for quick reference:

```bash
./tools/oanda_daily_help.sh
```

---

**Last Updated:** 2026-01-26  
**Branch:** feature/full-scan-signal-brain  
**Commit:** bc8cf75 (preflight marker fix)
