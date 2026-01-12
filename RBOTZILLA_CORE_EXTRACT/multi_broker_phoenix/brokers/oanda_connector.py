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
from typing import Optional, Any, Dict

logger = logging.getLogger(__name__)


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
                logger.warning('OANDA order attempt %s failed: %s', attempt, exc)
                time.sleep(0.2 * (attempt + 1))
        return {'success': False, 'error': f'OANDA order failed after {tries} attempts', 'status': 'ERROR', 'exception': str(last_exc)}

    def place_paper_order(self, candidate: Any, units: int) -> Dict[str, Any]:
        """Place a market order on the practice account (platform-paper).

        Uses the centralized `execution.oanda_practice_client.OandaPracticeClient` to
        ensure the request hits the practice host and that an OCO (SL + TP) bracket
        is attached. If SL/TP are missing the order will be refused.
        
        TRAILING STOP MODE: When OANDA_USE_TRAILING_STOP=true, uses broker-side
        trailing stop instead of fixed TP, which survives engine restarts.
        """
        if not self.token or not self.account_id:
            raise RuntimeError('OANDA credentials not configured')

        # Enforce OCO bracket presence: candidate must provide stop_loss and take_profit
        sl_price = getattr(candidate, 'stop_loss', None)
        tp_price = getattr(candidate, 'take_profit', None)
        if sl_price is None or tp_price is None:
            raise RuntimeError('Orders must include stop_loss and take_profit (OCO bracket required)')

        # Check if we should use OANDA's native trailing stop (DEFAULT: TRUE)
        use_trailing = os.getenv('OANDA_USE_TRAILING_STOP', 'true').lower() in ('true', '1', 'yes')
        trailing_pips = float(os.getenv('OANDA_TRAILING_STOP_PIPS', '20'))

        try:
            # Use the practice-only client (validates practice host and auth)
            from execution.oanda_practice_client import OandaPracticeClient

            client = OandaPracticeClient(
                token=self.token,
                account_id=self.account_id,
                base_url=self.base_url,
                http_client=self.http
            )

            instrument = getattr(candidate, 'symbol', getattr(candidate, 'instrument', 'EUR_USD'))
            client_tag = getattr(candidate, 'client_tag', None)

            res = client.create_order_market(
                instrument=instrument,
                units=units,
                sl_price=float(sl_price),
                tp_price=float(tp_price),
                client_tag=client_tag,
            )

            # Normalize success flag
            if ('orderCreateTransaction' in res) or ('orderFillTransaction' in res):
                res['success'] = True
                res['execution_type'] = 'PLATFORM_PAPER'
                
                # If trailing stop enabled, add trailing stop order after fill
                if use_trailing and res.get('orderFillTransaction'):
                    try:
                        trade_id = res['orderFillTransaction'].get('id') or res['orderFillTransaction'].get('tradeOpened', {}).get('tradeID')
                        if trade_id:
                            self._add_trailing_stop(trade_id, trailing_pips, instrument)
                            logger.info(f"🎯 OANDA Trailing stop added: {trailing_pips} pips for trade {trade_id}")
                            res['trailing_stop_added'] = True
                            res['trailing_pips'] = trailing_pips
                    except Exception as trail_exc:
                        logger.warning(f"Failed to add trailing stop: {trail_exc}")
                        
            return res

        except Exception as exc:
            logger.error('OANDA practice order failed: %s', exc)
            return {'success': False, 'status': 'ERROR', 'error': str(exc)}

    def _add_trailing_stop(self, trade_id: str, distance_pips: float, instrument: str) -> Dict[str, Any]:
        """Add a trailing stop to an existing trade using OANDA's native trailing stop.
        
        This is BROKER-SIDE - survives engine restarts!
        """
        # Calculate distance in price (depends on instrument)
        if 'JPY' in instrument:
            distance = distance_pips * 0.01  # JPY pairs
        else:
            distance = distance_pips * 0.0001  # Non-JPY pairs
        
        payload = {
            'trailingStopLoss': {
                'distance': f'{distance:.5f}',
                'timeInForce': 'GTC'
            }
        }
        
        resp = self.http.put(
            f"{self.base_url}/v3/accounts/{self.account_id}/trades/{trade_id}/orders",
            headers=self._headers(),
            json=payload,
            timeout=10
        )
        
        if resp.status_code in (200, 201):
            logger.info(f"✅ Trailing stop set: trade {trade_id}, {distance_pips} pips")
            return {'success': True, 'trade_id': trade_id, 'distance_pips': distance_pips}
        else:
            error = resp.json() if resp.content else resp.text
            logger.error(f"Failed to set trailing stop: {error}")
            return {'success': False, 'error': str(error)}

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

    def close_position(self, symbol: str, units: Optional[int] = None) -> Dict[str, Any]:
        """Close an open position (full or partial).
        
        Args:
            symbol: Instrument symbol (e.g., 'EUR_USD')
            units: Number of units to close. None = close all.
        
        Returns:
            Dict with success status and order details.
        """
        if not self.token or not self.account_id:
            return {'success': False, 'error': 'Missing OANDA credentials'}
        
        try:
            # First get the open position to determine side
            pos_resp = self.http.get(
                f"{self.base_url}/v3/accounts/{self.account_id}/positions/{symbol}",
                headers=self._headers(),
                timeout=10
            )
            
            if pos_resp.status_code != 200:
                return {'success': False, 'error': f'No open position for {symbol}'}
            
            pos_data = pos_resp.json().get('position', {})
            long_units = int(float(pos_data.get('long', {}).get('units', 0)))
            short_units = abs(int(float(pos_data.get('short', {}).get('units', 0))))
            
            # Determine which side to close
            if long_units > 0:
                close_units = units if units else long_units
                payload = {'longUnits': str(close_units)}
            elif short_units > 0:
                close_units = units if units else short_units
                payload = {'shortUnits': str(close_units)}
            else:
                return {'success': False, 'error': f'No open position for {symbol}'}
            
            # Close the position
            resp = self.http.put(
                f"{self.base_url}/v3/accounts/{self.account_id}/positions/{symbol}/close",
                headers=self._headers(),
                json=payload,
                timeout=10
            )
            
            if resp.status_code in (200, 201):
                result = resp.json()
                logger.info(f"OANDA position closed: {symbol} x{close_units}")
                return {
                    'success': True,
                    'symbol': symbol,
                    'units_closed': close_units,
                    'response': result
                }
            else:
                error = resp.json() if resp.content else resp.text
                return {'success': False, 'error': str(error)}
                
        except Exception as exc:
            logger.error(f'OANDA close position failed: {exc}')
            return {'success': False, 'error': str(exc)}

    def close_partial_position(self, symbol: str, units: int) -> Dict[str, Any]:
        """Convenience wrapper for partial position closes."""
        return self.close_position(symbol, units=units)

    def update_stop_loss(self, symbol: str, new_stop: float) -> Dict[str, Any]:
        """Update the stop loss on an open trade.
        
        Note: OANDA requires updating the trade, not the position.
        This finds open trades for the symbol and updates their SL.
        
        Args:
            symbol: Instrument symbol
            new_stop: New stop loss price
            
        Returns:
            Dict with success status
        """
        if not self.token or not self.account_id:
            return {'success': False, 'error': 'Missing OANDA credentials'}
        
        try:
            # Get open trades for this instrument
            trades_resp = self.http.get(
                f"{self.base_url}/v3/accounts/{self.account_id}/openTrades",
                headers=self._headers(),
                timeout=10
            )
            
            if trades_resp.status_code != 200:
                return {'success': False, 'error': 'Failed to get open trades'}
            
            trades = trades_resp.json().get('trades', [])
            updated = 0
            errors = []
            
            for trade in trades:
                if trade.get('instrument') == symbol:
                    trade_id = trade.get('id')
                    
                    # Update the trade's stop loss
                    update_payload = {
                        'stopLoss': {
                            'price': f'{new_stop:.5f}',
                            'timeInForce': 'GTC'
                        }
                    }
                    
                    update_resp = self.http.put(
                        f"{self.base_url}/v3/accounts/{self.account_id}/trades/{trade_id}/orders",
                        headers=self._headers(),
                        json=update_payload,
                        timeout=10
                    )
                    
                    if update_resp.status_code in (200, 201):
                        updated += 1
                        logger.info(f"OANDA SL updated: {symbol} trade {trade_id} → {new_stop:.5f}")
                    else:
                        errors.append(f"Trade {trade_id}: {update_resp.text}")
            
            if updated > 0:
                return {
                    'success': True,
                    'symbol': symbol,
                    'new_stop': new_stop,
                    'trades_updated': updated,
                    'errors': errors if errors else None
                }
            elif errors:
                return {'success': False, 'error': '; '.join(errors)}
            else:
                return {'success': False, 'error': f'No open trades found for {symbol}'}
                
        except Exception as exc:
            logger.error(f'OANDA stop loss update failed: {exc}')
            return {'success': False, 'error': str(exc)}