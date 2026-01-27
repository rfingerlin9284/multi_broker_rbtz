"""
ORDER FILL VERIFICATION SYSTEM
Ensures all counted trades are VERIFIED FILLED, not just PLACED
Tracks filled orders across all brokers (Coinbase, OANDA, IBKR)
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class OrderStatus(Enum):
    """Order statuses for verification."""
    PLACED = "placed"           # Order created but not filled yet
    PENDING = "pending"         # Order submitted to broker
    PARTIALLY_FILLED = "partially_filled"  # Some quantity filled
    FILLED = "filled"           # Completely filled
    CANCELLED = "cancelled"     # Order cancelled
    REJECTED = "rejected"       # Order rejected by broker
    UNKNOWN = "unknown"         # Status unknown


class OrderFillRecord:
    """Record of a single filled order."""
    
    def __init__(self, order_id: str, broker: str, symbol: str, 
                 side: str, qty: float, fill_price: float):
        self.order_id = order_id
        self.broker = broker
        self.symbol = symbol
        self.side = side
        self.qty = qty
        self.fill_price = fill_price
        self.status = OrderStatus.PLACED
        self.placed_time = datetime.now()
        self.filled_time: Optional[datetime] = None
        self.notional_usd = qty * fill_price
        self.fees_usd = 0.0
        
    def mark_filled(self, filled_price: Optional[float] = None):
        """Mark order as filled."""
        self.status = OrderStatus.FILLED
        self.filled_time = datetime.now()
        if filled_price:
            self.fill_price = filled_price
            self.notional_usd = self.qty * filled_price
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'order_id': self.order_id,
            'broker': self.broker,
            'symbol': self.symbol,
            'side': self.side,
            'qty': self.qty,
            'fill_price': self.fill_price,
            'status': self.status.value,
            'notional_usd': self.notional_usd,
            'placed_time': self.placed_time.isoformat(),
            'filled_time': self.filled_time.isoformat() if self.filled_time else None,
            'time_to_fill_sec': (self.filled_time - self.placed_time).total_seconds() if self.filled_time else None
        }


class OrderFillVerifier:
    """Unified order fill verification across all brokers."""
    
    def __init__(self):
        """Initialize fill verifier."""
        self.all_orders: Dict[str, OrderFillRecord] = {}  # order_id -> OrderFillRecord
        self.filled_orders: Dict[str, OrderFillRecord] = {}  # Only verified filled
        self.pending_orders: Dict[str, OrderFillRecord] = {}  # Awaiting confirmation
        self.rejected_orders: Dict[str, OrderFillRecord] = {}  # Failed orders
        
        # Statistics
        self.total_placed = 0
        self.total_filled = 0
        self.total_rejected = 0
        self.total_notional_usd = 0.0
        
        # By broker
        self.stats_by_broker: Dict[str, Dict[str, int]] = {}
        
        logger.info("🔍 Order Fill Verifier initialized")
    
    def record_order_placed(self, order_id: str, broker: str, symbol: str,
                           side: str, qty: float, price: float) -> OrderFillRecord:
        """Record that an order was PLACED (not yet filled)."""
        record = OrderFillRecord(order_id, broker, symbol, side, qty, price)
        self.all_orders[order_id] = record
        self.pending_orders[order_id] = record
        self.total_placed += 1
        
        # Track by broker
        if broker not in self.stats_by_broker:
            self.stats_by_broker[broker] = {'placed': 0, 'filled': 0, 'rejected': 0}
        self.stats_by_broker[broker]['placed'] += 1
        
        logger.debug(f"📋 Order PLACED: {order_id} | {broker} {symbol} {side} {qty} @ ${price}")
        return record
    
    def verify_order_filled(self, order_id: str, filled_price: Optional[float] = None) -> bool:
        """Verify that an order is FILLED (moved from placed to filled)."""
        if order_id not in self.all_orders:
            logger.warning(f"⚠️  Order {order_id} not found in records")
            return False
        
        record = self.all_orders[order_id]
        
        # Move from pending to filled
        if order_id in self.pending_orders:
            del self.pending_orders[order_id]
        
        # Mark as filled
        record.mark_filled(filled_price)
        self.filled_orders[order_id] = record
        self.total_filled += 1
        self.total_notional_usd += record.notional_usd
        
        # Track by broker
        if record.broker not in self.stats_by_broker:
            self.stats_by_broker[record.broker] = {'placed': 0, 'filled': 0, 'rejected': 0}
        self.stats_by_broker[record.broker]['filled'] += 1
        
        time_to_fill = (record.filled_time - record.placed_time).total_seconds()
        logger.info(f"✅ Order VERIFIED FILLED: {order_id} | {record.broker} {record.symbol} "
                   f"{record.qty} @ ${record.fill_price} | {time_to_fill:.1f}s")
        
        return True
    
    def reject_order(self, order_id: str, reason: str = "Broker rejected"):
        """Mark an order as rejected."""
        if order_id not in self.all_orders:
            logger.warning(f"⚠️  Order {order_id} not found in records")
            return
        
        record = self.all_orders[order_id]
        record.status = OrderStatus.REJECTED
        
        # Move from pending to rejected
        if order_id in self.pending_orders:
            del self.pending_orders[order_id]
        
        self.rejected_orders[order_id] = record
        self.total_rejected += 1
        
        # Track by broker
        if record.broker not in self.stats_by_broker:
            self.stats_by_broker[record.broker] = {'placed': 0, 'filled': 0, 'rejected': 0}
        self.stats_by_broker[record.broker]['rejected'] += 1
        
        logger.warning(f"❌ Order REJECTED: {order_id} | {record.broker} {record.symbol} | {reason}")
    
    def get_filled_count(self) -> int:
        """Get count of VERIFIED filled orders."""
        return self.total_filled
    
    def get_pending_count(self) -> int:
        """Get count of orders awaiting fill confirmation."""
        return len(self.pending_orders)
    
    def get_rejected_count(self) -> int:
        """Get count of rejected orders."""
        return self.total_rejected
    
    def get_filled_orders(self) -> List[OrderFillRecord]:
        """Get all verified filled orders."""
        return list(self.filled_orders.values())
    
    def get_pending_orders(self) -> List[OrderFillRecord]:
        """Get all orders awaiting fill confirmation."""
        return list(self.pending_orders.values())
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics."""
        return {
            'total_placed': self.total_placed,
            'total_filled': self.total_filled,
            'total_rejected': self.total_rejected,
            'total_pending': len(self.pending_orders),
            'fill_rate_pct': (self.total_filled / self.total_placed * 100) if self.total_placed > 0 else 0,
            'total_notional_usd': self.total_notional_usd,
            'stats_by_broker': self.stats_by_broker,
            'pending_orders': [o.to_dict() for o in self.get_pending_orders()],
            'filled_orders_sample': [o.to_dict() for o in self.get_filled_orders()[:10]]  # Last 10
        }
    
    def print_summary(self):
        """Print order fill summary."""
        stats = self.get_stats()
        
        logger.info("")
        logger.info("="*70)
        logger.info("📊 ORDER FILL VERIFICATION SUMMARY")
        logger.info("="*70)
        logger.info(f"Total Placed:     {stats['total_placed']}")
        logger.info(f"Total Filled:     {stats['total_filled']} ✅")
        logger.info(f"Total Rejected:   {stats['total_rejected']} ❌")
        logger.info(f"Awaiting Fill:    {stats['total_pending']} ⏳")
        logger.info(f"Fill Rate:        {stats['fill_rate_pct']:.1f}%")
        logger.info(f"Total Notional:   ${stats['total_notional_usd']:,.2f}")
        logger.info("")
        
        # By broker
        logger.info("BY BROKER:")
        for broker, broker_stats in stats['stats_by_broker'].items():
            logger.info(f"  {broker:10} | Placed: {broker_stats['placed']:3} | "
                       f"Filled: {broker_stats['filled']:3} ✅ | Rejected: {broker_stats['rejected']:3} ❌")
        
        logger.info("="*70)
        logger.info("")


# Global instance
_verifier: Optional[OrderFillVerifier] = None


def get_order_fill_verifier() -> OrderFillVerifier:
    """Get global order fill verifier instance."""
    global _verifier
    if _verifier is None:
        _verifier = OrderFillVerifier()
    return _verifier
