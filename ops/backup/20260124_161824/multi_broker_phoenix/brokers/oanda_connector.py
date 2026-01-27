"""OANDA connector with modular paper/live toggles.

Supports both practice (paper) and live trading by switching API hosts and
order methods based on constructor args or environment variables:

- ``practice_mode``: defaults to True unless explicitly set to False or
    overridden by env ``OANDA_MODE=LIVE`` / ``BROKER_MODE_OANDA=LIVE`` /
    ``OANDA_PRACTICE=false``.
- ``TRADING_MODE``: if set to ``LIVE`` but practice_mode=True, a warning is
    logged to surface misconfiguration.

Environment hints (all optional):
- ``OANDA_API_TOKEN`` / ``OANDA_ACCOUNT_ID``
- ``OANDA_API_URL`` (overrides host), ``OANDA_STREAM_URL``
- ``OANDA_MODE`` or ``BROKER_MODE_OANDA``: ``LIVE`` | ``PAPER``/``PRACTICE``
- ``OANDA_PRACTICE``: ``true``/``false`` convenience flag
"""
from __future__ import annotations
import os
import requests
import time
import logging
import json
from pathlib import Path
from typing import Optional, Any, Dict

logger = logging.getLogger(__name__)


def _import_oanda_practice_client():
    """Import OandaPracticeClient with a path fallback for execution/ package.

    This guards against environments where the repo root is missing from sys.path.
    """
    try:
        from execution.oanda_practice_client import OandaPracticeClient
        return OandaPracticeClient
    except Exception:
        try:
            import sys
            from pathlib import Path
            repo_root = Path(__file__).resolve().parents[3]
            if str(repo_root) not in sys.path:
                sys.path.insert(0, str(repo_root))
            from execution.oanda_practice_client import OandaPracticeClient
            return OandaPracticeClient
        except Exception:
            return None

# === RBOTZILLA_PAPER_AUTO_BRACKET (auto) ===
def _rbot_get_int(env_value: str | None, default: int) -> int:
    try:
        return int(str(env_value).strip())
    except Exception:
        return default


def _rbot_maybe_autofill_bracket(candidate: Any) -> Any:
    import os
    auto = str(os.getenv('PAPER_AUTO_BRACKET', '0')).strip().lower() in ('1', 'true', 'yes', 'y')
    if not auto:
        return candidate

    sl = _rbot_get_attr(candidate, ['stop_loss', 'stop', 'stoploss'])
    tp = _rbot_get_attr(candidate, ['take_profit', 'takeprofit'])
    if sl is not None and tp is not None:
        return candidate

    price = _rbot_get_attr(candidate, ['price', 'entry_price', 'entry'])
    side_val = _rbot_get_attr(candidate, ['side', 'direction'])
    side = str(side_val).upper() if side_val else ''
    if price is None or side not in ('BUY', 'SELL'):
        return candidate

    sl_pips = _rbot_get_int(os.getenv('PAPER_SL_PIPS', '20'), 20)
    tp_pips = _rbot_get_int(os.getenv('PAPER_TP_PIPS', '40'), 40)
    sym = _rbot_get_attr(candidate, ['symbol', 'instrument']) or ''
    
    # Use centralized pip_math for consistent pip size calculation
    try:
        from multi_broker_phoenix.risk.pip_math import pip_size as get_pip_size
        pip_size = get_pip_size(sym)
    except ImportError:
        # Fallback to inline calculation if pip_math not available
        pip_size = 0.01 if 'JPY' in sym.upper() else 0.0001

    price_f = float(price)
    sl_price = (price_f - sl_pips * pip_size) if side == 'BUY' else (price_f + sl_pips * pip_size)
    tp_price = (price_f + tp_pips * pip_size) if side == 'BUY' else (price_f - tp_pips * pip_size)

    if sl is None:
        _rbot_set_attr(candidate, 'stop_loss', round(sl_price, 6))
    if tp is None:
        _rbot_set_attr(candidate, 'take_profit', round(tp_price, 6))
    _rbot_set_attr(candidate, 'rbot_autobracket', True)
    return candidate


def _rbot_get_attr(candidate: Any, keys: list[str]) -> Optional[Any]:
    for key in keys:
        if isinstance(candidate, dict) and key in candidate:
            return candidate[key]
        attr = getattr(candidate, key, None)
        if attr is not None:
            return attr
    return None


def _rbot_set_attr(candidate: Any, key: str, value: Any) -> None:
    if isinstance(candidate, dict):
        candidate[key] = value
    else:
        setattr(candidate, key, value)


def _fmt_price(instrument: str, price: float) -> str:
    """Format a price for OANDA payloads.

    Controlled by FEATURE_FLAGS['OANDA_ADVANCED']['ENABLE_PRICE_PRECISION'].
    - JPY-denominated instruments use 3 decimals, others 5 decimals when enabled.
    - When disabled, fall back to 5 decimals for all instruments (legacy behavior).
    """
    try:
        from global_config import FEATURE_FLAGS as _FF
        enabled = _FF.get('OANDA_ADVANCED', {}).get('ENABLE_PRICE_PRECISION', True)
    except Exception:
        enabled = True

    try:
        inst = str(instrument or '').strip().upper()
        if enabled:
            dp = 3 if inst.endswith('_JPY') or inst.endswith('JPY') or '_JPY' in inst else 5
        else:
            dp = 5
        return f"{float(price):.{dp}f}"
    except Exception:
        return f"{float(price):.5f}"


class OANDAConnector:
    def __init__(self, token: Optional[str] = None, account_id: Optional[str] = None, base_url: Optional[str] = None, engine: Optional[Any] = None, fee_pct: float = 0.0, slippage_pct: float = 0.0, practice_mode: Optional[bool] = None, http_client: Optional[Any] = None):
        """Initialize connector with modular paper/live controls.

        Args:
            token: API token (defaults to ``OANDA_API_TOKEN``)
            account_id: Account ID (defaults to ``OANDA_ACCOUNT_ID``)
            base_url: Explicit API host override. If not provided, switches between
                      practice/live hosts based on ``practice_mode``.
            engine: Optional paper engine for simulated fills.
            practice_mode: When True, routes to fxpractice + uses paper order path.
                           When False, uses fxtrade + live order path. If None,
                           deduced from env (``OANDA_MODE``, ``BROKER_MODE_OANDA``,
                           ``OANDA_PRACTICE``, falling back to TRADING_MODE).
            http_client: Optional injected HTTP client (must expose get/post).
        """
        trading_mode = os.getenv('TRADING_MODE', 'PAPER').upper()
        mode_env = (os.getenv('OANDA_MODE') or os.getenv('BROKER_MODE_OANDA') or '').upper()
        practice_flag_env = os.getenv('OANDA_PRACTICE', '').lower()

        # Determine practice_mode precedence: explicit arg > mode envs > practice flag > trading_mode
        if practice_mode is None:
            if mode_env in ('LIVE', 'REAL'):
                practice_mode = False
            elif mode_env in ('PAPER', 'PRACTICE'):
                practice_mode = True
            elif practice_flag_env in ('true', '1', 'yes', 'y'):
                practice_mode = True
            elif practice_flag_env in ('false', '0', 'no', 'n'):
                practice_mode = False
            else:
                practice_mode = trading_mode != 'LIVE'

        self.token = token or os.getenv('OANDA_API_TOKEN')
        self.account_id = account_id or os.getenv('OANDA_ACCOUNT_ID')
        self.practice_mode = bool(practice_mode)
        self.paper_mode = self.practice_mode  # alias for consistency with other connectors

        # default base_url depends on practice_mode unless explicitly provided
        if base_url:
            self.base_url = base_url
        else:
            self.base_url = os.getenv('OANDA_API_URL', 'https://api-fxpractice.oanda.com' if self.practice_mode else 'https://api-fxtrade.oanda.com')
        # stream base (optional)
        self.stream_base = os.getenv('OANDA_STREAM_URL', 'https://stream-fxpractice.oanda.com' if self.practice_mode else 'https://stream-fxtrade.oanda.com')
        self.engine = engine
        self.fee_pct = float(fee_pct)
        self.slippage_pct = float(slippage_pct)
        # injection point: use provided http_client or fall back to requests module
        self.http = http_client or requests
        self.last_price: Dict[str, float] = {}
        self.last_price_ts: Dict[str, float] = {}
        self.connected = False

        mode_str = 'PRACTICE/PAPER' if self.practice_mode else 'LIVE'
        logger.info(f"🔧 OANDA connector initialized: {mode_str} | base_url={self.base_url}")
        if trading_mode == 'LIVE' and self.practice_mode:
            logger.warning("⚠️  TRADING_MODE=LIVE but OANDA practice_mode=True (paper). Set OANDA_MODE=LIVE to enable live trades.")


    def _headers(self):
        return {'Authorization': f'Bearer {self.token}', 'Content-Type': 'application/json'}

    def status(self) -> Dict[str, Any]:
        return {
            'creds_present': bool(self.token and self.account_id),
            'practice_mode': self.practice_mode,
            'paper_mode': self.paper_mode,
            'base_url': self.base_url,
            'stream_base': self.stream_base,
            'connected': self.connected,
            'last_price_ts': self.last_price_ts
        }

    def get_last_price(self, instrument: str) -> Optional[float]:
        # OANDA expects instrument like EUR_USD
        # Simple retry loop to tolerate transient errors
        tries = 3
        for attempt in range(tries):
            try:
                resp = self.http.get(f"{self.base_url}/v3/accounts/{self.account_id}/pricing", params={'instruments': instrument}, headers=self._headers(), timeout=5)
                resp.raise_for_status()
                data = resp.json()
                prices = data.get('prices', [])
                if not prices:
                    return self.last_price.get(instrument)
                p = prices[0]
                bid = float(p.get('closeoutBid', 0.0))
                ask = float(p.get('closeoutAsk', 0.0))
                last = (bid + ask) / 2.0
                self.last_price[instrument] = last
                self.last_price_ts[instrument] = time.time()
                self.connected = True
                return last
            except Exception as exc:
                logger.debug('get_last_price attempt %s failed: %s', attempt, exc)
                time.sleep(0.1 * (attempt + 1))
                continue
        # fallback to last known or None
        return self.last_price.get(instrument)

    def get_historical_data(self, instrument: str, count: int = 50, granularity: str = 'M5') -> list:
        """Fetch historical candle data from OANDA.
        
        Args:
            instrument: OANDA instrument (e.g., 'EUR_USD')
            count: Number of candles to fetch
            granularity: Candle size (S5, S10, S15, S30, M1, M2, M4, M5, M10, M15, M30, H1, H2, H3, H4, H6, H8, H12, D, W, M)
        
        Returns:
            List of candle dictionaries with 'mid' prices
        """
        try:
            url = f"{self.base_url}/v3/instruments/{instrument}/candles"
            params = {
                'count': count,
                'granularity': granularity,
                'price': 'M'  # Mid prices
            }
            resp = self.http.get(url, headers=self._headers(), params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return data.get('candles', [])
        except Exception as exc:
            logger.warning(f'OANDA historical data failed for {instrument}: {exc}')
            return []

    def update_price(self, instrument: str, price: float):
        self.last_price[instrument] = float(price)

    def _build_order_payload(self, candidate: Any, units: int) -> Dict[str, Any]:
        side = getattr(candidate, 'side', 'BUY')
        units = int(units) if side == 'BUY' else -int(units)
        return {
            'order': {
                'units': str(units),
                'instrument': getattr(candidate, 'symbol', 'EUR_USD'),
                'timeInForce': 'FOK',
                'type': 'MARKET',
                'positionFill': 'DEFAULT'
            }
        }

    def _post_order(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}/v3/accounts/{self.account_id}/orders"
        tries = 3
        last_exc = None
        r = None
        for attempt in range(tries):
            try:
                r = self.http.post(url, headers=self._headers(), json=payload, timeout=10)
                r.raise_for_status()
                body = r.json()
                order_id = body.get('orderCreateTransaction', {}).get('id') or body.get('orderFillTransaction', {}).get('orderID')
                filled_price = (body.get('orderFillTransaction', {}) or {}).get('price')
                return {
                    'success': True,
                    'id': order_id,
                    'platform': 'OANDA',
                    'symbol': payload['order'].get('instrument'),
                    'fill': body,
                    'filled_price': float(filled_price) if filled_price else None,
                    'status': 'OK'
                }
            except Exception as exc:
                last_exc = exc
                # TEMP DEBUG: if response available, print status and body for diagnostics
                if r is not None and getattr(r, 'status_code', None) is not None:
                    try:
                        print(f"   ⚠️ OANDA HTTP STATUS: {r.status_code}")
                        body = (r.text or '')[:2000]
                        print(f"   ⚠️ OANDA BODY: {body}")
                    except Exception:
                        pass
                logger.warning('OANDA order attempt %s failed: %s', attempt, exc)
                time.sleep(0.2 * (attempt + 1))
        return {'success': False, 'error': f'OANDA order failed after {tries} attempts', 'status': 'ERROR', 'exception': str(last_exc)}

    def flatten_positions(self) -> Dict[str, Any]:
        """Flatten (close) all open positions via the practice client. Returns per-instrument results."""
        try:
            client_cls = _import_oanda_practice_client()
            if client_cls is None:
                raise RuntimeError("OandaPracticeClient import failed")
            client = client_cls(token=self.token, account_id=self.account_id, base_url=self.base_url, http_client=self.http)
            res = client.close_all_positions()
            return res
        except Exception as e:
            logger.exception('FLATTEN positions failed: %s', e)
            return {'error': str(e)}

    def place_paper_order(self, candidate: Any, units: int) -> Dict[str, Any]:
        """Place a market order on the practice account (platform-paper).

        Uses the centralized `execution.oanda_practice_client.OandaPracticeClient` to
        ensure the request hits the practice host and that an OCO (SL + TP) bracket
        is attached. If SL/TP are missing the order will be refused. This method
        enforces the global watchdog freeze gate and performs a post-order
        verification (trailing-truth / OCO verification) that will trigger a
        system freeze if verification fails.
        """
        # Enforce WATCHDOG gate at the connector level (single submit gate)
        try:
            from multi_broker_phoenix.monitor.watchdog import trading_allowed as _watchdog_trading_allowed, _set_trading_allowed as _watchdog_set
            if not _watchdog_trading_allowed():
                raise RuntimeError('BLOCKED_BY_WATCHDOG: new trades currently frozen')
        except RuntimeError:
            raise
        except Exception:
            # If watchdog is unavailable, proceed but warn
            logger.warning('WATCHDOG: check unavailable; proceeding with order placement')

        # Enforce BROKER_HEALTH gate - no trading while disconnected
        try:
            from multi_broker_phoenix.risk.broker_health import is_healthy, is_trading_allowed
            if not is_healthy():
                raise RuntimeError('BLOCKED_BY_BROKER_HEALTH: broker unhealthy, no new trades')
            if not is_trading_allowed():
                raise RuntimeError('BLOCKED_BY_BROKER_HEALTH: trading not allowed (post-reconnect reconcile required)')
        except RuntimeError:
            raise
        except ImportError:
            # If broker_health module not available, proceed but warn
            logger.warning('BROKER_HEALTH: module unavailable; proceeding without health check')
        except Exception as e:
            logger.warning(f'BROKER_HEALTH: check failed ({e}); proceeding with caution')

        if not self.token or not self.account_id:
            raise RuntimeError('OANDA credentials not configured')

        # Auto-fill bracket when allowed (without touching strategy logic)
        candidate = _rbot_maybe_autofill_bracket(candidate)
        # Enforce OCO bracket presence: candidate must provide stop_loss and take_profit
        sl_price = getattr(candidate, 'stop_loss', None)
        tp_price = getattr(candidate, 'take_profit', None)
        if sl_price is None or tp_price is None:
            raise RuntimeError('Orders must include stop_loss and take_profit (OCO bracket required)')

        # Ensure TP is within respectable bounds (pips) and RR within limits
        try:
            from multi_broker_phoenix.risk.pip_math import tp_distance_pips, calculate_rr_ratio
            instrument = getattr(candidate, 'symbol', getattr(candidate, 'instrument', 'EUR_USD'))
            entry_price = float(getattr(candidate, 'entry_price', getattr(candidate, 'price', 0)) or 0)
            if entry_price > 0:
                tp_pips = tp_distance_pips(entry_price, float(tp_price), instrument)
                min_tp = float(os.getenv('MIN_TP_PIPS', '20'))
                max_tp = float(os.getenv('MAX_TP_PIPS', '300'))
                if tp_pips < min_tp or tp_pips > max_tp:
                    raise RuntimeError(f'TP distance out of bounds: {tp_pips:.1f} pips (min={min_tp}, max={max_tp})')
                rr = calculate_rr_ratio(entry_price, float(sl_price), float(tp_price))
                min_rr = float(os.getenv('OCO_MIN_RR', '1.0'))
                max_rr = float(os.getenv('OCO_MAX_RR', '5.0'))
                if rr < min_rr or rr > max_rr:
                    raise RuntimeError(f'RR out of bounds: {rr:.2f} (min={min_rr}, max={max_rr})')
        except RuntimeError:
            raise
        except Exception:
            # If pip math fails, proceed but warn in logs
            logger.warning('TP distance verification failed; proceeding without bounds check')

        try:
            # Use the practice-only client (validates practice host and auth)
            client_cls = _import_oanda_practice_client()
            if client_cls is None:
                raise RuntimeError("OandaPracticeClient import failed")

            client = client_cls(
                token=self.token,
                account_id=self.account_id,
                base_url=self.base_url,
                http_client=self.http
            )
            # Support test factories that return the real client when the instance is callable
            if callable(client) and not hasattr(client, 'create_order_market'):
                try:
                    client = client()
                except Exception:
                    pass

            instrument = getattr(candidate, 'symbol', getattr(candidate, 'instrument', 'EUR_USD'))
            client_tag = getattr(candidate, 'client_tag', None)
            if not client_tag:
                strategy_id = getattr(candidate, 'strategy_id', None) or getattr(candidate, 'strategy', None)
                if strategy_id:
                    client_tag = str(strategy_id).replace(' ', '_')[:32]

            # Enforce trailing for new trades when configured
            trailing_expected = getattr(candidate, 'trailing', None) or getattr(candidate, 'trailing_distance', None)
            if trailing_expected is None and os.getenv('OANDA_TRAILING_ALWAYS', 'true').lower() in ('true', '1', 'yes'):
                trailing_expected = float(os.getenv('OANDA_TRAILING_STOP_PIPS', os.getenv('EXIT_TRAILING_DISTANCE_PIPS', '15')))
                try:
                    setattr(candidate, 'trailing_distance', trailing_expected)
                except Exception:
                    pass

            # Format SL/TP for instrument precision (JPY vs non-JPY)
            fmt_sl = _fmt_price(instrument, float(sl_price))
            fmt_tp = _fmt_price(instrument, float(tp_price))

            # Apply safe sizing caps per-instrument
            try:
                from global_config import FEATURE_FLAGS as _FF
                metrics_enabled = _FF.get('OANDA_ADVANCED', {}).get('ENABLE_METRICS_REPORTER', True)
            except Exception:
                metrics_enabled = True

            if metrics_enabled:
                try:
                    from multi_broker_phoenix.monitor.bot_metrics import incr, add_failure, set_last_trade
                except Exception:
                    incr = lambda *a, **k: None
                    add_failure = lambda *a, **k: None
                    set_last_trade = lambda *a, **k: None
            else:
                # No-op metrics when disabled
                incr = lambda *a, **k: None
                add_failure = lambda *a, **k: None
                set_last_trade = lambda *a, **k: None

            # Determine absolute units, clamp to per-instrument cap
            try:
                requested_units = int(abs(int(units)))
            except Exception:
                requested_units = max(1, int(float(units))) if units else 1

            # Read cap: prefer explicit env OANDA_MAX_UNITS_<INST>, then default
            inst_key = instrument.upper().replace('-', '_')
            def _env_cap_for(inst: str) -> Optional[int]:
                name = f'OANDA_MAX_UNITS_{inst}'
                val = os.getenv(name)
                if val:
                    try:
                        return int(val)
                    except Exception:
                        pass
                return None

            cap = _env_cap_for(inst_key)
            if cap is None:
                # defaults
                defaults = {
                    'DEFAULT': int(os.getenv('OANDA_MAX_UNITS_DEFAULT', '1000')),
                    'USD_JPY': int(os.getenv('OANDA_MAX_UNITS_USD_JPY', '200')),
                    'EUR_USD': int(os.getenv('OANDA_MAX_UNITS_EUR_USD', '1000')),
                    'GBP_USD': int(os.getenv('OANDA_MAX_UNITS_GBP_USD', '800')),
                    'AUD_USD': int(os.getenv('OANDA_MAX_UNITS_AUD_USD', '1200')),
                    'USD_CAD': int(os.getenv('OANDA_MAX_UNITS_USD_CAD', '1000')),
                }
                cap = defaults.get(inst_key, defaults['DEFAULT'])

            # Dynamic preflight: ask OANDA for account balance & margin, and price, to further reduce cap safely
            try:
                from global_config import FEATURE_FLAGS as _FF
                dyn_enabled = _FF.get('OANDA_ADVANCED', {}).get('ENABLE_DYNAMIC_CAP', True)
            except Exception:
                dyn_enabled = True

            if dyn_enabled:
                try:
                    safety = float(os.getenv('OANDA_MARGIN_SAFETY_FACTOR', '10'))
                    acct = client.get_account_summary().get('account', {})
                    balance = float(acct.get('balance', 0.0))
                    margin_rate = float(acct.get('marginRate', 1.0))
                    prices = client.get_prices([instrument]).get('prices', [])
                    if prices:
                        mid_price = float(prices[0].get('closeoutAsk') or prices[0].get('closeoutBid') or prices[0].get('closeoutAsk'))
                        # conservative allowed units estimate
                        dyn_allowed = max(1, int(balance / (mid_price * (margin_rate or 1.0) * safety)))
                        if dyn_allowed < cap:
                            logger.warning(f"[RBOTZILLA_SIZING] DYNAMIC_CAP_APPLIED: instrument={instrument} balance={balance} margin_rate={margin_rate} price={mid_price} safety={safety} dyn_allowed={dyn_allowed} (was cap={cap})")
                            cap = dyn_allowed
                except Exception:
                    # if any of this fails, keep the existing cap
                    pass

            clamped = requested_units
            if requested_units > cap:
                clamped = cap
                # use logger to ensure visibility in logs
                try:
                    from global_config import FEATURE_FLAGS as _FF
                    sizing_enabled = _FF.get('OANDA_ADVANCED', {}).get('ENABLE_SIZING_CAPS', True)
                except Exception:
                    sizing_enabled = True

                if sizing_enabled:
                    logger.warning(f"[RBOTZILLA_SIZING] SIZING_CLAMP: requested={requested_units} clamped={clamped} instrument={instrument}")
                    try:
                        incr('sizing_clamped')
                    except Exception:
                        pass

            final_units = clamped if units >= 0 else -clamped

            # record last trade in metrics
            try:
                if set_last_trade is not None:
                    set_last_trade(symbol=instrument, side=('BUY' if final_units>0 else 'SELL'), units=final_units, sl=float(sl_price), tp=float(tp_price))
            except Exception:
                pass

            # --- MARGIN + EXPOSURE PREFLIGHT CHECKS ---
            try:
                # read emergency margin thresholds
                min_margin_env = float(os.getenv('MIN_MARGIN_AVAILABLE_USD', '500'))
                max_margin_used_pct = float(os.getenv('MAX_MARGIN_USED_PCT', '0.5'))
                max_exposure_usd = float(os.getenv('MAX_EXPOSURE_USD', '100000'))

                acct = client.get_account_summary().get('account', {})
                margin_avail = float(acct.get('marginAvailable', acct.get('marginAvailable', 0.0) or 0.0) or 0.0)
                margin_used = float(acct.get('marginUsed', acct.get('marginUsed', 0.0) or 0.0) or 0.0)
                balance = float(acct.get('balance', 0.0) or 0.0)
                margin_used_pct = (margin_used / balance) if balance > 0 else 1.0

                if margin_avail < min_margin_env or margin_used_pct > max_margin_used_pct:
                    logger.warning('PREFLIGHT: margin emergency - skipping order (avail=%s used_pct=%.2f)', margin_avail, margin_used_pct)
                    try:
                        incr('blocked_margin_emergency')
                    except Exception:
                        pass
                    return {'success': False, 'skip_reason': 'MARGIN_EMERGENCY', 'margin_available': margin_avail, 'margin_used_pct': margin_used_pct}

                # compute current exposure (USD notional) and compare to cap
                open_trades = client.list_open_trades().get('trades', [])
                total_exposure = 0.0
                for t in open_trades:
                    units_val = abs(float(t.get('currentUnits', 0) or t.get('units', 0) or 0))
                    sym = t.get('instrument')
                    try:
                        price_data = client.get_prices([sym]).get('prices', [])
                        p = float(price_data[0].get('closeoutAsk') or price_data[0].get('closeoutBid') or 0.0) if price_data else 0.0
                    except Exception:
                        p = 0.0
                    total_exposure += units_val * (p or 1.0)

                # requested notional
                try:
                    price_data = client.get_prices([instrument]).get('prices', [])
                    req_price = float(price_data[0].get('closeoutAsk') or price_data[0].get('closeoutBid') or 0.0) if price_data else 0.0
                except Exception:
                    req_price = 0.0
                requested_notional = abs(float(final_units)) * (req_price or 1.0)

                if total_exposure + requested_notional > max_exposure_usd:
                    logger.warning('PREFLIGHT: exposure cap hit - skipping order (current=%s requested=%s cap=%s)', total_exposure, requested_notional, max_exposure_usd)
                    try:
                        incr('blocked_exposure_cap')
                    except Exception:
                        pass
                    return {'success': False, 'skip_reason': 'EXPOSURE_CAP', 'current_exposure': total_exposure, 'requested_notional': requested_notional}
            except Exception:
                # If preflight fails for any reason, be conservative and skip
                logger.exception('PREFLIGHT: failed to perform margin/exposure preflight - skipping order')
                try:
                    incr('blocked_prefight_error')
                except Exception:
                    pass
                return {'success': False, 'skip_reason': 'PREFLIGHT_ERROR'}

            # send
            logger.warning(f"[RBOTZILLA_SIZING] EFFECTIVE_UNITS: instrument={instrument} effective_units={final_units} requested={requested_units} cap={cap}")
            res = client.create_order_market(
                instrument=instrument,
                units=final_units,
                sl_price=float(fmt_sl),
                tp_price=float(fmt_tp),
                client_tag=client_tag,
            )

            # Normalize success flag
            if ('orderCreateTransaction' in res) or ('orderFillTransaction' in res):
                res['success'] = True
                res['execution_type'] = 'PLATFORM_PAPER'

            # Post-order: verify OCO/trailing-truth attachments (stop_loss & take_profit) and trailing stop
            try:
                missing_oco = False
                octx = res.get('orderCreateTransaction') or {}
                trade_opened = (res.get('orderFillTransaction') or {}).get('tradeOpened') or {}
                trade_id = trade_opened.get('tradeID')
                # If the create transaction does not explicitly include SL/TP, treat as verification failure
                if not octx.get('takeProfitOnFill') or not octx.get('stopLossOnFill'):
                    missing_oco = True
                # Broker-side verification: ensure SL/TP exist on the live trade
                if trade_id:
                    try:
                        client_cls = _import_oanda_practice_client()
                        if client_cls is None:
                            raise RuntimeError("OandaPracticeClient import failed")
                        client = client_cls(token=self.token, account_id=self.account_id, base_url=self.base_url, http_client=self.http)
                        if callable(client) and not hasattr(client, 'list_open_trades'):
                            try:
                                client = client()
                            except Exception:
                                pass
                        trades = client.list_open_trades().get('trades', [])
                        for t in trades:
                            if t.get('tradeID') == trade_id:
                                has_sl = bool(t.get('stopLossOrder') or t.get('trailingStopLossOrder') or t.get('trailingStopLoss'))
                                has_tp = bool(t.get('takeProfitOrder'))
                                if not has_sl or not has_tp:
                                    missing_oco = True
                                break
                    except Exception:
                        # If we cannot verify, keep original missing_oco signal
                        pass
                if missing_oco:
                    try:
                        incr('trailing_truth_failed')
                    except Exception:
                        pass
                    # Attempt repair: create missing SL/TP via practice client if possible
                    repaired = False
                    try:
                        client_cls = _import_oanda_practice_client()
                        if client_cls is None:
                            raise RuntimeError("OandaPracticeClient import failed")
                        client = client_cls(token=self.token, account_id=self.account_id, base_url=self.base_url, http_client=self.http)
                        if callable(client) and not hasattr(client, 'create_order_market'):
                            try:
                                client = client()
                            except Exception:
                                pass
                        if trade_id:
                            # Attempt to attach missing SL/TP using known prices
                            try:
                                trades = client.list_open_trades().get('trades', [])
                                for t in trades:
                                    if t.get('tradeID') == trade_id:
                                        has_sl = bool(t.get('stopLossOrder') or t.get('trailingStopLossOrder') or t.get('trailingStopLoss'))
                                        has_tp = bool(t.get('takeProfitOrder'))
                                        if not has_sl and sl_price is not None:
                                            client.create_stop_loss(trade_id, float(sl_price))
                                        if not has_tp and tp_price is not None:
                                            client.create_take_profit(trade_id, float(tp_price))
                                        repaired = True
                                        break
                            except Exception:
                                repaired = False
                    except Exception:
                        repaired = False

                    if not repaired:
                        # Flatten trade and freeze system: missing OCO means we cannot trust attachments
                        flattened = False
                        try:
                            if trade_id:
                                close_trade_fn = getattr(client, 'close_trade', None)
                                close_pos_fn = getattr(client, 'close_position', None)
                                if callable(close_trade_fn):
                                    close_trade_fn(trade_id)
                                    flattened = True
                                elif callable(close_pos_fn):
                                    close_pos_fn(instrument)
                                    flattened = True
                        except Exception:
                            flattened = False

                        try:
                            from multi_broker_phoenix.monitor.watchdog import _set_trading_allowed as _wd_set
                            _wd_set(False)
                        except Exception:
                            logger.critical('WATCHDOG: failed to set freeze after OCO verification failure')

                        try:
                            from multi_broker_phoenix.monitor.pnl_kill_switch import _log_event as _durable_log
                            _durable_log('OCO_MISSING_POSTFILL', {
                                'trade_id': trade_id,
                                'instrument': instrument,
                                'repair_attempted': True,
                                'flattened': flattened,
                            })
                        except Exception:
                            pass

                        try:
                            oco_state_path = os.getenv('OCO_STATE_FILE', 'ops/state/oco_health.json')
                            Path(oco_state_path).parent.mkdir(parents=True, exist_ok=True)
                            with open(oco_state_path, 'w') as f:
                                json.dump({
                                    'last_reconcile': time.time(),
                                    'processed': 1,
                                    'missing': 1,
                                    'repaired': 0,
                                    'flattened': 1 if flattened else 0,
                                    'trades': [{
                                        'trade_id': trade_id,
                                        'instrument': instrument,
                                        'oco_status': 'MISSING',
                                        'action': 'flattened' if flattened else 'freeze_only'
                                    }],
                                }, f, indent=2)
                        except Exception:
                            pass

                        logger.critical('TRAILING_TRUTH: OCO missing after order placement - flattened=%s, freezing new entries', flattened)
                        res['watchdog_freeze'] = 'OCO_MISSING'

                # TRAILING STOP verification
                trailing_expected = getattr(candidate, 'trailing', None) or getattr(candidate, 'trailing_distance', None)
                if trailing_expected is not None:
                    # Try to detect trailingStop in order or tradeOpened details
                    ts_present = False
                    octx = res.get('orderCreateTransaction') or {}
                    if octx.get('trailingStopLossOnFill'):
                        ts_present = True
                    # fallback: check orderFillTransaction -> tradeOpened
                    of = res.get('orderFillTransaction') or {}
                    trade_opened = of.get('tradeOpened') or {}
                    if trade_opened and trade_opened.get('tradeID'):
                        # Query trade details via practice client
                        try:
                            client_cls = _import_oanda_practice_client()
                            if client_cls is None:
                                raise RuntimeError("OandaPracticeClient import failed")
                            client = client_cls(token=self.token, account_id=self.account_id, base_url=self.base_url, http_client=self.http)
                            if callable(client) and not hasattr(client, 'create_order_market'):
                                try:
                                    client = client()
                                except Exception:
                                    pass
                            tid = trade_opened.get('tradeID')
                            # Implementation note: client may not have a direct 'get_trade' helper; check list_open_trades
                            trades = client.list_open_trades().get('trades', [])
                            for t in trades:
                                if t.get('tradeID') == tid and t.get('trailingStopLoss'):
                                    ts_present = True
                        except Exception:
                            pass

                    if not ts_present:
                        # Attempt one repair: create trailing stop using provided distance (or default)
                        repair_ok = False
                        distance = getattr(candidate, 'trailing_distance', None) or getattr(candidate, 'trailing', None) or 10.0
                        try:
                            client_cls = _import_oanda_practice_client()
                            if client_cls is None:
                                raise RuntimeError("OandaPracticeClient import failed")
                            client = client_cls(token=self.token, account_id=self.account_id, base_url=self.base_url, http_client=self.http)
                            if callable(client) and not hasattr(client, 'create_order_market'):
                                try:
                                    client = client()
                                except Exception:
                                    pass
                            tid = trade_opened.get('tradeID')
                            if tid:
                                tr = client.create_trailing_stop(candidate.symbol, tid, distance)
                                # Consider success heuristically if no exception thrown
                                repair_ok = True if tr else False
                        except Exception:
                            repair_ok = False

                        if not repair_ok:
                            # Fallback behavior: enable SL->BREAKEVEN policy instead of freezing immediately.
                            try:
                                incr('trailing_repair_failed')
                            except Exception:
                                pass
                            logger.warning('TRAILING_TRUTH: trailing stop missing and repair failed - enabling SL->BREAKEVEN fallback (no immediate freeze)')
                            res['use_sl_to_breakeven'] = True
            except Exception as e:
                logger.exception('TRAILING_TRUTH verification failed: %s', e)

            # Metrics: order sent
            try:
                incr('order_sent')
            except Exception:
                pass

            # Detect immediate cancel due to insufficient margin
            cancel = res.get('orderCancelTransaction') or {}
            reason = (cancel.get('reason') or '').upper() if isinstance(cancel, dict) else ''
            try:
                from global_config import FEATURE_FLAGS as _FF
                retry_enabled = _FF.get('OANDA_ADVANCED', {}).get('ENABLE_MARGIN_RETRY', True)
            except Exception:
                retry_enabled = True

            if reason == 'INSUFFICIENT_MARGIN' and retry_enabled:
                try:
                    incr('order_canceled_margin')
                except Exception:
                    pass
                # Retry once at 25% size (respect cap)
                retry_abs = max(1, int(max(1, abs(final_units)) * 0.25))
                print(f"MARGIN_RETRY: units {abs(final_units)} -> {retry_abs}")
                try:
                    incr('margin_retry')
                except Exception:
                    pass
                retry_units = retry_abs if final_units > 0 else -retry_abs
                try:
                    retry_res = client.create_order_market(
                        instrument=instrument,
                        units=retry_units,
                        sl_price=float(fmt_sl),
                        tp_price=float(fmt_tp),
                        client_tag=client_tag,
                    )
                    # Annotate if succeeded
                    if ('orderCreateTransaction' in retry_res) or ('orderFillTransaction' in retry_res):
                        retry_res['success'] = True
                        retry_res['execution_type'] = 'PLATFORM_PAPER_RETRY'
                        try:
                            incr('order_sent')
                        except Exception:
                            pass
                        # if retry succeeded without insufficient margin cancel, return retry result
                        retry_cancel = retry_res.get('orderCancelTransaction') or {}
                        if (retry_cancel.get('reason') or '').upper() != 'INSUFFICIENT_MARGIN':
                            try:
                                incr('order_filled')
                            except Exception:
                                pass
                            return retry_res
                        else:
                            try:
                                incr('order_canceled_margin')
                            except Exception:
                                pass
                    # if retry failed or still canceled, fall through to return original response
                except Exception:
                    try:
                        incr('order_failed_other')
                    except Exception:
                        pass

            # If order succeeded (no margin cancel) mark filled
            if res.get('success') and not (res.get('orderCancelTransaction') and (res.get('orderCancelTransaction', {}).get('reason') or '').upper() == 'INSUFFICIENT_MARGIN'):
                try:
                    incr('order_filled')
                except Exception:
                    pass

            # If there was some other failure
            if not res.get('success'):
                try:
                    incr('order_failed_other')
                except Exception:
                    pass

            # Attach execution_type and return
            return res

        except Exception as exc:
            # TEMP DEBUG: print HTTP response details if present to capture OANDA error body (no secrets)
            resp = getattr(exc, 'response', None)
            if resp is not None:
                try:
                    print(f"   ⚠️ OANDA PRACTICE RESP STATUS: {getattr(resp, 'status_code', 'UNKNOWN')}")
                    print(f"   ⚠️ OANDA PRACTICE RESP BODY: {(getattr(resp, 'text', '') or '')[:4000]}")
                except Exception:
                    pass
            logger.error('OANDA practice order failed: %s', exc)
            return {'success': False, 'status': 'ERROR', 'error': str(exc)}

    def place_live_order(self, candidate: Any, units: int, confirm_real_money: bool = False) -> Dict[str, Any]:
        """Place a LIVE market order on fxTrade.

        Safety gates:
        1) ``practice_mode`` must be False
        2) ``TRADING_MODE`` must be ``LIVE``
        3) ``confirm_real_money`` must be True
        """
        if self.practice_mode:
            raise RuntimeError('Live orders require practice_mode=False (set OANDA_MODE=LIVE)')
        if os.getenv('TRADING_MODE', 'PAPER').upper() != 'LIVE':
            raise RuntimeError('Set TRADING_MODE=LIVE to enable real OANDA orders')
        if not confirm_real_money:
            raise RuntimeError('Must pass confirm_real_money=True for live OANDA order')
        if not self.token or not self.account_id:
            raise RuntimeError('OANDA credentials not configured')

        payload = self._build_order_payload(candidate, units)
        result = self._post_order(payload)
        if result.get('success'):
            result['execution_type'] = 'LIVE'
        return result

    def place_order(self, candidate: Any, units: int, confirm_real_money: bool = False) -> Dict[str, Any]:
        """Dispatch to paper/live path based on current mode."""
        if self.practice_mode:
            return self.place_paper_order(candidate, units)
        return self.place_live_order(candidate, units, confirm_real_money=confirm_real_money)

    def verify_credentials(self) -> Dict[str, Any]:
        """Lightweight credential check using /accounts summary."""
        if not self.token or not self.account_id:
            return {'success': False, 'error': 'Missing OANDA token/account'}
        try:
            resp = self.http.get(f"{self.base_url}/v3/accounts/{self.account_id}", headers=self._headers(), timeout=5)
            resp.raise_for_status()
            body = resp.json()
            currency = (body.get('account') or {}).get('currency', 'UNKNOWN')
            return {'success': True, 'currency': currency, 'mode': 'PAPER' if self.practice_mode else 'LIVE'}
        except Exception as exc:
            return {'success': False, 'error': str(exc)}