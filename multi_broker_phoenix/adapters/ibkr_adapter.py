"""IBKR Adapter - Maps IBKRLiveConnector to BrokerConnectorProtocol.

This adapter wraps the existing IBKR connector (via ib_insync) and exposes
the BrokerConnector Protocol interface for the supervised broker framework.

IBKR supports NATIVE BRACKET ORDERS:
- Parent market/limit order
- Child take-profit order (linked via parentId)
- Child stop-loss order (linked via parentId)
- Gateway handles cancel-other logic automatically
- Restart-safe (Gateway persists state)
"""
from __future__ import annotations
import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

from multi_broker_phoenix.core.interfaces import (
    BrokerConnectorProtocol,
    HealthCheckResult,
    PositionInfo,
    OrderInfo,
    OCOOrder,
    OCOUnsupportedError,
)

logger = logging.getLogger(__name__)


class IbkrAdapter:
    """Adapter mapping IBKRLiveConnector → BrokerConnectorProtocol."""
    
    def __init__(self):
        """Initialize IBKR adapter with TWS/Gateway connection."""
        try:
            from multi_broker_phoenix.brokers.ibkr_connector_live import IBKRLiveConnector
        except ImportError:
            # Fallback to deployment package location
            import sys
            from pathlib import Path
            deployment_pkg = Path(__file__).resolve().parents[3] / 'DEPLOYMENT_PACKAGE' / 'multi_broker_phoenix' / 'brokers'
            sys.path.insert(0, str(deployment_pkg.parent))
            from brokers.ibkr_connector_live import IBKRLiveConnector
        
        self.connector = IBKRLiveConnector()
        self.name = "ibkr"
        
        # Connect to TWS/Gateway
        connected = self.connector.connect()
        if not connected:
            raise RuntimeError("Failed to connect to IBKR TWS/Gateway")
        
        logger.info(f"✅ IbkrAdapter initialized | port={self.connector.port}")
    
    def health_check(self) -> HealthCheckResult:
        """Check IBKR Gateway connectivity and bracket order capability."""
        start = time.time()
        errors = []
        
        try:
            if not self.connector.connected:
                errors.append("Not connected to TWS/Gateway")
        except Exception as e:
            errors.append(f"Connection check failed: {e}")
        
        try:
            # Test account summary
            summary = self.connector.get_account_summary()
            if not summary:
                errors.append("Account summary empty")
        except Exception as e:
            errors.append(f"Account summary failed: {e}")
        
        latency = (time.time() - start) * 1000
        
        # IBKR natively supports bracket orders
        oco_ready = len(errors) == 0
        
        return HealthCheckResult(
            ok=len(errors) == 0,
            details={'connection_check': conn_check, 'account_check': account_check},
            errors=errors,
            latency_ms=latency,
            oco_capable=oco_ready,
            timestamp=datetime.utcnow().isoformat() + 'Z',
        )
    
    def get_prices(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get current prices for symbols."""
        start = time.time()
        result = {}
        
        for symbol in symbols:
            try:
                price = self.connector.get_current_price(symbol)
                if price:
                    result[symbol] = {
                        'bid': price,  # IBKR connector returns mid price
                        'ask': price,
                        'mid': price,
                        'timestamp': datetime.utcnow().isoformat() + 'Z',
                        'latency_ms': (time.time() - start) * 1000,
                    }
            except Exception as e:
                logger.error(f"get_prices failed for {symbol}: {e}")
        
        return result
    
    def get_positions(self) -> List[PositionInfo]:
        """Get open positions from IBKR."""
        positions = []
        
        try:
            # TODO: Implement via ib_insync ib.positions()
            # For now, return empty (exit_manager will handle gracefully)
            logger.warning("get_positions not yet fully implemented for IBKR")
        except Exception as e:
            logger.error(f"get_positions failed: {e}")
        
        return positions
    
    def place_order(self, order: Dict[str, Any]) -> OrderInfo:
        """Place order without OCO - intentionally not supported."""
        raise NotImplementedError(
            "place_order() not implemented for IBKR. "
            "Use place_oco() to ensure bracket orders."
        )
    
    def place_oco(self, oco: OCOOrder) -> OrderInfo:
        """Place IBKR bracket order (parent + TP + SL children).
        
        IBKR bracket orders:
        - Parent: Market or limit order
        - Child 1: Take-profit limit order (parentId linkage)
        - Child 2: Stop-loss stop order (parentId linkage)
        - Gateway auto-cancels children when parent fills or one child fills
        
        Args:
            oco: OCOOrder with symbol, side, quantity, stop_loss, take_profit
        
        Returns:
            OrderInfo with parent order ID as oco_group_id
        """
        if not oco.stop_loss or not oco.take_profit:
            raise ValueError(
                f"OCO requires both stop_loss and take_profit. "
                f"broker=ibkr symbol={oco.symbol} sl={oco.stop_loss} tp={oco.take_profit}"
            )
        
        try:
            # TODO: Implement via ib_insync bracket order
            # from ib_insync import Order, Stock
            # 
            # contract = Stock(oco.symbol, 'SMART', 'USD')
            # parent = Order()
            # parent.action = "BUY" if oco.side.lower() == 'long' else "SELL"
            # parent.orderType = "MKT"
            # parent.totalQuantity = oco.quantity
            # parent.transmit = False
            #
            # tp_order = Order()
            # tp_order.action = "SELL" if oco.side.lower() == 'long' else "BUY"
            # tp_order.orderType = "LMT"
            # tp_order.totalQuantity = oco.quantity
            # tp_order.lmtPrice = oco.take_profit
            # tp_order.parentId = parent.orderId
            # tp_order.transmit = False
            #
            # sl_order = Order()
            # sl_order.action = "SELL" if oco.side.lower() == 'long' else "BUY"
            # sl_order.orderType = "STP"
            # sl_order.totalQuantity = oco.quantity
            # sl_order.auxPrice = oco.stop_loss
            # sl_order.parentId = parent.orderId
            # sl_order.transmit = True  # Transmit all at once
            #
            # trade = self.connector.ib.placeOrder(contract, parent)
            # self.connector.ib.placeOrder(contract, tp_order)
            # self.connector.ib.placeOrder(contract, sl_order)
            
            logger.warning(f"place_oco stub: {oco.symbol} {oco.side} qty={oco.quantity}")
            
            return OrderInfo(
                broker='ibkr',
                order_id='stub',
                oco_group_id='stub',
                symbol=oco.symbol,
                side=oco.side,
                quantity=oco.quantity,
                status='pending',  # Would be 'filled' after actual execution
                filled_price=None,
                timestamp=datetime.utcnow().isoformat() + 'Z',
                error='STUB - Full implementation pending',
            )
        
        except Exception as e:
            logger.error(f"place_oco failed: {e}")
            return OrderInfo(
                broker='ibkr',
                order_id='error',
                oco_group_id='error',
                symbol=oco.symbol,
                side=oco.side,
                quantity=oco.quantity,                order_type='MARKET',                status='error',
                filled_price=None,
                timestamp=datetime.utcnow().isoformat() + 'Z',
                error=str(e),
            )
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel pending order."""
        logger.warning(f"cancel_order stub: order_id={order_id}")
        return False
    
    def cancel_oco(self, oco_group_id: str) -> bool:
        """Cancel bracket order group."""
        try:
            # TODO: Cancel parent order (children auto-cancel)
            logger.warning(f"cancel_oco stub: oco_group_id={oco_group_id}")
            return False
        except Exception as e:
            logger.error(f"cancel_oco failed: {e}")
            return False
