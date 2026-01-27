"""Exit Manager - Profit-aware exit logic for RBOTzilla.

CRITICAL RULE: EXITS NEVER FREEZE
---------------------------------
The Exit Manager operates INDEPENDENTLY of watchdog freeze status.
Even when the watchdog freezes NEW trade entries (due to AI seat failures,
broker health issues, etc.), the Exit Manager MUST continue to:
1. Monitor existing positions
2. Apply profit locks
3. Execute trailing stops
4. Enforce time-stop (6-8 hour max hold)
5. Close positions when rules are met

This is a SAFETY mechanism: we can freeze entries while protecting
existing capital. Zombie positions (held 15+ hours) are NEVER acceptable.

This module provides intelligent exit management with:
1. Profit Lock: Move SL to breakeven when trade reaches +X pips
2. Trailing Stop: Dynamic trailing after profit threshold
3. Time Stop: Close trades open beyond max duration (6-8 hours HARD LIMIT)
4. Partial TP: Scale out at intermediate targets

Key Features:
- Integrates with OANDA API to modify orders
- Respects existing OCO structures
- Emits events for audit trail
- Configurable thresholds via env vars
- NEVER checks trading_allowed() - exits always run
"""
from __future__ import annotations
import os
import time
import logging
import threading
from typing import Dict, Any, Optional, List
from datetime import datetime
import json

logger = logging.getLogger(__name__)

# State file for observability
STATE_FILE = os.getenv('EXIT_MANAGER_STATE_FILE', 'ops/state/exit_manager_state.json')
LEGACY_STATE_FILE = os.getenv('EXIT_MANAGER_STATE_FILE_LEGACY', 'ops/state/exit_manager.json')
EVENT_LOG = os.getenv('EXIT_MANAGER_EVENT_LOG', 'ops/state/exit_manager_events.jsonl')


# -----------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------
def _clamp_hold_hours(value: float) -> float:
  try:
    return max(6.0, min(8.0, float(value)))
  except Exception:
    return 8.0


_DEFAULT_MAX_HOLD_HOURS = _clamp_hold_hours(float(os.getenv('EXIT_MAX_HOLD_HOURS', '8')))

DEFAULT_CONFIG = {
  # Profit lock: move SL to breakeven after X pips profit
  'PROFIT_LOCK_PIPS': float(os.getenv('EXIT_PROFIT_LOCK_PIPS', '15.0')),

  # Trailing stop: start trailing after X pips profit
  'TRAILING_START_PIPS': float(os.getenv('EXIT_TRAILING_START_PIPS', '20.0')),
  'TRAILING_DISTANCE_PIPS': float(os.getenv('EXIT_TRAILING_DISTANCE_PIPS', '10.0')),

  # Time stop: close trades open longer than X hours (6-8 configurable)
  'MAX_HOLD_HOURS': _DEFAULT_MAX_HOLD_HOURS,
  'MAX_TRADE_HOURS': _DEFAULT_MAX_HOLD_HOURS,

  # Hard/soft max hold (seconds)
  'SOFT_MAX_HOLD_SECONDS': int(os.getenv('SOFT_MAX_HOLD_SECONDS', str(int(_DEFAULT_MAX_HOLD_HOURS * 3600)))),
  'MAX_HOLD_SECONDS': int(os.getenv('MAX_HOLD_SECONDS', str(int(_DEFAULT_MAX_HOLD_HOURS * 3600)))),

  # Profit giveback rule (pips-based trigger; name kept for config compatibility)
  'PROFIT_LOCK_TRIGGER_PCT': float(os.getenv('PROFIT_LOCK_TRIGGER_PCT', '0.20')),
  'GIVEBACK_PCT': float(os.getenv('GIVEBACK_PCT', '0.50')),

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
  max_hold_hours = _clamp_hold_hours(float(os.getenv('EXIT_MAX_HOLD_HOURS', DEFAULT_CONFIG['MAX_HOLD_HOURS'])))
  max_hold_seconds = int(os.getenv('MAX_HOLD_SECONDS', int(max_hold_hours * 3600)))
  soft_hold_seconds = int(os.getenv('SOFT_MAX_HOLD_SECONDS', int(max_hold_hours * 3600)))
  return {
    'PROFIT_LOCK_PIPS': float(os.getenv('EXIT_PROFIT_LOCK_PIPS', DEFAULT_CONFIG['PROFIT_LOCK_PIPS'])),
    'TRAILING_START_PIPS': float(os.getenv('EXIT_TRAILING_START_PIPS', DEFAULT_CONFIG['TRAILING_START_PIPS'])),
    'TRAILING_DISTANCE_PIPS': float(os.getenv('EXIT_TRAILING_DISTANCE_PIPS', DEFAULT_CONFIG['TRAILING_DISTANCE_PIPS'])),
    'MAX_HOLD_HOURS': max_hold_hours,
    'MAX_TRADE_HOURS': max_hold_hours,
    'SOFT_MAX_HOLD_SECONDS': soft_hold_seconds,
    'MAX_HOLD_SECONDS': max_hold_seconds,
    'PROFIT_LOCK_TRIGGER_PCT': float(os.getenv('PROFIT_LOCK_TRIGGER_PCT', DEFAULT_CONFIG['PROFIT_LOCK_TRIGGER_PCT'])),
    'GIVEBACK_PCT': float(os.getenv('GIVEBACK_PCT', DEFAULT_CONFIG['GIVEBACK_PCT'])),
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
  """Calculate current profit in pips for a position."""
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
    if LEGACY_STATE_FILE and LEGACY_STATE_FILE != STATE_FILE:
      _ensure_state_dir(LEGACY_STATE_FILE)
      with open(LEGACY_STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)
  except Exception as e:
    logger.warning(f"Failed to write exit manager state: {e}")


# -----------------------------------------------------------------
# Exit Manager Class
# -----------------------------------------------------------------
class ExitManager:
  """Manages intelligent exits for open positions."""

  def __init__(self, connector, account_id: Optional[str] = None):
    """Initialize Exit Manager."""
    self.connector = connector
    self.account_id = account_id or getattr(connector, 'account_id', None)
    self.config = get_config()
    self._running = False
    self._thread = None
    self._lock = threading.Lock()

    # Track which positions have had profit lock applied
    self._profit_locked: Dict[str, bool] = {}

    # Track trailing stop high-water marks
    self._trailing_hwm: Dict[str, float] = {}

    # Track peak profit for giveback logic
    self._max_profit_pips: Dict[str, float] = {}

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
        logger.info("EXIT_MANAGER_TICK positions=%d", result.get('checked', 0))
        _log_event('EXIT_MANAGER_TICK', {
          'checked': result.get('checked', 0),
          'profit_locks': result.get('profit_locks', 0),
          'trailing_updates': result.get('trailing_updates', 0),
          'time_closes': result.get('time_closes', 0),
          'hard_time_closes': result.get('hard_time_closes', 0),
          'profit_giveback_exits': result.get('profit_giveback_exits', 0),
          'profit_giveback_tightens': result.get('profit_giveback_tightens', 0),
        })
      except Exception as e:
        logger.error(f"ExitManager check error: {e}")

      time.sleep(self.config['CHECK_INTERVAL_SECS'])

  def check_all_positions(self) -> Dict[str, Any]:
    """Check all open positions and apply exit logic."""
    actions = {
      'checked': 0,
      'profit_locks': 0,
      'trailing_updates': 0,
      'time_closes': 0,
      'hard_time_closes': 0,
      'soft_time_warnings': 0,
      'profit_giveback_exits': 0,
      'profit_giveback_tightens': 0,
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
        age_sec = self._position_age_seconds(pos)

        actions['checked'] += 1

        # Hard time stop
        if age_sec is not None and age_sec >= self.config['MAX_HOLD_SECONDS']:
          if self._apply_time_stop(pos, age_sec, hard=True):
            actions['hard_time_closes'] += 1
            continue

        # Soft time stop warning / tighten
        if age_sec is not None and age_sec >= self.config['SOFT_MAX_HOLD_SECONDS']:
          if self._apply_soft_hold(pos, profit_pips, current_price, age_sec):
            actions['soft_time_warnings'] += 1

        # Profit Lock
        if self.config['ENABLE_PROFIT_LOCK']:
          if self._apply_profit_lock(pos, profit_pips, current_price):
            actions['profit_locks'] += 1

        # Trailing Stop
        if self.config['ENABLE_TRAILING']:
          if self._apply_trailing_stop(pos, profit_pips, current_price):
            actions['trailing_updates'] += 1

        # Soft time stop (legacy)
        if self.config['ENABLE_TIME_STOP']:
          if self._apply_time_stop(pos, age_sec, hard=False):
            actions['time_closes'] += 1

        # Profit giveback prevention
        giveback = self._apply_profit_giveback(pos, profit_pips, current_price)
        if giveback == 'EXIT':
          actions['profit_giveback_exits'] += 1
        elif giveback == 'TIGHTEN':
          actions['profit_giveback_tightens'] += 1

    except Exception as e:
      actions['errors'].append(str(e))
      logger.error(f"check_all_positions error: {e}")

    _write_state({
      'last_tick_utc': datetime.utcnow().isoformat() + 'Z',
      'open_trades_count': actions.get('checked', 0),
      'trailing_enabled': bool(self.config.get('ENABLE_TRAILING')),
      'max_hold_hours': float(self.config.get('MAX_HOLD_HOURS', 0.0)),
      'last_check': actions,
      'profit_locked': list(self._profit_locked.keys()),
      'trailing_hwm': self._trailing_hwm,
      'max_profit_pips': self._max_profit_pips,
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

  def _get_prices(self, pairs: List[Optional[str]]) -> Dict[str, float]:
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

  def _position_age_seconds(self, pos: Dict[str, Any]) -> Optional[float]:
    open_time_str = pos.get('openTime', '')
    if not open_time_str:
      return None
    try:
      open_time_str = open_time_str.split('.')[0]
      open_time = datetime.fromisoformat(open_time_str.replace('Z', '+00:00'))
      now = datetime.utcnow()
      return (now - open_time.replace(tzinfo=None)).total_seconds()
    except Exception:
      return None

  def _apply_profit_lock(self, pos: Dict[str, Any], profit_pips: float, current_price: float) -> bool:
    pos_id = pos.get('id', pos.get('trade_id', 'unknown'))
    if self._profit_locked.get(pos_id):
      return False
    if profit_pips < self.config['PROFIT_LOCK_PIPS']:
      return False

    entry_price = float(pos.get('averagePrice', pos.get('price', 0)))
    side = pos.get('side', 'long').lower()
    pair = pos.get('instrument', '')
    if entry_price == 0:
      return False

    pip = pip_size(pair)
    spread_buffer = pip * 2
    if side == 'long':
      new_sl = entry_price + spread_buffer
    else:
      new_sl = entry_price - spread_buffer

    current_sl = float(pos.get('stopLossOrder', {}).get('price', 0))
    if current_sl > 0:
      if side == 'long' and new_sl <= current_sl:
        return False
      if side == 'short' and new_sl >= current_sl:
        return False

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
          'old_sl': current_sl,
        })
        logger.info(f"Profit lock applied: {pos_id} {pair} SL → {new_sl}")
        return True
    except Exception as e:
      logger.error(f"Failed to apply profit lock for {pos_id}: {e}")
    return False

  def _apply_trailing_stop(self, pos: Dict[str, Any], profit_pips: float, current_price: float) -> bool:
    pos_id = pos.get('id', pos.get('trade_id', 'unknown'))
    pair = pos.get('instrument', '')
    side = pos.get('side', 'long').lower()
    if profit_pips < self.config['TRAILING_START_PIPS']:
      return False

    hwm = self._trailing_hwm.get(pos_id, 0)
    if profit_pips > hwm:
      self._trailing_hwm[pos_id] = profit_pips
      hwm = profit_pips

    pip = pip_size(pair)
    trailing_dist = self.config['TRAILING_DISTANCE_PIPS'] * pip
    entry_price = float(pos.get('averagePrice', pos.get('price', 0)))

    if side == 'long':
      hwm_price = entry_price + (hwm * pip)
      new_sl = hwm_price - trailing_dist
    else:
      hwm_price = entry_price - (hwm * pip)
      new_sl = hwm_price + trailing_dist

    current_sl = float(pos.get('stopLossOrder', {}).get('price', 0))
    if current_sl > 0:
      if side == 'long' and new_sl <= current_sl:
        return False
      if side == 'short' and new_sl >= current_sl:
        return False

    try:
      success = self._modify_trade_sl(pos_id, new_sl)
      if success:
        _log_event('TRAILING_UPDATE', {
          'trade_id': pos_id,
          'position_id': pos_id,
          'instrument': pair,
          'pair': pair,
          'side': side,
          'profit_pips': profit_pips,
          'hwm_pips': hwm,
          'new_sl': new_sl,
          'old_sl': current_sl,
        })
        logger.info("TRAILING_UPDATE trade_id=%s instrument=%s old_sl=%s new_sl=%s profit_pips=%.2f", pos_id, pair, current_sl, new_sl, profit_pips)
        return True
    except Exception as e:
      logger.error(f"Failed to update trailing SL for {pos_id}: {e}")
    return False

  def _apply_soft_hold(self, pos: Dict[str, Any], profit_pips: float, current_price: float, age_sec: float) -> bool:
    pos_id = pos.get('id', pos.get('trade_id', 'unknown'))
    pair = pos.get('instrument', '')
    side = pos.get('side', 'long').lower()
    entry_price = float(pos.get('averagePrice', pos.get('price', 0)))
    if entry_price == 0:
      return False

    logger.warning(f"TIME_STOP_SOFT position_id={pos_id} age_sec={int(age_sec)}")
    _log_event('TIME_STOP_SOFT', {'position_id': pos_id, 'age_sec': age_sec})

    # Tighten stop to breakeven when possible
    if profit_pips <= 0:
      return True

    pip = pip_size(pair)
    buffer = pip * 2
    if side == 'long':
      new_sl = entry_price + buffer
    else:
      new_sl = entry_price - buffer

    current_sl = float(pos.get('stopLossOrder', {}).get('price', 0))
    if current_sl > 0:
      if side == 'long' and new_sl <= current_sl:
        return True
      if side == 'short' and new_sl >= current_sl:
        return True

    try:
      success = self._modify_trade_sl(pos_id, new_sl)
      if success:
        logger.info(f"TIME_STOP_SOFT tighten SL: {pos_id} {pair} SL → {new_sl}")
    except Exception:
      pass
    return True

  def _apply_time_stop(self, pos: Dict[str, Any], age_sec: Optional[float], hard: bool = False) -> bool:
    pos_id = pos.get('id', pos.get('trade_id', 'unknown'))
    if age_sec is None:
      return False
    max_sec = self.config['MAX_HOLD_SECONDS'] if hard else self.config['MAX_TRADE_HOURS'] * 3600.0
    if age_sec < max_sec:
      return False

    success = self._close_trade(pos_id)
    if success:
      reason = 'MAX_HOLD' if hard else 'MAX_HOLD_SOFT'
      age_minutes = float(age_sec) / 60.0
      _log_event('TIME_STOP_CLOSE', {
        'trade_id': pos_id,
        'position_id': pos_id,
        'instrument': pos.get('instrument', ''),
        'age_minutes': age_minutes,
        'reason': reason,
      })
      logger.info("TIME_STOP_CLOSE trade_id=%s age_minutes=%.1f reason=%s", pos_id, age_minutes, reason)
      return True
    return False

  def _apply_profit_giveback(self, pos: Dict[str, Any], profit_pips: float, current_price: float) -> Optional[str]:
    pos_id = pos.get('id', pos.get('trade_id', 'unknown'))
    pair = pos.get('instrument', '')
    side = pos.get('side', 'long').lower()
    trigger = float(self.config['PROFIT_LOCK_TRIGGER_PCT'])
    giveback = float(self.config['GIVEBACK_PCT'])

    peak = self._max_profit_pips.get(pos_id, profit_pips)
    if profit_pips > peak:
      peak = profit_pips
      self._max_profit_pips[pos_id] = peak

    if peak < trigger:
      return None

    if profit_pips > peak * (1 - giveback):
      return None

    # Giveback triggered
    action = None
    if self._close_trade(pos_id):
      action = 'EXIT'
    else:
      # tighten stop near current price
      pip = pip_size(pair)
      if side == 'long':
        new_sl = current_price - (pip * 2)
      else:
        new_sl = current_price + (pip * 2)
      try:
        if self._modify_trade_sl(pos_id, new_sl):
          action = 'TIGHTEN'
      except Exception:
        action = None

    if action:
      _log_event('PROFIT_LOCK', {
        'position_id': pos_id,
        'pair': pair,
        'peak_pips': peak,
        'now_pips': profit_pips,
        'action': action,
      })
      logger.info(f"PROFIT_LOCK: peak={peak:.2f} now={profit_pips:.2f} action={action}")
    return action

  def _modify_trade_sl(self, trade_id: str, new_sl: float) -> bool:
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
    with self._lock:
      closed = [pid for pid in self._profit_locked if pid not in open_position_ids]
      for pid in closed:
        del self._profit_locked[pid]

      closed = [pid for pid in self._trailing_hwm if pid not in open_position_ids]
      for pid in closed:
        del self._trailing_hwm[pid]

      closed = [pid for pid in self._max_profit_pips if pid not in open_position_ids]
      for pid in closed:
        del self._max_profit_pips[pid]


# -----------------------------------------------------------------
# Module-level convenience functions
# -----------------------------------------------------------------
_exit_manager: Optional[ExitManager] = None


def start_exit_manager(connector, account_id: Optional[str] = None) -> ExitManager:
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
  print("Exit Manager Configuration:")
  for k, v in get_config().items():
    print(f"  {k}: {v}")
