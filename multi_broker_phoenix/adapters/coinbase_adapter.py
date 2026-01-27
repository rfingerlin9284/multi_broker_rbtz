"""Coinbase Adapter - Maps CoinbaseSafeConnector to BrokerConnectorProtocol.

CRITICAL OCO DECISION:
Coinbase Advanced Trade API does NOT natively support OCO/bracket orders.

OPTIONS:
1. EMULATED OCO (Complex):
   - Place market order
   - Place separate STOP_LOSS_STOP + TAKE_PROFIT_LIMIT orders
   - Track linkage in ops/state/coinbase_oco_links.json
   - Poll fills, cancel sibling when one executes
   - Reconcile on restart (fix orphaned orders)
   
2. BLOCK OCO (Safer):
   - Raise OCOUnsupportedError in place_oco()
   - Broker stays PAUSED with explicit reason
   - User must opt-in to emulated OCO or accept broker unusable

CURRENT IMPLEMENTATION: **BLOCK OCO** (fail-closed)
User can implement emulated OCO later if willing to accept complexity + risk.
"""
from __future__ import annotations
import logging
import os
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


class CoinbaseAdapter:
    """Adapter mapping CoinbaseSafeConnector → BrokerConnectorProtocol.
    
    WARNING: OCO NOT SUPPORTED (blocks trading by default).
    """
    
    def __init__(self):
        """Initialize Coinbase adapter."""
        try:
            from multi_broker_phoenix.brokers.coinbase_safe_connector import CoinbaseSafeConnector
        except ImportError:
            import sys
            from pathlib import Path
            deployment_pkg = Path(__file__).resolve().parents[3] / 'DEPLOYMENT_PACKAGE' / 'multi_broker_phoenix' / 'brokers'
            sys.path.insert(0, str(deployment_pkg.parent))
            from brokers.coinbase_safe_connector import CoinbaseSafeConnector
        
        # Determine if emulated OCO is explicitly enabled
        self.emulated_oco_enabled = os.getenv('COINBASE_EMULATED_OCO', 'false').lower() == 'true'
        
        # Initialize connector in paper mode by default
        self.connector = CoinbaseSafeConnector(paper_mode=True)
        self.name = "coinbase"
        
        logger.info(f"✅ CoinbaseAdapter initialized | emulated_oco={self.emulated_oco_enabled}")
        
        if not self.emulated_oco_enabled:
            logger.warning(
                "⚠️  Coinbase adapter initialized WITHOUT OCO support. "
                "Broker will remain PAUSED. Set COINBASE_EMULATED_OCO=true to enable (NOT RECOMMENDED)."
            )
    
    def health_check(self) -> HealthCheckResult:
        """Check Coinbase API connectivity."""
        start = time.time()
        errors = []
        
        try:
            balance = self.connector.get_account_balance()
            if not balance:
                errors.append("Account balance empty")
        except Exception as e:
            errors.append(f"Account balance failed: {e}")
        
        try:
            price = self.connector.get_current_price('BTC-USD')
            if not price:
                errors.append("Price fetch returned no data")
        except Exception as e:
            errors.append(f"Price fetch failed: {e}")
        
        latency = (time.time() - start) * 1000
        
        # OCO NOT capable unless emulated mode explicitly enabled
        oco_ready = self.emulated_oco_enabled and len(errors) == 0
        
        return HealthCheckResult(
            ok=len(errors) == 0,
            details={'auth_check': auth_check},
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
                        'bid': price,
                        'ask': price,
                        'mid': price,
                        'timestamp': datetime.utcnow().isoformat() + 'Z',
                        'latency_ms': (time.time() - start) * 1000,
                    }
            except Exception as e:
                logger.error(f"get_prices failed for {symbol}: {e}")
        
        return result
    
    def get_positions(self) -> List[PositionInfo]:
        """Get open positions from Coinbase.
        
        Note: Coinbase has no native positions API. Must track fills.
        """
        positions = []
        
        try:
            # TODO: Track open positions via fill history
            logger.warning("get_positions not fully implemented for Coinbase")
        except Exception as e:
            logger.error(f"get_positions failed: {e}")
        
        return positions
    
    def place_order(self, order: Dict[str, Any]) -> OrderInfo:
        """Place order without OCO - not supported."""
        raise NotImplementedError(
            "place_order() not implemented for Coinbase. "
            "Use place_oco() (but OCO not supported unless emulated mode enabled)."
        )
    
    def place_oco(self, oco: OCOOrder) -> OrderInfo:
        """Place OCO order - BLOCKED unless emulated mode enabled.
        
        Coinbase does NOT natively support OCO/bracket orders.
        
        Raises:
            OCOUnsupportedError: Always (unless COINBASE_EMULATED_OCO=true)
        """
        if not self.emulated_oco_enabled:
            raise OCOUnsupportedError(
                broker='coinbase',
                symbol=oco.symbol,
                reason=(
                    "Coinbase does not natively support OCO/bracket orders. "
                    "Set COINBASE_EMULATED_OCO=true to enable emulated OCO (RISKY). "
                    "Emulated OCO requires complex order tracking, fill polling, "
                    "restart reconciliation, and orphan cleanup. "
                    "Mitigation: (1) Use OANDA or IBKR for OCO-dependent strategies, OR "
                    "(2) Set COINBASE_EMULATED_OCO=true and implement full emulation logic, OR "
                    "(3) Accept Coinbase broker staying PAUSED (fail-closed)"
                ),
            )
        
        # If emulated OCO is enabled (user opted-in to risk)
        logger.warning(
            f"⚠️  EMULATED OCO (RISKY): {oco.symbol} {oco.side} "
            f"qty={oco.quantity} sl={oco.stop_loss} tp={oco.take_profit}"
        )
        
        # TODO: Implement emulated OCO if user insists:
        # 1. Place market order
        # 2. Place STOP_LOSS_STOP order (sell if long, buy if short)
        # 3. Place TAKE_PROFIT_LIMIT order
        # 4. Store linkage in ops/state/coinbase_oco_links.json
        # 5. Poll fills every N seconds
        # 6. When one fills, cancel the other IMMEDIATELY
        # 7. On restart, reconcile orphans and re-link
        
        return OrderInfo(
            broker='coinbase',
            order_id='emulated_stub',
            oco_group_id='emulated_stub',
            symbol=oco.symbol,
            side=oco.side,
            quantity=oco.quantity,            order_type='MARKET',            status='pending',
            filled_price=None,
            timestamp=datetime.utcnow().isoformat() + 'Z',
            error='Emulated OCO not fully implemented (stub)',
        )
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel pending order."""
        logger.warning(f"cancel_order stub: order_id={order_id}")
        return False
    
    def cancel_oco(self, oco_group_id: str) -> bool:
        """Cancel emulated OCO group."""
        logger.warning(f"cancel_oco stub: oco_group_id={oco_group_id}")
        return False
