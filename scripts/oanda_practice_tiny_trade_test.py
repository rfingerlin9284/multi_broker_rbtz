"""Place a tiny OANDA practice trade with strict SL/TP bracket."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from execution.oanda_practice_client import OandaPracticeClient


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


def _mid_price(price_entry: dict) -> float:
    bids = price_entry.get('bids', [])
    asks = price_entry.get('asks', [])
    if not bids or not asks:
        raise ValueError('Missing bid/ask data for instrument')
    bid = float(bids[0]['price'])
    ask = float(asks[0]['price'])
    return (bid + ask) / 2.0


def main() -> None:
    client = OandaPracticeClient()

    instrument = os.getenv('OANDA_TINY_TRADE_INSTRUMENT', 'EUR_USD')
    direction = os.getenv('OANDA_TINY_TRADE_DIRECTION', 'buy').lower()
    sl_pips = float(os.getenv('OANDA_TINY_TRADE_SL_PIPS', '0.0008'))
    tp_pips = float(os.getenv('OANDA_TINY_TRADE_TP_PIPS', '0.0018'))

    payload = client.get_prices([instrument])
    prices = payload.get('prices', [])
    if not prices:
        print('No price data returned, aborting tiny trade test')
        sys.exit(1)
    price_entry = prices[0]

    mid = _mid_price(price_entry)
    if direction == 'buy':
        units = 1
        sl_price = mid - sl_pips
        tp_price = mid + tp_pips
    else:
        units = -1
        sl_price = mid + sl_pips
        tp_price = mid - tp_pips

    print('Placing tiny practice order (1 unit) | instrument=%s direction=%s' % (instrument, direction))
    result = client.create_order_market(
        instrument=instrument,
        units=units,
        sl_price=sl_price,
        tp_price=tp_price,
        client_tag='tiny_trade_test',
    )

    print('\nOrder response:')
    print(result)

    open_trades = client.list_open_trades()
    print('\nOpen trades snapshot:')
    print(open_trades)


if __name__ == '__main__':
    main()
