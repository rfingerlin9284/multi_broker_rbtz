"""OANDA Adapter - Maps OandaPracticeClient to BrokerConnectorProtocol.

This adapter wraps the existing proven-profitable OANDA connector and exposes
the BrokerConnector Protocol interface required by the supervised broker framework.

NO STRATEGY LOGIC HERE - only API mapping.
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


class OandaAdapter:
    """Adapter mapping OandaPracticeClient → BrokerConnectorProtocol."""
    
    def __init__(self):
        """Initialize OANDA adapter with existing client."""
        from execution.oanda_practice_client import OandaPracticeClient
        
        self.client = OandaPracticeClient()
        self.name = "oanda"
        
        # Store token internally for property access
        self._token = getattr(self.client, 'token', None)
        self.account_id = self.client.account_id  
        self.base_url = self.client.base_url
        self.http = getattr(self.client, 'http', None)
        
        # Mask token in logs
        account_display = self.client.account_id
        logger.info(f"✅ OandaAdapter initialized | account={account_display}")
    
    @property
    def token(self) -> str:
        """RBOTZILLA_TOKEN_COMPAT: Stable token accessor for risk layer.
        
        This property ensures protect_loop and other risk components can always
        access a token string without AttributeError exceptions. It follows a
        fallback chain and returns empty string (never None) if unavailable.
        
        Priority:
        1. Cached token from client during __init__
        2. Live client.token attribute (if still accessible)
        3. Alternative attribute names (api_token, access_token, auth_token, _token)
        4. Environment variables (OANDA_API_TOKEN, OANDA_TOKEN, OANDA_ACCESS_TOKEN)
        5. Empty string (never raises, never returns None)
        
        Returns:
            Token string or empty string (never None, never raises)
        """
        # Priority 1: Cached token from initialization
        if self._token:
            return self._token
        
        # Priority 2: Live client token
        if hasattr(self, 'client') and hasattr(self.client, 'token'):
            tok = getattr(self.client, 'token', None)
            if tok:
                self._token = tok  # Cache for future calls
                return tok
        
        # Priority 3: Alternative attribute names
        for attr in ('api_token', 'access_token', 'auth_token', '_token'):
            if hasattr(self, 'client'):
                tok = getattr(self.client, attr, None)
                if tok:
                    self._token = tok
                    return tok
        
        # Priority 4: Environment variables
        import os
        for env_var in ('OANDA_API_TOKEN', 'OANDA_TOKEN', 'OANDA_ACCESS_TOKEN'):
            tok = os.getenv(env_var)
            if tok:
                self._token = tok
                return tok
        
        # Priority 5: Empty string (fail-safe, never crash)
        logger.warning("OandaAdapter.token unavailable (all fallbacks exhausted)")
        return ""
    
    # ========================================================================
    # BrokerConnectorProtocol Implementation
    # ========================================================================
    
    def health_check(self) -> HealthCheckResult:
        """Check OANDA API connectivity, latency, and OCO capability.
        
        Returns:
            HealthCheckResult with is_healthy=True if all checks pass
        """
        start = time.time()
        errors = []
        
        try:
            # Test 1: Account summary (auth + connectivity)
            summary = self.client.get_account_summary()
            if not summary or 'account' not in summary:
                errors.append("Account summary missing or malformed")
        except Exception as e:
            errors.append(f"Account summary failed: {e}")
        
        try:
            # Test 2: Price fetch (market data connectivity)
            prices = self.client.get_prices(['EUR_USD'])
            if not prices or 'prices' not in prices:
                errors.append("Price fetch returned no data")
        except Exception as e:
            errors.append(f"Price fetch failed: {e}")
        
        latency = (time.time() - start) * 1000  # ms
        
        # Test 3: Verify OCO capability (OANDA native support)
        # No actual test order needed - documented native support
        oco_ready = len(errors) == 0  # If basic connectivity works, OCO works
        
        return HealthCheckResult(
            ok=len(errors) == 0,
            details={'latency_ms': latency, 'oco_capable': oco_ready},
            errors=errors,
            latency_ms=latency,
            oco_capable=oco_ready,
            timestamp=time.time(),  # Unix timestamp as float
        )
    
    def get_prices(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get current bid/ask prices for symbols.
        
        Args:
            symbols: List of OANDA instruments (e.g., ['EUR_USD', 'GBP_USD'])
        
        Returns:
            Dict mapping symbol -> {bid, ask, timestamp, latency_ms}
        """
        start = time.time()
        result = {}
        
        try:
            response = self.client.get_prices(symbols)
            prices_data = response.get('prices', [])
            
            for price_obj in prices_data:
                symbol = price_obj.get('instrument')
                if not symbol:
                    continue
                
                # Extract bid/ask
                bids = price_obj.get('bids', [])
                asks = price_obj.get('asks', [])
                
                bid_price = float(bids[0]['price']) if bids else 0.0
                ask_price = float(asks[0]['price']) if asks else 0.0
                
                result[symbol] = {
                    'bid': bid_price,
                    'ask': ask_price,
                    'mid': (bid_price + ask_price) / 2 if bid_price and ask_price else 0.0,
                    'timestamp': price_obj.get('time', datetime.utcnow().isoformat() + 'Z'),
                    'latency_ms': (time.time() - start) * 1000,
                }
        except Exception as e:
            logger.error(f"get_prices failed: {e}")
            # Return empty result (fail-safe: caller checks for missing symbols)
        
        return result
    
    def get_positions(self) -> List[PositionInfo]:
        """Get open positions from OANDA.
        
        Returns:
            List of PositionInfo objects with normalized structure
        """
        positions = []
        
        try:
            response = self.client.list_open_trades()
            trades = response.get('trades', [])
            
            for trade in trades:
                # Normalize OANDA trade structure to PositionInfo
                position = PositionInfo(
                    broker='oanda',
                    symbol=trade.get('instrument', ''),
                    side='long' if int(trade.get('currentUnits', 0)) > 0 else 'short',
                    quantity=abs(int(trade.get('currentUnits', 0))),
                    entry_price=float(trade.get('price', 0)),
                    current_price=float(trade.get('price', 0)),  # May be stale; updated by protect loop
                    unrealized_pnl=float(trade.get('unrealizedPL', 0)),
                    entry_time=trade.get('openTime', ''),
                    broker_position_id=trade.get('id', ''),
                    stop_loss=float(trade.get('stopLossOrder', {}).get('price', 0)) or None,
                    take_profit=float(trade.get('takeProfitOrder', {}).get('price', 0)) or None,
                )
                positions.append(position)
        except Exception as e:
            logger.error(f"get_positions failed: {e}")
            # Return empty list (fail-safe)
        
        return positions
    
    def place_order(self, order: Dict[str, Any]) -> OrderInfo:
        """Place a simple market order (NO OCO).
        
        WARNING: This should NOT be used for real trading.
        Use place_oco() instead to ensure protective orders.
        
        Args:
            order: Order dict with keys: symbol, side, quantity
        
        Returns:
            OrderInfo with execution details
        """
        raise NotImplementedError(
            "place_order() intentionally not implemented for OANDA. "
            "Use place_oco() to ensure all trades have protective SL/TP."
        )
    
    def place_oco(self, oco: OCOOrder) -> dict[str, Any]:
        """Place OANDA market order with native OCO bracket (SL + TP).
        
        OANDA supports native OCO via stopLossOnFill + takeProfitOnFill.
        This is the ONLY way to place trades via this adapter.
        
        Args:
            oco: OCOOrder with symbol, side, quantity, stop_loss, take_profit
        
        Returns:
            dict with oco_group_id and OrderInfo for entry/TP/SL orders
        
        Raises:
            ValueError: If sl_price or tp_price missing
        """
        if not oco.stop_loss or not oco.take_profit:
            raise ValueError(
                f"OCO requires both stop_loss and take_profit. "
                f"broker=oanda symbol={oco.symbol} sl={oco.stop_loss} tp={oco.take_profit}"
            )
        
        # Determine units (OANDA uses signed units: +100 = long, -100 = short)
        units = oco.quantity if oco.side.lower() == 'long' else -oco.quantity
        
        try:
            # Use native OANDA OCO bracket order
            response = self.client.create_order_market(
                instrument=oco.symbol,
                units=int(units),
                sl_price=oco.stop_loss,
                tp_price=oco.take_profit,
                client_tag=oco.client_tag or f"oco_{int(time.time())}",
            )
            
            # Extract order/fill transaction details
            order_create = response.get('orderCreateTransaction', {})
            order_fill = response.get('orderFillTransaction', {})
            sl_create = response.get('stopLossOrderTransaction', {})
            tp_create = response.get('takeProfitOrderTransaction', {})
            
            order_id = (
                order_create.get('id')
                or order_fill.get('orderID')
                or order_fill.get('id')
                or 'unknown'
            )
            
            # OCO group ID = trade ID (OANDA links SL/TP to trade automatically)
            oco_group_id = (
                order_fill.get('tradeOpened', {}).get('tradeID')
                or order_id
            )
            
            timestamp = datetime.utcnow().isoformat() + 'Z'
            
            # Create entry order info
            entry_order = OrderInfo(
                broker='oanda',
                order_id=order_id,
                oco_group_id=oco_group_id,
                symbol=oco.symbol,
                side=oco.side,
                quantity=oco.quantity,
                order_type='MARKET',
                status='filled',  # OANDA market orders fill immediately or reject
                filled_price=float(order_fill.get('price', 0)) if order_fill else None,
                timestamp=timestamp,
            )
            
            # Create SL order info
            sl_order = OrderInfo(
                broker='oanda',
                order_id=sl_create.get('id', f"{order_id}_sl"),
                oco_group_id=oco_group_id,
                symbol=oco.symbol,
                side='SELL' if oco.side == 'BUY' else 'BUY',  # Opposite side for exit
                quantity=oco.quantity,
                order_type='STOP',
                price=oco.stop_loss,
                status='pending',
                timestamp=timestamp,
            )
            
            # Create TP order info
            tp_order = OrderInfo(
                broker='oanda',
                order_id=tp_create.get('id', f"{order_id}_tp"),
                oco_group_id=oco_group_id,
                symbol=oco.symbol,
                side='SELL' if oco.side == 'BUY' else 'BUY',  # Opposite side for exit
                quantity=oco.quantity,
                order_type='LIMIT',
                price=oco.take_profit,
                status='pending',
                timestamp=timestamp,
            )
            
            logger.info(
                f"✅ OANDA OCO placed: {oco.symbol} {oco.side} "
                f"qty={oco.quantity} sl={oco.stop_loss} tp={oco.take_profit} "
                f"order_id={order_id} oco_group={oco_group_id}"
            )
            
            return {
                "oco_group_id": oco_group_id,
                "entry_order": entry_order,
                "stop_loss_order": sl_order,
                "take_profit_order": tp_order,
            }
        
        except Exception as e:
            logger.error(f"place_oco failed: {e}")
            # Return error response with error OrderInfo
            error_order = OrderInfo(
                broker='oanda',
                order_id='error',
                oco_group_id='error',
                symbol=oco.symbol,
                side=oco.side,
                quantity=oco.quantity,
                order_type='MARKET',
                status='error',
                error=str(e),
                timestamp=datetime.utcnow().isoformat() + 'Z',
            )
            return {
                "oco_group_id": "error",
                "entry_order": error_order,
                "stop_loss_order": error_order,
                "take_profit_order": error_order,
                "error": str(e),
            }
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order.
        
        Note: OANDA market orders fill immediately, so cancellation rarely used.
        For SL/TP modification, use exit_manager instead.
        """
        logger.warning(f"cancel_order not fully implemented for OANDA (order_id={order_id})")
        return False
    
    def cancel_oco(self, oco_group_id: str) -> bool:
        """Cancel OCO group by closing the position.
        
        Args:
            oco_group_id: Trade ID in OANDA (same as position ID)
        
        Returns:
            True if position closed successfully
        """
        try:
            # In OANDA, canceling OCO = closing the trade (which cancels SL/TP automatically)
            # Need to get instrument from trade ID first
            trades_response = self.client.list_open_trades()
            trades = trades_response.get('trades', [])
            
            trade = next((t for t in trades if t.get('id') == oco_group_id), None)
            if not trade:
                logger.error(f"cancel_oco: trade {oco_group_id} not found")
                return False
            
            instrument = trade.get('instrument')
            response = self.client.close_position(instrument)
            
            logger.info(f"✅ OANDA OCO canceled (position closed): {instrument} trade_id={oco_group_id}")
            return True
        
        except Exception as e:
            logger.error(f"cancel_oco failed: {e}")
            return False
    
    def get_open_orders(self) -> List[OrderInfo]:
        """
        Get all open orders (pending orders, not including active positions).
        
        NOTE: OANDA doesn't support traditional "pending orders" - all market
        orders execute immediately. For OANDA, "pending" means protective
        SL/TP orders that are attached to trades, which are accessed via
        get_positions() instead.
        
        Returns:
            Empty list (OANDA-specific behavior)
        """
        # OANDA executes market orders immediately - no "pending" state
        # SL/TP orders are attached to trades, not standalone pending orders
        return []
    
    def close_position(
        self,
        symbol: str,
        quantity: Optional[float] = None,
        reason: str = "manual_close"
    ) -> OrderInfo:
        """
        Close a position (market order).
        
        Args:
            symbol: Symbol/instrument to close (e.g. 'EUR_USD')
            quantity: Optional quantity (None = close entire position)
            reason: Reason for closure (for logging)
        
        Returns:
            OrderInfo for the closing order
        """
        try:
            logger.info(f"close_position: {symbol} quantity={quantity} reason={reason}")
            
            # OANDA close_position closes entire position for instrument
            # If partial close needed, would need to use place order with opposite units
            if quantity is not None:
                logger.warning(f"Partial close requested but OANDA close_position closes entire position")
            
            response = self.client.close_position(symbol)
            
            # Extract order info from response
            long_order = response.get('longOrderFillTransaction', {})
            short_order = response.get('shortOrderFillTransaction', {})
            
            # Use whichever order was filled
            filled_order = long_order if long_order else short_order
            
            if not filled_order:
                # No fill transaction (position might not have existed)
                logger.error(f"close_position: no fill transaction for {symbol}")
                return OrderInfo(
                    order_id='error',
                    symbol=symbol,
                    side='UNKNOWN',
                    quantity=0,
                    order_type='MARKET_CLOSE',
                    status='ERROR',
                    broker='oanda',
                    error=f"No fill transaction returned for {symbol}",
                    timestamp=datetime.utcnow().isoformat() + 'Z'
                )
            
            order_info = OrderInfo(
                order_id=filled_order.get('id', filled_order.get('orderID', 'unknown')),
                symbol=filled_order.get('instrument', symbol),
                side='SELL' if float(filled_order.get('units', 0)) < 0 else 'BUY',
                quantity=abs(float(filled_order.get('units', 0))),
                order_type='MARKET_CLOSE',
                status='FILLED',
                broker='oanda',
                filled_price=float(filled_order.get('price', 0)) if filled_order.get('price') else None,
                timestamp=filled_order.get('time', datetime.utcnow().isoformat() + 'Z'),
                raw=response
            )
            
            logger.info(f"✅ Position closed: {symbol} order_id={order_info.order_id}")
            return order_info
        
        except Exception as e:
            logger.error(f"close_position failed: {e}", exc_info=True)
            return OrderInfo(
                order_id='error',
                symbol=symbol,
                side='UNKNOWN',
                quantity=0,
                order_type='MARKET_CLOSE',
                status='ERROR',
                broker='oanda',
                error=str(e),
                timestamp=datetime.utcnow().isoformat() + 'Z'
            )
