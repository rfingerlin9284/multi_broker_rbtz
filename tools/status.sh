#!/bin/bash
# Quick Status Check - Shows what's tradeable right now

cd /home/ing/RICK/MULTI_BROKER_PHOENIX

source .venv/bin/activate 2>/dev/null
export PYTHONPATH="/home/ing/RICK/MULTI_BROKER_PHOENIX:/home/ing/RICK/MULTI_BROKER_PHOENIX/MULTI_BROKER_PHOENIX"

python3 << 'EOF'
import sys
sys.path.insert(0, 'MULTI_BROKER_PHOENIX')
from multi_broker_phoenix.foundation.market_sessions import MarketSession
import os

# Get symbols from .env
try:
    with open('.env', 'r') as f:
        for line in f:
            if line.startswith('FEED_SYMBOLS='):
                symbols_str = line.split('=', 1)[1].strip()
                break
except:
    symbols_str = 'EUR_USD,GBP_USD,USD_JPY,AUD_USD,USD_CAD,NZD_USD,USD_CHF,BTC-USD,ETH-USD'

all_symbols = [s.strip() for s in symbols_str.split(',')]

# Create session detector
session = MarketSession()

# Display status
print(session.get_session_status_display())

# Show tradeable count
market_info = session.get_tradeable_instruments_count(all_symbols)
print(f"\n🎯 TRADEABLE NOW: {market_info['total']}/{len(all_symbols)} instruments")
print(f"   📊 Forex: {market_info['forex']} pairs")
print(f"   ₿  Crypto: {market_info['crypto']} coins") 
print(f"   📈 Futures: {market_info['futures']} contracts")

if market_info['total'] > 0:
    print(f"\n✅ Active symbols: {', '.join(market_info['tradeable_symbols'][:10])}")
else:
    print("\n⚠️  NO MARKETS OPEN - System will wait for next trading session")

# Check if battlestation is running
import subprocess
result = subprocess.run(['pgrep', '-f', 'autonomous_trading'], capture_output=True)
if result.returncode == 0:
    print("\n🚀 BATTLESTATION: RUNNING")
else:
    print("\n⏸️  BATTLESTATION: STOPPED")
    print("   Start with: python3 tools/autonomous_trading.py")

EOF
