"""Minimal wrapper around the OANDA v20 practice REST API."""
from __future__ import annotations

import os
import logging
from typing import Sequence, Dict, Any, Optional

try:
    import requests
except ImportError:  # pragma: no cover - requests is a runtime requirement
    requests = None  # type: ignore

logger = logging.getLogger(__name__)

PRACTICE_API_URL = "https://api-fxpractice.oanda.com"
PRACTICE_STREAM_URL = "https://stream-fxpractice.oanda.com"


class OandaPracticeClient:
    """Simple, practice-only OANDA client with mandatory OCO enforcement."""

    def __init__(
        self,
        token: Optional[str] = None,
        account_id: Optional[str] = None,
        base_url: Optional[str] = None,
        stream_url: Optional[str] = None,
        http_client: Optional[Any] = None,
    ):
        if requests is None and http_client is None:
            raise RuntimeError("The requests library is required to use OANDAPracticeClient")

        self.token = token or os.getenv('OANDA_API_TOKEN') or os.getenv('OANDA_TOKEN')
        self.account_id = account_id or os.getenv('OANDA_ACCOUNT_ID')
        if not self.token or not self.account_id:
            raise RuntimeError('OANDA_API_TOKEN (or OANDA_TOKEN) and OANDA_ACCOUNT_ID are required')

        self.base_url = base_url or os.getenv('OANDA_API_URL', PRACTICE_API_URL)
        if not self.base_url.startswith(PRACTICE_API_URL):
            raise RuntimeError(
                f'OANDA practice client only supports {PRACTICE_API_URL} (got {self.base_url})'
            )

        self.stream_url = stream_url or os.getenv('OANDA_STREAM_URL', PRACTICE_STREAM_URL)
        self.http = http_client or requests
        self.headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json',
        }
        logger.debug(
            'OANDA Practice client initialized | account=%s | base_url=%s',
            self.account_id,
            self.base_url,
        )

    def _format_price(self, price: float, instrument: Optional[str] = None) -> str:
        """Format price with instrument-specific precision.

        - JPY pairs: 3 decimals
        - Others: 5 decimals
        If instrument is unknown, fall back to a heuristic based on price magnitude.
        """
        try:
            p = float(price)
        except Exception:
            p = float(price)

        if instrument:
            inst = instrument.upper().replace('-', '_').replace('/', '_')
            if inst.endswith('JPY') or '_JPY' in inst:
                return f"{p:.3f}"
            return f"{p:.5f}"

        # Heuristic: JPY pairs usually have price >= 20
        if p >= 20:
            return f"{p:.3f}"
        return f"{p:.5f}"

    # ------------------------------------------------------------------
    # Health helpers
    # ------------------------------------------------------------------
    def get_account_summary(self) -> Dict[str, Any]:
        """Return /v3/accounts/{account_id} payload."""
        return self._get(f'/v3/accounts/{self.account_id}')

    def get_prices(self, instruments: Sequence[str]) -> Dict[str, Any]:
        """Return latest bid/ask for the requested instruments."""
        if not instruments:
            raise ValueError('At least one instrument is required')
        instrument_str = ','.join(instruments)
        return self._get(
            f'/v3/accounts/{self.account_id}/pricing',
            params={'instruments': instrument_str},
        )

    def list_open_trades(self) -> Dict[str, Any]:
        """Return /openTrades payload with live trade state."""
        return self._get(f'/v3/accounts/{self.account_id}/openTrades')

    def get_transactions(self, since_id: str = None, count: int = 50) -> Dict[str, Any]:
        """
        Fetch recent transactions from OANDA.
        Used to detect closed trades and realized P&L.
        
        Args:
            since_id: Only fetch transactions after this ID
            count: Max transactions to return (default 50)
        
        Returns:
            Dict with 'transactions' list containing transaction details
        """
        params = {'count': str(count)}
        if since_id:
            params['sinceTransactionID'] = since_id
        return self._get(f'/v3/accounts/{self.account_id}/transactions', params=params)

    def get_transaction_range(self, from_id: str, to_id: str) -> Dict[str, Any]:
        """Fetch transactions in a specific ID range."""
        return self._get(
            f'/v3/accounts/{self.account_id}/transactions/idrange',
            params={'from': from_id, 'to': to_id}
        )

    def close_position(self, instrument: str) -> Dict[str, Any]:
        """Close position for the given instrument.
        
        Closes long and short sides separately to avoid rejection when only one side exists.
        Returns success even if position doesn't exist (already closed by TP/SL).
        """
        url = f'{self.base_url}/v3/accounts/{self.account_id}/positions/{instrument}/close'
        results = {'instrument': instrument, 'closed': []}
        
        # Try to close LONG side
        try:
            resp = self.http.put(url, headers=self.headers, timeout=15, json={'longUnits': 'ALL'})
            if resp.status_code == 200:
                data = resp.json()
                if 'longOrderFillTransaction' in data:
                    pl = float(data['longOrderFillTransaction'].get('pl', 0))
                    results['closed'].append({'side': 'long', 'pl': pl})
                    logger.info('Closed LONG %s position, P/L: $%.2f', instrument, pl)
        except Exception as e:
            if '400' not in str(e):
                logger.warning('Error closing LONG %s: %s', instrument, str(e)[:100])
        
        # Try to close SHORT side
        try:
            resp = self.http.put(url, headers=self.headers, timeout=15, json={'shortUnits': 'ALL'})
            if resp.status_code == 200:
                data = resp.json()
                if 'shortOrderFillTransaction' in data:
                    pl = float(data['shortOrderFillTransaction'].get('pl', 0))
                    results['closed'].append({'side': 'short', 'pl': pl})
                    logger.info('Closed SHORT %s position, P/L: $%.2f', instrument, pl)
        except Exception as e:
            if '400' not in str(e):
                logger.warning('Error closing SHORT %s: %s', instrument, str(e)[:100])
        
        # Return results - if nothing was closed, it was already closed
        if not results['closed']:
            results['status'] = 'already_closed'
            logger.info('Position %s already closed (no units to close)', instrument)
        else:
            results['status'] = 'closed'
            total_pl = sum(c['pl'] for c in results['closed'])
            results['total_pl'] = total_pl
        
        return results

    def close_all_positions(self) -> Dict[str, Any]:
        """Close all open positions by enumerating open trades and closing each instrument once."""
        try:
            trades = self.list_open_trades().get('trades', [])
            instruments = set(t.get('instrument') for t in trades if t.get('instrument'))
            results = {}
            for inst in instruments:
                try:
                    results[inst] = self.close_position(inst)
                except Exception as e:
                    results[inst] = {'error': str(e)}
            return results
        except Exception as e:
            raise


    # ------------------------------------------------------------------
    # Order helpers
    # ------------------------------------------------------------------
    def create_order_market(
        self,
        instrument: str,
        units: int,
        sl_price: float,
        tp_price: float,
        client_tag: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Place a market order with SL & TP attached (OCO bracket)."""
        self._validate_units(units)
        self._validate_bracket(sl_price, tp_price)

        def _fmt_price(instr: str, p: float) -> str:
            # Controlled by FEATURE_FLAGS['OANDA_ADVANCED']['ENABLE_PRICE_PRECISION']
            try:
                from global_config import FEATURE_FLAGS as _FF
                enabled = _FF.get('OANDA_ADVANCED', {}).get('ENABLE_PRICE_PRECISION', True)
            except Exception:
                enabled = True
            try:
                p = float(p)
            except Exception:
                p = float(p)
            if enabled and instr.endswith('_JPY'):
                return f"{p:.3f}"
            return f"{p:.5f}"

        payload = {
            'order': {
                'type': 'MARKET',
                'instrument': instrument,
                'units': str(units),
                'timeInForce': 'FOK',
                'positionFill': 'DEFAULT',
                'stopLossOnFill': {'price': _fmt_price(instrument, sl_price)},
                'takeProfitOnFill': {'price': _fmt_price(instrument, tp_price)},
            }
        }

        if client_tag:
            payload['order']['clientExtensions'] = {'tag': client_tag}

        result = self._post(f'/v3/accounts/{self.account_id}/orders', json=payload)
        order_id = (
            result.get('orderCreateTransaction', {})
            .get('id')
            or result.get('orderFillTransaction', {}).get('orderID')
        )
        if order_id:
            logger.info(
                'SENT ORDER -> OANDA PRACTICE | instrument=%s units=%s sl=%s tp=%s order_id=%s',
                instrument,
                units,
                sl_price,
                tp_price,
                order_id,
            )
        return result

    # ------------------------------------------------------------------
    def _validate_units(self, units: int) -> None:
        if units == 0:
            raise ValueError('Units must be non-zero')
        if abs(units) > 1_000_000:
            raise ValueError('Units exceed sane limit (1,000,000)')

    _CASTED_SLTP_LOGGED = False

    def _validate_bracket(self, sl_price: float, tp_price: float) -> None:
        # Defensive: accept numeric strings too; cast and log once if casting occurred
        global _CASTED_SLTP_LOGGED
        try:
            if isinstance(sl_price, str) or isinstance(tp_price, str):
                sl_price = float(sl_price)
                tp_price = float(tp_price)
                if not _CASTED_SLTP_LOGGED:
                    print("CASTED_SLTP: casted SL/TP from strings to floats (one-time)")
                    _CASTED_SLTP_LOGGED = True
        except Exception:
            # Let natural validation raise a helpful error below
            pass

        if sl_price is None or tp_price is None:
            raise ValueError('Both stop-loss and take-profit prices are required')
        if sl_price <= 0 or tp_price <= 0:
            raise ValueError('SL and TP must be positive prices')
        if sl_price == tp_price:
            raise ValueError('SL and TP cannot be equal; ensure a real bracket')

    def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = self.base_url + endpoint
        return self._request('get', url, params=params)

    def _post(self, endpoint: str, json: Dict[str, Any]) -> Dict[str, Any]:
        url = self.base_url + endpoint
        return self._request('post', url, json=json)

    def _put(self, endpoint: str, json: Dict[str, Any]) -> Dict[str, Any]:
        url = self.base_url + endpoint
        return self._request('put', url, json=json)

    # ------------------------------------------------------------------
    # Trailing stop helpers
    # ------------------------------------------------------------------
    def create_trailing_stop(self, instrument: str, trade_id: str, distance: float) -> Dict[str, Any]:
        """Create a trailing stop for the given trade.

        Note: OANDA supports trailingStopLossOnFill in order creation; this
        helper provides a convenience for tests and basic repair attempts.
        """
        payload = {
            'trailingStopLoss': {
                'distance': self._format_price(distance, instrument)
            }
        }
        return self._put(f'/v3/accounts/{self.account_id}/trades/{trade_id}/orders', json=payload)

    def create_stop_loss(self, trade_id: str, price: float, instrument: Optional[str] = None) -> Dict[str, Any]:
        """Create a stop loss order for the given trade at the specified price.

        This helper is used by the breakeven worker to set stop-loss to entry.
        """
        payload = {
            'stopLoss': {
                'price': self._format_price(price, instrument)
            }
        }
        return self._put(f'/v3/accounts/{self.account_id}/trades/{trade_id}/orders', json=payload)

    def create_take_profit(self, trade_id: str, price: float, instrument: Optional[str] = None) -> Dict[str, Any]:
        """Create a take profit order for the given trade at the specified price."""
        payload = {
            'takeProfit': {
                'price': self._format_price(price, instrument)
            }
        }
        return self._put(f'/v3/accounts/{self.account_id}/trades/{trade_id}/orders', json=payload)

    def _request(self, method: str, url: str, **kwargs: Any) -> Dict[str, Any]:
        try:
            response = getattr(self.http, method)(
                url, headers=self.headers, timeout=15, **kwargs
            )
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            # TEMP DEBUG: print response status/body if available to diagnose 400 errors
            try:
                if 'response' in locals() and getattr(response, 'status_code', None) is not None:
                    print(f"   ⚠️ OANDA RAW RESP STATUS: {response.status_code}")
                    print(f"   ⚠️ OANDA RAW RESP BODY: {(getattr(response, 'text', '') or '')[:4000]}")
            except Exception:
                pass
            logger.error('OANDA API request failed: %s %s', method.upper(), url)
            raise
