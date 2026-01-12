#!/usr/bin/env python3
"""IBKR Wrapper (Paper mode safe).

This module provides an IBKRConnector that can operate in full integration mode
(using ib_insync when available) or in a fully-offline, testable stub mode.
It supports dependency injection of an `ib_client` (fake or real) and exposes a
compatibility API expected by the project's IBKR unit tests (connect, get_best_bid_ask,
place_order, get_funding_rate, etc.).

This file is a copied, adapted artifact and intentionally self-contained for
unit testing and integration into the Phoenix project.
"""
from __future__ import annotations
import os
import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class IBKRConnector:
    def __init__(self, ib_client: Optional[Any] = None, pin: Optional[int] = None, environment: str = 'paper', max_funding_rate_pct: float = 0.001):
        """Create a connector.

        - ib_client: injected IB client (FakeIB for tests or ib_insync.IB instance)
        - environment: 'paper' or 'live'
        - max_funding_rate_pct: funding rate gate
        """
        self.ib = ib_client
        self.environment = environment or os.getenv('IBKR_ENV', 'paper')
        # For safety, trading_enabled requires explicit API creds in env and proper env
        self.api_key = os.getenv('IBKR_API_KEY')
        self.api_secret = os.getenv('IBKR_API_SECRET')
        self.trading_enabled = bool(self.api_key and self.api_secret and self.environment in ('paper', 'live'))
        self.max_funding_rate_pct = float(max_funding_rate_pct)
        # gating / thresholds used by tests
        self.min_notional = 0
        self.min_expected_pnl = 0
        self.min_rr_ratio = 0
        logger.info('IBKRConnector initialized for %s ; trading_enabled=%s', self.environment, self.trading_enabled)

    # --- compatibility API used by unit tests ---
    def connect(self) -> bool:
        # if an ib client is injected, assume connect is a no-op for tests
        if self.ib is not None:
            try:
                if hasattr(self.ib, 'connect'):
                    return self.ib.connect(host=os.getenv('IBKR_HOST', '127.0.0.1'), port=int(os.getenv('IBKR_PORT', '4001')), clientId=int(os.getenv('IBKR_CLIENT_ID', '1')))
                return True
            except Exception as exc:
                logger.debug('IBKR connect failed: %s', exc)
                return False
        # try to import ib_insync if present
        try:
            from ib_insync import IB
        except Exception:
            return False
        try:
            ib = IB()
            ib.connect(host=os.getenv('IBKR_HOST', '127.0.0.1'), port=int(os.getenv('IBKR_PORT', '4001')), clientId=int(os.getenv('IBKR_CLIENT_ID', '1')))
            ib.disconnect()
            return True
        except Exception:
            return False

    def get_best_bid_ask(self, symbol: str) -> tuple[float, float]:
        # Expect ib client to provide reqMktData(contract) returning object with bid/ask
        if self.ib is None:
            raise RuntimeError('no_ib_client')
        tick = self.ib.reqMktData(symbol)
        return float(tick.bid), float(tick.ask)

    def get_funding_rate(self, symbol: str) -> float:
        # Default: 0. Can be patched in tests.
        return 0.0

    def _narrate(self, event_type: str, details: Dict[str, Any]):
        fn = os.getenv('NARRATION_FILE_OVERRIDE')
        if not fn:
            return
        ev = {'timestamp': datetime.now(timezone.utc).isoformat(), 'event_type': event_type, 'details': details}
        try:
            with open(fn, 'a') as f:
                f.write(json.dumps(ev) + '\n')
        except Exception:
            logger.exception('Failed to write narration event')

    def place_order(self, symbol: str, side: str, units: int, entry_price: Optional[float] = None, stop_loss: Optional[float] = None, take_profit: Optional[float] = None, explanation: Optional[str] = None, use_twap: bool = False, twap_slices: int = 1) -> Dict[str, Any]:
        # Execution gating
        if os.getenv('EXECUTION_ENABLED', '0') != '1':
            return {'success': False, 'error': 'EXECUTION_DISABLED_OR_BREAKER'}
        # Funding rate gate
        if self.get_funding_rate(symbol) > self.max_funding_rate_pct:
            return {'success': False, 'error': 'FUNDING_RATE_TOO_HIGH'}
        # Basic TWAP slicing support
        if use_twap and int(twap_slices) > 1:
            slices = []
            for i in range(int(twap_slices)):
                slices.append({'slice': i + 1, 'qty': max(1, units // int(twap_slices))})
            self._narrate('BROKER_ORDER_CREATED', {'symbol': symbol, 'slices': slices})
            return {'success': True, 'slices': slices}
        # Simulate bracket order placement via ib client
        if self.ib is None:
            # stubbed behavior
            order_id = f'sim-ibkr-{symbol}-{int(units)}'
            self._narrate('BROKER_ORDER_CREATED', {'order_id': order_id, 'symbol': symbol, 'units': units})
            # Aggressive leverage events
            if os.getenv('RICK_AGGRESSIVE_PLAN'):
                self._narrate('AGGRESSIVE_LEVERAGE_APPLIED', {'symbol': symbol, 'explanation': explanation})
            return {'success': True, 'order_id': order_id}
        # If we have a real IB client, attempt bracket order
        try:
            orders = self.ib.bracketOrder(side, units, limitPrice=entry_price, takeProfitPrice=take_profit, stopLossPrice=stop_loss)
            trade = self.ib.placeOrder(None, orders[0])
            order_id = getattr(trade.order, 'orderId', 'ib-order-unknown')
            self._narrate('BROKER_ORDER_CREATED', {'order_id': order_id, 'symbol': symbol, 'units': units})
            if os.getenv('RICK_AGGRESSIVE_PLAN'):
                self._narrate('AGGRESSIVE_LEVERAGE_APPLIED', {'symbol': symbol, 'explanation': explanation})
            return {'success': True, 'order_id': order_id}
        except Exception as exc:
            logger.exception('IB bracket order failed: %s', exc)
            return {'success': False, 'error': 'ORDER_FAILED'}

    def get_trades(self) -> List[Dict[str, Any]]:
        if self.ib is None:
            return []
        return []


def get_ibkr_connector(ib_client: Optional[Any] = None, environment: str = 'paper') -> IBKRConnector:
    return IBKRConnector(ib_client=ib_client, environment=environment)
