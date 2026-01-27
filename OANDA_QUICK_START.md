# OANDA Quick Start - Just Click These Tasks

## 🎯 DAILY WORKFLOW (In Order)

### 1️⃣ START SYSTEM (Guard Locked = Safe)

**Click:** `RBOTzilla: 🚀 Start + Preflight + Arm OANDA (Enable Trading)`

- Enter PIN when prompted: `841921`
- **This does EVERYTHING:** Start → Preflight → Unlock → Trade

**What it does:**

- Starts orchestrator + OANDA broker
- Runs all preflight checks automatically
- Unlocks guard (enables trading)
- System ready to trade in ~10 seconds

### 2️⃣ CHECK STATUS

**Click:** `RBOTZILLA: Status`

- Shows: OANDA running, positions, PNL, gates

### 3️⃣ VIEW LIVE LOGS

**Click:** `RBOTZILLA: Tail Engine Logs`

- See: Trade entries, exits, OCO orders, trailing stops
- Shows narration of each trade decision

### 4️⃣ STOP SYSTEM (Clean Shutdown)

**Click:** `RBOTZILLA: Stop Full System`

- Stops all brokers cleanly
- Locks guard automatically

---

## 🔧 TROUBLESHOOTING

### If Preflight Fails

**Click:** `RBOTzilla: 🚦 Preflight (OANDA) — must PASS`

- See exactly what failed
- Fix issues, then restart

### Lock Trading (Keep System Running)

**Click:** `RBOTzilla: 🛑 Disable Trading (Lock Guard)`

- System stays on but won't enter new trades
- Existing positions still managed

### Unlock Trading (System Already Running)

**Click:** `RBOTzilla: 🟢 Arm OANDA (Enable Trading)`

- Enter PIN: `841921`
- Starts trading without restarting system

---

## 📊 MONITORING TASKS

**Position Details:**

- Click: `RBOTZILLA: Show Positions`
- Shows: All open trades, entry, SL, TP, age

**OCO Health:**

- Click: `RBOTZILLA: OCO Health Audit`
- Verifies: Stop-loss and take-profit orders are properly linked

**System Health:**

- Click: `[ANY] RBOTZILLA STATUS`
- Shows: Toggles, PIDs, credentials status

**Position Age:**

- Click: `[ANY] HOLDTIME AUDIT`
- Shows: How long each position has been open (6-8hr limit enforced)

---

## 💡 WHAT YOU SEE IN LOGS

**Trade Narration (every trade shows):**

```
TRADE_ENTRY: EUR_USD LONG entry=1.0850 sl=1.0820 tp=1.0920
OCO_RECONCILE: Verified SL/TP orders linked
EXIT_MANAGER_TICK: positions=3 profit_locks=1 trailing_updates=1
TRAILING_UPDATE: EUR_USD SL moved 1.0820→1.0860 (trailing +40 pips)
PROFIT_LOCK: EUR_USD moved SL to breakeven (+15 pips reached)
TIME_STOP_CLOSE: EUR_USD closed after 7.2 hours (max hold)
```

**Each trade gets:**

- Entry narration (why it entered)
- OCO order confirmation (SL/TP linked)
- Profit lock narration (when SL moves to breakeven)
- Trailing stop updates (as price moves in your favor)
- Time-based exit (if held too long)

---

## 🚨 EMERGENCY

**Kill Everything:**

```bash
./tools/stop_broker.sh all
```

**Restart from Scratch:**

1. Click: `RBOTZILLA: Stop Full System`
2. Wait 5 seconds
3. Click: `RBOTzilla: 🚀 Start + Preflight + Arm OANDA`

---

## ✅ YOUR SYSTEM IS WORKING

Your last run showed:

```
✅ PASS PRE-FLIGHT: ALL TESTS PASSED
✅ Preflight marker found
✅ Fresh preflight PASS detected
✅ ARMED: Trading enabled (AI Hive required for approvals)
✅ DONE: System running + preflight PASS
```

**Just use the one-click task daily:**
`RBOTzilla: 🚀 Start + Preflight + Arm OANDA (Enable Trading)`

That's it. It does everything automatically.
