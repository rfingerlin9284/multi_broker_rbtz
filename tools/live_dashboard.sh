#!/bin/bash
# RBOTzilla Live Dashboard - Human-friendly position monitoring
# Usage: ./tools/live_dashboard.sh

cd "$(dirname "$0")/.." || exit 1
source tools/env_load.sh 2>/dev/null

REFRESH_INTERVAL=${DASHBOARD_REFRESH:-5}

clear_screen() {
    printf "\033[H\033[2J"
}

# ANSI colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m' # No Color

while true; do
    clear_screen
    
    python3 << 'PYTHON_EOF'
import os
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path

# Add repo to path
REPO = Path(__file__).resolve().parent if '__file__' in dir() else Path('/home/ing/RICK/MULTI_BROKER_PHOENIX')
sys.path.insert(0, str(REPO))

try:
    import requests
except ImportError:
    print("❌ requests module not found")
    sys.exit(1)

# Colors
G = '\033[0;32m'   # Green
R = '\033[0;31m'   # Red  
Y = '\033[1;33m'   # Yellow
C = '\033[0;36m'   # Cyan
B = '\033[1m'      # Bold
D = '\033[2m'      # Dim
N = '\033[0m'      # Reset

def load_env():
    env_path = REPO / '.env'
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                if '#' in line:
                    line = line[:line.find('#', line.find('='))].strip()
                if '=' in line:
                    k, v = line.split('=', 1)
                    if k.strip() not in os.environ:
                        os.environ[k.strip()] = v.strip()

load_env()

token = os.getenv('OANDA_API_TOKEN')
acct = os.getenv('OANDA_ACCOUNT_ID')
base = 'https://api-fxpractice.oanda.com'
headers = {'Authorization': f'Bearer {token}'}

def get_pip_value(symbol):
    """Get pip value for symbol."""
    if 'JPY' in symbol:
        return 0.01
    return 0.0001

def format_pips(symbol, price_diff):
    """Convert price difference to pips."""
    pip = get_pip_value(symbol)
    return price_diff / pip

# Get account info
try:
    r = requests.get(f'{base}/v3/accounts/{acct}/summary', headers=headers)
    account = r.json().get('account', {})
    balance = float(account.get('balance', 0))
    unrealized_pl = float(account.get('unrealizedPL', 0))
    nav = float(account.get('NAV', balance))
    margin_used = float(account.get('marginUsed', 0))
except Exception as e:
    print(f"❌ API Error: {e}")
    sys.exit(1)

# Get open trades
r = requests.get(f'{base}/v3/accounts/{acct}/openTrades', headers=headers)
trades = r.json().get('trades', [])

# Get current prices
symbols = list(set(t['instrument'] for t in trades))
prices = {}
if symbols:
    r = requests.get(f'{base}/v3/accounts/{acct}/pricing', 
                     params={'instruments': ','.join(symbols)}, headers=headers)
    for p in r.json().get('prices', []):
        bid = float(p['bids'][0]['price']) if p.get('bids') else 0
        ask = float(p['asks'][0]['price']) if p.get('asks') else 0
        prices[p['instrument']] = {'bid': bid, 'ask': ask, 'mid': (bid + ask) / 2}

# Header
now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
print(f"{B}{'═' * 70}{N}")
print(f"{B}  🤖 RBOTzilla LIVE DASHBOARD{N}")
print(f"{D}  {now}{N}")
print(f"{B}{'═' * 70}{N}")
print()

# Account Summary
pl_color = G if unrealized_pl >= 0 else R
print(f"  {B}💰 ACCOUNT{N}")
print(f"      Balance:      ${balance:,.2f}")
print(f"      Unrealized:   {pl_color}${unrealized_pl:+,.2f}{N}")
print(f"      NAV:          ${nav:,.2f}")
print(f"      Margin Used:  ${margin_used:,.2f}")
print()

# Exit Manager Config
profit_lock_pips = float(os.getenv('EXIT_PROFIT_LOCK_PIPS', '8'))
trailing_start = float(os.getenv('EXIT_TRAILING_START_PIPS', '10'))
trailing_dist = float(os.getenv('EXIT_TRAILING_DISTANCE_PIPS', '6'))
max_hold = float(os.getenv('EXIT_MAX_HOLD_HOURS', '8'))
smart_sl = os.getenv('EXIT_ENABLE_TRAILING', 'true').lower() == 'true'

print(f"  {B}⚙️  SMART SL CONFIG{N}")
print(f"      Profit Lock:   {G if smart_sl else D}{profit_lock_pips} pips → move SL to BE{N}")
print(f"      Trailing:      {G if smart_sl else D}After +{trailing_start} pips, trail {trailing_dist} pips{N}")
print(f"      Max Hold:      {max_hold}h")
print(f"      Status:        {G}✅ ACTIVE{N}" if smart_sl else f"      Status:        {R}❌ DISABLED{N}")
print()

# Positions
print(f"  {B}📊 OPEN POSITIONS ({len(trades)}){N}")
print(f"  {D}{'─' * 66}{N}")

if not trades:
    print(f"      {D}No open positions{N}")
else:
    # Group by symbol
    by_symbol = {}
    for t in trades:
        sym = t['instrument']
        if sym not in by_symbol:
            by_symbol[sym] = []
        by_symbol[sym].append(t)
    
    for symbol, symbol_trades in sorted(by_symbol.items()):
        total_units = sum(int(float(t['currentUnits'])) for t in symbol_trades)
        total_pl = sum(float(t.get('unrealizedPL', 0)) for t in symbol_trades)
        side = 'LONG' if total_units > 0 else 'SHORT'
        side_color = G if total_units > 0 else R
        pl_color = G if total_pl >= 0 else R
        
        # Get current price
        curr_price = prices.get(symbol, {}).get('mid', 0)
        pip = get_pip_value(symbol)
        
        print(f"\n  {B}{symbol}{N} {side_color}{side}{N} x{abs(total_units):,}")
        print(f"      Current Price: {curr_price:.5f}  |  P&L: {pl_color}${total_pl:+.2f}{N}")
        
        for t in sorted(symbol_trades, key=lambda x: x['id']):
            tid = t['id']
            units = int(float(t['currentUnits']))
            entry = float(t['price'])
            upl = float(t.get('unrealizedPL', 0))
            open_time = t.get('openTime', '')[:19]
            
            # Calculate pips from entry
            if units > 0:  # Long
                pips_profit = (curr_price - entry) / pip
            else:  # Short
                pips_profit = (entry - curr_price) / pip
            
            # Check for SL/TP
            sl_price = None
            tp_price = None
            if t.get('stopLossOrder'):
                sl_price = float(t['stopLossOrder'].get('price', 0))
            if t.get('takeProfitOrder'):
                tp_price = float(t['takeProfitOrder'].get('price', 0))
            
            # Calculate progress to TP
            tp_progress = 0
            if tp_price and sl_price:
                total_dist = abs(tp_price - entry)
                curr_dist = abs(curr_price - entry) if pips_profit > 0 else 0
                tp_progress = min(100, (curr_dist / total_dist) * 100) if total_dist > 0 else 0
            
            # SL status
            sl_status = ""
            if sl_price:
                sl_pips = abs(curr_price - sl_price) / pip
                if units > 0:  # Long
                    if sl_price >= entry:
                        sl_status = f"{G}🔒 BE+{N}"
                    else:
                        sl_status = f"{Y}⚡ {sl_pips:.0f}p{N}"
                else:  # Short
                    if sl_price <= entry:
                        sl_status = f"{G}🔒 BE+{N}"
                    else:
                        sl_status = f"{Y}⚡ {sl_pips:.0f}p{N}"
            else:
                sl_status = f"{R}⚠️ NO SL{N}"
            
            # Progress bar for TP
            bar_len = 15
            filled = int(tp_progress / 100 * bar_len)
            bar = '█' * filled + '░' * (bar_len - filled)
            
            pip_color = G if pips_profit >= 0 else R
            pl_color = G if upl >= 0 else R
            
            # Hold time
            try:
                open_dt = datetime.fromisoformat(open_time.replace('Z', ''))
                hold_hours = (datetime.utcnow() - open_dt).total_seconds() / 3600
                hold_str = f"{hold_hours:.1f}h"
                if hold_hours > 6:
                    hold_str = f"{Y}{hold_str}{N}"
            except:
                hold_str = "?h"
            
            print(f"      {D}#{tid}{N} │ {pip_color}{pips_profit:+6.1f}p{N} │ {pl_color}${upl:+6.2f}{N} │ TP: [{bar}] {tp_progress:4.0f}% │ {sl_status} │ {hold_str}")

print()
print(f"  {D}{'─' * 66}{N}")
print(f"  {D}Refresh: {os.getenv('DASHBOARD_REFRESH', '5')}s │ Press Ctrl+C to exit{N}")
print(f"{B}{'═' * 70}{N}")
PYTHON_EOF

    sleep "$REFRESH_INTERVAL"
done
