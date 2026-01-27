"""IBKR Live Connector with TWS/Gateway Integration

This module provides REAL Interactive Brokers connectivity through TWS/IB Gateway.
Supports both paper trading (port 4002) and live trading (port 4001).

PAPER MODE (Port 4002):
- Real paper account with $1M fake money
- Real market data and execution
- Zero financial risk
- Perfect for strategy validation

LIVE MODE (Port 4001):  
- REAL MONEY - Use with extreme caution
- Requires proper authentication
- Should only be enabled after extensive paper testing
"""
from __future__ import annotations
import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    from ib_insync import IB, Stock, Order, MarketOrder, LimitOrder, StopOrder
    IB_INSYNC_AVAILABLE = True
except ImportError:
    IB_INSYNC_AVAILABLE = False
    logger.warning("ib_insync not installed - IBKR connector will run in stub mode only")


class IBKRLiveConnector:
    """Real IBKR connector using ib_insync for TWS/Gateway communication."""
    
    def __init__(
        self,
        host: str = None,
        port: int = None,
        client_id: int = None,
        paper_mode: bool = True,
        engine: Optional[Any] = None,
        fee_pct: float = 0.001,
        slippage_pct: float = 0.001
    ):
        """Initialize IBKR connector.
        
        Args:
            host: TWS/Gateway host (default: localhost)
            port: TWS/Gateway port (4002=paper, 4001=live)
            client_id: Unique client ID for this connection
            paper_mode: Safety flag - must be True for paper account
            engine: PaperEngine for fallback
            fee_pct: Estimated fee percentage
            slippage_pct: Estimated slippage percentage
        """
        self.host = host or os.getenv('IBKR_HOST', 'localhost')
        self.port = int(port or os.getenv('IBKR_PORT', '4002'))
        self.client_id = int(client_id or os.getenv('IBKR_CLIENT_ID', '1'))
        self.paper_mode = bool(paper_mode or os.getenv('IBKR_PAPER_MODE', 'true').lower() == 'true')
        self.engine = engine
        self.fee_pct = float(fee_pct)
        self.slippage_pct = float(slippage_pct)
        
        # Safety check: Port 4002 = paper, 4001 = live
        if self.port == 4001 and self.paper_mode:
            logger.error("❌ SAFETY: Port 4001 is LIVE mode but paper_mode=True")
            raise ValueError("Port 4001 requires paper_mode=False")
        
        if self.port == 4002 and not self.paper_mode:
            logger.warning("⚠️  Port 4002 is paper mode but paper_mode=False - forcing paper_mode=True")
            self.paper_mode = True
        
        self.ib = None
        self.connected = False
        
        if not IB_INSYNC_AVAILABLE:
            logger.error("❌ ib_insync not available - install with: pip install ib_insync")
            return
        
        logger.info(f"🔧 IBKR Connector initialized: {self.host}:{self.port} (paper={self.paper_mode})")
    
    def connect(self) -> bool:
        """Connect to TWS/Gateway."""
        if not IB_INSYNC_AVAILABLE:
            logger.error("❌ Cannot connect - ib_insync not installed")
            return False
        
        try:
            self.ib = IB()
            self.ib.connect(self.host, self.port, clientId=self.client_id)
            self.connected = True
            
            mode_str = "🟢 PAPER" if self.paper_mode else "🔴 LIVE"
            logger.info(f"✅ Connected to IBKR {mode_str}: {self.host}:{self.port}")
            return True
        
        except Exception as e:
            logger.error(f"❌ IBKR connection failed: {e}")
            logger.error(f"   Make sure TWS/IB Gateway is running on port {self.port}")
            self.connected = False
            return False
    
    def disconnect(self):
        """Disconnect from TWS/Gateway."""
        if self.ib and self.connected:
            self.ib.disconnect()
            self.connected = False
            logger.info("Disconnected from IBKR")
    
    def get_last_price(self, symbol: str) -> Optional[float]:
        """Get current market price for symbol."""
        if not self.connected:
            if not self.connect():
                return None
        
        try:
            # Create contract
            contract = Stock(symbol, 'SMART', 'USD')
            
            # Request market data
            ticker = self.ib.reqMktData(contract, '', False, False)
            self.ib.sleep(1)  # Wait for data
            
            # Get last price
            price = ticker.last if ticker.last and ticker.last > 0 else ticker.close
            
            if price and price > 0:
                return float(price)
            
            return None
        
        except Exception as e:
            logger.error(f"❌ Error getting price for {symbol}: {e}")
            return None
    
    def place_paper_order(self, candidate: Any, size: float) -> Dict[str, Any]:
        """Place order through IBKR paper account."""
        if not self.paper_mode:
            logger.error("❌ SAFETY: place_paper_order called but paper_mode=False")
            raise RuntimeError("Cannot place_paper_order in live mode")
        
        return self._place_order(candidate, size)
    
    def place_live_order(self, candidate: Any, size: float) -> Dict[str, Any]:
        """Place REAL MONEY order through IBKR live account.
        
        ⚠️  WARNING: This uses REAL MONEY!
        Should only be called after extensive paper testing.
        """
        if self.paper_mode:
            logger.error("❌ Cannot place live order in paper mode")
            raise RuntimeError("Live orders require paper_mode=False and port=4001")
        
        logger.warning(f"🔴 PLACING LIVE ORDER (REAL MONEY): {candidate.symbol}")
        return self._place_order(candidate, size)
    
    def _place_order(self, candidate: Any, size: float) -> Dict[str, Any]:
        """Internal order placement logic."""
        if not self.connected:
            if not self.connect():
                logger.error("❌ Cannot place order - not connected")
                # Fallback to engine if available
                if self.engine:
                    return self.engine.place_order(candidate, size, execution_type='SIMULATED')
                raise RuntimeError("Not connected to IBKR and no engine fallback")
        
        try:
            symbol = getattr(candidate, 'symbol', None)
            side = getattr(candidate, 'side', None)
            entry_price = getattr(candidate, 'entry_price', None)
            stop_loss = getattr(candidate, 'stop_loss', None)
            take_profit = getattr(candidate, 'take_profit', None)
            
            # Create contract
            contract = Stock(symbol, 'SMART', 'USD')
            
            # Qualify contract
            self.ib.qualifyContracts(contract)
            
            # Create order
            action = 'BUY' if side in ('LONG', 'BUY') else 'SELL'
            quantity = int(abs(size))
            
            if entry_price:
                order = LimitOrder(action, quantity, entry_price)
            else:
                order = MarketOrder(action, quantity)
            
            # Place order
            trade = self.ib.placeOrder(contract, order)
            
            # Wait for fill (up to 10 seconds)
            for _ in range(10):
                self.ib.sleep(1)
                if trade.orderStatus.status in ('Filled', 'Cancelled'):
                    break
            
            # Get fill details
            fill_price = trade.orderStatus.avgFillPrice if trade.orderStatus.avgFillPrice > 0 else entry_price
            filled_qty = trade.orderStatus.filled
            
            # Calculate fees (IBKR typically ~$1 per order for small sizes)
            fees = max(1.0, abs(fill_price * filled_qty * self.fee_pct))
            
            order_result = {
                'id': f'IB-{trade.order.orderId}',
                'platform': 'IBKR',
                'mode': 'PAPER' if self.paper_mode else 'LIVE',
                'strategy_id': getattr(candidate, 'strategy_id', None),
                'symbol': symbol,
                'side': side,
                'entry': entry_price,
                'fill_price': fill_price,
                'stop': stop_loss,
                'take_profit': take_profit,
                'size': filled_qty,
                'fees': fees,
                'status': trade.orderStatus.status,
                'execution_type': 'IBKR_PAPER' if self.paper_mode else 'IBKR_LIVE',
                'timestamp': datetime.now().isoformat()
            }
            
            mode_emoji = "🟢" if self.paper_mode else "🔴"
            logger.info(f"{mode_emoji} IBKR order placed: {symbol} {action} {filled_qty} @ ${fill_price:.2f}")
            
            # Also record in engine if available
            if self.engine:
                self.engine.place_order(candidate, filled_qty, execution_type=order_result['execution_type'])
            
            return order_result
        
        except Exception as e:
            logger.error(f"❌ IBKR order failed: {e}")
            
            # Fallback to engine simulation
            if self.engine:
                logger.warning("⚠️  Falling back to engine simulation")
                return self.engine.place_order(candidate, size, execution_type='SIMULATED')
            
            raise
    
    def get_account_summary(self) -> Dict[str, Any]:
        """Get account information."""
        if not self.connected:
            if not self.connect():
                return {}
        
        try:
            account_values = self.ib.accountSummary()
            
            summary = {}
            for av in account_values:
                summary[av.tag] = av.value
            
            return {
                'net_liquidation': float(summary.get('NetLiquidation', 0)),
                'total_cash': float(summary.get('TotalCashValue', 0)),
                'buying_power': float(summary.get('BuyingPower', 0)),
                'mode': 'PAPER' if self.paper_mode else 'LIVE'
            }
        
        except Exception as e:
            logger.error(f"❌ Error getting account summary: {e}")
            return {}
    
    def __del__(self):
        """Cleanup on deletion."""
        if self.connected:
            self.disconnect()


def get_ibkr_connector(paper_mode: bool = True, **kwargs) -> IBKRLiveConnector:
    """Factory function to create IBKR connector."""
    return IBKRLiveConnector(paper_mode=paper_mode, **kwargs)
