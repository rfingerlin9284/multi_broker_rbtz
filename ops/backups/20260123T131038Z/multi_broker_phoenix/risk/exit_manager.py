"""Exit Manager - Profit-aware exit logic for RBOTzilla.

This module provides intelligent exit management with:
1. Profit Lock: Move SL to breakeven when trade reaches +X pips
2. Trailing Stop: Dynamic trailing after profit threshold
3. Time Stop: Close trades open beyond max duration
4. Partial TP: Scale out at intermediate targets

Key Features:
- Integrates with OANDA API to modify orders
- Respects existing OCO structures
- Emits events for audit trail
- Configurable thresholds via env vars

Usage:
    from multi_broker_phoenix.risk.exit_manager import ExitManager
    
    em = ExitManager(connector)
    em.start_background_monitor()  # Runs every 30s
"""
from __future__ import annotations
import os
import time
import logging
import threading
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

# State file for observability
STATE_FILE = os.getenv('EXIT_MANAGER_STATE_FILE', 'ops/state/exit_manager.json')
EVENT_LOG = os.getenv('EXIT_MANAGER_EVENT_LOG', 'ops/state/exit_manager_events.jsonl')


# -----------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------
DEFAULT_CONFIG = {
    # Profit lock: move SL to breakeven after X pips profit
    'PROFIT_LOCK_PIPS': float(os.getenv('EXIT_PROFIT_LOCK_PIPS', '15.0')),
    
    # Trailing stop: start trailing after X pips profit
    'TRAILING_START_PIPS': float(os.getenv('EXIT_TRAILING_START_PIPS', '20.0')),
    'TRAILING_DISTANCE_PIPS': float(os.getenv('EXIT_TRAILING_DISTANCE_PIPS', '10.0')),
    
    # Time stop: close trades open longer than X hours
    'MAX_TRADE_HOURS': float(os.getenv('EXIT_MAX_TRADE_HOURS', '48.0')),
    # Hard time stop: ALWAYS close trades open longer than this many hours
    'HARD_MAX_TRADE_HOURS': float(os.getenv('HARD_MAX_TRADE_HOURS', '8.0')),
    
    # Partial TP: take X% at first target
    'PARTIAL_TP_PERCENT': float(os.getenv('EXIT_PARTIAL_TP_PERCENT', '50.0')),
    'PARTIAL_TP_PIPS': float(os.getenv('EXIT_PARTIAL_TP_PIPS', '25.0')),
    
    # Check interval (seconds)
    'CHECK_INTERVAL_SECS': int(os.getenv('EXIT_CHECK_INTERVAL', '30')),
    
    # Enable/disable features
    'ENABLE_PROFIT_LOCK': os.getenv('EXIT_ENABLE_PROFIT_LOCK', 'true').lower() == 'true',
    'ENABLE_TRAILING': os.getenv('EXIT_ENABLE_TRAILING', 'true').lower() == 'true',
    'ENABLE_TIME_STOP': os.getenv('EXIT_ENABLE_TIME_STOP', 'true').lower() == 'true',
    'ENABLE_PARTIAL_TP': os.getenv('EXIT_ENABLE_PARTIAL_TP', 'false').lower() == 'true',
}


def get_config() -> Dict[str, Any]:
    """Return current exit manager configuration."""
    return {
        'PROFIT_LOCK_PIPS': float(os.getenv('EXIT_PROFIT_LOCK_PIPS', DEFAULT_CONFIG['PROFIT_LOCK_PIPS'])),
        'TRAILING_START_PIPS': float(os.getenv('EXIT_TRAILING_START_PIPS', DEFAULT_CONFIG['TRAILING_START_PIPS'])),
        'TRAILING_DISTANCE_PIPS': float(os.getenv('EXIT_TRAILING_DISTANCE_PIPS', DEFAULT_CONFIG['TRAILING_DISTANCE_PIPS'])),
        'MAX_TRADE_HOURS': float(os.getenv('EXIT_MAX_TRADE_HOURS', DEFAULT_CONFIG['MAX_TRADE_HOURS'])),
        'HARD_MAX_TRADE_HOURS': float(os.getenv('HARD_MAX_TRADE_HOURS', DEFAULT_CONFIG['HARD_MAX_TRADE_HOURS'])),
        'PARTIAL_TP_PERCENT': float(os.getenv('EXIT_PARTIAL_TP_PERCENT', DEFAULT_CONFIG['PARTIAL_TP_PERCENT'])),
        'PARTIAL_TP_PIPS': float(os.getenv('EXIT_PARTIAL_TP_PIPS', DEFAULT_CONFIG['PARTIAL_TP_PIPS'])),
        'CHECK_INTERVAL_SECS': int(os.getenv('EXIT_CHECK_INTERVAL', DEFAULT_CONFIG['CHECK_INTERVAL_SECS'])),
        'ENABLE_PROFIT_LOCK': os.getenv('EXIT_ENABLE_PROFIT_LOCK', str(DEFAULT_CONFIG['ENABLE_PROFIT_LOCK'])).lower() == 'true',
        'ENABLE_TRAILING': os.getenv('EXIT_ENABLE_TRAILING', str(DEFAULT_CONFIG['ENABLE_TRAILING'])).lower() == 'true',
        'ENABLE_TIME_STOP': os.getenv('EXIT_ENABLE_TIME_STOP', str(DEFAULT_CONFIG['ENABLE_TIME_STOP'])).lower() == 'true',
        'ENABLE_PARTIAL_TP': os.getenv('EXIT_ENABLE_PARTIAL_TP', str(DEFAULT_CONFIG['ENABLE_PARTIAL_TP'])).lower() == 'true',
    }


# -----------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------
def pip_size(pair: str) -> float:
    """Return pip size for a currency pair."""
    pair_upper = pair.upper().replace('-', '_').replace('/', '_')
    if pair_upper.endswith('JPY') or '_JPY' in pair_upper:
        return 0.01
    return 0.0001


def current_profit_pips(position: Dict[str, Any], current_price: float) -> float:
    """Calculate current profit in pips for a position.
    
    Args:
        position: Position dict with 'instrument', 'side', 'averagePrice'
        current_price: Current market price
    
    Returns:
        Profit in pips (positive = profitable, negative = losing)
    """
    pair = position.get('instrument', '')
    entry_price = float(position.get('averagePrice', position.get('price', 0)))
    side = position.get('side', 'long').lower()
    
    if not pair or entry_price == 0:
        return 0.0
    
    pip = pip_size(pair)
    
    if side == 'long':
        return (current_price - entry_price) / pip
    else:  # short
        return (entry_price - current_price) / pip


def _ensure_state_dir(path: str) -> None:
    """Ensure state directory exists for the given file path."""
    try:
        import pathlib
        pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass


def _log_event(event_type: str, details: Dict[str, Any]):
    """Append event to durable event log."""
    try:
        event = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'type': event_type,
            **details
        }
        _ensure_state_dir(EVENT_LOG)
        with open(EVENT_LOG, 'a') as f:
            f.write(json.dumps(event) + '\n')
    except Exception as e:
        logger.warning(f"Failed to log exit event: {e}")


def _write_state(state: Dict[str, Any]):
    """Write state to file for observability."""
    try:
        state['updated_at'] = datetime.utcnow().isoformat() + 'Z'
        _ensure_state_dir(STATE_FILE)
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logger.warning(f"Failed to write exit manager state: {e}")


# -----------------------------------------------------------------
# Exit Manager Class
# -----------------------------------------------------------------
class ExitManager:
    """Manages intelligent exits for open positions."""
    
    def __init__(self, connector, account_id: str = None):
        """Initialize Exit Manager.
        
        Args:
            connector: OANDA connector with API methods
            account_id: OANDA account ID (uses default if None)
        """
        self.connector = connector
        self.account_id = account_id or getattr(connector, 'account_id', None)
        self.config = get_config()
        self.hard_max_hours = float(self.config.get('HARD_MAX_TRADE_HOURS', 8.0))
        self._running = False
        self._thread = None
        self._lock = threading.Lock()
        
        # Track which positions have had profit lock applied
        self._profit_locked: Dict[str, bool] = {}
        
        # Track trailing stop high-water marks
        self._trailing_hwm: Dict[str, float] = {}  # position_id -> highest profit pips
        
        logger.info(f"ExitManager initialized with config: {self.config}")
    
    def start_background_monitor(self):
        """Start background thread that monitors positions."""
        if self._running:
            logger.warning("ExitManager already running")
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info("ExitManager background monitor started")
    
    def stop(self):
        """Stop the background monitor."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)
        logger.info("ExitManager stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop."""
        while self._running:
            try:
                result = self.check_all_positions()
                # Emit EXIT_MANAGER_TICK for observability/audit trail
                _log_event('EXIT_MANAGER_TICK', {
                    'checked': result.get('checked', 0),
                    'profit_locks': result.get('profit_locks', 0),
                    'trailing_updates': result.get('trailing_updates', 0),
                    'time_closes': result.get('time_closes', 0),
                    'hard_time_closes': result.get('hard_time_closes', 0),
                })
            except Exception as e:
                logger.error(f"ExitManager check error: {e}")
            
            time.sleep(self.config['CHECK_INTERVAL_SECS'])
    
    def check_all_positions(self) -> Dict[str, Any]:
        """Check all open positions and apply exit logic.
        
        Returns:
            Dict with actions taken
        """
        actions = {
            'checked': 0,
            'profit_locks': 0,
            'trailing_updates': 0,
            'time_closes': 0,
            'hard_time_closes': 0,
            'errors': []
        }
        
        try:
            positions = self._get_positions()
            prices = self._get_prices([p.get('instrument') for p in positions])
            
            for pos in positions:
                pos_id = pos.get('id', pos.get('trade_id', 'unknown'))
                pair = pos.get('instrument', '')
                
                if not pair or pair not in prices:
                    continue
                
                current_price = prices[pair]
                profit_pips = current_profit_pips(pos, current_price)
                
                actions['checked'] += 1
                
                # 1. Profit Lock
                if self.config['ENABLE_PROFIT_LOCK']:
                    if self._apply_profit_lock(pos, profit_pips, current_price):
                        actions['profit_locks'] += 1
                
                # 2. Trailing Stop
                if self.config['ENABLE_TRAILING']:
                    if self._apply_trailing_stop(pos, profit_pips, current_price):
                        actions['trailing_updates'] += 1
                
                # 3a. Hard Time Stop (ALWAYS enforced)
                if self._apply_time_stop(pos, max_hours=self.hard_max_hours, hard=True):
                    actions['hard_time_closes'] += 1
                    continue

                # 3b. Soft Time Stop
                if self.config['ENABLE_TIME_STOP']:
                    if self._apply_time_stop(pos, max_hours=self.config['MAX_TRADE_HOURS'], hard=False):
                        actions['time_closes'] += 1
        
        except Exception as e:
            actions['errors'].append(str(e))
            logger.error(f"check_all_positions error: {e}")
        
        # Write state for observability
        _write_state({
            'last_check': actions,
            'profit_locked': list(self._profit_locked.keys()),
            'trailing_hwm': self._trailing_hwm
        })
        
        return actions
    
    def _get_positions(self) -> List[Dict[str, Any]]:
        """Get open positions from connector."""
        try:
            if hasattr(self.connector, 'get_open_trades'):
                return self.connector.get_open_trades() or []
            if hasattr(self.connector, 'get_positions'):
                return self.connector.get_positions() or []
            logger.warning("No position retrieval method found on connector")
            return []
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            return []
    
    def _get_prices(self, pairs: List[str]) -> Dict[str, float]:
        """Get current prices for pairs."""
        prices = {}
        try:
            unique_pairs = list(set(p for p in pairs if p))
            if not unique_pairs:
                return prices
            
            if hasattr(self.connector, 'get_prices'):
                raw = self.connector.get_prices(unique_pairs)
                for pair, data in (raw or {}).items():
                    if isinstance(data, dict):
                        # Use mid price
                        bid = float(data.get('bid', 0))
                        ask = float(data.get('ask', 0))
                        prices[pair] = (bid + ask) / 2 if bid and ask else 0
                    else:
                        prices[pair] = float(data)
            elif hasattr(self.connector, 'get_current_price'):
                for pair in unique_pairs:
                    p = self.connector.get_current_price(pair)
                    if p:
                        prices[pair] = float(p)
        except Exception as e:
            logger.error(f"Failed to get prices: {e}")
        
        return prices
    
    def _apply_profit_lock(self, pos: Dict[str, Any], profit_pips: float, current_price: float) -> bool:
        """Move SL to breakeven if profit exceeds threshold.
        
        Returns True if SL was modified.
        """
        pos_id = pos.get('id', pos.get('trade_id', 'unknown'))
        
        # Skip if already profit-locked
        if self._profit_locked.get(pos_id):
            return False
        
        # Check if profit exceeds threshold
        if profit_pips < self.config['PROFIT_LOCK_PIPS']:
            return False
        
        entry_price = float(pos.get('averagePrice', pos.get('price', 0)))
        side = pos.get('side', 'long').lower()
        pair = pos.get('instrument', '')
        
        if entry_price == 0:
            return False
        
        # Calculate breakeven SL (entry price + spread buffer)
        pip = pip_size(pair)
        spread_buffer = pip * 2  # 2 pip buffer for spread
        
        if side == 'long':
            new_sl = entry_price + spread_buffer
        else:
            new_sl = entry_price - spread_buffer
        
        # Only move SL if it improves position
        current_sl = float(pos.get('stopLossOrder', {}).get('price', 0))
        
        if current_sl > 0:
            if side == 'long' and new_sl <= current_sl:
                return False
            if side == 'short' and new_sl >= current_sl:
                return False
        
        # Apply the new SL
        try:
            success = self._modify_trade_sl(pos_id, new_sl)
            if success:
                self._profit_locked[pos_id] = True
                _log_event('PROFIT_LOCK', {
                    'position_id': pos_id,
                    'pair': pair,
                    'side': side,
                    'entry': entry_price,
                    'profit_pips': profit_pips,
                    'new_sl': new_sl,
                    'old_sl': current_sl
                })
                logger.info(f"Profit lock applied: {pos_id} {pair} SL → {new_sl}")
                return True
        except Exception as e:
            logger.error(f"Failed to apply profit lock for {pos_id}: {e}")
        
        return False
    
    def _apply_trailing_stop(self, pos: Dict[str, Any], profit_pips: float, current_price: float) -> bool:
        """Update trailing stop if profit exceeds threshold.
        
        Returns True if SL was modified.
        """
        pos_id = pos.get('id', pos.get('trade_id', 'unknown'))
        pair = pos.get('instrument', '')
        side = pos.get('side', 'long').lower()
        
        # Check if trailing should start
        if profit_pips < self.config['TRAILING_START_PIPS']:
            return False
        
        # Update high-water mark
        hwm = self._trailing_hwm.get(pos_id, 0)
        if profit_pips > hwm:
            self._trailing_hwm[pos_id] = profit_pips
            hwm = profit_pips
        
        # Calculate trailing SL distance from HWM
        pip = pip_size(pair)
        trailing_dist = self.config['TRAILING_DISTANCE_PIPS'] * pip
        
        # Calculate new SL based on HWM
        entry_price = float(pos.get('averagePrice', pos.get('price', 0)))
        
        if side == 'long':
            # SL is below price by trailing distance from HWM profit level
            hwm_price = entry_price + (hwm * pip)
            new_sl = hwm_price - trailing_dist
        else:
            # SL is above price by trailing distance from HWM profit level
            hwm_price = entry_price - (hwm * pip)
            new_sl = hwm_price + trailing_dist
        
        # Only update if better than current SL
        current_sl = float(pos.get('stopLossOrder', {}).get('price', 0))
        
        if current_sl > 0:
            if side == 'long' and new_sl <= current_sl:
                return False
            if side == 'short' and new_sl >= current_sl:
                return False
        
        # Apply trailing SL
        try:
            success = self._modify_trade_sl(pos_id, new_sl)
            if success:
                _log_event('TRAILING_UPDATE', {
                    'position_id': pos_id,
                    'pair': pair,
                    'side': side,
                    'profit_pips': profit_pips,
                    'hwm_pips': hwm,
                    'new_sl': new_sl,
                    'old_sl': current_sl
                })
                logger.info(f"Trailing SL updated: {pos_id} {pair} SL → {new_sl}")
                return True
        except Exception as e:
            logger.error(f"Failed to update trailing SL for {pos_id}: {e}")
        
        return False
    
    def _apply_time_stop(self, pos: Dict[str, Any], max_hours: float, hard: bool = False) -> bool:
        """Close trade if open beyond max duration.
        
        Returns True if trade was closed.
        """
        pos_id = pos.get('id', pos.get('trade_id', 'unknown'))
        open_time_str = pos.get('openTime', '')
        
        if not open_time_str:
            return False
        
        try:
            # Parse open time (OANDA format: 2026-01-22T10:30:00.000000000Z)
            open_time_str = open_time_str.split('.')[0]  # Remove nanoseconds
            open_time = datetime.fromisoformat(open_time_str.replace('Z', '+00:00'))
            now = datetime.now(open_time.tzinfo) if open_time.tzinfo else datetime.utcnow()
            
            hours_open = (now - open_time.replace(tzinfo=None)).total_seconds() / 3600
            
            if hours_open < max_hours:
                return False
            
            # Close the trade
            success = self._close_trade(pos_id)
            if success:
                _log_event('HARD_TIME_STOP' if hard else 'TIME_STOP', {
                    'position_id': pos_id,
                    'pair': pos.get('instrument', ''),
                    'hours_open': hours_open,
                    'max_hours': max_hours,
                    'hard': hard
                })
                label = 'HARD' if hard else 'SOFT'
                logger.info(f"{label} time stop triggered: {pos_id} open {hours_open:.1f}h > {max_hours}h")
                return True
        except Exception as e:
            logger.error(f"Failed to check/apply time stop for {pos_id}: {e}")
        
        return False
    
    def _modify_trade_sl(self, trade_id: str, new_sl: float) -> bool:
        """Modify a trade's stop-loss via connector."""
        try:
            if hasattr(self.connector, 'modify_trade'):
                result = self.connector.modify_trade(trade_id, stopLoss={'price': str(new_sl)})
                return result is not None
            if hasattr(self.connector, 'update_stop_loss'):
                return self.connector.update_stop_loss(trade_id, new_sl)
            logger.warning("No trade modification method found on connector")
            return False
        except Exception as e:
            logger.error(f"modify_trade_sl error: {e}")
            return False
    
    def _close_trade(self, trade_id: str) -> bool:
        """Close a trade via connector."""
        try:
            if hasattr(self.connector, 'close_trade'):
                result = self.connector.close_trade(trade_id)
                return result is not None
            if hasattr(self.connector, 'close_position'):
                return self.connector.close_position(trade_id)
            logger.warning("No trade close method found on connector")
            return False
        except Exception as e:
            logger.error(f"close_trade error: {e}")
            return False
    
    def cleanup_closed_positions(self, open_position_ids: List[str]):
        """Remove tracking data for closed positions."""
        with self._lock:
            closed = [pid for pid in self._profit_locked if pid not in open_position_ids]
            for pid in closed:
                del self._profit_locked[pid]
            
            closed = [pid for pid in self._trailing_hwm if pid not in open_position_ids]
            for pid in closed:
                del self._trailing_hwm[pid]


# -----------------------------------------------------------------
# Module-level convenience functions
# -----------------------------------------------------------------
_exit_manager: Optional[ExitManager] = None


def start_exit_manager(connector, account_id: str = None) -> ExitManager:
    """Start the global exit manager instance."""
    global _exit_manager
    if _exit_manager is not None:
        _exit_manager.stop()
    _exit_manager = ExitManager(connector, account_id)
    _exit_manager.start_background_monitor()
    return _exit_manager


def stop_exit_manager():
    """Stop the global exit manager."""
    global _exit_manager
    if _exit_manager:
        _exit_manager.stop()
        _exit_manager = None


def get_exit_manager() -> Optional[ExitManager]:
    """Get the global exit manager instance."""
    return _exit_manager


if __name__ == '__main__':
    # Quick self-test
    print("Exit Manager Configuration:")
    for k, v in get_config().items():
        print(f"  {k}: {v}")
