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
        logger.info(
            'OANDA Practice client initialized | account=%s | base_url=%s',
            self.account_id,
            self.base_url,
        )

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

        payload = {
            'order': {
                'type': 'MARKET',
                'instrument': instrument,
                'units': str(units),
                'timeInForce': 'FOK',
                'positionFill': 'DEFAULT',
                'stopLossOnFill': {'price': f'{sl_price:.5f}'},
                'takeProfitOnFill': {'price': f'{tp_price:.5f}'},
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

    def _validate_bracket(self, sl_price: float, tp_price: float) -> None:
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

    def _request(self, method: str, url: str, **kwargs: Any) -> Dict[str, Any]:
        try:
            response = getattr(self.http, method)(
                url, headers=self.headers, timeout=15, **kwargs
            )
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            logger.error('OANDA API request failed: %s %s', method.upper(), url)
            raise
