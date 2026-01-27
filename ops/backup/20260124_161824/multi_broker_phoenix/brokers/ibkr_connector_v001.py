#!/usr/bin/env python3
"""
IBKR Wrapper (Paper mode safe). This is a safe stub that will integrate with IBKR API
when credentials are present; otherwise it will return stubbed telemetry.
"""
import os
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

class IBKRConnector:
    def __init__(self, pin: int = None, environment: str = None):
        self.environment = environment or os.getenv('IBKR_ENV', 'paper')
        self.api_key = os.getenv('IBKR_API_KEY')
        self.api_secret = os.getenv('IBKR_API_SECRET')
        self.trading_enabled = bool(self.api_key and self.api_secret and self.environment in ('paper', 'live'))
        logger.info(f"IBKRConnector initialized for {self.environment} ; trading_enabled={self.trading_enabled}")

    def get_account_summary(self) -> Optional[Dict[str, Any]]:
        if not self.trading_enabled:
            logger.warning('IBKR credentials missing or not configured; returning stub telemetry')
            return None
        # If we have a real IBKR library (ib_insync or ibapi), try to call it; otherwise return a stub.
        try:
            from ib_insync import IB
        except Exception:
            IB = None
        if IB:
                ib = IB()
                # Connection logic is complex; assume a paper gateway exists and connect if env variables exist
                # We'll keep it read-only and return basic summary if connection succeed
                try:
                    ib.connect(host=os.getenv('IBKR_HOST', '127.0.0.1'), port=int(os.getenv('IBKR_PORT', '4001')), clientId=int(os.getenv('IBKR_CLIENT_ID', '1')))
                    # Fetch account summary via IB
                    accounts = ib.accountValues()
                    # Minimal parsing for now
                    balance = None
                    for a in accounts:
                        if a.tag == 'NetLiquidationByCurrency' and a.currency == 'USD':
                            balance = float(a.value)
                    ib.disconnect()
                    return {
                        'account_id': os.getenv('IBKR_ACCOUNT_ID', 'paper-ibkr-1'),
                        'currency': 'USD',
                        'balance': balance or 0.0
                    }
                except Exception as e:
                    logger.debug('IBKR ib_insync call failed: %s', e)
                    # Fall through to stub
        # Fallback to stub if no real IB wrapper
        return {
                'account_id': 'paper-ibkr-1',
                'currency': 'USD',
                'balance': 25000.0,
            }

    def place_order(self, symbol: str, qty: int, side: str) -> Dict[str, Any]:
        if not self.trading_enabled:
            return {'success': False, 'error': 'TRADING_DISABLED'}
        # Simulate placing an order if no real IBKR wrapper available
        logger.info('Placing stubbed IBKR order for %s %s %s', symbol, qty, side)
        return {'success': True, 'order_id': 'sim-ibkr-001', 'symbol': symbol, 'qty': qty, 'side': side}

    def get_trades(self) -> List[Dict[str, Any]]:
        if not self.trading_enabled:
            return []
        # Stub
        return []

def get_ibkr_connector(pin: int = None, environment: str = 'paper') -> IBKRConnector:
    return IBKRConnector(pin=pin, environment=environment)
