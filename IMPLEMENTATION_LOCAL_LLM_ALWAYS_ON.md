# LOCAL LLM ALWAYS-ON + AI SEAT ROTATION Implementation Summary

**Date:** 2026-01-23
**Status:** IMPLEMENTED & TESTED

## What Was Fixed

### Root Cause of Freezes

Your logs showed repeated:

```
WATCHDOG FREEZE ... grok ok=False code=404 ... deepseek ok=False code=401
```

**Problem:** `REQUIRE_XAI=1` and `REQUIRE_DEEPSEEK=1` in `config/toggles.env` meant the system was fail-closed on AI seat health. When both cloud seats failed, trading froze entirely.

**15-hour zombie positions:** The exit manager ran but couldn't override frozen state because the engine was in full lockdown mode.

### Solution Implemented

**QUORUM MODEL:** Instead of requiring ALL seats healthy, we now require **MIN_BRAIN_SEATS=1** (at least one healthy seat, usually local Ollama).

---

## Files Changed/Added

### New Files

| File                                                       | Purpose                                                     |
| ---------------------------------------------------------- | ----------------------------------------------------------- |
| [llm_gate/gate_service.py](llm_gate/gate_service.py)       | LLM Gate HTTP service with hard rule checks + Ollama review |
| [llm_gate/install_service.sh](llm_gate/install_service.sh) | Systemd service installer for LLM Gate                      |
| [tools/tasks/ai_status.sh](tools/tasks/ai_status.sh)       | Deterministic AI seat status snapshot                       |
| [tools/tasks/exit_status.sh](tools/tasks/exit_status.sh)   | Exit manager + position age status                          |
| [tools/tasks/ai_repair.sh](tools/tasks/ai_repair.sh)       | Trigger AI repair scan with cooldown                        |

### Modified Files

| File                                                                                   | Change                                                                                           |
| -------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| [config/toggles.env](config/toggles.env)                                               | Changed to quorum model (REQUIRE_XAI=0, REQUIRE_DEEPSEEK=0, REQUIRE_OLLAMA=1, MIN_BRAIN_SEATS=1) |
| [.env](.env)                                                                           | Removed conflicting REQUIRE_XAI=1 / REQUIRE_DEEPSEEK=1 at end of file                            |
| [multi_broker_phoenix/risk/exit_manager.py](multi_broker_phoenix/risk/exit_manager.py) | Added EXITS NEVER FREEZE documentation                                                           |

### Pre-existing Infrastructure (Already Working)

| Component                   | Location                                             |
| --------------------------- | ---------------------------------------------------- |
| AI Seat Router with quorum  | `multi_broker_phoenix/ai/seat_router.py`             |
| Quarantine + backoff logic  | `SeatStatus.mark_failure()` with exponential backoff |
| Ollama client               | `llm_gate/ollama_gate.py`                            |
| Exit Manager with time-stop | `multi_broker_phoenix/risk/exit_manager.py`          |
| Protect Loop with ticks     | `multi_broker_phoenix/risk/protect_loop.py`          |

---

## Configuration Changes

### Before (Broken - Both Required)

```dotenv
REQUIRE_XAI=1
REQUIRE_DEEPSEEK=1
REQUIRE_AI=1
```

### After (Working - Quorum Model)

```dotenv
# Cloud seats are PREFERRED, not MANDATORY
REQUIRE_XAI=0
REQUIRE_DEEPSEEK=0
REQUIRE_OPENAI=0
REQUIRE_OLLAMA=1

# Quorum: at least 1 healthy seat allows trading
REQUIRE_AI=1
MIN_BRAIN_SEATS=1
REQUIRE_SEATS_MIN=1

# Cloud failures don't block trading
AI_FAIL_OPEN_ON_CLOUD_ERRORS=1
REQUIRE_XAI_MANDATORY=0
REQUIRE_DEEPSEEK_MANDATORY=0
```

---

## How It Works Now

### AI Seat Rotation

```
Seat Priority: ollama (local) → grok → deepseek → openai
```

1. **Health Check:** Each seat is checked on watchdog tick
2. **Quarantine:** Failed seats get exponential backoff (10s → 20s → ... → 300s max)
3. **Recovery:** 2 consecutive successes removes quarantine
4. **Selection:** First healthy, preferred seat is used

### When Grok/DeepSeek Fail

```
Before: Both fail → FREEZE ALL TRADING
After:  Both fail → Use Ollama (local) → TRADING CONTINUES
```

### Exit Manager Independence

The Exit Manager:

- **NEVER** checks `trading_allowed()`
- **ALWAYS** runs profit locks, trailing stops, time-stops
- **ENFORCES** 6-8 hour max hold regardless of watchdog state

---

## Acceptance Tests (All Pass)

| Test                                                                      | Result                                                   |
| ------------------------------------------------------------------------- | -------------------------------------------------------- |
| Grok=404, DeepSeek=401, Ollama=healthy → Bot uses Ollama, trading allowed | ✅ PASS                                                  |
| All seats unhealthy → New entries frozen, exits continue                  | ✅ PASS                                                  |
| Time-stop closes positions > MAX_HOLD_HOURS                               | ✅ (code verified)                                       |
| OCO enforced on every order                                               | ✅ (code verified)                                       |
| Proof-of-life ticks in logs                                               | ✅ (EXIT_MANAGER_TICK, PROTECT_LOOP_TICK, WATCHDOG_TICK) |

---

## How to Verify

### 1. Check AI Status

```bash
/home/ing/RICK/MULTI_BROKER_PHOENIX/tools/tasks/ai_status.sh
```

Expected: `"verdict": "PASS"` with `"ollama": {"healthy": true}`

### 2. Check Exit Status

```bash
/home/ing/RICK/MULTI_BROKER_PHOENIX/tools/tasks/exit_status.sh
```

Expected: Shows heartbeat status and any positions at risk

### 3. Test Ollama Generation

```bash
curl -fsS http://127.0.0.1:11434/api/generate \
  -H 'Content-Type: application/json' \
  -d '{"model":"llama3.1:8b","prompt":"Reply OK.","stream":false}'
```

Expected: JSON with `"response": "OK"` or similar

### 4. (Optional) Start LLM Gate Service

```bash
bash /home/ing/RICK/MULTI_BROKER_PHOENIX/llm_gate/install_service.sh
sudo systemctl start rbotzilla-llm-gate
curl http://127.0.0.1:6060/health
```

---

## Environment Variables Reference

| Variable              | Default                  | Description                                       |
| --------------------- | ------------------------ | ------------------------------------------------- |
| `REQUIRE_OLLAMA`      | `true`                   | Enable local Ollama seat                          |
| `REQUIRE_XAI`         | `0`                      | Enable Grok seat (0=preferred, not mandatory)     |
| `REQUIRE_DEEPSEEK`    | `0`                      | Enable DeepSeek seat (0=preferred, not mandatory) |
| `MIN_BRAIN_SEATS`     | `1`                      | Minimum healthy seats for trading                 |
| `REQUIRE_SEATS_MIN`   | `1`                      | Same as MIN_BRAIN_SEATS (router compat)           |
| `OLLAMA_BASE_URL`     | `http://127.0.0.1:11434` | Ollama API URL                                    |
| `OLLAMA_MODEL`        | `llama3.1:8b`            | Default model for generation                      |
| `EXIT_MAX_HOLD_HOURS` | `8`                      | Max position age (6-8 enforced)                   |
| `LLM_GATE_PORT`       | `6060`                   | LLM Gate service port                             |

---

## What Happens Next Time Cloud Seats Fail

1. Watchdog detects Grok/DeepSeek failures
2. Seats are quarantined with backoff
3. Ollama (local) is selected as active brain
4. Trading continues with local LLM approval
5. Auto-repair probes providers periodically
6. When cloud seats recover, they're re-enabled after 2 successes

**The bot will NOT go silent.** It uses the local brain and keeps protecting capital.
