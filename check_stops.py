#!/usr/bin/env python3
"""Check stop loss status on all open trades."""
import os, requests
from dotenv import load_dotenv
load_dotenv()

token = os.getenv('OANDA_API_TOKEN')
resp = requests.get(
    'https://api-fxpractice.oanda.com/v3/accounts/101-001-31210531-001/openTrades',
    headers={'Authorization': f'Bearer {token}'}
)
trades = resp.json().get('trades', [])

print('OPEN TRADES - STOP LOSS CHECK:')
print('='*60)
for t in trades:
    sl = t.get('stopLossOrder')
    ts = t.get('trailingStopLossOrder')
    print(f"{t['instrument']}: Entry={t['price']}")
    print(f"  Units: {t['currentUnits']}, P/L: ${float(t['unrealizedPL']):.2f}")
    if sl:
        print(f"  StopLoss: {sl['price']}")
    else:
        print(f"  StopLoss: NONE ⚠️")
    if ts:
        print(f"  TrailingStop: distance={ts['distance']}")
    else:
        print(f"  TrailingStop: NONE ⚠️")
    print()

print(f"Total open trades: {len(trades)}")
