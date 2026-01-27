"""A tiny mock engine to simulate order placement for demo and tests."""
from __future__ import annotations
from typing import Dict, Any


class MockEngine:
    def __init__(self, platform: str = 'OANDA', fee_pct: float = 0.0, slippage_pct: float = 0.0):
        self.platform = platform
        self.orders = []
        self._next_id = 1
        self.fee_pct = float(fee_pct)
        self.slippage_pct = float(slippage_pct)

    def place_order(self, candidate: Any, size: float) -> Dict[str, Any]:
        oid = f"MOCK-{self._next_id}"
        self._next_id += 1
        # simulate slippage by moving fill price slightly against the trade
        fill_price = float(candidate.entry_price)
        if getattr(candidate, 'side', None) == 'BUY':
            fill_price = fill_price * (1.0 + self.slippage_pct)
        elif getattr(candidate, 'side', None) == 'SELL':
            fill_price = fill_price * (1.0 - self.slippage_pct)
        fees = abs(fill_price * float(size) * self.fee_pct)
        order = {
            'id': oid,
            'platform': self.platform,
            'strategy_id': getattr(candidate, 'strategy_id', getattr(candidate, 'strategy', None)),
            'symbol': candidate.symbol,
            'side': getattr(candidate, 'side', None),
            'entry': candidate.entry_price,
            'fill_price': fill_price,
            'stop': candidate.stop_loss,
            'size': size,
            'fees': fees,
            'status': 'FILLED',
        }
        self.orders.append(order)
        return order
