"""Coinbase nano trade test.

By default this runs in simulation (paper_mode=True). To place a REAL tiny
order (not recommended until you've validated IBKR/OANDA paper flows), set
COINBASE_ALLOW_REAL=true and ensure COINBASE_API_KEY/COINBASE_API_SECRET are
configured (and you accept the real-money risk).
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

from multi_broker_phoenix.brokers.coinbase_safe_connector import CoinbaseSafeConnector


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


def build_candidate(symbol: str, side: str, entry: float, sl: float, tp: float) -> SimpleNamespace:
    return SimpleNamespace(symbol=symbol, side=side, entry_price=entry, stop_loss=sl, take_profit=tp, strategy_id='CB_NANO_TEST')


def main() -> None:
    symbol = os.getenv('COINBASE_TEST_SYMBOL', 'BTC-USD')
    side = os.getenv('COINBASE_TEST_SIDE', 'BUY')
    size_usd = float(os.getenv('COINBASE_TEST_SIZE_USD', '5.0'))

    # Allow explicit opt-in for real orders
    allow_real = os.getenv('COINBASE_ALLOW_REAL', 'false').lower() in ('1', 'true', 'yes')

    # If user set allow_real, start in live mode; otherwise remain paper/simulated
    paper_mode = not allow_real

    coin = CoinbaseSafeConnector(paper_mode=paper_mode)

    price = coin.fetch_live_price(symbol)
    if not price:
        print(f"Could not fetch price for {symbol} from Coinbase public API. Aborting.")
        sys.exit(1)

    units = size_usd / price

    sl = price * 0.98
    tp = price * 1.02

    cand = build_candidate(symbol, side, price, sl, tp)

    if paper_mode:
        print(f"Paper mode: Simulating {symbol} {side} for ${size_usd:.2f} (~{units:.6f} units)")
        res = coin.place_paper_order(cand, units)
        print("Simulated order result:", res)
        return

    # Live path (explicit opt-in)
    print("LIVE ORDER OPT-IN DETECTED - placing nano order in Coinbase LIVE (real money).")
    res = coin.place_live_order(cand, units, confirm_real_money=True)
    print("Live order result:", res)


if __name__ == '__main__':
    main()
