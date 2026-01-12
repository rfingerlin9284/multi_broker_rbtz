"""
OANDA CONNECTOR - ENHANCED FOR MULTI-POSITION DIVERSITY
Unlimited positions (5-10 recommended), strategy diversity, full position management
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import os

logger = logging.getLogger(__name__)

class OANDAConnector:
    """
    OANDA broker connector with unlimited position support.
    Runs multiple diverse strategies simultaneously.
    Full position tracking and management.
    """
    
    def __init__(self, api_key: str = None, account_id: str = None, 
                 paper_mode: bool = True):
        """
        Initialize OANDA connector.
        
        Args:
            api_key: OANDA API key (from env or param)
            account_id: OANDA Account ID (from env or param)
            paper_mode: Use practice account (True) or live (False)
        """
        self.api_key = api_key or os.getenv('OANDA_API_KEY', '')
        self.account_id = account_id or os.getenv('OANDA_ACCOUNT_ID', '')
        self.paper_mode = paper_mode
        
        # Remove max trade limits - support unlimited positions
        self.max_positions = int(os.getenv('OANDA_MAX_POSITIONS', '10'))
        self.min_trade_usd = float(os.getenv('OANDA_MIN_TRADE_USD', '100.0'))
        self.max_trade_usd = float(os.getenv('OANDA_MAX_TRADE_USD', '5000.0'))
        
        # Strategy diversity configuration
        self.strategy_assignment = {
            'trap_reversal': {'brokers': ['oanda'], 'max_positions': 2, 'symbols': ['GBP/USD', 'EUR/GBP']},
            'institutional_sd': {'brokers': ['oanda'], 'max_positions': 2, 'symbols': ['EUR/USD', 'AUD/USD']},
            'holy_grail': {'brokers': ['oanda'], 'max_positions': 2, 'symbols': ['USD/JPY', 'NZD/USD']},
            'ema_scalper': {'brokers': ['oanda'], 'max_positions': 2, 'symbols': ['GBP/JPY']},
            'fabio_aaa': {'brokers': ['oanda'], 'max_positions': 2, 'symbols': ['CAD/JPY']}
        }
        
        self.open_positions: Dict[str, Dict[str, Any]] = {}
        self.price_cache: Dict[str, float] = {}
        
        # Order fill verification tracking
        self._total_filled_orders = 0  # VERIFIED fills only, not placements
        self._filled_orders: Dict[str, Dict] = {}  # Track order ID -> fill details
        self._pending_fills: Dict[str, Dict] = {}  # Track orders awaiting fill confirmation
        
        mode_str = "🟡 PAPER (Practice)" if paper_mode else "🔴 LIVE"
        logger.info(f"🌍 OANDA Connector initialized: {mode_str}")
        logger.info(f"   Account: {account_id}")
        logger.info(f"   Max positions: {self.max_positions} (UNLIMITED - no per-day cap)")
        logger.info(f"   Trade range: ${self.min_trade_usd:.0f} - ${self.max_trade_usd:.0f}")
        logger.info(f"   Strategy diversity: 5 strategies across {self.max_positions} positions")
    
    def get_live_positions(self) -> List[Dict[str, Any]]:
        """
        Fetch all live positions from OANDA.
        
        Returns:
            List of open position dictionaries
        """
        if not self.api_key or not self.account_id:
            logger.warning("❌ OANDA credentials not configured")
            return []
        
        try:
            # Call OANDA v20 API to get positions
            import requests
            
            base_url = f"https://{'stream-' if self.paper_mode else ''}api-fxpractice.oanda.com" \
                      if self.paper_mode else "https://stream-api-fxtrade.oanda.com"
            
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'AcceptDatetimeFormat': 'UNIX'
            }
            
            response = requests.get(
                f"{base_url}/v3/accounts/{self.account_id}/positions",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                positions = data.get('positions', [])
                
                logger.info(f"✅ Synced {len(positions)} positions from OANDA")
                
                for pos in positions:
                    self.open_positions[pos['instrument']] = {
                        'instrument': pos['instrument'],
                        'long': pos.get('long', {}),
                        'short': pos.get('short', {}),
                        'units': pos.get('long', {}).get('units', 0) + pos.get('short', {}).get('units', 0)
                    }
                
                return positions
            else:
                logger.warning(f"⚠️  OANDA API error: {response.status_code}")
                return []
        
        except Exception as e:
            logger.warning(f"⚠️  Error fetching OANDA positions: {e}")
            return []
    
    def place_order(self, symbol: str, side: str, size: float, 
                   entry_price: float, stop_loss: float = None,
                   take_profit: float = None, strategy: str = None) -> Dict[str, Any]:
        """
        Place order on OANDA with unlimited position support.
        
        Args:
            symbol: Instrument (EUR/USD, GBP/USD, etc)
            side: BUY or SELL
            size: Position size in units
            entry_price: Current price
            stop_loss: Optional stop loss price
            take_profit: Optional take profit price
            strategy: Strategy name for diversity tracking
        
        Returns:
            Order result
        """
        if not self.api_key or not self.account_id:
            logger.error("❌ OANDA credentials not configured")
            return {'success': False, 'error': 'No credentials'}
        
        # Check position limit
        if len(self.open_positions) >= self.max_positions:
            logger.warning(f"⚠️  Position limit reached ({self.max_positions})")
            return {'success': False, 'error': f'Max {self.max_positions} positions reached'}
        
        # Check trade size
        notional = size * entry_price
        if notional < self.min_trade_usd or notional > self.max_trade_usd:
            logger.warning(f"⚠️  Trade size out of range: ${notional:.0f}")
            return {'success': False, 'error': f'Trade size ${notional:.0f} out of range'}
        
        try:
            import requests
            import json
            
            base_url = f"https://{'api-fxpractice' if self.paper_mode else 'api-fxtrade'}.oanda.com"
            
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
                'AcceptDatetimeFormat': 'UNIX'
            }
            
            order_spec = {
                'order': {
                    'type': 'MARKET',
                    'instrument': symbol,
                    'units': str(int(size)) if side == 'BUY' else str(-int(size)),
                    'timeInForce': 'FOK',
                    'takeProfitOnFill': {'price': str(take_profit)} if take_profit else None,
                    'stopLossOnFill': {'price': str(stop_loss)} if stop_loss else None
                }
            }
            
            # Remove None values
            if not order_spec['order']['takeProfitOnFill']:
                del order_spec['order']['takeProfitOnFill']
            if not order_spec['order']['stopLossOnFill']:
                del order_spec['order']['stopLossOnFill']
            
            response = requests.post(
                f"{base_url}/v3/accounts/{self.account_id}/orders",
                headers=headers,
                json=order_spec,
                timeout=10
            )
            
            if response.status_code in (200, 201):
                data = response.json()
                order_id = data.get('orderFillTransaction', {}).get('id')
                
                logger.info(f"✅ OANDA order placed: {symbol} {side} {size}u")
                logger.info(f"   Order ID: {order_id}")
                logger.info(f"   Strategy: {strategy}")
                
                # Track position
                self.open_positions[symbol] = {
                    'instrument': symbol,
                    'side': side,
                    'units': size if side == 'BUY' else -size,
                    'entry_price': entry_price,
                    'order_id': order_id,
                    'strategy': strategy,
                    'opened_time': datetime.now().isoformat()
                }
                
                return {
                    'success': True,
                    'order_id': order_id,
                    'symbol': symbol,
                    'side': side,
                    'size': size
                }
            else:
                logger.error(f"❌ OANDA API error: {response.status_code} {response.text[:200]}")
                return {'success': False, 'error': f'API error {response.status_code}'}
        
        except Exception as e:
            logger.error(f"❌ Error placing OANDA order: {e}")
            return {'success': False, 'error': str(e)}
    
    def close_position(self, symbol: str, units: int = None) -> Dict[str, Any]:
        """
        Close position on OANDA.
        
        Args:
            symbol: Instrument to close
            units: Specific units to close (all if None)
        
        Returns:
            Close result
        """
        try:
            import requests
            
            if symbol not in self.open_positions:
                logger.warning(f"⚠️  Position not found: {symbol}")
                return {'success': False, 'error': 'Position not found'}
            
            base_url = f"https://{'api-fxpractice' if self.paper_mode else 'api-fxtrade'}.oanda.com"
            
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            # Get current position size
            position = self.open_positions[symbol]
            close_units = units or abs(position.get('units', 0))
            
            order_spec = {
                'order': {
                    'type': 'MARKET',
                    'instrument': symbol,
                    'units': str(-close_units) if position.get('units', 0) > 0 else str(close_units),
                    'timeInForce': 'FOK'
                }
            }
            
            response = requests.post(
                f"{base_url}/v3/accounts/{self.account_id}/orders",
                headers=headers,
                json=order_spec,
                timeout=10
            )
            
            if response.status_code in (200, 201):
                logger.info(f"✅ Position closed: {symbol}")
                
                # Remove from tracking
                if symbol in self.open_positions:
                    del self.open_positions[symbol]
                
                return {'success': True, 'symbol': symbol}
            else:
                logger.error(f"❌ OANDA close failed: {response.status_code}")
                return {'success': False, 'error': f'Close failed: {response.status_code}'}
        
        except Exception as e:
            logger.error(f"❌ Error closing OANDA position: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for symbol."""
        return self.price_cache.get(symbol)
    
    def update_price(self, symbol: str, price: float):
        """Update price cache."""
        self.price_cache[symbol] = price
    
    def get_open_positions(self) -> List[Dict[str, Any]]:
        """Get all open positions."""
        return list(self.open_positions.values())
    
    def print_position_summary(self):
        """Print OANDA position summary."""
        logger.info("")
        logger.info("="*70)
        logger.info("🌍 OANDA POSITIONS")
        logger.info("="*70)
        
        if not self.open_positions:
            logger.info("No open positions")
        else:
            logger.info(f"Open: {len(self.open_positions)}/{self.max_positions}")
            for symbol, pos in self.open_positions.items():
                logger.info(f"  {symbol:10} | Strategy: {pos.get('strategy', 'N/A'):15} | Units: {pos.get('units', 0)}")
        
        logger.info("="*70)
        logger.info("")
    
    def verify_order_filled(self, order_id: str) -> bool:
        """Verify that an order is actually FILLED at OANDA.
        
        Returns:
            True if order is confirmed filled
            False if order is pending or failed
        """
        if not self.api_key or not self.account_id:
            # Paper mode - verify from pending fills
            if order_id in self._pending_fills:
                self._filled_orders[order_id] = self._pending_fills.pop(order_id)
                self._total_filled_orders += 1
                logger.info(f"✅ OANDA ORDER VERIFIED FILLED: {order_id} (Total fills: {self._total_filled_orders})")
                return True
            return False
        
        # Live mode - query OANDA for fill status
        try:
            import requests
            
            base_url = "https://stream-sandbox-v20.oanda.com" if self.paper_mode else "https://stream-v20.oanda.com"
            headers = {'Authorization': f'Bearer {self.api_key}'}
            
            response = requests.get(
                f"{base_url}/v3/accounts/{self.account_id}/orders/{order_id}",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                order_data = response.json().get('order', {})
                state = order_data.get('state', '').upper()
                
                if state == 'FILLED':
                    self._filled_orders[order_id] = {
                        'order_id': order_id,
                        'status': state,
                        'filled_qty': order_data.get('units'),
                        'filled_price': order_data.get('filledPrice'),
                        'timestamp': datetime.now().isoformat()
                    }
                    if order_id in self._pending_fills:
                        del self._pending_fills[order_id]
                    self._total_filled_orders += 1
                    logger.info(f"✅ OANDA ORDER VERIFIED FILLED: {order_id} (Total fills: {self._total_filled_orders})")
                    return True
                else:
                    logger.warning(f"⏳ OANDA order {order_id} state: {state}")
                    return False
            else:
                logger.error(f"❌ Failed to verify OANDA order {order_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ OANDA verification error: {e}")
            return False
    
    def get_filled_orders_count(self) -> int:
        """Get count of VERIFIED filled orders."""
        return self._total_filled_orders
    
    def get_filled_orders(self) -> dict:
        """Get all verified filled orders."""
        return self._filled_orders.copy()
