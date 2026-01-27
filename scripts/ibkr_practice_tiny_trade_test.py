"""Place a tiny IBKR paper trade (uses live Gateway if available).

This script will only place an order if the IBKR live connector can connect to
TWS/Gateway (paper port 4002). It refuses to place live-money orders.
"""
from __future__ import annotations

# pyright: reportMissingImports=false

import os
import sys
from types import SimpleNamespace
from pathlib import Path


# Allow running this script directly from the repo without PYTHONPATH exports.
_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / 'MULTI_BROKER_PHOENIX'))


def _load_env() -> None:
    """Load repo-root .env without overriding existing process environment."""
    repo_root = Path(__file__).resolve().parents[1]
    env_path = repo_root / '.env'
    if not env_path.exists():
        return

    parsed: dict[str, str] = {}
    with env_path.open('r', encoding='utf-8', errors='ignore') as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            if '#' in line:
                eq = line.find('=')
                hp = line.find('#', eq)
                if hp > 0:
                    line = line[:hp].strip()
            if '=' not in line:
                continue
            k, v = line.split('=', 1)
            k = k.strip()
            v = v.strip()
            if not k:
                continue
            parsed[k] = v

    for k, v in parsed.items():
        if k not in os.environ:
            os.environ[k] = v


_load_env()

try:
    from multi_broker_phoenix.brokers.ibkr_connector_live import get_ibkr_connector
    IBKR_LIVE_AVAILABLE = True
except Exception:
    get_ibkr_connector = None  # type: ignore[assignment]
    IBKR_LIVE_AVAILABLE = False

try:
    from multi_broker_phoenix.brokers.ibkr_connector import IBKRConnector
except Exception:
    IBKRConnector = None


def build_candidate(symbol: str, side: str, entry: float, sl: float, tp: float) -> SimpleNamespace:
    return SimpleNamespace(symbol=symbol, side=side, entry_price=entry, stop_loss=sl, take_profit=tp, strategy_id='TINY_TEST')


def main() -> None:
    symbol = os.getenv('IBKR_TINY_TRADE_SYMBOL', 'AAPL')
    side = os.getenv('IBKR_TINY_TRADE_SIDE', 'BUY')
    size = int(os.getenv('IBKR_TINY_TRADE_SIZE', '1'))

    print(f"Tiny IBKR trade test: {symbol} {side} size={size}")

    if IBKR_LIVE_AVAILABLE and get_ibkr_connector is not None:
        conn = get_ibkr_connector(paper_mode=True)
        if not conn.connect():
            print("Could not connect to IBKR Gateway on configured host/port. Aborting.")
            sys.exit(1)
        price = conn.get_last_price(symbol)
        if not price:
            print(f"No market price for {symbol} available from IBKR. Aborting.")
            sys.exit(1)

        cand = build_candidate(symbol, side, price, price * 0.99, price * 1.01)
        res = conn.place_paper_order(cand, size)
        print("Order result:", res)
        return

    if IBKRConnector is not None:
        print("Live IBKR connector not available; using simulated IBKRConnector.")
        conn = IBKRConnector()
        # Need a price to simulate fill
        price = conn.get_last_price(symbol)
        if not price:
            print(f"No price cached for {symbol}. You can seed a price by calling conn.update_price('{symbol}', <price>) in the Python REPL.")
            sys.exit(1)
        cand = build_candidate(symbol, side, price, price * 0.99, price * 1.01)
        res = conn.place_paper_order(cand, size)
        print("Simulated order result:", res)
        return

    print("No IBKR connector available to place an order.")


if __name__ == '__main__':
    main()
