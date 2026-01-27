# RBOTZILLA CORE EXTRACT

**Extracted: 2026-01-11**
**Version: Golden Path v2.0.0**

---

## 🎯 Mission

This is the **extracted golden path** of the RBOTzilla HiveAgent headless trading system.
It contains ONLY the essential code that has proven to trade profitably using:

- OANDA Practice API (real API connection to practice account)
- IBKR Paper Trading (real TWS connection to paper port 4002)
- Coinbase Advanced Trade API (real money with nano-lot limits)
- AI Hive consensus voting (OpenAI + Grok + DeepSeek)

**NO SIMULATION. NO MOCK EXECUTION. REAL API CONNECTIONS.**

---

## 📁 Structure

```
RBOTZILLA_CORE_EXTRACT/
├── .vscode/tasks.json          # VS Code launch tasks
├── .env.example                # Required environment variables template
├── multi_broker_phoenix/       # Main trading package
│   ├── brokers/                # OANDA, IBKR, Coinbase connectors
│   ├── engines/                # Trading engines
│   ├── strategies/             # ALL strategies (PROTECTED - DO NOT MODIFY)
│   ├── risk/                   # Risk management
│   └── foundation/             # Charters, filters, sessions
├── execution/
│   └── oanda_practice_client.py  # OCO-enforced OANDA practice orders
├── hive_real/                  # AI Hive voting system
│   ├── api_ai_hive.py          # Main AI voting (get_api_ai_vote)
│   └── autonomous_repair.py    # Self-healing
├── scripts/                    # Auth verification & smoke tests
│   ├── verify_all_broker_auth.py
│   ├── oanda_practice_smoke_test.py
│   ├── oanda_practice_tiny_trade_test.py
│   ├── ibkr_practice_smoke_test.py
│   └── coinbase_nano_trade_test.py
└── tools/
    ├── run_headless.py         # GOLDEN RUNNER (main entrypoint)
    └── monitor_narration.py    # Real-time trade monitoring
```

---

## 🚀 Quick Start

### 1. Setup Environment

```bash
cd RBOTZILLA_CORE_EXTRACT
cp .env.example .env
# Edit .env with your actual API credentials
```

### 2. Verify Broker Auth

```bash
PYTHONPATH=. python3 scripts/verify_all_broker_auth.py
```

### 3. Run OANDA Practice Smoke Test

```bash
PYTHONPATH=. python3 scripts/oanda_practice_smoke_test.py
```

### 4. Start Headless Trading (OANDA Only)

```bash
PYTHONPATH=. python3 tools/run_headless.py --mode oanda-only
```

### 5. Start Multi-Asset Trading (All Brokers)

```bash
PYTHONPATH=. python3 tools/run_headless.py --mode multi-asset
```

---

## 🔒 PROTECTED FILES (DO NOT MODIFY)

The following files contain strategy/indicator logic and **MUST NOT be edited**:

- `multi_broker_phoenix/strategies/*.py`
- `multi_broker_phoenix/engines/atr_auto_tuner.py`
- `multi_broker_phoenix/engines/profit_extraction_engine.py`
- `hive_real/api_ai_hive.py`
- `hive_real/data_gate.py`

---

## 📊 Broker Execution Paths

| Broker   | Mode     | Order Path                                    | Endpoint                                           |
| -------- | -------- | --------------------------------------------- | -------------------------------------------------- |
| OANDA    | Practice | `place_paper_order()` → `OandaPracticeClient` | `api-fxpractice.oanda.com/v3/accounts/{id}/orders` |
| IBKR     | Paper    | `place_paper_order()` → TWS/IB Gateway        | Port 4002                                          |
| Coinbase | Live     | `place_live_order()` (if COINBASE_LIVE=true)  | `/api/v3/brokerage/orders`                         |

---

## 🛡️ Safety Features

- **OCO Bracket Enforcement**: Every OANDA order MUST include stop-loss and take-profit
- **AI Hive Consensus**: Trades require unanimous AI agent approval
- **Risk Manager**: Size limits, drawdown protection, trade risk gates
- **Canary Mode**: Ultra-conservative monitoring mode with slow polling

---

## 🚨 Emergency Stop

```bash
pkill -f run_headless.py
```

---

## 📜 Charter

This extraction follows the **NON-NEGOTIABLE CHARTER**:

- NO strategy/indicator edits
- NO new features or architecture
- NO simulation execution in headless mode
- Practice/Paper = REAL API connections

**No strategy/indicator logic was changed during extraction.**

---

## 🏷️ Lockdown

After smoke tests pass, lock the extraction:

```bash
chmod 444 .env
find . -type f -name "*.py" -exec chmod 444 {} \;
find . -type d -exec chmod 555 {} \;
```

To verify no drift:

```bash
find . -type f -name "*.py" -print0 | sort -z | xargs -0 sha256sum | sha256sum
```
