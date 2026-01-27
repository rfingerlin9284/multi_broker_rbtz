# INTEGRATION_DISCOVERY.md

## Discovery Results

### OANDA (PROVEN PROFITABLE)

**Client Implementation:**

- File: `execution/oanda_practice_client.py`
- Class: `OandaPracticeClient`
- API: `https://api-fxpractice.oanda.com/v3` (Practice)

**Key Methods:**

```python
get_account_summary() -> Dict
get_prices(instruments: List[str]) -> Dict  # Returns bid/ask with timestamp
list_open_trades() -> Dict                  # Returns open trades with SL/TP/id
create_order_market(instrument, units, sl_price, tp_price, client_tag) -> Dict
close_position(instrument) -> Dict
create_stop_loss(trade_id, price) -> Dict
create_take_profit(trade_id, price) -> Dict
```

**OCO Capability:**

- ✅ **NATIVE SUPPORT** via `stopLossOnFill` and `takeProfitOnFill` in order payload
- Orders placed without SL/TP are **REJECTED** at client level (validation enforced)
- Verified TP/SL attached at order creation time
- Restart-safe: broker manages protective orders natively

**BrokerConnectorProtocol Mapping:**

- `get_positions()` → `list_open_trades()` then normalize structure
- `place_oco(oco)` → `create_order_market(instrument, units, sl, tp)`
- `health_check()` → `get_account_summary()` + validate response
- `get_prices(symbols)` → `get_prices(instruments)` direct
- `cancel_oco(group_id)` → `close_position(instrument)`

**Current Entry Point:**

- File: `DEPLOYMENT_PACKAGE/tools/run_headless.py`
- Mode: `--mode oanda-only`
- Launch Command: `python3 -u tools/run_headless.py --mode oanda-only`
- Strategy Brain: Uses `multi_broker_phoenix.strategies.base.get_strategy()`
- Risk Gates: `multi_broker_phoenix.risk.risk_manager.RiskManager`
- Exit Logic: Currently embedded in run_headless loop

**Existing Safety Monitors (NOT YET SUPERVISED):**

- `multi_broker_phoenix.risk.exit_manager` (profit lock, trailing, time stop)
- `multi_broker_phoenix.risk.oco_reconcile` (verify OCO integrity)
- `multi_broker_phoenix.risk.protect_loop` (runs exit_manager + oco_reconcile)
- `multi_broker_phoenix.monitor.pnl_kill_switch` (flatten on threshold breach)
- `multi_broker_phoenix.risk.broker_health` (health monitoring)

---

### COINBASE (REAL MONEY ONLY)

**Connector Implementation:**

- File: `DEPLOYMENT_PACKAGE/multi_broker_phoenix/brokers/coinbase_safe_connector.py`
- Class: `CoinbaseSafeConnector`
- API: Coinbase Advanced Trade API (`/api/v3/brokerage/orders`)

**Key Methods:**

```python
place_live_order(cand, size_usd, confirm_real_money=True) -> Dict
place_paper_order(cand, size_usd) -> Dict  # Simulated via PaperEngine
get_current_price(symbol) -> float
get_account_balance() -> Dict
```

**OCO Capability:**

- ⚠️ **UNCLEAR - REQUIRES ASSESSMENT**
- Coinbase Advanced Trade API does NOT natively support OCO/bracket orders
- Options:
  1. **Emulated OCO** (complex):
     - Place market order
     - Place separate STOP_LOSS_STOP and TAKE_PROFIT_LIMIT orders
     - Track linkage in durable store (ops/state/oco_linkage.json)
     - Watch fills via polling, cancel sibling when one fills
     - Reconcile on restart to fix orphans
  2. **Block OCO entirely** (safer):
     - Raise `OCOUnsupportedError` in place_oco()
     - Broker stays PAUSED
     - User explicitly opts-in to emulated OCO or accepts broker unusable

**BrokerConnectorProtocol Mapping:**

- `get_positions()` → Requires polling + tracking open fills (no REST positions API)
- `place_oco(oco)` → **DECISION REQUIRED** (emulated vs blocked)
- `health_check()` → `get_account_balance()` + latency check
- `get_prices(symbols)` → `get_current_price(symbol)` per symbol
- `cancel_oco(group_id)` → Track open orders, cancel via order IDs

**Current Entry Point:**

- File: `DEPLOYMENT_PACKAGE/tools/run_headless.py`
- Mode: `--mode coinbase-only`
- Launch Command: `python3 -u tools/run_headless.py --mode coinbase-only`
- Real Money Flag: `COINBASE_LIVE=true` (env var)

**Safety Limits (Nano Trading):**

- Min: $5, Max: $10 per trade
- Daily loss limit: $50
- Consecutive loss breaker: 5 losses
- Max trades per day: Unlimited (env: COINBASE_MAX_TRADES_PER_DAY)

---

### IBKR (PAPER + LIVE VIA TWS/GATEWAY)

**Connector Implementation:**

- File: `DEPLOYMENT_PACKAGE/multi_broker_phoenix/brokers/ibkr_connector_live.py`
- Class: `IBKRLiveConnector`
- API: IB Gateway / TWS via `ib_insync` library
  - Paper: Port 4002
  - Live: Port 4001

**Key Methods:**

```python
connect() -> bool
get_account_summary() -> Dict
get_current_price(symbol) -> float
place_paper_order(cand, size) -> Dict
close_position(symbol) -> bool
```

**OCO Capability:**

- ✅ **NATIVE BRACKET ORDERS**
- Place parent market/limit order
- Attach child TP order (LMT, parentId linkage)
- Attach child SL order (STP, parentId linkage)
- Gateway manages cancel-other logic natively
- Restart-safe: Gateway persists bracket state

**BrokerConnectorProtocol Mapping:**

- `get_positions()` → `ib.positions()` via ib_insync
- `place_oco(oco)` → Create parent + 2 children with parentId linkage
- `health_check()` → Check `ib.isConnected()` + account summary
- `get_prices(symbols)` → `ib.reqMktData()` per contract
- `cancel_oco(group_id)` → Cancel parent_id (children auto-cancel)

**Current Entry Point:**

- File: `DEPLOYMENT_PACKAGE/tools/run_headless.py`
- Mode: `--mode ibkr-only`
- Launch Command: `python3 -u tools/run_headless.py --mode ibkr-only`
- Prerequisite: IB Gateway or TWS running on configured port

**Gateway Setup (Headless):**

- Recommended: Docker container with IB Gateway (port 4002)
- Alternative: TWS with API enabled (requires X11 for GUI)
- Connection params: `IBKR_HOST`, `IBKR_PORT`, `IBKR_CLIENT_ID`

---

## Integration Architecture Decision

### Chosen Approach: SUPERVISED ENGINE WRAPPER

**Rationale:**

- Existing engines in `tools/run_headless.py` contain **profitable strategy logic**
- Exit manager, OCO reconcile, protect loop already work
- Risk manager, signal brain, AI hive already integrated
- **DO NOT REWRITE** — only wrap and supervise

**Wrapper Pattern:**

```python
# multi_broker_phoenix/engines/oanda_supervised.py
from multi_broker_phoenix.core.broker_supervisor import BrokerSupervisor
from multi_broker_phoenix.adapters.oanda_adapter import OandaAdapter
from multi_broker_phoenix.risk.exit_manager import start_exit_manager
from multi_broker_phoenix.risk.protect_loop import start_protect_loop
from multi_broker_phoenix.monitor.pnl_kill_switch import start_pnl_loop

def start_oanda_broker():
    adapter = OandaAdapter()
    supervisor = BrokerSupervisor(name='oanda', connector=adapter)

    supervisor.start_heartbeat()  # Write ops/state/brokers/oanda.json

    # Start safety monitors (exit manager, oco reconcile, pnl kill)
    start_exit_manager(adapter)
    start_protect_loop(adapter)
    start_pnl_loop(adapter)

    # Run existing engine logic
    while supervisor.can_trade():
        # Existing run_headless poll loop
        # Strategy signal → risk check → place order via adapter
        pass
```

---

## Adapter Mapping Summary

| Broker   | Client/Connector File                   | OCO Support | Adapter Priority |
| -------- | --------------------------------------- | ----------- | ---------------- |
| OANDA    | `execution/oanda_practice_client.py`    | ✅ Native   | 1 (proven $$$)   |
| IBKR     | `...brokers/ibkr_connector_live.py`     | ✅ Bracket  | 2 (native OCO)   |
| Coinbase | `...brokers/coinbase_safe_connector.py` | ⚠️ TBD      | 3 (complex)      |

**Integration Priority:** OANDA → IBKR → Coinbase

---

## Next Steps (Automated)

1. Create `multi_broker_phoenix/runners/oanda_runner.py`
   - Load env via tools/env_load.sh pattern
   - Instantiate OandaAdapter
   - Instantiate BrokerSupervisor
   - Start heartbeat writer
   - Run adapted run_headless loop
   - Write PID to ops/state/brokers/oanda.pid

2. Create `multi_broker_phoenix/adapters/oanda_adapter.py`
   - Implement BrokerConnectorProtocol
   - Wrap OandaPracticeClient methods
   - Map list_open_trades → get_positions (normalized)
   - Map create_order_market → place_oco
   - Add health_check with connectivity + latency + OCO test

3. Update `tools/start_broker.sh`
   - Replace placeholder: `python3 -m multi_broker_phoenix.engines.oanda_engine`
   - Real command: `python3 -m multi_broker_phoenix.runners.oanda_runner`

4. Repeat for IBKR, then Coinbase (with OCO decision)

5. Add acceptance tests (isolation, gates, OCO enforcement, auto-activate)

---

## File Paths Summary

### Existing Working Code (DO NOT MODIFY)

```
execution/oanda_practice_client.py                          # OANDA REST client
multi_broker_phoenix/risk/exit_manager.py                    # Profit lock, trailing, time stop
multi_broker_phoenix/risk/oco_reconcile.py                   # OCO integrity checks
multi_broker_phoenix/risk/protect_loop.py                    # Safety monitor runner
multi_broker_phoenix/monitor/pnl_kill_switch.py              # Account P&L flatten
multi_broker_phoenix/strategies/base.py                      # Strategy loader
multi_broker_phoenix/risk/risk_manager.py                    # Size + risk gates
DEPLOYMENT_PACKAGE/tools/run_headless.py                     # Current entry point
```

### New Files to Create

```
multi_broker_phoenix/runners/oanda_runner.py                 # OANDA supervised engine
multi_broker_phoenix/runners/coinbase_runner.py              # Coinbase supervised engine
multi_broker_phoenix/runners/ibkr_runner.py                  # IBKR supervised engine
multi_broker_phoenix/adapters/oanda_adapter.py               # OANDA → Protocol
multi_broker_phoenix/adapters/coinbase_adapter.py            # Coinbase → Protocol
multi_broker_phoenix/adapters/ibkr_adapter.py                # IBKR → Protocol
tools/test_isolation.sh                                       # Broker isolation test
tools/test_gates.sh                                           # Gate failure test
tools/test_oco_enforcement.sh                                 # OCO block test
tools/test_auto_activate.sh                                   # Auto-arm test
```

### Files to Update

```
tools/start_broker.sh                                         # Remove placeholders
.vscode/tasks.json                                            # Add missing tasks
multi_broker_phoenix/core/gates.py                            # Real eligibility checks
```

---

## Environment Variables Required

```bash
# OANDA (proven profitable)
OANDA_API_TOKEN=your_practice_token
OANDA_ACCOUNT_ID=your_practice_account

# IBKR (TWS/Gateway)
IBKR_HOST=localhost
IBKR_PORT=4002  # Paper trading
IBKR_CLIENT_ID=1

# Coinbase (real money - use with caution)
COINBASE_API_KEY=your_api_key
COINBASE_API_SECRET=your_api_secret
COINBASE_LIVE=false  # Set true to enable real orders

# Broker toggles
BROKER_OANDA_ENABLED=1
BROKER_COINBASE_ENABLED=0  # Disable until OCO decision made
BROKER_IBKR_ENABLED=0      # Disable until Gateway running

# Auto-arm defaults
AUTO_ARM_ON_HEALTHY=0      # Require explicit arm command
```

---

## Critical Path

✅ **PHASE 0 COMPLETE** — Discovery finished
🔄 **PHASE 1 NEXT** — Create runners (oanda first)

**Estimated Integration Time:**

- OANDA runner + adapter: 30 minutes
- IBKR runner + adapter: 45 minutes
- Coinbase OCO decision + adapter: 60 minutes
- Tests + docs: 30 minutes
- Total: ~3 hours end-to-end
