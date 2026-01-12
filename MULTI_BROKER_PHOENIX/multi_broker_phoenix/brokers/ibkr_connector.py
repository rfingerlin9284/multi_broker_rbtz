"""IBKR connector (paper-first). This is a paper-mode adapter that can be
extended to talk to the real IBKR Gateway/TWS when credentials and local
gateway are available. For now, it uses provided price updates or a linked
engine to execute paper orders.
"""
from __future__ import annotations
from typing import Optional, Dict, Any


class IBKRConnector:
    def __init__(self, paper_mode: bool = True, engine: Optional[Any] = None, fee_pct: float = 0.001, slippage_pct: float = 0.001):
        self.paper_mode = bool(paper_mode)
        self._price_by_symbol: Dict[str, float] = {}
        self.engine = engine
        self.fee_pct = float(fee_pct)
        self.slippage_pct = float(slippage_pct)

    def update_price(self, symbol: str, price: float):
        self._price_by_symbol[symbol] = float(price)

    def get_last_price(self, symbol: str) -> Optional[float]:
        return self._price_by_symbol.get(symbol)

    def place_paper_order(self, candidate: Any, size: float) -> Dict[str, Any]:
        sym = getattr(candidate, 'symbol', None)
        price = self.get_last_price(sym)
        if price is None:
            raise RuntimeError('no_price')
        side = getattr(candidate, 'side', None)
        fill = price * (1.0 + self.slippage_pct) if side == 'BUY' else price * (1.0 - self.slippage_pct)
        fees = abs(fill * float(size) * self.fee_pct)
        from ..config.runtime import resolve_execution_type
        execution_type = resolve_execution_type('IBKR', supports_platform_paper=True)
        order = {
            'id': f'IB-PAPER-{sym}-{int(fill*100000)}',
            'platform': 'IBKR',
            'strategy_id': getattr(candidate, 'strategy_id', None),
            'symbol': sym,
            'side': side,
            'entry': getattr(candidate, 'entry_price', None),
            'fill_price': fill,
            'stop': getattr(candidate, 'stop_loss', None),
            'size': size,
            'fees': fees,
            'status': 'FILLED',
            'execution_type': execution_type,
        }
        if self.engine is not None:
            return self.engine.place_order(candidate, size, execution_type=execution_type)
        return order

    def enable_live_gateway(self, host: str = 'localhost', port: int = 4002):
        raise NotImplementedError('IBKR live gateway integration not implemented; please extend with IB-insync or TWS API')