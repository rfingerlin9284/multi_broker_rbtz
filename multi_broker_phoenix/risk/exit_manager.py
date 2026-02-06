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
from typing import Dict, Any, Optional, List, Set
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
  # Profit lock: move SL to breakeven after X pips profit (AGGRESSIVE - lock gains fast)
  'PROFIT_LOCK_PIPS': float(os.getenv('EXIT_PROFIT_LOCK_PIPS', '8.0')),

  # Trailing stop: start trailing after X pips profit (EARLY activation)
  'TRAILING_START_PIPS': float(os.getenv('EXIT_TRAILING_START_PIPS', '10.0')),
  'TRAILING_DISTANCE_PIPS': float(os.getenv('EXIT_TRAILING_DISTANCE_PIPS', '6.0')),

  # Time stop: close trades open longer than X hours (6-8 configurable)
  'MAX_HOLD_HOURS': _DEFAULT_MAX_HOLD_HOURS,
  'MAX_TRADE_HOURS': _DEFAULT_MAX_HOLD_HOURS,

  # Hard/soft max hold (seconds)
  'SOFT_MAX_HOLD_SECONDS': int(os.getenv('SOFT_MAX_HOLD_SECONDS', str(int(_DEFAULT_MAX_HOLD_HOURS * 3600)))),
  'MAX_HOLD_SECONDS': int(os.getenv('MAX_HOLD_SECONDS', str(int(_DEFAULT_MAX_HOLD_HOURS * 3600)))),

  # Profit giveback rule (TIGHT - exit if 40% giveback from peak)
  'PROFIT_LOCK_TRIGGER_PCT': float(os.getenv('PROFIT_LOCK_TRIGGER_PCT', '0.15')),
  'GIVEBACK_PCT': float(os.getenv('GIVEBACK_PCT', '0.40')),

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

  # Auto-TP: create a TP for SL-only trades when profit threshold met
  'ENABLE_AUTO_TP': os.getenv('EXIT_ENABLE_AUTO_TP', 'true').lower() == 'true',
  'AUTO_TP_TRIGGER_PIPS': float(os.getenv('EXIT_AUTO_TP_TRIGGER_PIPS', '12.0')),
  'AUTO_TP_RR': float(os.getenv('EXIT_AUTO_TP_RR', '1.0')),
}


def get_config() -> Dict[str, Any]:
  """Return current exit manager configuration.

  Supports global env-based configuration as before **and** optional
  per-strategy overrides loaded from JSON (file path via
  EXIT_STRATEGY_OVERRIDES_FILE or JSON string in
  EXIT_STRATEGY_OVERRIDES_JSON). Per-strategy overrides will be merged
  at runtime for each position so strategies can have tighter/looser
  parameters depending on trading style.
  """
  max_hold_hours = _clamp_hold_hours(float(os.getenv('EXIT_MAX_HOLD_HOURS', DEFAULT_CONFIG['MAX_HOLD_HOURS'])))
  max_hold_seconds = int(os.getenv('MAX_HOLD_SECONDS', int(max_hold_hours * 3600)))
  soft_hold_seconds = int(os.getenv('SOFT_MAX_HOLD_SECONDS', int(max_hold_hours * 3600)))
  base = {
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
  # Add path/json env hook for optional per-strategy overrides
  try:
    overrides_file = os.getenv('EXIT_STRATEGY_OVERRIDES_FILE', 'ops/config/exit_overrides.json')
    overrides_json = os.getenv('EXIT_STRATEGY_OVERRIDES_JSON')
    strategy_overrides = {}
    if overrides_json:
      import json as _json
      strategy_overrides = _json.loads(overrides_json)
    elif os.path.exists(overrides_file):
      with open(overrides_file, 'r') as f:
        strategy_overrides = json.load(f)
    base['STRATEGY_OVERRIDES'] = strategy_overrides
  except Exception as e:
    base['STRATEGY_OVERRIDES'] = {}
    logger = logging.getLogger(__name__)
    logger.warning(f"Failed to load EXIT strategy overrides: {e}")
  return base


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
  pair = position.get('instrument', position.get('symbol', ''))
  entry_price = float(position.get('averagePrice', position.get('price', position.get('entry_price', 0))))
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
    
    # P4 FIX: Track trailing stop failures (position_id -> failure_count)
    self._trailing_failures: Dict[str, int] = {}
    # P4 FIX: Positions with disabled trailing (too many failures)
    self._trailing_disabled: Set[str] = set()
    
    # Suppress repeated warnings (log only once)
    self._warned_no_modify = False
    self._warned_no_close = False

    # Cache for per-strategy override resolution
    self._strategy_config_cache: Dict[str, Dict[str, Any]] = {}

    logger.info(f"ExitManager initialized with config: {self.config}")

  def _config_for_strategy(self, strategy_name: Optional[str]) -> Dict[str, Any]:
    """Return merged config for a given strategy name.

    Strategy-specific overrides are loaded from the base config's
    STRATEGY_OVERRIDES mapping (see get_config()). If none found,
    returns the base config values used by ExitManager.
    """
    base_cfg = self.config.copy()
    if not strategy_name:
      return base_cfg

    # Cache lookup
    if strategy_name in self._strategy_config_cache:
      return self._strategy_config_cache[strategy_name]

    overrides = base_cfg.get('STRATEGY_OVERRIDES') or {}
    strat_override = overrides.get(strategy_name) or overrides.get(strategy_name.lower()) or {}

    # Merge shallowly - numeric keys only; fallback to base
    merged = base_cfg.copy()
    for k, v in strat_override.items():
      try:
        # Accept numeric / bool overrides
        merged[k] = v
      except Exception:
        merged[k] = strat_override[k]

    self._strategy_config_cache[strategy_name] = merged
    logger.info(f"ExitManager strategy config applied: strategy={strategy_name} overrides={list(strat_override.keys())}")
    return merged

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
    tick_count = 0
    while self._running:
      try:
        result = self.check_all_positions()
        tick_count += 1
        # Log at DEBUG normally, INFO every 10th tick for visibility
        if tick_count % 10 == 0:
          logger.info("EXIT_MANAGER positions=%d | profit_locks=%d | trailing=%d", 
                     result.get('checked', 0), result.get('profit_locks', 0), result.get('trailing_updates', 0))
        else:
          logger.debug("EXIT_MANAGER_TICK positions=%d", result.get('checked', 0))
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
      'hedge_opportunities': 0,
      'hedges_placed': 0,
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

        # Strategy-specific config
        cfg = self._config_for_strategy(pos.get('strategy'))

        # Hard time stop
        if age_sec is not None and age_sec >= int(cfg.get('MAX_HOLD_SECONDS', self.config['MAX_HOLD_SECONDS'])):
          if self._apply_time_stop(pos, age_sec, hard=True):
            actions['hard_time_closes'] += 1
            continue

        # Soft time stop warning / tighten
        if age_sec is not None and age_sec >= int(cfg.get('SOFT_MAX_HOLD_SECONDS', self.config['SOFT_MAX_HOLD_SECONDS'])):
          if self._apply_soft_hold(pos, profit_pips, current_price, age_sec):
            actions['soft_time_warnings'] += 1

        # Profit Lock
        if bool(cfg.get('ENABLE_PROFIT_LOCK', self.config['ENABLE_PROFIT_LOCK'])):
          if self._apply_profit_lock(pos, profit_pips, current_price):
            actions['profit_locks'] += 1

        # Trailing Stop
        if bool(cfg.get('ENABLE_TRAILING', self.config['ENABLE_TRAILING'])):
          if self._apply_trailing_stop(pos, profit_pips, current_price):
            actions['trailing_updates'] += 1

        # ===== QUANT HEDGING - LOSS RECAPTURE =====
        # Check if losing position should be hedged
        if profit_pips < -15:  # Only check positions losing > 15 pips
          hedge = self._check_hedge_opportunity(pos, profit_pips, current_price)
          if hedge:
            actions['hedge_opportunities'] += 1
            if self._execute_hedge(hedge):
              actions['hedges_placed'] += 1

        # Soft time stop (legacy)
        if bool(cfg.get('ENABLE_TIME_STOP', self.config['ENABLE_TIME_STOP'])):
          if self._apply_time_stop(pos, age_sec, hard=False):
            actions['time_closes'] += 1

        # Profit giveback prevention
        giveback = self._apply_profit_giveback(pos, profit_pips, current_price)
        if giveback == 'EXIT':
          actions['profit_giveback_exits'] += 1
        elif giveback == 'TIGHTEN':
          actions['profit_giveback_tightens'] += 1

        # Auto-TP: If position has no TP (SL-only) and meets trigger, create a TP (1R default)
        try:
          if bool(cfg.get('ENABLE_AUTO_TP', self.config.get('ENABLE_AUTO_TP'))):
            if not pos.get('takeProfitOrder') or not pos.get('takeProfitOrder', {}).get('price'):
              if self._apply_auto_tp(pos, profit_pips, current_price):
                actions.setdefault('auto_tp_created', 0)
                actions['auto_tp_created'] += 1
        except Exception as e:
          logger.debug(f"Auto-TP error for {pos.get('id')}: {e}")
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
    """
    Get open positions from connector.
    
    FIXED: Proper connector contract enforcement.
    - Prefer get_positions() (canonical BrokerConnectorProtocol method)
    - Fallback to get_open_trades() for legacy connectors
    - If neither exists, write error state and return empty (fail-safe, not crash)
    
    Returns:
        List of position/trade dicts, empty list on failure
    """
    try:
      # Primary: BrokerConnectorProtocol.get_positions()
      if hasattr(self.connector, 'get_positions'):
        result = self.connector.get_positions()
        if result is not None:
          normalized = []
          for pos in result or []:
            normalized_pos = self._normalize_position(pos)
            if normalized_pos:
              normalized.append(normalized_pos)
          return normalized
      
      # Fallback: Legacy get_open_trades()
      if hasattr(self.connector, 'get_open_trades'):
        trades = self.connector.get_open_trades()
        normalized = []
        for pos in trades or []:
          normalized_pos = self._normalize_position(pos)
          if normalized_pos:
            normalized.append(normalized_pos)
        return normalized
      
      # No position retrieval method available
      error_msg = (
        f"Connector '{getattr(self.connector, 'name', 'unknown')}' lacks get_positions() "
        f"and get_open_trades(). Cannot retrieve positions for exit management."
      )
      logger.error(error_msg)
      
      # Write error state to broker state file
      try:
        import json
        from pathlib import Path
        broker_name = getattr(self.connector, 'name', 'unknown')
        state_file = Path('ops/state/brokers') / f"{broker_name}.json"
        state_file.parent.mkdir(parents=True, exist_ok=True)
        
        state_data = {}
        if state_file.exists():
          with open(state_file, 'r') as f:
            state_data = json.load(f)
        
        state_data.update({
          'error': 'NO_POSITION_API',
          'error_detail': error_msg,
          'timestamp': datetime.utcnow().isoformat() + 'Z',
        })
        
        with open(state_file, 'w') as f:
          json.dump(state_data, f, indent=2)
        
        logger.warning(f"Wrote NO_POSITION_API error to {state_file}")
      except Exception as state_err:
        logger.error(f"Failed to write broker error state: {state_err}")
      
      # Return empty (fail-safe: exit_manager won't manage positions but won't crash engine)
      return []
    
    except Exception as e:
      logger.error(f"Failed to get positions: {e}", exc_info=True)
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
    open_time_str = pos.get('openTime', pos.get('entry_time', ''))
    if not open_time_str:
      return None
    try:
      open_time_str = open_time_str.split('.')[0]
      open_time = datetime.fromisoformat(open_time_str.replace('Z', '+00:00'))
      now = datetime.utcnow()
      return (now - open_time.replace(tzinfo=None)).total_seconds()
    except Exception:
      return None

  def _normalize_position(self, pos: Any) -> Dict[str, Any]:
    """Normalize position objects/dicts to the fields used by ExitManager."""
    if isinstance(pos, dict):
      data = pos
    elif hasattr(pos, '__dict__'):
      data = vars(pos)
    else:
      return {}

    if any(k in data for k in ('instrument', 'openTime', 'averagePrice')):
      # Ensure consistent fields even if connector returned 'raw' position dict
      stop = data.get('stop_loss') or data.get('stopLoss') or (data.get('stopLossOrder', {}) or {}).get('price')
      tp = data.get('take_profit') or data.get('takeProfit') or (data.get('takeProfitOrder', {}) or {}).get('price')
      data['stopLossOrder'] = {'price': stop} if stop else {}
      data['takeProfitOrder'] = {'price': tp} if tp else {}
      return data

    symbol = data.get('symbol') or data.get('instrument') or ''
    entry_price = data.get('entry_price', data.get('price', data.get('averagePrice', 0)))
    entry_time = data.get('entry_time', data.get('openTime', ''))
    stop_loss = data.get('stop_loss', data.get('stopLoss'))
    take_profit = data.get('take_profit', data.get('takeProfit'))
    broker_position_id = data.get('broker_position_id', data.get('id', data.get('trade_id', 'unknown')))
    side = data.get('side', 'long')

    normalized = {
      'id': broker_position_id,
      'trade_id': broker_position_id,
      'instrument': symbol,
      'symbol': symbol,
      'side': side,
      'averagePrice': entry_price or 0,
      'price': entry_price or 0,
      'openTime': entry_time or '',
      'stopLossOrder': {'price': stop_loss} if stop_loss else {},
      'takeProfitOrder': {'price': take_profit} if take_profit else {},
    }

    if 'current_price' in data:
      normalized['current_price'] = data.get('current_price')

    return normalized

  def _apply_profit_lock(self, pos: Dict[str, Any], profit_pips: float, current_price: float) -> bool:
    pos_id = pos.get('id', pos.get('trade_id', 'unknown'))
    if self._profit_locked.get(pos_id):
      return False

    cfg = self._config_for_strategy(pos.get('strategy'))
    if profit_pips < int(cfg.get('PROFIT_LOCK_PIPS', self.config['PROFIT_LOCK_PIPS'])):
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
    
    # P4 FIX: Check if trailing is disabled for this position
    if pos_id in self._trailing_disabled:
      return False
    
    cfg = self._config_for_strategy(pos.get('strategy'))

    if profit_pips < int(cfg.get('TRAILING_START_PIPS', self.config['TRAILING_START_PIPS'])):
      return False

    hwm = self._trailing_hwm.get(pos_id, 0)
    if profit_pips > hwm:
      self._trailing_hwm[pos_id] = profit_pips
      hwm = profit_pips

    pip = pip_size(pair)
    trailing_dist = int(cfg.get('TRAILING_DISTANCE_PIPS', self.config['TRAILING_DISTANCE_PIPS'])) * pip
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

    # P4 FIX: Attempt trailing update with failure tracking
    MAX_TRAILING_FAILURES = 5
    try:
      success = self._modify_trade_sl(pos_id, new_sl)
      if success:
        # Reset failure count on success
        if pos_id in self._trailing_failures:
          del self._trailing_failures[pos_id]
        
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
      # P4 FIX: Track failures and disable trailing if exceeds threshold
      failure_count = self._trailing_failures.get(pos_id, 0) + 1
      self._trailing_failures[pos_id] = failure_count
      
      if failure_count >= MAX_TRAILING_FAILURES:
        self._trailing_disabled.add(pos_id)
        logger.warning(f"🚫 TRAILING_DISABLED tradeId={pos_id} instrument={pair} - {failure_count} consecutive failures. SL/TP remain active.")
        _log_event('TRAILING_DISABLED', {
          'trade_id': pos_id,
          'instrument': pair,
          'failure_count': failure_count,
          'reason': str(e),
          'current_sl': current_sl,
        })
      else:
        logger.error(f"Failed to update trailing SL for {pos_id} (attempt {failure_count}/{MAX_TRAILING_FAILURES}): {e}")

    return False

  def _apply_auto_tp(self, pos: Dict[str, Any], profit_pips: float, current_price: float) -> bool:
    """Create a take-profit for SL-only trades when they reach the configured trigger.

    Policy:
      - Only act if no TP exists for the position
      - Respect per-strategy and global config (ENABLE_AUTO_TP)
      - Trigger when profit_pips >= AUTO_TP_TRIGGER_PIPS
      - Compute TP at 1R by default (entry + sl_distance * AUTO_TP_RR)
      - Use connector.create_take_profit() when available, else fall back to modify_trade
    """
    pos_id = pos.get('id', pos.get('trade_id', 'unknown'))
    pair = pos.get('instrument', '')
    entry_price = float(pos.get('averagePrice', pos.get('price', 0)))
    side = pos.get('side', 'long').lower()

    if not pair or entry_price == 0:
      return False

    cfg = self._config_for_strategy(pos.get('strategy'))
    trigger = float(cfg.get('AUTO_TP_TRIGGER_PIPS', self.config.get('AUTO_TP_TRIGGER_PIPS', 12.0)))
    rr = float(cfg.get('AUTO_TP_RR', self.config.get('AUTO_TP_RR', 1.0)))

    if profit_pips < trigger:
      return False

    current_sl = float(pos.get('stopLossOrder', {}).get('price', 0))
    if not current_sl or current_sl == 0:
      return False

    # compute sl distance and TP at entry +/- sl_distance*rr
    sl_dist = abs(entry_price - current_sl)
    if side == 'long':
      new_tp = entry_price + (sl_dist * rr)
    else:
      new_tp = entry_price - (sl_dist * rr)

    try:
      # Use explicit create_take_profit if connector supports it
      if hasattr(self.connector, 'create_take_profit'):
        result = self.connector.create_take_profit(pos_id, new_tp, instrument=pair)
        success = result is not None
      elif hasattr(self.connector, 'modify_trade'):
        payload = {'takeProfit': {'price': str(new_tp)}}
        result = self.connector.modify_trade(pos_id, payload)
        success = result is not None
      else:
        logger.warning("Connector lacks create_take_profit/modify_trade methods; cannot add TP for %s", pos_id)
        return False

      if success:
        _log_event('AUTO_TP_CREATED', {
          'position_id': pos_id,
          'instrument': pair,
          'side': side,
          'entry_price': entry_price,
          'new_tp': new_tp,
          'profit_pips': profit_pips,
          'trigger_pips': trigger,
        })
        logger.info("AUTO_TP_CREATED %s %s TP=%.5f (profit=%.2f pips)", pos_id, pair, new_tp, profit_pips)
        return True
    except Exception as e:
      logger.error(f"Failed to create AUTO TP for {pos_id}: {e}")
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

    cfg = self._config_for_strategy(pos.get('strategy'))
    if hard:
      max_sec = int(cfg.get('MAX_HOLD_SECONDS', self.config['MAX_HOLD_SECONDS']))
    else:
      # For soft, allow using MAX_TRADE_HOURS (hours -> seconds) or SOFT_MAX_HOLD_SECONDS
      if 'SOFT_MAX_HOLD_SECONDS' in cfg:
        max_sec = int(cfg.get('SOFT_MAX_HOLD_SECONDS', self.config.get('SOFT_MAX_HOLD_SECONDS', 0)))
      else:
        max_sec = float(cfg.get('MAX_TRADE_HOURS', self.config['MAX_TRADE_HOURS'])) * 3600.0

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
    cfg = self._config_for_strategy(pos.get('strategy'))
    trigger = float(cfg.get('PROFIT_LOCK_TRIGGER_PCT', self.config['PROFIT_LOCK_TRIGGER_PCT']))
    giveback = float(cfg.get('GIVEBACK_PCT', self.config['GIVEBACK_PCT']))

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

  # =========================================================================
  # QUANT HEDGING - LOSS RECAPTURE
  # =========================================================================
  
  def _check_hedge_opportunity(self, pos: Dict[str, Any], profit_pips: float, 
                               current_price: float) -> Optional[Dict[str, Any]]:
    """
    Check if a losing position should be hedged.
    Uses the GoalPursuitEngine's hedge logic.
    """
    try:
      from multi_broker_phoenix.risk.goal_pursuit_engine import check_for_hedge
      
      pos_id = pos.get('id', pos.get('trade_id', 'unknown'))
      pair = pos.get('instrument', '')
      units = abs(float(pos.get('units', pos.get('currentUnits', 0))))
      side = 'BUY' if float(pos.get('units', pos.get('currentUnits', 0))) > 0 else 'SELL'
      entry_price = float(pos.get('price', pos.get('averagePrice', 0)))
      
      hedge = check_for_hedge(
        trade_id=pos_id,
        symbol=pair,
        side=side,
        units=units,
        entry_price=entry_price,
        current_price=current_price
      )
      
      if hedge:
        return {
          'original_trade_id': hedge.original_trade_id,
          'symbol': hedge.symbol,
          'hedge_side': hedge.hedge_side,
          'hedge_units': hedge.hedge_units,
          'hedge_entry': hedge.hedge_entry,
          'hedge_sl': hedge.hedge_sl,
          'hedge_tp': hedge.hedge_tp,
          'reason': hedge.reason,
          'current_loss_pips': hedge.current_loss_pips
        }
      return None
      
    except Exception as e:
      logger.error(f"Hedge check error: {e}")
      return None

  def _execute_hedge(self, hedge: Dict[str, Any]) -> bool:
    """Execute a hedge trade."""
    try:
      from multi_broker_phoenix.risk.goal_pursuit_engine import get_goal_engine
      
      symbol = hedge['symbol']
      side = hedge['hedge_side']
      units = int(hedge['hedge_units'])
      sl = hedge['hedge_sl']
      tp = hedge['hedge_tp']
      
      # Print hedge execution announcement
      print(f"\n{'🔄'*20}")
      print(f"🛡️ EXECUTING QUANT HEDGE")
      print(f"{'🔄'*20}")
      print(f"   Original losing {symbol} → Opening {side} hedge")
      print(f"   • Size: {units} units")
      print(f"   • Stop Loss: {sl:.5f}")
      print(f"   • Take Profit: {tp:.5f}")
      print(f"   • Goal: Recapture {hedge['current_loss_pips']*1.5:.1f} pips")
      print(f"{'='*60}\n")
      
      # Place the hedge order via connector
      if not hasattr(self.connector, 'place_order') and not hasattr(self.connector, 'submit_order'):
        logger.warning("Connector does not support order placement for hedge")
        return False
      
      # Create hedge order
      signed_units = units if side == 'BUY' else -units
      
      order_params = {
        'instrument': symbol,
        'units': str(signed_units),
        'type': 'MARKET',
        'stopLossOnFill': {'price': str(sl), 'timeInForce': 'GTC'},
        'takeProfitOnFill': {'price': str(tp), 'timeInForce': 'GTC'},
      }
      
      if hasattr(self.connector, 'submit_order'):
        # Preferred unified interface
        try:
          result = self.connector.submit_order(order_params)
        except TypeError as e:
          logger.warning(f"submit_order signature mismatch, falling back: {e}")
          result = None
      elif hasattr(self.connector, 'place_order'):
        # Adapt to multiple place_order signatures across connectors
        try:
          import inspect
          sig = inspect.signature(self.connector.place_order)
          params = list(sig.parameters.keys())

          # Common connector variants:
          # 1) place_order(order_dict)
          # 2) place_order(symbol, side, units, ...)
          # 3) place_order(candidate, units, ...)

          if params and len(params) >= 2 and ('symbol' in params or 'candidate' not in params and 'units' in params):
            # Try calling (symbol, side, units) first
            try:
              result = self.connector.place_order(symbol, side, units)
            except Exception:
              # Fallback to dict-based call
              result = self.connector.place_order(order_params)
          else:
            # Default to dict-based call
            result = self.connector.place_order(order_params)
        except Exception as e:
          # Best-effort fallback if signature inspection fails
          logger.warning(f"place_order adaptive call failed, attempting dict call: {e}")
          try:
            result = self.connector.place_order(order_params)
          except Exception as e2:
            logger.error(f"Final hedge place_order attempt failed: {e2}")
            result = None
      else:
        return False

      if result:
        # Track hedge in goal engine
        engine = get_goal_engine()
        engine.active_hedges[hedge['original_trade_id']] = {
          'hedge_trade_id': result.get('id', 'unknown') if isinstance(result, dict) else 'unknown',
          'symbol': symbol,
          'side': side,
          'units': units,
          'entry': hedge['hedge_entry'],
          'placed_at': time.time()
        }
        engine.state.hedges_placed += 1
        
        print(f"✅ HEDGE PLACED SUCCESSFULLY!")
        _log_event('HEDGE_PLACED', {
          'original_trade_id': hedge['original_trade_id'],
          'symbol': symbol,
          'side': side,
          'units': units,
          'loss_pips': hedge['current_loss_pips']
        })
        return True
      
      return False
      
    except Exception as e:
      logger.error(f"Hedge execution error: {e}")
      return False

  def _modify_trade_sl(self, trade_id: str, new_sl: float) -> bool:
    try:
      if hasattr(self.connector, 'modify_trade'):
        result = self.connector.modify_trade(trade_id, stopLoss={'price': str(new_sl)})
        return result is not None
      if hasattr(self.connector, 'update_stop_loss'):
        return self.connector.update_stop_loss(trade_id, new_sl)
      if not self._warned_no_modify:
        logger.warning("No trade modification method found on connector (this warning logs once)")
        self._warned_no_modify = True
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
      if not self._warned_no_close:
        logger.warning("No trade close method found on connector (this warning logs once)")
        self._warned_no_close = True
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
