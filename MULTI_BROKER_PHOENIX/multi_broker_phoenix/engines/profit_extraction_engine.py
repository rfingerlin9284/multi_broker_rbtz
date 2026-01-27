import logging
import numpy as np
import pandas as pd
from typing import Optional, Dict, Any
import os
from datetime import datetime
from .atr_auto_tuner import ATRAutoTuner

class ProfitExtractionEngine:
    """
    Profit extraction with ATR-based trailing stops (primary).
    Adaptive to volatility - perfect for crypto/FX.
    
    AUTO-TUNING: System learns optimal multipliers based on actual trade outcomes.
    No manual configuration needed!
    """
    def __init__(self):
        self.default_period = int(os.getenv("ATR_PERIOD_DEFAULT", "14"))
        self.default_multiplier = 2.5
        self.logger = logging.getLogger(__name__)
        self.auto_tuner = ATRAutoTuner()  # Initialize auto-tuning system
        self.active_trades = {}  # Track trades for outcome recording
        self._open_positions: Dict[str, Dict[str, Any]] = {}  # CRITICAL: Track open positions
        self.logger.info(f"🔧 ATR Config: Period {self.default_period} (configurable per-symbol) | Multiplier {self.default_multiplier}x (auto-tuning)")

    def _get_period(self, symbol: str) -> int:
        """Get ATR period for symbol from .env (per-symbol override), fallback to default."""
        key = f"ATR_PERIOD_{symbol.replace('-', '_').upper()}"
        period = int(os.getenv(key, self.default_period))
        return period

    def _get_multiplier(self, symbol: str) -> float:
        """Get AUTO-TUNED multiplier for symbol (learns from actual trades)."""
        # Use auto-tuner to get optimal multiplier
        auto_tuned = self.auto_tuner.get_multiplier(symbol)
        return auto_tuned

    @staticmethod
    def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Wilder ATR - vectorized and efficient.
        
        Args:
            df: DataFrame with 'high', 'low', 'close' columns
            period: ATR period (10=responsive, 14=classic, 20=smooth)
        
        Returns:
            Series of ATR values
        """
        high = df['high']
        low = df['low']
        close = df['close'].shift(1)
        
        tr1 = high - low
        tr2 = np.abs(high - close)
        tr3 = np.abs(low - close)
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        atr = pd.Series(index=df.index, dtype=float)
        atr.iloc[period-1] = tr.iloc[:period].mean()
        
        for i in range(period, len(df)):
            atr.iloc[i] = (atr.iloc[i-1] * (period - 1) + tr.iloc[i]) / period
        
        return atr

    def should_extract(self, position, price_data: pd.DataFrame) -> tuple[bool, Optional[float]]:
        """
        Returns (should_exit, current_stop_price)
        price_data: recent candles for this symbol (OHLC, min period rows recommended)
        """
        symbol = position.symbol
        current_price = position.current_price
        
        # Get configurable period and auto-tuned multiplier
        period = self._get_period(symbol)
        multiplier = self._get_multiplier(symbol)
        
        # Track entry for later outcome recording
        trade_key = f"{symbol}_{position.entry_time}"
        if trade_key not in self.active_trades:
            self.active_trades[trade_key] = {
                'symbol': symbol,
                'entry_price': position.entry_price,
                'entry_time': position.entry_time,
                'period_used': period,
                'multiplier_used': multiplier
            }
        
        if len(price_data) < period:
            self.logger.debug("Insufficient data for ATR period %d on %s (%d bars) - using fixed fallback", period, symbol, len(price_data))
            fallback_pct = 0.10
            if position.direction == "LONG":
                stop = current_price * (1 - fallback_pct)
            else:
                stop = current_price * (1 + fallback_pct)
            return current_price <= stop if position.direction == "LONG" else current_price >= stop, stop
        
        atr_series = self.calculate_atr(price_data, period=period)
        current_atr = atr_series.iloc[-1]
        
        if position.direction == "LONG":
            stop_price = current_price - (current_atr * multiplier)
            hit = current_price <= stop_price
        else:
            stop_price = current_price + (current_atr * multiplier)
            hit = current_price >= stop_price
        
        self.logger.info("[ATR TRAIL] %s %s | Period: %d | ATR: %.5f | Mult: %.2f (AUTO-TUNED) | Price: %.5f | Stop: %.5f | Hit: %s",
                         position.direction, symbol, period, current_atr, multiplier, current_price, stop_price, hit)
        
        return hit, stop_price
    
    def record_trade_exit(self, symbol: str, entry_price: float, exit_price: float, 
                         pnl_pct: float, bars_held: int, exit_reason: str = "atr_stop"):
        """Record trade outcome for auto-tuning system to learn from."""
        multiplier = self.active_trades.get(f"{symbol}_{entry_price}", {}).get('multiplier_used', 2.5)
        
        self.auto_tuner.record_trade_outcome(
            symbol=symbol,
            multiplier=multiplier,
            pnl_pct=pnl_pct,
            bars_held=bars_held,
            exit_reason=exit_reason
        )
        
        self.logger.info(f"📊 AUTO-TUNE: {symbol} recorded | P/L: {pnl_pct:+.2f}% | Bars: {bars_held} | Reason: {exit_reason}")

    def generate_exit_order(self, position):
        self.logger.info("PROFIT EXTRACTION: Exiting %s %s at market (ATR trailing stop)", position.direction, position.symbol)
        return {
            "symbol": position.symbol,
            "side": "SELL" if position.direction == "LONG" else "BUY",
            "size": position.size,
            "type": "market",
            "reason": "atr_trailing_stop"
        }
    
    # ============================================================================
    # CRITICAL POSITION TRACKING METHODS (MISSING - FIX FOR EXECUTION PIPELINE)
    # ============================================================================
    
    def add_trade(self, trade_id: str, symbol: str, entry_price: float, entry_size: float, 
                  signal_strength: float = 1.0) -> bool:
        """
        ⚠️  CRITICAL METHOD - Register a new trade for tracking.
        
        This is called AFTER order execution to track position for:
        - Trailing stop activation
        - Profit extraction
        - Auto-tuning feedback
        
        Args:
            trade_id: Unique identifier (e.g., 'coinbase:BTC-USD')
            symbol: Trading symbol
            entry_price: Entry price
            entry_size: Position size in USD notional
            signal_strength: Signal strength (0.0-1.0)
        
        Returns:
            True if added successfully
        """
        if trade_id in self._open_positions:
            self.logger.warning(f"⚠️  Trade {trade_id} already open, skipping duplicate")
            return False
        
        # Get configurable period for this symbol
        period = self._get_period(symbol)
        multiplier = self._get_multiplier(symbol)
        
        # Initial stop loss calculation (2% below entry for LONG)
        initial_stop_loss_pct = 2.0
        stop_loss_price = entry_price * (1 - initial_stop_loss_pct / 100.0)
        
        # Trailing stop activation threshold (1.5% above entry)
        trail_activation_pct = 1.5
        trail_activation = entry_price * (1 + trail_activation_pct / 100.0)
        
        self._open_positions[trade_id] = {
            'symbol': symbol,
            'entry_price': entry_price,
            'entry_size': entry_size,
            'entry_time': datetime.now().isoformat(),
            'highest_price': entry_price,  # Track best price for trailing stop
            'current_price': entry_price,
            'stop_loss_price': stop_loss_price,
            'trail_activation': trail_activation,
            'trailing_active': False,
            'signal_strength': signal_strength,
            'period': period,
            'multiplier': multiplier,
            'bars_held': 0,
            'realized_pnl': 0.0,
            'realized_pnl_pct': 0.0
        }
        
        self.logger.info(f"✅ POSITION TRACKED: {trade_id}")
        self.logger.info(f"   Entry: ${entry_price:.2f} | Size: ${entry_size:.2f}")
        self.logger.info(f"   Stop Loss: ${stop_loss_price:.2f} (-{initial_stop_loss_pct}%)")
        self.logger.info(f"   Trail Activation: ${trail_activation:.2f} (+{trail_activation_pct}%)")
        self.logger.info(f"   ATR Period: {period} bars | Multiplier: {multiplier}x (AUTO-TUNED)")
        
        return True
    
    def update_trade(self, trade_id: str, current_price: float) -> Optional[Dict[str, Any]]:
        """
        Update trade with latest price and check for stop loss/trailing activation.
        
        Args:
            trade_id: Trade identifier
            current_price: Current market price
        
        Returns:
            Trade data if exists, None otherwise
        """
        if trade_id not in self._open_positions:
            return None
        
        position = self._open_positions[trade_id]
        position['current_price'] = current_price
        position['bars_held'] += 1
        
        # Update highest price for trailing stop
        if current_price > position['highest_price']:
            position['highest_price'] = current_price
            
            # Check if trailing stop should activate
            if not position['trailing_active'] and current_price >= position['trail_activation']:
                position['trailing_active'] = True
                self.logger.info(f"🎯 TRAILING STOP ACTIVATED: {trade_id} @ ${current_price:.2f}")
            
            # Update trailing stop if active (1% distance from highest)
            if position['trailing_active']:
                trail_distance_pct = 1.0
                new_stop = current_price * (1 - trail_distance_pct / 100.0)
                old_stop = position['stop_loss_price']
                
                if new_stop > old_stop:
                    position['stop_loss_price'] = new_stop
                    self.logger.info(f"📈 TRAILING STOP UPDATED: {trade_id}")
                    self.logger.info(f"   Price: ${current_price:.2f} | New Stop: ${new_stop:.2f} (was ${old_stop:.2f})")
        
        return position
    
    def get_exit_signal(self, trade_id: str) -> Optional[Dict[str, Any]]:
        """
        Check if position should exit (stop loss hit or profit target reached).
        
        Args:
            trade_id: Trade identifier
        
        Returns:
            Exit signal dict with should_exit, reason, etc., or None
        """
        if trade_id not in self._open_positions:
            return None
        
        position = self._open_positions[trade_id]
        current_price = position['current_price']
        entry_price = position['entry_price']
        
        # Check stop loss hit
        if current_price <= position['stop_loss_price']:
            pnl_pct = ((current_price - entry_price) / entry_price) * 100.0
            self.logger.warning(f"🛑 STOP LOSS HIT: {trade_id}")
            self.logger.warning(f"   Entry: ${entry_price:.2f} | Exit: ${current_price:.2f} | Loss: {pnl_pct:.2f}%")
            
            return {
                'should_exit': True,
                'exit_reason': 'stop_loss_hit',
                'exit_price': current_price,
                'exit_size': 1.0,  # Full position
                'pnl_pct': pnl_pct
            }
        
        # Check profit target (1.5% or 3.0% depending on signal strength)
        profit_target_pct = 1.5 if position['signal_strength'] < 0.8 else 3.0
        profit_target = entry_price * (1 + profit_target_pct / 100.0)
        
        if current_price >= profit_target:
            pnl_pct = ((current_price - entry_price) / entry_price) * 100.0
            self.logger.info(f"💰 PROFIT TARGET REACHED: {trade_id}")
            self.logger.info(f"   Entry: ${entry_price:.2f} | Exit: ${current_price:.2f} | Profit: {pnl_pct:.2f}%")
            
            return {
                'should_exit': True,
                'exit_reason': 'profit_target_hit',
                'exit_price': current_price,
                'exit_size': 1.0,  # Full position
                'pnl_pct': pnl_pct
            }
        
        # No exit signal
        return None
    
    def close_trade(self, trade_id: str, exit_price: float, exit_size: float = 1.0) -> Dict[str, Any]:
        """
        Close a position and calculate P/L.
        
        Args:
            trade_id: Trade identifier
            exit_price: Exit price
            exit_size: Fraction of position to close (1.0 = full)
        
        Returns:
            Trade result dict with realized P/L
        """
        if trade_id not in self._open_positions:
            return {'error': f'Trade {trade_id} not found'}
        
        position = self._open_positions[trade_id]
        entry_price = position['entry_price']
        entry_size = position['entry_size']
        
        # Calculate P/L
        closed_size = entry_size * exit_size
        pnl = (exit_price - entry_price) * (closed_size / entry_price)
        pnl_pct = ((exit_price - entry_price) / entry_price) * 100.0
        
        # Store P/L in position for tracking
        position['realized_pnl'] = pnl
        position['realized_pnl_pct'] = pnl_pct
        
        self.logger.info(f"📤 TRADE CLOSED: {trade_id}")
        self.logger.info(f"   Entry: ${entry_price:.2f} | Exit: ${exit_price:.2f}")
        self.logger.info(f"   Size: ${closed_size:.2f} | P/L: ${pnl:+.2f} ({pnl_pct:+.2f}%)")
        
        # Remove from open positions if fully closed
        if exit_size >= 1.0:
            del self._open_positions[trade_id]
        
        return {
            'trade_id': trade_id,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'realized_pnl': pnl,
            'realized_pct': pnl_pct,
            'bars_held': position['bars_held'],
            'success': True
        }
    
    def get_open_positions(self) -> Dict[str, Dict[str, Any]]:
        """Get all currently open positions."""
        return dict(self._open_positions)
