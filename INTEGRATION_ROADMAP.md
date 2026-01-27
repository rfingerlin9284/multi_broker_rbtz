# RBOTZILLA Integration Roadmap - Connector Wiring

**Status:** Architecture ✅ Complete | Connector Integration ⚠️ Required  
**Priority:** Wire OANDA first (proven profitable, fastest path to autonomous OANDA-only operation)

---

## Critical Path: Three Broker Adapters

The framework expects each broker to implement `BrokerConnectorProtocol` from [multi_broker_phoenix/core/interfaces.py](multi_broker_phoenix/core/interfaces.py#L94).

### Required Methods Per Broker

Every connector must provide:

```python
class YourBrokerConnector:
    name: str = "oanda"  # or "coinbase" or "ibkr"

    def health_check(self) -> HealthCheckResult
    def get_prices(self, symbols: list[str]) -> dict
    def get_positions(self) -> list[PositionInfo]  # ← CRITICAL
    def place_order(self, order: dict) -> OrderInfo
    def place_oco(self, oco: OCOOrder) -> dict      # ← CRITICAL
    def cancel_order(self, order_id: str) -> bool
    def cancel_oco(self, oco_group_id: str) -> bool
    def get_open_orders(self) -> list[OrderInfo]
    def close_position(self, symbol: str, ...) -> OrderInfo
```

**Two non-negotiables:**

1. **`get_positions()`** - Exit manager cannot manage positions it cannot see
2. **`place_oco()`** - No trade without OCO protection

---

## Phase 1: OANDA Connector Adapter (PRIORITY 1)

### Current State Assessment Needed

**Action:** Locate your current OANDA connector implementation:

```bash
# Find existing OANDA connector
find . -type f -name "*.py" -exec grep -l "class.*Oanda.*Connector\|class.*OANDA" {} \;
```

**Likely locations:**

- `execution/oanda_connector.py`
- `execution/oanda_practice_client.py`
- `multi_broker_phoenix/execution/oanda_*.py`

### Adapter Strategy

If your OANDA connector has different method names, create an adapter:

```python
# File: multi_broker_phoenix/adapters/oanda_adapter.py

from multi_broker_phoenix.core.interfaces import (
    BrokerConnectorProtocol,
    HealthCheckResult,
    PositionInfo,
    OCOOrder,
    OrderInfo,
)
from execution.your_oanda_connector import YourOandaConnector


class OandaAdapter:
    """Adapts existing OANDA connector to BrokerConnectorProtocol."""

    name = "oanda"

    def __init__(self, legacy_connector: YourOandaConnector):
        self._connector = legacy_connector

    def get_positions(self) -> list[PositionInfo]:
        """Adapt list_open_trades() to get_positions()."""
        trades = self._connector.list_open_trades()

        positions = []
        for trade in trades:
            pos = PositionInfo(
                symbol=trade.get('instrument'),
                side="LONG" if float(trade.get('currentUnits', 0)) > 0 else "SHORT",
                quantity=abs(float(trade.get('currentUnits', 0))),
                entry_price=float(trade.get('price', 0)),
                current_price=float(trade.get('currentPrice', 0)),
                unrealized_pnl=float(trade.get('unrealizedPL', 0)),
                broker_position_id=trade.get('id'),
                raw=trade
            )
            positions.append(pos)

        return positions

    def place_oco(self, oco: OCOOrder) -> dict:
        """
        OANDA supports bracket orders via order dependencies.

        Place entry order with attached TP/SL orders linked via dependencies.
        """
        # Validate first
        valid, errors = oco.validate()
        if not valid:
            raise ValueError(f"Invalid OCO: {errors}")

        # OANDA bracket order structure
        bracket = {
            "order": {
                "type": "MARKET" if oco.entry_price is None else "LIMIT",
                "instrument": oco.symbol,
                "units": str(oco.entry_quantity) if oco.entry_side == "BUY" else str(-oco.entry_quantity),
                "timeInForce": oco.time_in_force,
                "takeProfitOnFill": {
                    "price": str(oco.take_profit_price)
                },
                "stopLossOnFill": {
                    "price": str(oco.stop_loss_price)
                }
            }
        }

        if oco.entry_price:
            bracket["order"]["price"] = str(oco.entry_price)

        # Place via existing OANDA connector
        result = self._connector.place_order(bracket)

        return {
            "oco_group_id": result.get("orderCreateTransaction", {}).get("id"),
            "entry_order": OrderInfo(
                order_id=result.get("orderCreateTransaction", {}).get("id"),
                symbol=oco.symbol,
                side=oco.entry_side,
                quantity=oco.entry_quantity,
                order_type="MARKET" if oco.entry_price is None else "LIMIT",
                price=oco.entry_price,
                status="PENDING",
                raw=result
            ),
            "take_profit_order": None,  # OANDA attaches these to trade, not separate orders
            "stop_loss_order": None,
            "status": "PLACED",
            "errors": []
        }

    # Delegate other methods to legacy connector
    def health_check(self) -> HealthCheckResult:
        try:
            summary = self._connector.get_account_summary()
            return HealthCheckResult(
                ok=bool(summary),
                details={"account": summary},
                errors=[],
                timestamp=time.time()
            )
        except Exception as e:
            return HealthCheckResult(
                ok=False,
                details={},
                errors=[str(e)],
                timestamp=time.time()
            )

    def get_prices(self, symbols: list[str]) -> dict:
        return self._connector.get_prices(symbols)

    # ... delegate remaining methods similarly
```

### OANDA Engine Start Integration

Once adapter exists, update [tools/start_broker.sh](tools/start_broker.sh#L47):

```bash
case "$BROKER_NAME" in
  oanda)
    # Start OANDA engine with supervisor
    nohup python3 -c "
from multi_broker_phoenix.engines.oanda_supervised import start_oanda_broker
start_oanda_broker()
" >> "$BROKER_LOG" 2>&1 &
    echo $! > "$BROKER_PID_FILE"
    ;;
```

And create the supervised engine wrapper:

```python
# File: multi_broker_phoenix/engines/oanda_supervised.py

from multi_broker_phoenix.core.broker_supervisor import BrokerSupervisor
from multi_broker_phoenix.core.gates import BrokerGates, get_default_maintenance_windows
from multi_broker_phoenix.adapters.oanda_adapter import OandaAdapter
from execution.your_oanda_connector import YourOandaConnector
from pathlib import Path


def start_oanda_broker():
    """Start OANDA broker under supervision."""
    repo_root = Path(__file__).resolve().parents[3]

    # Create legacy connector
    legacy_oanda = YourOandaConnector(
        # ... your existing init params
    )

    # Wrap in adapter
    connector = OandaAdapter(legacy_oanda)

    # Create supervisor
    supervisor = BrokerSupervisor(
        broker_name="oanda",
        connector=connector,
        repo_root=repo_root,
        fail_threshold=5,
        heartbeat_interval_sec=10.0
    )

    # Create gates
    gates = BrokerGates(
        broker_name="oanda",
        max_spread_pct=0.5,
        max_latency_ms=1000.0,
        maintenance_windows=get_default_maintenance_windows("oanda")
    )

    # Start heartbeat
    supervisor.start_heartbeat()
    supervisor.set_state(BrokerState.STARTING, "Initializing OANDA broker")

    # Run gate checks
    symbols = ["EUR_USD", "GBP_USD", "USD_JPY"]  # Your trading universe
    all_passed, gate_results = gates.run_all_gates(connector, symbols)
    supervisor.handle_gate_checks(gate_results)

    # If gates pass and auto-arm enabled
    if all_passed and os.getenv("AUTO_ARM_ON_HEALTHY") == "1":
        supervisor.set_state(BrokerState.ACTIVE, "All gates passed, auto-armed")
    else:
        supervisor.set_state(BrokerState.PAUSED, "Gates passed, awaiting guard unlock")

    # Start your existing trading loop here
    # (exit manager, protect loop, signal brain, etc.)
    # But now it respects supervisor.can_trade() before placing new trades

    while True:
        try:
            # Health check
            is_healthy, details = supervisor.run_health_check()
            if not is_healthy:
                logger.warning(f"OANDA health check failed: {details}")

            # Re-run gates periodically
            all_passed, gate_results = gates.run_all_gates(connector, symbols)
            supervisor.handle_gate_checks(gate_results)

            # Your trading logic (if supervisor.can_trade())
            if supervisor.can_trade():
                # Place trades via connector.place_oco()
                pass

            time.sleep(30)

        except KeyboardInterrupt:
            supervisor.shutdown()
            break
        except Exception as e:
            supervisor.record_failure(str(e))
            logger.error(f"OANDA broker error: {e}", exc_info=True)
            time.sleep(10)
```

---

## Phase 2: Coinbase Connector (PRIORITY 2)

### OCO Capability Assessment Required

**Critical question:** Does Coinbase Advanced Trade API support bracket orders or native OCO?

**Research needed:**

```bash
# Check Coinbase docs or existing connector
grep -r "bracket\|OCO\|stop_loss_on_fill" execution/coinbase* || echo "No native OCO found"
```

### Three Possible Outcomes

#### A) Native OCO/Bracket Supported

```python
def place_oco(self, oco: OCOOrder) -> dict:
    # Use Coinbase native bracket order API
    pass
```

#### B) OCO Not Supported (Fail Closed)

```python
from multi_broker_phoenix.core.interfaces import OCOUnsupportedError

def place_oco(self, oco: OCOOrder) -> dict:
    raise OCOUnsupportedError(
        broker="coinbase",
        symbol=oco.symbol,
        reason="Coinbase Advanced Trade does not support bracket/OCO orders. "
               "Emulation requires fill monitoring which cannot guarantee atomic cancel-other. "
               "Broker PAUSED for new trades to enforce no-trade-without-OCO rule."
    )
```

This is **valid and correct**. Broker goes PAUSED, existing positions managed, no new trades until OCO capability verified.

#### C) Emulated OCO (Acceptable Only If Strictly Enforced)

```python
def place_oco(self, oco: OCOOrder) -> dict:
    """
    EMULATED OCO for Coinbase.

    WARNING: This is a best-effort implementation.
    Failure modes:
    - Entry fills but TP/SL placement fails → FLATTEN immediately
    - TP fills but SL cancel fails → Log error, manual intervention
    - SL fills but TP cancel fails → Log error (no action needed)
    """
    # 1. Place entry order
    entry_result = self._place_entry(oco)
    entry_id = entry_result['id']

    # 2. Monitor for fill (blocking or async callback)
    fill_result = self._wait_for_fill(entry_id, timeout=30)
    if not fill_result['filled']:
        return {"status": "ENTRY_NOT_FILLED", "errors": ["Entry timeout"]}

    # 3. Place TP and SL
    try:
        tp_result = self._place_limit_order(oco.symbol, oco.take_profit_price, -oco.entry_quantity)
        sl_result = self._place_stop_order(oco.symbol, oco.stop_loss_price, -oco.entry_quantity)
    except Exception as e:
        # CRITICAL: Entry filled but protections failed
        # Must flatten immediately
        self._emergency_flatten(oco.symbol)
        raise OCOUnsupportedError(
            broker="coinbase",
            symbol=oco.symbol,
            reason=f"Entry filled but protective orders failed: {e}. Position flattened."
        )

    # 4. Store linkage and monitor
    self._oco_groups[entry_id] = {
        "tp_id": tp_result['id'],
        "sl_id": sl_result['id'],
        "symbol": oco.symbol
    }

    # 5. Start background monitor for cancel-other
    self._start_oco_monitor(entry_id)

    return {
        "oco_group_id": entry_id,
        "entry_order": entry_result,
        "take_profit_order": tp_result,
        "stop_loss_order": sl_result,
        "status": "EMULATED_ACTIVE",
        "errors": []
    }
```

**If emulation chosen:** Must add aggressive monitoring loop that cancels the other order within <1 second of one filling.

---

## Phase 3: IBKR Connector (PRIORITY 3)

### Gateway/TWS Headless Setup

IBKR requires stable IB Gateway or TWS running headless:

```bash
# Typical Gateway setup
docker run -d \
  --name ibkr-gateway \
  -p 4001:4001 \
  -p 4002:4002 \
  -v $HOME/.ibkr:/root/Jts \
  ghcr.io/unusualwhales/ib-gateway:latest
```

### IBKR Bracket Order Implementation

```python
def place_oco(self, oco: OCOOrder) -> dict:
    """IBKR native bracket order via TWS API."""
    from ib_insync import IB, Order, LimitOrder, StopOrder

    # Parent (entry) order
    parent = LimitOrder(
        "BUY" if oco.entry_side == "BUY" else "SELL",
        oco.entry_quantity,
        oco.entry_price
    )
    parent.orderId = self.ib.client.getReqId()
    parent.transmit = False

    # Take profit child
    take_profit = LimitOrder(
        "SELL" if oco.entry_side == "BUY" else "BUY",
        oco.entry_quantity,
        oco.take_profit_price
    )
    take_profit.orderId = parent.orderId + 1
    take_profit.parentId = parent.orderId
    take_profit.transmit = False

    # Stop loss child
    stop_loss = StopOrder(
        "SELL" if oco.entry_side == "BUY" else "BUY",
        oco.entry_quantity,
        oco.stop_loss_price
    )
    stop_loss.orderId = parent.orderId + 2
    stop_loss.parentId = parent.orderId
    stop_loss.transmit = True  # Transmit all together

    # Place bracket
    contract = self._get_contract(oco.symbol)
    parent_trade = self.ib.placeOrder(contract, parent)
    tp_trade = self.ib.placeOrder(contract, take_profit)
    sl_trade = self.ib.placeOrder(contract, stop_loss)

    return {
        "oco_group_id": str(parent.orderId),
        "entry_order": OrderInfo(...),
        "take_profit_order": OrderInfo(...),
        "stop_loss_order": OrderInfo(...),
        "status": "BRACKET_PLACED",
        "errors": []
    }
```

---

## Integration Checklist

### For Each Broker:

- [ ] **Locate existing connector** (grep for class definitions)
- [ ] **Create adapter** if needed (map methods to BrokerConnectorProtocol)
- [ ] **Implement `get_positions()`** (adapt from list_trades/positions/open_orders)
- [ ] **Implement `place_oco()`** (native OR emulated OR raise OCOUnsupportedError)
- [ ] **Create supervised engine wrapper** (like oanda_supervised.py example)
- [ ] **Update start_broker.sh** with correct engine entrypoint
- [ ] **Test isolated start/stop** (kill process, verify orchestrator restarts)
- [ ] **Test circuit breaker** (force auth failure, verify PAUSED state)
- [ ] **Test OCO validation** (try trade without TP/SL, verify blocked)

---

## Quick Win Path (Recommended Order)

1. **OANDA first** (you have profitable history, fastest validation)
   - Create OandaAdapter
   - Test supervised start
   - Verify heartbeat + gates working
   - Enable via `BROKER_OANDA_ENABLED=1`
   - Run autonomous OANDA-only for 48 hours

2. **IBKR second** (native bracket orders, cleaner implementation)
   - Ensure Gateway stable headless
   - Implement bracket order place_oco
   - Test isolated from OANDA
   - Enable via `BROKER_IBKR_ENABLED=1`

3. **Coinbase last** (highest OCO complexity)
   - Assess native capability
   - If unsupported: raise OCOUnsupportedError (valid choice)
   - If emulated: build aggressive monitoring
   - Test extensively before enabling

---

## Next Immediate Actions

1. **Find your OANDA connector:**

   ```bash
   grep -r "class.*Oanda" --include="*.py" .
   ```

2. **Run status to confirm framework is ready:**

   ```bash
   ./tools/status_full_system.sh
   ```

3. **Create first adapter:**

   ```bash
   mkdir -p multi_broker_phoenix/adapters
   # Start with oanda_adapter.py using template above
   ```

4. **Wire and test OANDA supervised start**

5. **Verify isolation:**

   ```bash
   # Start system
   ./tools/start_full_system.sh

   # Kill OANDA
   kill $(cat ops/state/brokers/oanda.pid)

   # Wait 60 seconds
   # Verify orchestrator restarted it
   ./tools/status_full_system.sh
   ```

---

## Success Criteria (Definition of Done)

You'll know integration is complete when:

✅ Each broker can start independently via Task dropdown  
✅ Heartbeat files update every 10 seconds with current state  
✅ Killing one broker process does not affect others  
✅ Broker without valid OCO capability stays PAUSED with clear error  
✅ Guard lock/unlock controls trading globally  
✅ Per-broker circuit breaker trips on repeated failures  
✅ Exit manager continues managing positions even when guard locked

---

**Current State:** Framework installed, awaiting connector integration  
**Blocker:** Need to locate/adapt existing OANDA connector as proof-of-concept  
**Timeline:** OANDA adapter = ~2-4 hours | Full 3-broker integration = ~8-16 hours
