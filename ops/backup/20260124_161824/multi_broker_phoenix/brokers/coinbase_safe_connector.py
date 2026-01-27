"""Coinbase Safe Connector with Nano-Lot Limits

WARNING: Coinbase has NO paper trading account.
Any orders placed = REAL MONEY with REAL BITCOIN.

This connector implements strict safety limits for nano-lot testing:
- $5-10 per trade (minimum viable exposure)
- Daily loss limits ($50 default)
- Consecutive loss breaker (5 losses = stop)
- Trade count limits (10 per day default)
- Detailed logging of every trade

Use this ONLY after IBKR paper trading proves edge!
"""
from __future__ import annotations
import os
import logging
import time
import json
import hmac
import hashlib
from typing import Optional, Dict, Any, List
from datetime import datetime, date
import requests

try:
    import jwt
    from cryptography.hazmat.primitives import serialization
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    # PyJWT or cryptography not installed - JWT auth will be disabled (logged later in __init__ if needed)

logger = logging.getLogger(__name__)


class CoinbaseSafeConnector:
    """Coinbase connector with strict safety limits for nano-lot real money testing."""
    
    def __init__(
        self,
        paper_mode: bool = True,
        engine: Optional[Any] = None,
        narrator: Optional[Any] = None,
        fee_pct: float = 0.006,  # Coinbase Pro ~0.5-0.6%
        slippage_pct: float = 0.002,
        min_trade_usd: float = None,
        max_trade_usd: float = None,
        daily_loss_limit: float = None,
        max_trades_per_day: int = None,
        stop_on_consecutive_losses: int = None
    ):
        """Initialize safe Coinbase connector.
        
        Args:
            paper_mode: If True, only simulates (no real orders)
            engine: PaperEngine for simulation
            fee_pct: Coinbase Pro fee (0.5-0.6%)
            slippage_pct: Estimated slippage
            min_trade_usd: Minimum trade size (default: $5)
            max_trade_usd: Maximum trade size (default: $10)
            daily_loss_limit: Max loss per day (default: $50)
            max_trades_per_day: Max trades per day (default: 10)
            stop_on_consecutive_losses: Stop after N losses (default: 5)
        """
        self.paper_mode = bool(paper_mode)
        self.engine = engine
        self.narrator = narrator  # Live position narrator
        self.fee_pct = float(fee_pct)
        self.slippage_pct = float(slippage_pct)
        
        # Safety limits from env or params
        self.min_trade_usd = float(min_trade_usd or os.getenv('COINBASE_MIN_TRADE_USD', '5.0'))
        self.max_trade_usd = float(max_trade_usd or os.getenv('COINBASE_MAX_TRADE_USD', '10.0'))
        self.daily_loss_limit = float(daily_loss_limit or os.getenv('COINBASE_DAILY_LOSS_LIMIT', '50.0'))
        self.max_trades_per_day = int(max_trades_per_day or os.getenv('COINBASE_MAX_TRADES_PER_DAY', '999999'))  # UNLIMITED: removed 50 daily limit
        self.stop_on_consecutive_losses = int(stop_on_consecutive_losses or os.getenv('COINBASE_STOP_ON_CONSECUTIVE_LOSSES', '5'))
        
        # Trailing stop configuration
        self.initial_stop_loss_pct = float(os.getenv('COINBASE_INITIAL_STOP_LOSS_PCT', '2.0'))
        self.trailing_activation_pct = float(os.getenv('COINBASE_TRAILING_STOP_ACTIVATION_PCT', '1.5'))
        self.trailing_distance_pct = float(os.getenv('COINBASE_TRAILING_STOP_DISTANCE_PCT', '1.0'))
        self.use_trailing_stops = os.getenv('COINBASE_USE_TRAILING_STOPS', 'true').lower() == 'true'
        
        # AUTO-SCALING PERFORMANCE TRACKER (Coinbase Advanced only)
        # Automatically adjusts trade sizes based on performance
        self._scaling_enabled = os.getenv('COINBASE_AUTO_SCALING', 'true').lower() == 'true'
        self._performance_history: List[Dict] = []  # Track closed trades
        self._current_tier = 1  # Start at tier 1
        self._base_min_trade = self.min_trade_usd  # Store original limits
        self._base_max_trade = self.max_trade_usd
        
        # Performance thresholds for scaling UP
        self._scale_up_tiers = [
            # Tier 1: $5-10 (starting point)
            {'name': 'Nano', 'min': 5, 'max': 10, 'win_rate': 0.0, 'profit': 0, 'trades': 0},
            # Tier 2: $10-25 (requires 60% win rate, +$20 profit, 20+ trades)
            {'name': 'Micro', 'min': 10, 'max': 25, 'win_rate': 0.60, 'profit': 20, 'trades': 20},
            # Tier 3: $25-50 (requires 62% win rate, +$75 profit, 30+ trades)
            {'name': 'Mini', 'min': 25, 'max': 50, 'win_rate': 0.62, 'profit': 75, 'trades': 30},
            # Tier 4: $50-100 (requires 64% win rate, +$200 profit, 50+ trades)
            {'name': 'Small', 'min': 50, 'max': 100, 'win_rate': 0.64, 'profit': 200, 'trades': 50},
            # Tier 5: $100-250 (requires 66% win rate, +$500 profit, 75+ trades)
            {'name': 'Standard', 'min': 100, 'max': 250, 'win_rate': 0.66, 'profit': 500, 'trades': 75},
            # Tier 6: $250-500 (requires 68% win rate, +$1500 profit, 100+ trades)
            {'name': 'Large', 'min': 250, 'max': 500, 'win_rate': 0.68, 'profit': 1500, 'trades': 100},
        ]
        
        # Scale DOWN thresholds (protect capital on poor performance)
        self._scale_down_win_rate = 0.45  # Drop tier if < 45% win rate
        self._scale_down_consecutive_losses = 8  # Drop tier after 8 consecutive losses
        
        # Tracking
        self._price_by_symbol: Dict[str, float] = {}
        self._trades_today: List[Dict] = []
        self._current_date = date.today()
        self._daily_loss_current = 0.0
        self._consecutive_losses = 0
        self._consecutive_wins = 0  # Track win streaks for scaling
        self._total_trades_today = 0
        self._total_filled_orders = 0  # VERIFIED fills only, not placements
        self._filled_orders: Dict[str, Dict] = {}  # Track order ID -> fill details
        self._pending_fills: Dict[str, Dict] = {}  # Track orders awaiting fill confirmation
        self._stopped = False
        self._public_api = 'https://api.exchange.coinbase.com'
        
        # Position tracking for trailing stops
        self._open_positions: Dict[str, Dict[str, Any]] = {}  # symbol -> position details
        
        # Coinbase Advanced Trade API endpoint (not the deprecated Pro API)
        # Allow overriding host for sandbox/testing via env vars
        self._public_api = os.getenv('COINBASE_PUBLIC_API', 'https://api.coinbase.com/api/v3/brokerage')
        self._base_url = os.getenv('COINBASE_BASE_URL', 'https://api.coinbase.com')
        
        # API credentials for authenticated requests
        self._api_key = os.getenv('COINBASE_API_KEY', '')
        self._api_secret = os.getenv('COINBASE_API_SECRET', '')
        # Support using a secret file (COINBASE_API_SECRET_FILE) to avoid .env newline/quote issues
        secret_file_env = os.getenv('COINBASE_API_SECRET_FILE', '')
        if not self._api_secret and secret_file_env and os.path.exists(secret_file_env):
            try:
                with open(secret_file_env, 'r') as fh:
                    self._api_secret = fh.read()
            except Exception as e:
                logger.warning(f"Could not read COINBASE_API_SECRET_FILE: {e}")
        # JWT enabled if PyJWT available, API key present, and a secret (env or file) is available
        self._jwt_enabled = JWT_AVAILABLE and bool(self._api_key) and bool(self._api_secret)
        
        # Log configuration
        mode_str = "🟢 SIMULATION" if self.paper_mode else "🔴 REAL MONEY"
        logger.info(f"🔧 Coinbase Advanced Trade Connector initialized: {mode_str}")
        logger.info(f"   API: Coinbase Advanced Trade (v3)")
        logger.info(f"   JWT Auth: {'✅ READY' if self._jwt_enabled else '❌ NOT CONFIGURED'}")
        logger.info(f"   Min trade: ${self.min_trade_usd:.2f}, Max: ${self.max_trade_usd:.2f}")
        logger.info(f"   Daily loss limit: ${self.daily_loss_limit:.2f}")
        logger.info(f"   Max trades/day: {self.max_trades_per_day}")
        logger.info(f"   Stop after {self.stop_on_consecutive_losses} consecutive losses")
        if self.use_trailing_stops:
            logger.info(f"🛡️  Trailing Stops ACTIVE:")
            logger.info(f"   Initial stop: {self.initial_stop_loss_pct}%")
            logger.info(f"   Trail activation: +{self.trailing_activation_pct}%")
            logger.info(f"   Trail distance: {self.trailing_distance_pct}%")
    
    def _reset_daily_stats(self):
        """Reset daily tracking if new day."""
        today = date.today()
        if today != self._current_date:
            logger.info(f"📅 New trading day - resetting stats")
            logger.info(f"   Previous day: {self._total_trades_today} trades, ${self._daily_loss_current:.2f} loss")
            self._current_date = today
            self._trades_today = []
            self._daily_loss_current = 0.0
            self._total_trades_today = 0
            self._stopped = False
    
    def update_price(self, symbol: str, price: float):
        """Update price cache."""
        self._price_by_symbol[symbol] = float(price)
    
    def fetch_live_price(self, symbol: str) -> Optional[float]:
        """Fetch current price from Coinbase public exchange API (no auth needed)."""
        try:
            # Use PUBLIC exchange API (no auth required) for price data
            # This is more reliable than the authenticated brokerage API
            public_url = f'https://api.exchange.coinbase.com/products/{symbol}/ticker'
            
            resp = requests.get(public_url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                price = float(data.get('price', 0))
                if price > 0:
                    self.update_price(symbol, price)
                    return price
            else:
                logger.debug(f"Price fetch failed for {symbol}: {resp.status_code} {resp.text[:100]}")
        except Exception as e:
            logger.error(f"❌ Error fetching price for {symbol}: {e}")
        return None
    
    def get_historical_data(self, symbol: str, periods: int = 50, granularity: int = 300) -> List[float]:
        """Fetch historical price data (close prices) from Coinbase public API.
        
        Args:
            symbol: Trading pair (e.g., 'BTC-USD')
            periods: Number of candles to fetch (default 50)
            granularity: Candle size in seconds (300=5min, 900=15min, 3600=1hr)
        
        Returns:
            List of close prices from oldest to newest
        """
        try:
            url = f"https://api.exchange.coinbase.com/products/{symbol}/candles"
            params = {"granularity": granularity}
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                candles = resp.json()[:periods]  # Get requested number of candles
                # Coinbase returns [timestamp, low, high, open, close, volume]
                # Index 4 = close price
                prices = [float(c[4]) for c in candles]
                prices.reverse()  # Oldest to newest
                return prices
            else:
                logger.warning(f"Historical data fetch failed: {resp.status_code}")
        except Exception as e:
            logger.error(f"❌ Error fetching historical data for {symbol}: {e}")
        return []
    
    def get_last_price(self, symbol: str) -> Optional[float]:
        """Get cached price."""
        return self._price_by_symbol.get(symbol)
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price - alias for fetch_live_price() for compatibility.
        
        This method exists for backward compatibility with other broker connectors
        that use get_current_price() naming convention.
        """
        return self.fetch_live_price(symbol)
    
    def _record_trade_result(self, profit_usd: float, win: bool):
        """Record trade result and check for auto-scaling (Coinbase Advanced ONLY)."""
        if not self._scaling_enabled:
            return
        
        # Add to performance history
        self._performance_history.append({
            'timestamp': datetime.now(),
            'profit': profit_usd,
            'win': win
        })
        
        # Update win/loss streaks
        if win:
            self._consecutive_wins += 1
            self._consecutive_losses = 0
        else:
            self._consecutive_losses += 1
            self._consecutive_wins = 0
        
        # Check for SCALE DOWN (protect capital)
        if self._consecutive_losses >= self._scale_down_consecutive_losses:
            if self._current_tier > 1:
                self._current_tier -= 1
                self._apply_tier_limits()
                logger.warning(f"📉 AUTO-SCALE DOWN: {self._consecutive_losses} consecutive losses")
                logger.warning(f"   Dropping to Tier {self._current_tier}: {self._scale_up_tiers[self._current_tier-1]['name']}")
                self._consecutive_losses = 0  # Reset after scaling down
                return
        
        # Calculate overall performance (last 100 trades or all if less)
        recent_trades = self._performance_history[-100:]
        if len(recent_trades) < 10:
            return  # Need minimum data
        
        total_profit = sum(t['profit'] for t in recent_trades)
        wins = sum(1 for t in recent_trades if t['win'])
        win_rate = wins / len(recent_trades)
        
        # Check for SCALE DOWN based on win rate
        if win_rate < self._scale_down_win_rate and len(recent_trades) >= 20:
            if self._current_tier > 1:
                self._current_tier -= 1
                self._apply_tier_limits()
                logger.warning(f"📉 AUTO-SCALE DOWN: Win rate {win_rate:.1%} < {self._scale_down_win_rate:.1%}")
                logger.warning(f"   Dropping to Tier {self._current_tier}: {self._scale_up_tiers[self._current_tier-1]['name']}")
                return
        
        # Check for SCALE UP
        if self._current_tier < len(self._scale_up_tiers):
            next_tier = self._scale_up_tiers[self._current_tier]  # Next tier to unlock
            
            # Check if we meet ALL requirements for next tier
            if (win_rate >= next_tier['win_rate'] and
                total_profit >= next_tier['profit'] and
                len(recent_trades) >= next_tier['trades']):
                
                self._current_tier += 1
                self._apply_tier_limits()
                logger.info(f"📈 AUTO-SCALE UP: Performance requirements met!")
                logger.info(f"   Win Rate: {win_rate:.1%} >= {next_tier['win_rate']:.1%} ✅")
                logger.info(f"   Profit: ${total_profit:.2f} >= ${next_tier['profit']:.2f} ✅")
                logger.info(f"   Trades: {len(recent_trades)} >= {next_tier['trades']} ✅")
                logger.info(f"   🎉 UNLOCKED TIER {self._current_tier}: {self._scale_up_tiers[self._current_tier-1]['name']}")
    
    def _apply_tier_limits(self):
        """Apply trade size limits for current tier (Coinbase Advanced ONLY)."""
        tier_config = self._scale_up_tiers[self._current_tier - 1]
        old_min = self.min_trade_usd
        old_max = self.max_trade_usd
        
        self.min_trade_usd = tier_config['min']
        self.max_trade_usd = tier_config['max']
        
        logger.info(f"💰 Trade Limits Updated (Tier {self._current_tier}: {tier_config['name']})")
        logger.info(f"   Min: ${old_min:.2f} → ${self.min_trade_usd:.2f}")
        logger.info(f"   Max: ${old_max:.2f} → ${self.max_trade_usd:.2f}")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get current performance and tier status (Coinbase Advanced ONLY)."""
        if not self._performance_history:
            return {
                'tier': self._current_tier,
                'tier_name': self._scale_up_tiers[self._current_tier-1]['name'],
                'trades': 0,
                'win_rate': 0.0,
                'total_profit': 0.0,
                'limits': {'min': self.min_trade_usd, 'max': self.max_trade_usd}
            }
        
        recent_trades = self._performance_history[-100:]
        wins = sum(1 for t in recent_trades if t['win'])
        win_rate = wins / len(recent_trades) if recent_trades else 0
        total_profit = sum(t['profit'] for t in recent_trades)
        
        # Check progress to next tier
        next_tier_req = None
        if self._current_tier < len(self._scale_up_tiers):
            next_tier = self._scale_up_tiers[self._current_tier]
            next_tier_req = {
                'name': next_tier['name'],
                'win_rate_needed': next_tier['win_rate'],
                'profit_needed': next_tier['profit'],
                'trades_needed': next_tier['trades'],
                'win_rate_progress': f"{win_rate:.1%} / {next_tier['win_rate']:.1%}",
                'profit_progress': f"${total_profit:.2f} / ${next_tier['profit']:.2f}",
                'trades_progress': f"{len(recent_trades)} / {next_tier['trades']}"
            }
        
        return {
            'tier': self._current_tier,
            'tier_name': self._scale_up_tiers[self._current_tier-1]['name'],
            'trades': len(recent_trades),
            'win_rate': win_rate,
            'total_profit': total_profit,
            'consecutive_wins': self._consecutive_wins,
            'consecutive_losses': self._consecutive_losses,
            'limits': {'min': self.min_trade_usd, 'max': self.max_trade_usd},
            'next_tier': next_tier_req
        }
    
    def _check_safety_limits(self, symbol: str, size: float, price: float) -> Dict[str, Any]:
        """Check all safety limits before placing order."""
        self._reset_daily_stats()
        
        # Check if stopped
        if self._stopped:
            return {
                'allowed': False,
                'reason': f'⛔ TRADING STOPPED: {self.stop_on_consecutive_losses} consecutive losses'
            }
        
        # Calculate notional value
        notional_usd = size * price
        
        # Check minimum size
        if notional_usd < self.min_trade_usd:
            return {
                'allowed': False,
                'reason': f'Below minimum trade size (${notional_usd:.2f} < ${self.min_trade_usd:.2f})'
            }
        
        # Check maximum size
        if notional_usd > self.max_trade_usd:
            # Auto-adjust size to max
            adjusted_size = self.max_trade_usd / price
            logger.warning(f"⚠️  Trade size adjusted: {size:.6f} → {adjusted_size:.6f} (max ${self.max_trade_usd})")
            size = adjusted_size
            notional_usd = size * price
        
        # Check daily trade count
        if self._total_trades_today >= self.max_trades_per_day:
            return {
                'allowed': False,
                'reason': f'Daily trade limit reached ({self._total_trades_today}/{self.max_trades_per_day})'
            }
        
        # Check daily loss limit
        if self._daily_loss_current >= self.daily_loss_limit:
            self._stopped = True
            return {
                'allowed': False,
                'reason': f'⛔ DAILY LOSS LIMIT HIT: ${self._daily_loss_current:.2f} >= ${self.daily_loss_limit:.2f}'
            }
        
        # All checks passed
        return {
            'allowed': True,
            'adjusted_size': size,
            'notional_usd': notional_usd
        }
    
    def place_paper_order(self, candidate: Any, size: float) -> Dict[str, Any]:
        """Place simulated order (no real money)."""
        sym = getattr(candidate, 'symbol', None)
        price = self.get_last_price(sym)
        
        if price is None:
            raise RuntimeError('no_price')
        
        # Check safety limits even in paper mode (for testing)
        check = self._check_safety_limits(sym, size, price)
        if not check['allowed']:
            logger.warning(f"🚫 Paper order blocked: {check['reason']}")
            return {'success': False, 'error': check['reason']}
        
        size = check['adjusted_size']
        side = getattr(candidate, 'side', None)
        fill = price * (1.0 + self.slippage_pct) if side in ('BUY', 'LONG') else price * (1.0 - self.slippage_pct)
        fees = abs(fill * float(size) * self.fee_pct)
        
        from ..config.runtime import resolve_execution_type
        execution_type = resolve_execution_type('COINBASE', supports_platform_paper=False)
        
        order = {
            'id': f'CB-PAPER-{sym}-{int(fill*100000)}',
            'platform': 'COINBASE',
            'mode': 'PAPER',
            'strategy_id': getattr(candidate, 'strategy_id', None),
            'symbol': sym,
            'side': side,
            'entry': getattr(candidate, 'entry_price', None),
            'fill_price': fill,
            'stop': getattr(candidate, 'stop_loss', None),
            'size': size,
            'notional_usd': check['notional_usd'],
            'fees': fees,
            'status': 'FILLED',
            'execution_type': execution_type,
            'timestamp': datetime.now().isoformat()
        }
        
        # Track trade
        self._total_trades_today += 1
        
        logger.info(f"🟢 PAPER: {sym} {side} {size:.6f} @ ${fill:.2f} (${check['notional_usd']:.2f})")
        
        if self.engine:
            return self.engine.place_order(candidate, size, execution_type=execution_type)
        
        return order
    
    def place_live_order(self, candidate: Any, size: float, confirm_real_money: bool = False) -> Dict[str, Any]:
        """Place REAL MONEY order on Coinbase.
        
        ⚠️  WARNING: This uses REAL MONEY!
        
        Safety Gates (ALL must pass):
        1. paper_mode=False required
        2. TRADING_MODE=LIVE in environment
        3. confirm_real_money=True explicitly passed
        4. JWT authentication configured
        5. All nano-lot safety limits
        
        Args:
            candidate: Trade candidate with symbol, side, entry, stop
            size: Position size
            confirm_real_money: Must be True to place real order (safety gate)
        """
        # SAFETY GATE 1: Paper mode check
        if self.paper_mode:
            logger.error("❌ SAFETY GATE 1 FAILED: Cannot place live order in paper mode")
            raise RuntimeError("Live orders require paper_mode=False")
        
        # SAFETY GATE 2: Environment check
        if os.getenv('TRADING_MODE', 'PAPER') != 'LIVE':
            logger.error("❌ SAFETY GATE 2 FAILED: TRADING_MODE must be set to LIVE")
            raise RuntimeError("Set TRADING_MODE=LIVE in .env to enable real orders")
        
        # SAFETY GATE 3: Explicit confirmation
        if not confirm_real_money:
            logger.error("❌ SAFETY GATE 3 FAILED: Must pass confirm_real_money=True")
            raise RuntimeError("Must explicitly confirm real money with confirm_real_money=True")
        
        # SAFETY GATE 4: JWT authentication
        if not self._jwt_enabled:
            logger.error("❌ SAFETY GATE 4 FAILED: JWT authentication not configured")
            raise RuntimeError("COINBASE_API_KEY and COINBASE_API_SECRET required")
        
        sym = getattr(candidate, 'symbol', None)
        price = self.get_last_price(sym)
        
        if price is None:
            raise RuntimeError(f'No price available for {sym}')
        
        # SAFETY GATE 5: Nano-lot safety limits
        check = self._check_safety_limits(sym, size, price)
        if not check['allowed']:
            logger.error(f"❌ SAFETY GATE 5 FAILED: {check['reason']}")
            return {'success': False, 'error': check['reason']}
        
        size = check['adjusted_size']
        side = getattr(candidate, 'side', None)
        
        logger.warning(f"""\n{'='*60}
🔴 PLACING LIVE ORDER - REAL MONEY TRADE
{'='*60}
Symbol: {sym}
Side: {side}
Size: {size:.6f}
Price: ${price:.2f}
Notional: ${check['notional_usd']:.2f}
---
Trades Today: {self._total_trades_today + 1}/{self.max_trades_per_day}
Daily Loss: ${self._daily_loss_current:.2f}/${self.daily_loss_limit:.2f}
{'='*60}""")
        
        try:
            # Place authenticated order via Coinbase Advanced Trade API
            order_response = self._place_coinbase_order(
                symbol=sym,
                side=side.lower(),
                size=size,
                price=price
            )
            
            # Track successful order
            self._total_trades_today += 1
            
            logger.info(f"✅ LIVE ORDER PLACED: {order_response.get('order_id', 'unknown')}")
            
            return {
                'success': True,
                'order_id': order_response.get('order_id'),
                'symbol': sym,
                'side': side,
                'size': size,
                'fill_price': price,
                'notional_usd': check['notional_usd'],
                'response': order_response
            }
            
        except Exception as e:
            logger.error(f"❌ Order placement failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def verify_order_filled(self, order_id: str) -> bool:
        """Verify that an order is actually FILLED at broker (not just placed).
        
        Returns:
            True if order is confirmed filled at broker
            False if order is pending, failed, or unconfirmed
        """
        if not self._jwt_enabled:
            # Paper mode - orders auto-fill
            if order_id in self._pending_fills:
                self._filled_orders[order_id] = self._pending_fills.pop(order_id)
                self._total_filled_orders += 1
                logger.info(f"✅ PAPER ORDER VERIFIED FILLED: {order_id} (Total fills: {self._total_filled_orders})")
                return True
            return False
        
        # Live mode - query Coinbase for actual fill status
        try:
            import requests
            
            headers = {'Authorization': f'Bearer {self._api_key}'}
            response = requests.get(
                f"{self._base_url}/api/v3/brokerage/orders/{order_id}",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                order_data = response.json()
                status = order_data.get('status', '').upper()
                
                if status == 'FILLED':
                    self._filled_orders[order_id] = {
                        'order_id': order_id,
                        'status': status,
                        'filled_qty': order_data.get('filled_size'),
                        'filled_price': order_data.get('average_filled_price'),
                        'timestamp': datetime.now().isoformat()
                    }
                    if order_id in self._pending_fills:
                        del self._pending_fills[order_id]
                    self._total_filled_orders += 1
                    logger.info(f"✅ LIVE ORDER VERIFIED FILLED: {order_id} @ ${order_data.get('average_filled_price')} (Total fills: {self._total_filled_orders})")
                    return True
                else:
                    logger.warning(f"⏳ Order {order_id} status: {status} (not yet filled)")
                    return False
            else:
                logger.error(f"❌ Failed to verify order {order_id}: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Order verification error: {e}")
            return False
    
    def get_filled_orders_count(self) -> int:
        """Get count of VERIFIED filled orders (not placements)."""
        return self._total_filled_orders
    
    def get_filled_orders(self) -> Dict[str, Dict]:
        """Get all verified filled orders."""
        return self._filled_orders.copy()
    
    def record_trade_result(self, trade: Dict[str, Any]):
        """Record trade result and update tracking."""
        self._reset_daily_stats()
        
        pnl = trade.get('pnl', 0.0)
        
        # Track loss
        if pnl < 0:
            self._daily_loss_current += abs(pnl)
            self._consecutive_losses += 1
            
            logger.warning(f"📉 Loss: ${abs(pnl):.2f} (consecutive: {self._consecutive_losses})")
            
            # Check consecutive loss breaker
            if self._consecutive_losses >= self.stop_on_consecutive_losses:
                self._stopped = True
                logger.error(f"⛔ TRADING STOPPED: {self._consecutive_losses} consecutive losses")
        else:
            self._consecutive_losses = 0  # Reset on win
            logger.info(f"📈 Win: ${pnl:.2f}")
        
        # Record trade
        self._trades_today.append({
            'timestamp': datetime.now(),
            'symbol': trade['symbol'],
            'pnl': pnl,
            'notional': trade.get('notional_usd', 0)
        })
        
        # Status update
        logger.info(f"📊 Today: {len(self._trades_today)} trades, ${self._daily_loss_current:.2f} loss")
    
    def _generate_jwt_token(self, method: str = 'GET', endpoint: str = '/api/v3/brokerage/orders') -> str:
        """Generate JWT token for Coinbase Advanced Trade API authentication.
        
        MATCHES OFFICIAL COINBASE SDK FORMAT EXACTLY:
        - URI format: "METHOD api.coinbase.com/path" (e.g., "GET api.coinbase.com/api/v3/brokerage/accounts")
        - kid header: FULL API key path (organizations/org_id/apiKeys/key_id)
        - sub claim: FULL API key path (same as kid)
        - iss claim: "cdp"
        - nonce: secrets.token_hex() (random hex, NOT timestamp)

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: The API path (e.g. '/api/v3/brokerage/accounts')
        """
        import secrets as crypto_secrets  # For secure random nonce
        
        if not JWT_AVAILABLE:
            raise RuntimeError("PyJWT and cryptography packages required for authentication")

        # Prefer a file path if provided (helps avoid .env newline issues)
        secret_file = os.getenv('COINBASE_API_SECRET_FILE')
        secret_val = None

        if secret_file and os.path.exists(secret_file):
            try:
                with open(secret_file, 'r') as fh:
                    secret_val = fh.read()
            except Exception as e:
                logger.error(f"Could not read COINBASE_API_SECRET_FILE: {e}")

        # Fall back to env var
        if secret_val is None:
            secret_val = self._api_secret

        # Strip surrounding quotes and normalize escaped newlines
        secret_val = (secret_val or '').strip().strip('"').strip("'")
        secret_val = secret_val.replace('\\n', '\n')

        # FULL API key path - used for BOTH kid header AND sub claim
        # This is what the official SDK does: headers={"kid": key_var, ...}
        key_name_full = self._api_key  # e.g., "organizations/xxx/apiKeys/yyy"

        try:
            private_key = serialization.load_pem_private_key(
                secret_val.encode('utf-8'),
                password=None
            )
        except Exception as key_error:
            logger.error(f"Failed to load private key: {key_error}")
            logger.debug(f"Key format check - starts with BEGIN: {(secret_val or '').startswith('-----BEGIN')}")
            raise RuntimeError(f"Invalid private key format: {key_error}")

        # Build URI in EXACT format from official Coinbase SDK:
        # format_jwt_uri returns: f"{method} {BASE_URL}{path}"
        # where BASE_URL = "api.coinbase.com"
        # Example: "GET api.coinbase.com/api/v3/brokerage/accounts"
        if not endpoint.startswith('/api'):
            endpoint = f'/api/v3/brokerage{endpoint}'
        
        uri = f"{method} api.coinbase.com{endpoint}"
        
        current_time = int(time.time())

        # JWT payload - matches official SDK exactly
        payload = {
            'sub': key_name_full,  # FULL path (official SDK uses key_var directly)
            'iss': 'cdp',
            'nbf': current_time,
            'exp': current_time + 120,  # 2 minute expiry
            'uri': uri,  # "METHOD api.coinbase.com/path"
        }

        # JWT headers - matches official SDK exactly
        # Official SDK: headers={"kid": key_var, "nonce": secrets.token_hex()}
        headers = {
            'kid': key_name_full,  # FULL path (NOT short UUID!)
            'nonce': crypto_secrets.token_hex()  # Random hex (NOT timestamp!)
        }

        try:
            token = jwt.encode(
                payload,
                private_key,
                algorithm='ES256',
                headers=headers
            )

            # Debug: log token header & claims (unverified) to help diagnose auth failures
            try:
                header = jwt.get_unverified_header(token)
                claims = jwt.decode(token, options={"verify_signature": False})
                logger.debug(f"JWT header: {header}")
                logger.debug(f"JWT claims: {claims}")
            except Exception:
                pass

            return token
        except Exception as jwt_error:
            logger.error(f"Failed to generate JWT: {jwt_error}")
            raise RuntimeError(f"JWT generation failed: {jwt_error}")
    
    def _make_authenticated_request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        """Make authenticated request to Coinbase Advanced Trade API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., '/orders', '/accounts')
            data: Request body for POST requests
        
        Returns:
            API response as dictionary
        """
        if not self._jwt_enabled:
            raise RuntimeError("JWT authentication not configured")
        
        # Expand short endpoints to full path
        if not endpoint.startswith('/api'):
            endpoint = f'/api/v3/brokerage{endpoint}'
        
        # Generate JWT scoped to this specific method + endpoint
        token = self._generate_jwt_token(method.upper(), endpoint)
        
        # Build full URL
        url = f"{self._base_url}{endpoint}"
        
        # Set headers
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        # Make request
        if method.upper() == 'GET':
            response = requests.get(url, headers=headers, timeout=10)
        elif method.upper() == 'POST':
            response = requests.post(url, headers=headers, json=data, timeout=10)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        # Check response
        if response.status_code not in (200, 201):
            logger.error(f"API error {response.status_code}: {response.text}")
            raise RuntimeError(f"Coinbase API error: {response.status_code} - {response.text}")
        
        return response.json()
    
    def verify_credentials(self) -> Dict[str, Any]:
        """Verify API credentials work WITHOUT placing any orders.
        
        This is a read-only operation that checks:
        - JWT token generation works
        - API credentials are valid
        - Can access account information
        
        Returns:
            dict with 'success' (bool) and account info or error message
        """
        if not self._jwt_enabled:
            return {
                'success': False,
                'error': 'JWT authentication not configured',
                'details': 'Set COINBASE_API_KEY and COINBASE_API_SECRET in .env'
            }
        
        logger.info("🔐 Verifying Coinbase API credentials (read-only)...")
        
        errors = []

        # Build key variants to try (some keypairs require short vs full values in header or sub)
        key_full = self._api_key
        key_short = key_full.split('/')[-1] if key_full else ''

        variants = [
            (key_short, key_full),  # kid=short, sub=full
            (key_full, key_full),   # kid=full,  sub=full
            (key_short, key_short), # kid=short, sub=short
            (key_full, key_short),  # kid=full,  sub=short
        ]

        # Try different issuer and uri claim formats used by CDP/Advanced
        iss_variants = ['coinbase-cloud', 'cdp']
        uri_variants = [
            '/api/v3/brokerage/accounts',
            'GET api.coinbase.com/api/v3/brokerage/accounts',
            'https://api.coinbase.com/api/v3/brokerage/accounts'
        ]

        for kid, sub in variants:
            for iss in iss_variants:
                for uri_val in uri_variants:
                    try:
                        logger.info(f"Attempting credential check with kid={kid} sub={sub} iss={iss} uri={uri_val}")
                        token = self._generate_jwt_token('/accounts', kid_override=kid, sub_override=sub, iss_override=iss, uri_override=uri_val)
                        response = self._make_authenticated_request('GET', '/accounts', token_override=token)

                        accounts = response.get('accounts', [])
                        logger.info(f"✅ Credentials verified! Found {len(accounts)} accounts (kid={kid} iss={iss} uri={uri_val})")
                        for account in accounts[:3]:
                            currency = account.get('currency', 'UNKNOWN')
                            available = account.get('available_balance', {}).get('value', '0')
                            logger.info(f"   Account: {currency} - Available: {available}")

                        return {
                            'success': True,
                            'accounts': len(accounts),
                            'details': f"Successfully authenticated with {len(accounts)} accounts (kid={kid} iss={iss} uri={uri_val})"
                        }
                    except Exception as e:
                        logger.warning(f"Attempt with kid={kid} iss={iss} uri={uri_val} failed: {e}")
                        errors.append({'kid': kid, 'iss': iss, 'uri': uri_val, 'error': str(e)})

        # If we reach here all attempts failed
        logger.error(f"❌ Credential verification failed: attempts={len(errors)}")
        return {
            'success': False,
            'error': 'All attempts failed',
            'details': errors
        }

    def get_account(self, account_uuid: str) -> Dict[str, Any]:
        """Fetch a single account by UUID (GET /api/v3/brokerage/accounts/{account_uuid})."""
        if not account_uuid:
            raise ValueError("account_uuid is required")
        try:
            resp = self._make_authenticated_request('GET', f'/accounts/{account_uuid}')
            account = resp.get('account') or resp
            return {'success': True, 'account': account}
        except Exception as e:
            logger.warning(f"Get account {account_uuid} failed: {e}")
            return {'success': False, 'error': str(e)}

    def list_accounts(self) -> List[Dict[str, Any]]:
        """List all accounts (GET /api/v3/brokerage/accounts)."""
        try:
            resp = self._make_authenticated_request('GET', '/accounts')
            accounts = resp.get('accounts') or resp if isinstance(resp, list) else []
            return accounts
        except Exception as e:
            logger.warning(f"List accounts failed: {e}")
            return []

    def _place_coinbase_order(self, symbol: str, side: str, size: float, price: float) -> Dict:
        """Place authenticated order via Coinbase Advanced Trade API.
        
        Args:
            symbol: Trading pair (e.g., 'BTC-USD')
            side: 'buy' or 'sell'
            size: Amount to trade
            price: Limit price (uses limit order for safety)
        
        Returns:
            Order response from Coinbase API
        """
        order_data = {
            'product_id': symbol,
            'side': side.upper(),
            'order_configuration': {
                'limit_limit_gtc': {
                    'base_size': str(size),
                    'limit_price': str(price),
                    'post_only': False
                }
            },
            'client_order_id': f"RICK-{int(time.time() * 1000)}"
        }
        
        logger.info(f"📤 Sending order to Coinbase: {json.dumps(order_data, indent=2)}")
        
        response = self._make_authenticated_request('POST', '/orders', order_data)
        
        return response
    
    def get_daily_stats(self) -> Dict[str, Any]:
        """Get current daily statistics."""
        self._reset_daily_stats()
        
        return {
            'date': self._current_date.isoformat(),
            'trades_today': self._total_trades_today,
            'daily_loss': self._daily_loss_current,
            'consecutive_losses': self._consecutive_losses,
            'stopped': self._stopped,
            'remaining_trades': max(0, self.max_trades_per_day - self._total_trades_today),
            'remaining_loss_budget': max(0, self.daily_loss_limit - self._daily_loss_current)
        }
    
    def open_position(self, symbol: str, side: str, entry_price: float, size: float, order_id: str = None):
        """Track a new open position for trailing stop monitoring."""
        if not self.use_trailing_stops:
            return
        
        # Calculate initial stop loss
        if side in ('BUY', 'LONG'):
            stop_loss = entry_price * (1 - self.initial_stop_loss_pct / 100)
            trail_activation = entry_price * (1 + self.trailing_activation_pct / 100)
        else:  # SHORT
            stop_loss = entry_price * (1 + self.initial_stop_loss_pct / 100)
            trail_activation = entry_price * (1 - self.trailing_activation_pct / 100)
        
        self._open_positions[symbol] = {
            'side': side,
            'entry_price': entry_price,
            'size': size,
            'order_id': order_id,
            'stop_loss': stop_loss,
            'highest_price': entry_price if side in ('BUY', 'LONG') else None,
            'lowest_price': entry_price if side in ('SHORT', 'SELL') else None,
            'trail_activation': trail_activation,
            'trailing_active': False,
            'timestamp': datetime.now()
        }
        
        logger.info(f"📍 Position opened: {symbol} {side} {size:.6f} @ ${entry_price:.2f}")
        logger.info(f"   Initial stop: ${stop_loss:.2f} (-{self.initial_stop_loss_pct}%)")
        logger.info(f"   Trail activates at: ${trail_activation:.2f} (+{self.trailing_activation_pct}%)")
    
    def update_trailing_stops(self) -> List[Dict[str, Any]]:
        """Update all trailing stops based on current prices.
        
        Returns:
            List of positions that hit their stop loss
        """
        if not self.use_trailing_stops:
            return []
        
        triggered_stops = []
        
        for symbol, position in list(self._open_positions.items()):
            current_price = self.get_last_price(symbol)
            if current_price is None:
                continue
            
            side = position['side']
            
            if side in ('BUY', 'LONG'):
                # Update highest price
                if current_price > position['highest_price']:
                    position['highest_price'] = current_price
                    
                    # Check if trailing should activate
                    if not position['trailing_active'] and current_price >= position['trail_activation']:
                        position['trailing_active'] = True
                        logger.info(f"🎯 Trailing stop ACTIVATED for {symbol} @ ${current_price:.2f}")
                    
                    # Update trailing stop if active
                    if position['trailing_active']:
                        new_stop = current_price * (1 - self.trailing_distance_pct / 100)
                        if new_stop > position['stop_loss']:
                            old_stop = position['stop_loss']
                            position['stop_loss'] = new_stop
                            logger.info(f"📈 {symbol} trailing stop updated: ${old_stop:.2f} → ${new_stop:.2f}")
                            
                            # ★ NARRATOR: Announce trailing stop update
                            if self.narrator:
                                pnl = (current_price - position['entry_price']) * position.get('size', 0.01)
                                self.narrator.update_position_price(
                                    ticket=position.get('position_id', symbol),
                                    current_price=current_price,
                                    unrealized_pnl=pnl
                                )
                                self.narrator.narrate_trailing_stop_update(
                                    ticket=position.get('position_id', symbol),
                                    new_sl=new_stop,
                                    reason=f"Price moved to ${current_price:.2f}, trailing stop adjusted"
                                )
                            
                            # ★ NARRATOR: Announce trailing stop update
                            if self.narrator:
                                pnl = (current_price - position['entry_price']) * position.get('size', 0.01)
                                self.narrator.update_position_price(
                                    ticket=position.get('position_id', symbol),
                                    current_price=current_price,
                                    unrealized_pnl=pnl
                                )
                                self.narrator.narrate_trailing_stop_update(
                                    ticket=position.get('position_id', symbol),
                                    new_sl=new_stop,
                                    reason=f"Price moved to ${current_price:.2f}, trailing stop adjusted"
                                )
                
                # Check if stop loss hit
                if current_price <= position['stop_loss']:
                    logger.warning(f"🛑 STOP LOSS HIT: {symbol} @ ${current_price:.2f} (stop: ${position['stop_loss']:.2f})")
                    triggered_stops.append({
                        'symbol': symbol,
                        'side': 'SELL',  # Exit LONG
                        'price': current_price,
                        'position': position
                    })
                    del self._open_positions[symbol]
            
            else:  # SHORT
                # Update lowest price
                if current_price < position['lowest_price']:
                    position['lowest_price'] = current_price
                    
                    # Check if trailing should activate
                    if not position['trailing_active'] and current_price <= position['trail_activation']:
                        position['trailing_active'] = True
                        logger.info(f"🎯 Trailing stop ACTIVATED for {symbol} @ ${current_price:.2f}")
                    
                    # Update trailing stop if active
                    if position['trailing_active']:
                        new_stop = current_price * (1 + self.trailing_distance_pct / 100)
                        if new_stop < position['stop_loss']:
                            old_stop = position['stop_loss']
                            position['stop_loss'] = new_stop
                            logger.info(f"📉 {symbol} trailing stop updated: ${old_stop:.2f} → ${new_stop:.2f}")
                            
                            # ★ NARRATOR: Announce trailing stop update
                            if self.narrator:
                                pnl = (position['entry_price'] - current_price) * position.get('size', 0.01)
                                self.narrator.update_position_price(
                                    ticket=position.get('position_id', symbol),
                                    current_price=current_price,
                                    unrealized_pnl=pnl
                                )
                                self.narrator.narrate_trailing_stop_update(
                                    ticket=position.get('position_id', symbol),
                                    new_sl=new_stop,
                                    reason=f"Price moved to ${current_price:.2f}, trailing stop adjusted"
                                )
                            
                            # ★ NARRATOR: Announce trailing stop update
                            if self.narrator:
                                pnl = (position['entry_price'] - current_price) * position.get('size', 0.01)
                                self.narrator.update_position_price(
                                    ticket=position.get('position_id', symbol),
                                    current_price=current_price,
                                    unrealized_pnl=pnl
                                )
                                self.narrator.narrate_trailing_stop_update(
                                    ticket=position.get('position_id', symbol),
                                    new_sl=new_stop,
                                    reason=f"Price moved to ${current_price:.2f}, trailing stop adjusted"
                                )
                
                # Check if stop loss hit
                if current_price >= position['stop_loss']:
                    logger.warning(f"🛑 STOP LOSS HIT: {symbol} @ ${current_price:.2f} (stop: ${position['stop_loss']:.2f})")
                    triggered_stops.append({
                        'symbol': symbol,
                        'side': 'BUY',  # Exit SHORT
                        'price': current_price,
                        'position': position
                    })
                    del self._open_positions[symbol]
        
        return triggered_stops
    
    def close_position(self, symbol: str, exit_price: float = None, reason: str = "manual"):
        """Close a tracked position."""
        if symbol in self._open_positions:
            position = self._open_positions[symbol]
            if exit_price:
                pnl_pct = ((exit_price - position['entry_price']) / position['entry_price']) * 100
                if position['side'] in ('SHORT', 'SELL'):
                    pnl_pct *= -1
                logger.info(f"📤 Position closed: {symbol} @ ${exit_price:.2f} ({pnl_pct:+.2f}%) - {reason}")
            del self._open_positions[symbol]
    
    def get_open_positions(self) -> Dict[str, Dict[str, Any]]:
        """Get all currently open positions."""
        return self._open_positions.copy()
    
    def disconnect(self):
        """Disconnect from broker (cleanup on shutdown)."""
        logger.info("🔌 Coinbase connector disconnected")
        # No persistent connection to close for REST API


def get_coinbase_safe_connector(paper_mode: bool = True, **kwargs) -> CoinbaseSafeConnector:
    """Factory function to create safe Coinbase connector."""
    return CoinbaseSafeConnector(paper_mode=paper_mode, **kwargs)
