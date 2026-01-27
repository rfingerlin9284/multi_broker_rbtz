"""Always-on connection watchdog for brokers and AI services."""
from __future__ import annotations
import threading
import time
import requests
import logging
import os
import subprocess
import json
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

try:
  from ai_router.router import AIRouter
except Exception:
  AIRouter = None

logger = logging.getLogger(__name__)

WATCHDOG_STATE: Dict[str, Any] = {
  'ok': True,
  'last_check': None,
  'details': {}
}

_TRADING_ALLOWED = True
_RECONNECT_CALLBACKS: list = []


def _log_event(event_type: str, details: Dict[str, Any]):
  try:
    from . import pnl_kill_switch as pk
    pk._log_event(event_type, details)
  except Exception:
    try:
      logger.info('EVENT: %s %s', event_type, details)
    except Exception:
      pass


def register_reconnect_callback(cb):
  try:
    if callable(cb):
      _RECONNECT_CALLBACKS.append(cb)
      return True
  except Exception:
    pass
  return False


def unregister_reconnect_callback(cb):
  try:
    if cb in _RECONNECT_CALLBACKS:
      _RECONNECT_CALLBACKS.remove(cb)
      return True
  except Exception:
    pass
  return False


def trading_allowed() -> bool:
  return _TRADING_ALLOWED


def _set_trading_allowed(val: bool):
  global _TRADING_ALLOWED
  _TRADING_ALLOWED = bool(val)


def _check_oanda(oanda_connector) -> bool:
  try:
    r = oanda_connector.verify_credentials()
    return r.get('success', False)
  except Exception:
    return False


def _env_bool(key: str, default: str = 'false') -> bool:
  val = (os.getenv(key, default) or '').strip().lower()
  return val in ('1', 'true', 'yes', 'y', 'on')


def _load_hive_endpoints() -> Dict[str, Any]:
  path = os.getenv('HIVE_ENDPOINTS_FILE', 'config/hive_endpoints.json')
  try:
    with open(path, 'r') as f:
      return json.load(f) or {}
  except Exception:
    return {}


def _normalize_base_url(base_url: Optional[str]) -> str:
  url = (base_url or '').strip()
  if not url:
    return url
  url = url.rstrip('/')
  while '/v1/v1' in url:
    url = url.replace('/v1/v1', '/v1')
  return url


def _join_url(base_url: Optional[str], path: str) -> str:
  base = _normalize_base_url(base_url)
  if not path:
    return base
  if not path.startswith('/'):
    path = '/' + path
  return base + path


def _write_hive_endpoints(data: Dict[str, Any]) -> None:
  path = os.getenv('HIVE_ENDPOINTS_FILE', 'config/hive_endpoints.json')
  try:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, 'w') as f:
      json.dump(data, f, indent=2)
  except Exception:
    pass


def _maybe_fix_xai_endpoint(xai_url: Optional[str], details: Dict[str, Any]) -> None:
  try:
    data = _load_hive_endpoints()
    xai_cfg = data.get('xai', {})
    base_url = xai_cfg.get('base_url') or os.getenv('XAI_BASE_URL') or os.getenv('XAI_API_URL')
    if not base_url:
      return
    normalized = _normalize_base_url(base_url)
    if base_url and normalized != base_url:
      xai_cfg['base_url'] = normalized
      data['xai'] = xai_cfg
      _write_hive_endpoints(data)
      details['xai_endpoint_repair'] = {'old': base_url, 'new': normalized}
      _log_event('XAI_ENDPOINT_REPAIR', {'old': base_url, 'new': normalized})
  except Exception:
    pass


def _check_endpoint(url: str, timeout: float = 5.0, headers: Optional[Dict[str, str]] = None) -> Tuple[bool, Optional[int], Optional[str]]:
  try:
    r = requests.get(url, timeout=timeout, headers=headers)
    code = getattr(r, 'status_code', None)
    if code == 200:
      return True, code, 'OK'
    if code in (401, 403):
      return False, code, 'AUTH_FAIL'
    return False, code, f'HTTP_{code}'
  except Exception as e:
    return False, None, f'EXCEPTION_{str(e)}'


def _state_age_seconds(path: str) -> Optional[float]:
  try:
    p = Path(path)
    if not p.exists():
      return None
    return time.time() - p.stat().st_mtime
  except Exception:
    return None


def heartbeat_status() -> Dict[str, Any]:
  max_skew = int(os.getenv('HEARTBEAT_MAX_SKEW_SEC', '180'))
  enforce_missing = os.getenv('HEARTBEAT_ENFORCE_MISSING', '0').lower() in ('1', 'true', 'yes')
  exit_state = os.getenv('HEARTBEAT_EXIT_STATE_FILE', 'ops/state/exit_manager_state.json')
  protect_state = os.getenv('HEARTBEAT_PROTECT_STATE_FILE', 'ops/state/protect_loop.json')
  watchdog_state = os.getenv('HEARTBEAT_WATCHDOG_STATE_FILE', 'ops/state/watchdog.json')

  ages = {
    'exit_manager': _state_age_seconds(exit_state),
    'protect_loop': _state_age_seconds(protect_state),
    'watchdog': _state_age_seconds(watchdog_state),
  }

  stale = []
  for k, age in ages.items():
    if age is None and not enforce_missing:
      continue
    if age is None or age > max_skew:
      stale.append(k)

  return {
    'ok': len(stale) == 0,
    'max_skew_sec': max_skew,
    'enforce_missing': enforce_missing,
    'ages_sec': ages,
    'stale': stale,
  }


def _write_watchdog_state() -> None:
  path = os.getenv('HEARTBEAT_WATCHDOG_STATE_FILE', 'ops/state/watchdog.json')
  try:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, 'w') as f:
      f.write(str(int(time.time())))
  except Exception:
    pass


def _failsafe_flatten(oanda_connector, reason: str, details: Dict[str, Any]) -> bool:
  try:
    from execution.oanda_practice_client import OandaPracticeClient
    client = OandaPracticeClient(
      token=oanda_connector.token,
      account_id=oanda_connector.account_id,
      base_url=oanda_connector.base_url,
      http_client=getattr(oanda_connector, 'http', None)
    )
    res = client.close_all_positions()
    _log_event('HEARTBEAT_FAILSAFE_FLATTEN', {'reason': reason, 'details': details, 'result': res})
    _set_trading_allowed(False)
    return True
  except Exception as e:
    _log_event('HEARTBEAT_FAILSAFE_ERROR', {'reason': reason, 'error': str(e)})
    try:
      _set_trading_allowed(False)
    except Exception:
      pass
    return False


def _maybe_run_repair(ai_details: Dict[str, Any]) -> None:
  if os.getenv('AI_REPAIR_ENABLED', '1').lower() not in ('1', 'true', 'yes'):
    return
  state_file = os.getenv('AI_REPAIR_LAST_FILE', 'ops/state/ai_repair_last.json')
  min_interval = int(os.getenv('AI_REPAIR_MIN_INTERVAL', '300'))
  now = time.time()

  last_ts = 0.0
  try:
    with open(state_file, 'r') as f:
      last_ts = float(json.load(f).get('last_ts', 0.0))
  except Exception:
    last_ts = 0.0

  if now - last_ts < min_interval:
    return

  script = '/home/ing/RICK/MULTI_BROKER_PHOENIX/tools/ai_repair.sh'
  try:
    res = subprocess.run([script], check=False, capture_output=True, text=True)
    with open(state_file, 'w') as f:
      json.dump({'last_ts': now, 'exit_code': res.returncode}, f)
    _log_event('AI_REPAIR_TRIGGER', {'exit_code': res.returncode})
  except Exception as e:
    _log_event('AI_REPAIR_ERROR', {'error': str(e)})


def _log_freeze_change(ok: bool, details: Dict[str, Any]):
  ts = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
  if not ok:
    logger.critical('WATCHDOG FREEZE %s - details=%s', ts, details)
  else:
    logger.info('WATCHDOG UNFREEZE %s - details=%s', ts, details)


def resolve_ai_health_urls() -> Tuple[Optional[str], Optional[str]]:
  """Resolve health URLs for Grok/XAI and DeepSeek.

  Returns (grok_url, deepseek_url).
  """
  cfg = _load_hive_endpoints()

  grok_url = os.getenv('GROK_HEALTH_URL')
  if not grok_url:
    xai_base = os.getenv('XAI_BASE_URL') or os.getenv('XAI_API_URL') or (cfg.get('xai', {}) or {}).get('base_url')
    xai_path = (cfg.get('xai', {}) or {}).get('health_path', '/v1/models')
    if xai_base:
      grok_url = _join_url(xai_base, xai_path)

  deepseek_url = os.getenv('DEEPSEEK_HEALTH_URL')
  if not deepseek_url:
    deepseek_base = os.getenv('DEEPSEEK_BASE_URL') or (cfg.get('deepseek', {}) or {}).get('base_url', 'https://api.deepseek.com/v1')
    deepseek_path = (cfg.get('deepseek', {}) or {}).get('health_path', '/models')
    deepseek_url = _join_url(deepseek_base, deepseek_path)

  return grok_url, deepseek_url


def _resolve_openai_url() -> Optional[str]:
  cfg = _load_hive_endpoints()
  openai_url = os.getenv('OPENAI_HEALTH_URL')
  if not openai_url:
    openai_base = os.getenv('OPENAI_BASE_URL') or (cfg.get('openai', {}) or {}).get('base_url', 'https://api.openai.com/v1')
    openai_path = (cfg.get('openai', {}) or {}).get('health_path', '/models')
    openai_url = _join_url(openai_base, openai_path)
  return openai_url


def run_watchdog_once(oanda_connector, grok_url: Optional[str], deepseek_url: Optional[str], invoke_callbacks_async: bool = True) -> Dict[str, Any]:
  details: Dict[str, Any] = {}
  ok = True

  try:
    o_ok = _check_oanda(oanda_connector)
    details['oanda'] = {'ok': bool(o_ok)}
    if not o_ok:
      ok = False
  except Exception as e:
    details['oanda'] = {'ok': False, 'reason': str(e)}
    ok = False
    logger.exception('Watchdog OANDA check failed: %s', e)

  require_ai = _env_bool('REQUIRE_AI', '0')
  require_xai = _env_bool('REQUIRE_XAI', os.getenv('REQUIRE_GROK', 'false'))
  require_deepseek = _env_bool('REQUIRE_DEEPSEEK', 'false')
  require_openai = _env_bool('REQUIRE_OPENAI', 'false')
  require_ollama = _env_bool('REQUIRE_OLLAMA', 'true')
  min_brain_seats = int(os.getenv('MIN_BRAIN_SEATS', '1'))

  ai_ok = True
  local_ok = False
  cloud_ok = False
  seat_details: Dict[str, Any] = {}

  enabled_seats = {
    'xai': bool(require_xai or (grok_url is not None)),
    'deepseek': bool(require_deepseek or (deepseek_url is not None)),
    'openai': bool(require_openai),
    'ollama': bool(require_ollama),
  }

  if require_ai or any(enabled_seats.values()):
    healthy_count = 0
    enabled_count = 0

    if enabled_seats.get('xai'):
      enabled_count += 1
      if not grok_url:
        grok_url, _ = resolve_ai_health_urls()
      headers = None
      if os.getenv('XAI_API_KEY'):
        headers = {'Authorization': f"Bearer {os.getenv('XAI_API_KEY')}"}
      x_ok, x_code, x_reason = _check_endpoint(grok_url, timeout=5.0, headers=headers) if grok_url else (False, None, 'NO_URL')
      seat_details['grok'] = {'ok': x_ok, 'code': x_code, 'reason': x_reason, 'url': grok_url}
      if x_code == 404:
        _maybe_fix_xai_endpoint(grok_url, seat_details['grok'])
      if x_ok:
        healthy_count += 1

    if enabled_seats.get('deepseek'):
      enabled_count += 1
      if not deepseek_url:
        _, deepseek_url = resolve_ai_health_urls()
      headers = None
      if os.getenv('DEEPSEEK_API_KEY'):
        headers = {'Authorization': f"Bearer {os.getenv('DEEPSEEK_API_KEY')}"}
      d_ok, d_code, d_reason = _check_endpoint(deepseek_url, timeout=5.0, headers=headers) if deepseek_url else (False, None, 'NO_URL')
      seat_details['deepseek'] = {'ok': d_ok, 'code': d_code, 'reason': d_reason, 'url': deepseek_url}
      if d_code in (401, 403):
        seat_details['deepseek']['auth_action'] = 'check DEEPSEEK_API_KEY'
        _log_event('DEEPSEEK_AUTH_FAIL', {'reason': d_reason, 'code': d_code, 'action': 'check DEEPSEEK_API_KEY'})
        enabled_seats['deepseek'] = False
        enabled_count -= 1
      if d_ok:
        healthy_count += 1

    if enabled_seats.get('openai'):
      enabled_count += 1
      openai_url = _resolve_openai_url()
      headers = None
      if os.getenv('OPENAI_API_KEY'):
        headers = {'Authorization': f"Bearer {os.getenv('OPENAI_API_KEY')}"}
      o_ok, o_code, o_reason = _check_endpoint(openai_url, timeout=5.0, headers=headers) if openai_url else (False, None, 'NO_URL')
      seat_details['openai'] = {'ok': o_ok, 'code': o_code, 'reason': o_reason, 'url': openai_url}
      if o_ok:
        healthy_count += 1

    if enabled_seats.get('ollama'):
      enabled_count += 1
      try:
        from multi_broker_phoenix.llm import ollama_client
        o_health = ollama_client.health(timeout=2.0)
        seat_details['ollama'] = o_health
        if o_health.get('ok'):
          healthy_count += 1
          local_ok = True
      except Exception as e:
        seat_details['ollama'] = {'ok': False, 'reason': f'EXCEPTION_{str(e)}'}

    cloud_ok = bool(seat_details.get('grok', {}).get('ok') or seat_details.get('deepseek', {}).get('ok') or seat_details.get('openai', {}).get('ok'))
    details['ai_seats'] = seat_details
    if seat_details.get('grok'):
      details['grok'] = seat_details.get('grok')
    if seat_details.get('deepseek'):
      details['deepseek'] = seat_details.get('deepseek')
    details['ai_enabled_seats'] = enabled_seats
    details['ai_min_seats'] = min_brain_seats
    details['ai_healthy_count'] = healthy_count
    details['ai_enabled_count'] = enabled_count

    ai_ok = healthy_count >= max(1, min_brain_seats) if enabled_count > 0 else False
    if local_ok and not cloud_ok:
      _maybe_run_repair(seat_details)

    if not ai_ok:
      ok = False

  hb = heartbeat_status()
  details['heartbeat'] = hb
  if not hb.get('ok', True):
    ok = False
    if os.getenv('HEARTBEAT_FAILSAFE_FLATTEN', '1').lower() in ('1', 'true', 'yes'):
      try:
        _failsafe_flatten(oanda_connector, 'HEARTBEAT_STALE', hb)
      except Exception:
        pass

  action = 'ALLOW' if ok else 'FREEZE'
  logger.info('WATCHDOG: ai_ok=%s local_ok=%s cloud_ok=%s action=%s', ai_ok, local_ok, cloud_ok, action)

  prev_ok = WATCHDOG_STATE.get('ok', True)
  WATCHDOG_STATE['ok'] = ok
  WATCHDOG_STATE['last_check'] = time.time()
  WATCHDOG_STATE['details'] = details

  if not ok:
    _set_trading_allowed(False)
  else:
    _set_trading_allowed(True)

  _write_watchdog_state()

  if not prev_ok and ok:
    try:
      _log_event('WATCHDOG_UNFREEZE', {'details': details, 'timestamp': WATCHDOG_STATE.get('last_check')})
    except Exception:
      logger.exception('Watchdog: failed to record WATCHDOG_UNFREEZE event')

    try:
      for cb in list(_RECONNECT_CALLBACKS):
        try:
          if invoke_callbacks_async:
            threading.Thread(target=lambda c=cb: c(oanda_connector), daemon=True).start()
          else:
            c = cb
            c(oanda_connector)
        except Exception:
          logger.exception('Watchdog: failed to start/invoke reconnect callback')
    except Exception:
      logger.exception('Watchdog: failed to invoke reconnect callbacks')
  elif not ok and prev_ok:
    try:
      _log_event('WATCHDOG_FREEZE', {'details': details, 'timestamp': WATCHDOG_STATE.get('last_check')})
    except Exception:
      logger.exception('Watchdog: failed to record WATCHDOG_FREEZE event')

  _log_event('WATCHDOG_TICK', {'details': details, 'timestamp': WATCHDOG_STATE.get('last_check')})
  _log_freeze_change(ok, details)

  return dict(WATCHDOG_STATE)


def _run_watchdog(oanda_connector, grok_url: str | None, deepseek_url: str | None, interval: int = 15):
  while True:
    try:
      run_watchdog_once(oanda_connector, grok_url, deepseek_url)
    except Exception:
      logger.exception('Watchdog iteration failed')
    time.sleep(interval)


def start_watchdog(oanda_connector, grok_url: str | None = None, deepseek_url: str | None = None, interval: int = 15):
  t = threading.Thread(target=_run_watchdog, args=(oanda_connector, grok_url, deepseek_url, interval), daemon=True, name='watchdog')
  t.start()
  return t
