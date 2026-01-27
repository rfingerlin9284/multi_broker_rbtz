"""
Broker connector interface and protocol definitions.

This module defines the contract that all broker connectors must implement
to ensure consistent behavior across OANDA, Coinbase, IBKR, and future brokers.

NON-NEGOTIABLES:
- Every connector must implement get_positions()
- Every connector must implement place_oco() (native or emulated)
- Connectors that cannot support OCO must raise OCOUnsupportedError and fail closed per-trade
"""

from typing import Protocol, Any, Optional
from dataclasses import dataclass
from enum import Enum


class OCOUnsupportedError(Exception):
    """
    Raised when a broker cannot natively or reliably emulate OCO orders.
    
    When this error is raised, the broker must:
    1. NOT place the trade
    2. Mark itself PAUSED for NEW trades
    3. Write actionable error details to ops/state/brokers/{broker}.json
    """
    
    def __init__(self, broker: str, symbol: str, reason: str):
        self.broker = broker
        self.symbol = symbol
        self.reason = reason
        super().__init__(
            f"OCO unsupported for {broker}/{symbol}: {reason}. "
            f"Trade blocked. Broker PAUSED for new orders."
        )


class BrokerState(str, Enum):
    """Per-broker state machine."""
    DISABLED = "DISABLED"      # Toggle off, should not run
    STARTING = "STARTING"      # Process starting up
    PAUSED = "PAUSED"          # Healthy but not trading (gate failure or auto-arm disabled)
    ACTIVE = "ACTIVE"          # Healthy and trading
    FAILED = "FAILED"          # Circuit breaker tripped, needs manual intervention


@dataclass
class HealthCheckResult:
    """Standardized health check response."""
    ok: bool
    details: dict[str, Any]
    errors: list[str]
    timestamp: float
    latency_ms: float = 0.0
    oco_capable: bool = False


@dataclass
class PositionInfo:
    """Standardized position information."""
    symbol: str
    side: str  # "LONG" or "SHORT"
    quantity: float
    entry_price: float
    current_price: Optional[float] = None
    unrealized_pnl: Optional[float] = None
    broker_position_id: Optional[str] = None
    broker: Optional[str] = None
    entry_time: Optional[str] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    raw: Optional[dict] = None  # Broker-specific raw data


@dataclass
class OrderInfo:
    """Standardized order information."""
    order_id: str
    symbol: str
    side: str  # "BUY" or "SELL"
    quantity: float
    order_type: str  # "MARKET", "LIMIT", "STOP", etc.
    price: Optional[float] = None
    status: Optional[str] = None
    oco_group_id: Optional[str] = None  # OCO group ID if part of OCO
    broker: Optional[str] = None
    filled_price: Optional[float] = None
    timestamp: Optional[str] = None
    error: Optional[str] = None
    raw: Optional[dict] = None


@dataclass
class OCOOrder:
    """
    One-Cancels-Other order specification.
    
    This represents a trade entry with protective exit orders (TP/SL)
    that are linked such that when one executes, the other cancels.
    """
    symbol: str
    entry_side: str  # "BUY" or "SELL"
    entry_quantity: float
    take_profit_price: float
    stop_loss_price: float
    entry_price: Optional[float] = None  # None for market orders
    oco_group_id: Optional[str] = None  # Broker-assigned or generated
    client_tag: Optional[str] = None  # Client-assigned order tag
    time_in_force: str = "GTC"
    
    # Convenience properties for backward compatibility
    @property
    def side(self) -> str:
        """Alias for entry_side."""
        return self.entry_side
    
    @property
    def quantity(self) -> float:
        """Alias for entry_quantity."""
        return self.entry_quantity
    
    @property
    def stop_loss(self) -> float:
        """Alias for stop_loss_price."""
        return self.stop_loss_price
    
    @property
    def take_profit(self) -> float:
        """Alias for take_profit_price."""
        return self.take_profit_price
    
    def validate(self) -> tuple[bool, list[str]]:
        """Validate OCO order parameters."""
        errors = []
        
        if not self.symbol:
            errors.append("Symbol is required")
        
        if self.entry_side not in ("BUY", "SELL"):
            errors.append(f"Invalid entry_side: {self.entry_side}")
        
        if self.entry_quantity <= 0:
            errors.append(f"Invalid quantity: {self.entry_quantity}")
        
        if self.entry_side == "BUY":
            # Long position: TP > entry, SL < entry
            if self.entry_price and self.take_profit_price <= self.entry_price:
                errors.append(f"BUY: TP {self.take_profit_price} must be > entry {self.entry_price}")
            if self.entry_price and self.stop_loss_price >= self.entry_price:
                errors.append(f"BUY: SL {self.stop_loss_price} must be < entry {self.entry_price}")
        else:  # SELL
            # Short position: TP < entry, SL > entry
            if self.entry_price and self.take_profit_price >= self.entry_price:
                errors.append(f"SELL: TP {self.take_profit_price} must be < entry {self.entry_price}")
            if self.entry_price and self.stop_loss_price <= self.entry_price:
                errors.append(f"SELL: SL {self.stop_loss_price} must be > entry {self.entry_price}")
        
        return len(errors) == 0, errors


class BrokerConnectorProtocol(Protocol):
    """
    Required interface for all broker connectors.
    
    This protocol ensures:
    1. Consistent position retrieval across brokers
    2. Consistent OCO order placement (native or emulated)
    3. Consistent health checks and error handling
    4. Deterministic failure modes
    
    Implementation notes:
    - If a broker lacks native OCO, implement emulated OCO with verified cancel-other enforcement
    - If emulated OCO cannot be guaranteed, raise OCOUnsupportedError in place_oco()
    - get_positions() must return current positions or empty list (never raise)
    - health_check() should be fast (<2s) and non-blocking
    """
    
    name: str  # Broker name: "oanda", "coinbase", "ibkr"
    
    def health_check(self) -> HealthCheckResult:
        """
        Check broker connectivity and auth status.
        
        Returns:
            HealthCheckResult with details about connectivity, auth, API latency
        """
        ...
    
    def get_prices(self, symbols: list[str]) -> dict[str, dict[str, float]]:
        """
        Get current prices for symbols.
        
        Args:
            symbols: List of symbol names
        
        Returns:
            {symbol: {"bid": float, "ask": float, "mid": float, "timestamp": float}}
        """
        ...
    
    def get_positions(self) -> list[PositionInfo]:
        """
        Get all current positions.
        
        REQUIRED: Every connector must implement this.
        If broker API lacks a positions endpoint, adapter must map from trades/orders.
        
        Returns:
            List of PositionInfo objects, empty list if no positions
        """
        ...
    
    def place_order(self, order: dict[str, Any]) -> OrderInfo:
        """
        Place a single order (not OCO protected).
        
        WARNING: This should rarely be used directly. Prefer place_oco().
        
        Args:
            order: Order specification dict
        
        Returns:
            OrderInfo with broker order ID and status
        """
        ...
    
    def place_oco(self, oco: OCOOrder) -> dict[str, Any]:
        """
        Place an OCO (One-Cancels-Other) protected trade.
        
        REQUIRED: Every connector must implement this (native or emulated).
        
        For native bracket support (IBKR):
            - Use broker's native bracket order API
        
        For emulated OCO (Coinbase, others):
            - Place entry order
            - On fill, place TP and SL orders with verified linkage
            - Monitor and enforce cancel-other behavior
            - If any step fails, cancel all and raise OCOUnsupportedError
        
        Args:
            oco: OCOOrder specification
        
        Returns:
            {
                "oco_group_id": str,
                "entry_order": OrderInfo,
                "take_profit_order": OrderInfo,
                "stop_loss_order": OrderInfo,
                "status": str,
                "errors": list[str]
            }
        
        Raises:
            OCOUnsupportedError: If OCO cannot be guaranteed
        """
        ...
    
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel a single order.
        
        Args:
            order_id: Broker order ID
        
        Returns:
            True if cancelled, False otherwise
        """
        ...
    
    def cancel_oco(self, oco_group_id: str) -> bool:
        """
        Cancel all orders in an OCO group.
        
        Args:
            oco_group_id: OCO group identifier
        
        Returns:
            True if all orders cancelled, False otherwise
        """
        ...
    
    def get_open_orders(self) -> list[OrderInfo]:
        """
        Get all open orders.
        
        Returns:
            List of OrderInfo objects
        """
        ...
    
    def close_position(
        self,
        symbol: str,
        quantity: Optional[float] = None,
        reason: str = "manual_close"
    ) -> OrderInfo:
        """
        Close a position (market order).
        
        Args:
            symbol: Symbol to close
            quantity: Optional quantity (None = close entire position)
            reason: Reason for closure (for logging)
        
        Returns:
            OrderInfo for the closing order
        """
        ...


class GateCheckResult:
    """Result from a broker gate check."""
    
    def __init__(
        self,
        gate_name: str,
        passed: bool,
        details: dict[str, Any],
        errors: Optional[list[str]] = None
    ):
        self.gate_name = gate_name
        self.passed = passed
        self.details = details
        self.errors = errors or []
    
    def __repr__(self) -> str:
        status = "✅ PASS" if self.passed else "❌ FAIL"
        return f"<GateCheck {self.gate_name} {status}>"


class BrokerGatesProtocol(Protocol):
    """
    Protocol for broker auto-activation gate checks.
    
    Each broker must pass three gates to become ACTIVE:
    1. CONNECTIVITY: auth + price feed working
    2. LIQUIDITY: spreads/latency reasonable, not in maintenance window
    3. OCO_READINESS: can place and verify protective orders
    """
    
    def check_connectivity(self, connector: BrokerConnectorProtocol) -> GateCheckResult:
        """Check if broker connection and auth are healthy."""
        ...
    
    def check_liquidity(
        self,
        connector: BrokerConnectorProtocol,
        symbols: list[str]
    ) -> GateCheckResult:
        """Check if market liquidity and conditions are acceptable."""
        ...
    
    def check_oco_readiness(self, connector: BrokerConnectorProtocol) -> GateCheckResult:
        """Check if OCO orders can be placed and verified."""
        ...
    
    def run_all_gates(
        self,
        connector: BrokerConnectorProtocol,
        symbols: list[str]
    ) -> tuple[bool, list[GateCheckResult]]:
        """
        Run all gate checks.
        
        Returns:
            (all_passed: bool, results: list[GateCheckResult])
        """
        ...
