"""Multi-strategy headless runner - runs multiple strategies simultaneously

Uses ALL enabled strategies from ENABLED_STRATEGIES env var.
Each strategy generates signals independently, then best signal is selected.
"""
from __future__ import annotations
import os
import time
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path

# Load .env file FIRST before anything else
from dotenv import load_dotenv
env_paths = [
    Path('/home/ing/RICK/MULTI_BROKER_PHOENIX/.env'),
    Path.cwd().parent / '.env',
    Path.cwd() / '.env'
]
for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path, override=True)
        print(f'📋 Loaded env from: {env_path}')
        break

print(f'🔐 TRADING_MODE = {os.getenv("TRADING_MODE", "NOT SET")}')

from multi_broker_phoenix.risk.risk_manager import RiskManager
from multi_broker_phoenix.strategies.base import get_strategy, list_strategies
from multi_broker_phoenix.engines.paper_engine import PaperEngine
from multi_broker_phoenix.brokers.coinbase_safe_connector import CoinbaseSafeConnector as CoinbaseConnector
from multi_broker_phoenix.brokers.ibkr_connector import IBKRConnector

try:
    from multi_broker_phoenix.brokers.oanda_connector import OANDAConnector
    OANDA_AVAILABLE = True
except:
    OANDAConnector = None
    OANDA_AVAILABLE = False

print('🎯 MULTI-STRATEGY LIVE TRADING SYSTEM')
print('=' * 60)

# Load enabled strategies from env
enabled_str = os.getenv('ENABLED_STRATEGIES', 'fabio_aaa_full,holy_grail,ema_scalper,institutional_sd')
strategy_names = [s.strip() for s in enabled_str.split(',') if s.strip()]

print(f'Loading {len(strategy_names)} strategies:')
strategies = {}
for name in strategy_names:
    try:
        strat = get_strategy(name)
        strategies[name] = strat
        print(f'  ✅ {name}')
    except Exception as e:
        print(f'  ❌ {name}: {e}')

if not strategies:
    print('❌ No strategies loaded!')
    exit(1)

print(f'\n✅ {len(strategies)} strategies active\n')

TRADING_MODE = os.getenv('TRADING_MODE', 'PAPER').upper()

# Initialize connectors
rm = RiskManager()
engine = PaperEngine()

# Initialize all brokers
print('🔧 Initializing brokers...')

# Coinbase - crypto (using public API for prices temporarily)
import requests

def fetch_coinbase_public_price(symbol: str) -> Optional[float]:
    """Fetch price from public Coinbase API (no auth needed)."""
    try:
        url = f'https://api.coinbase.com/v2/prices/{symbol}/spot'
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            return float(data['data']['amount'])
    except:
        pass
    return None

class PublicPriceConnector(CoinbaseConnector):
    def fetch_live_price(self, symbol: str) -> Optional[float]:
        price = fetch_coinbase_public_price(symbol)
        if price:
            self.update_price(symbol, price)
        return price

coin = PublicPriceConnector(paper_mode=False, engine=engine)
print(f'  ✅ Coinbase (crypto) mode: {"LIVE" if not coin.paper_mode else "PAPER"} (${coin.min_trade_usd}-{coin.max_trade_usd})')

# OANDA - FX pairs (paper trading)
oanda = None
if OANDA_AVAILABLE and os.getenv('OANDA_API_TOKEN'):
    try:
        assert OANDAConnector is not None
        oanda_mode_env = (os.getenv('OANDA_MODE') or os.getenv('BROKER_MODE_OANDA') or '').upper()
        oanda_practice = None
        if oanda_mode_env == 'LIVE':
            oanda_practice = False
        elif oanda_mode_env in ('PAPER', 'PRACTICE'):
            oanda_practice = True

        oanda = OANDAConnector(
            token=os.getenv('OANDA_API_TOKEN'),
            account_id=os.getenv('OANDA_ACCOUNT_ID'),
            base_url=os.getenv('OANDA_API_URL'),
            engine=engine,
            practice_mode=oanda_practice
        )
        mode_label = 'PAPER' if oanda.practice_mode else 'LIVE'
        print(f'  ✅ OANDA (FX) mode: {mode_label} | host={oanda.base_url}')
    except Exception as e:
        print(f'  ⚠️  OANDA failed: {e}')

# IBKR - stocks/futures (paper trading)
ibkr = None
if os.getenv('IBKR_ENABLED', 'false').lower() == 'true':
    try:
        ibkr_mode_env = (os.getenv('IBKR_MODE') or os.getenv('BROKER_MODE_IBKR') or '').upper()
        ibkr_paper = True if ibkr_mode_env in ('', 'PAPER', 'PRACTICE') else False
        ibkr = IBKRConnector(
            paper_mode=ibkr_paper,
            engine=engine
        )
        print(f'  ✅ IBKR (stocks/futures) mode: {"PAPER" if ibkr.paper_mode else "LIVE"}')
    except Exception as e:
        print(f'  ⚠️  IBKR failed: {e}')

print('')

symbols = [s.strip() for s in os.getenv('FEED_SYMBOLS', 'BTC-USD,ETH-USD,EUR_USD').split(',') if s.strip()]
print(f'Monitoring {len(symbols)} symbols: {", ".join(symbols)}')
print(f'Coinbase limits: ${coin.min_trade_usd}-${coin.max_trade_usd} per trade, ${coin.daily_loss_limit} daily loss limit')
print(f'Max trades/day: {coin.max_trades_per_day}\n')

# Pre-warm: fetch prices once to verify connectivity
print('🔍 Testing connectivity...')
for sym in symbols:
    if '-' in sym:  # Crypto -> Coinbase
        price = coin.fetch_live_price(sym)
        broker = 'Coinbase'
    elif '_' in sym and oanda:  # FX -> OANDA
        price = oanda.get_last_price(sym)
        broker = 'OANDA'
    elif ibkr:  # Others -> IBKR
        price = ibkr.get_last_price(sym)
        broker = 'IBKR'
    else:
        price = None
        broker = 'N/A'
    
    if price:
        print(f'  ✅ {sym}: ${price:,.4f} ({broker})')
    else:
        print(f'  ⚠️  {sym}: No price ({broker})')
print('')

prices = {s: [] for s in symbols}
poll_interval = float(os.getenv('HEADLESS_POLL_SECONDS', '5.0'))

print('🚀 STARTING LIVE TRADING LOOP\n')

# Normalize confidence to 0-1 range for ranking/logging
def _norm_conf(conf: float) -> float:
    try:
        c = float(conf)
    except Exception:
        return 0.5
    if c > 1.0:
        c = c / 100.0
    if c < 0:
        c = 0.0
    if c > 1:
        c = 1.0
    return c

# ═══════════════════════════════════════════════════════════════════════════════
# POSITION TRACKING & DUPLICATE PREVENTION (CRITICAL SAFETY SYSTEM)
# ═══════════════════════════════════════════════════════════════════════════════
open_positions = {}  # {symbol: {'side': 'BUY', 'entry_price': X, 'size': Y, 'timestamp': Z}}
last_trade_time = {}  # {symbol: timestamp} - cooldown tracking
TRADE_COOLDOWN_SECONDS = 300  # 5 minute cooldown between trades on same symbol
MAX_POSITIONS_PER_SYMBOL = 1  # Only 1 position per symbol
MAX_TOTAL_POSITIONS = 5  # Maximum 5 open positions total
DAILY_TRADES_LIMIT = 20  # Maximum trades per day
daily_trade_count = 0
last_trade_date = datetime.now().date()

def can_trade_symbol(symbol: str) -> tuple[bool, str]:
    """Check if we can place a new trade on this symbol."""
    global daily_trade_count, last_trade_date
    
    # Reset daily counter
    today = datetime.now().date()
    if today != last_trade_date:
        daily_trade_count = 0
        last_trade_date = today
    
    # Check daily limit
    if daily_trade_count >= DAILY_TRADES_LIMIT:
        return False, f'daily_limit_reached ({daily_trade_count}/{DAILY_TRADES_LIMIT})'
    
    # Check if already have position on this symbol
    if symbol in open_positions:
        return False, f'position_exists ({open_positions[symbol]["side"]})'
    
    # Check total positions
    if len(open_positions) >= MAX_TOTAL_POSITIONS:
        return False, f'max_positions_reached ({len(open_positions)}/{MAX_TOTAL_POSITIONS})'
    
    # Check cooldown
    if symbol in last_trade_time:
        elapsed = (datetime.now() - last_trade_time[symbol]).total_seconds()
        if elapsed < TRADE_COOLDOWN_SECONDS:
            remaining = int(TRADE_COOLDOWN_SECONDS - elapsed)
            return False, f'cooldown ({remaining}s remaining)'
    
    return True, 'OK'

def record_trade(symbol: str, side: str, entry_price: float, size: float):
    """Record a new trade."""
    global daily_trade_count
    open_positions[symbol] = {
        'side': side,
        'entry_price': entry_price,
        'size': size,
        'timestamp': datetime.now()
    }
    last_trade_time[symbol] = datetime.now()
    daily_trade_count += 1
    print(f'📍 POSITION OPENED: {symbol} {side} @ ${entry_price:.4f} (Total: {len(open_positions)} positions)')

print(f'🛡️  SAFETY: Max {MAX_POSITIONS_PER_SYMBOL} position/symbol, {MAX_TOTAL_POSITIONS} total, {TRADE_COOLDOWN_SECONDS}s cooldown\n')

def place_broker_order(connector: Any, candidate: Any, size: float, price: float) -> Dict[str, Any]:
    """Unified order dispatcher honoring paper/live flags."""
    is_live_capable = hasattr(connector, 'place_live_order') and getattr(connector, 'paper_mode', True) is False
    if is_live_capable and TRADING_MODE == 'LIVE':
        return connector.place_live_order(candidate, size, confirm_real_money=True)
    if hasattr(connector, 'place_order'):
        return connector.place_order(candidate, size, confirm_real_money=(TRADING_MODE == 'LIVE'))
    return connector.place_paper_order(candidate, size)


try:
    loop_count = 0
    while True:
        loop_count += 1
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        for sym in symbols:
            # Route to appropriate broker
            if '-' in sym:  # Crypto -> Coinbase
                connector = coin
                price = coin.fetch_live_price(sym)
            elif '_' in sym and oanda:  # FX -> OANDA
                connector = oanda
                price = oanda.get_last_price(sym)
            elif ibkr:  # Others -> IBKR
                connector = ibkr
                price = ibkr.get_last_price(sym)
            else:
                continue
            
            if price is None:
                continue
                
            prices[sym].append(price)
            if len(prices[sym]) > 50:  # Keep 50 prices (enough for strategies)
                prices[sym] = prices[sym][-50:]
            
            # Show progress on data collection
            if len(prices[sym]) < 30 and loop_count % 20 == 1:
                print(f'[{timestamp}] 📊 {sym}: Collecting data... {len(prices[sym])}/30 prices')
            
            # Skip if not enough data yet (need at least 30 prices)
            if len(prices[sym]) < 30:
                continue
            
            # Run ALL strategies
            market_data = {
                'symbol': sym,
                'platform': 'COINBASE',
                'prices': prices[sym],
                'volumes': []
            }
            
            candidates = []
            for strat_name, strategy in strategies.items():
                try:
                    cand = strategy.generate_candidate(market_data)
                    if cand:
                        # Add strategy name to candidate
                        setattr(cand, 'strategy_name', strat_name)
                        # Normalize confidence for fair ranking
                        current_conf = getattr(cand, 'confidence', 0.5)
                        normed_conf = _norm_conf(current_conf)
                        setattr(cand, 'confidence', normed_conf)
                        candidates.append(cand)
                        # Only log signals if we can actually trade this symbol
                        if sym not in open_positions:
                            print(f'[{timestamp}] 🎯 {strat_name}: {sym} {cand.side} @ ${price:,.2f} (conf: {normed_conf:.2%})')
                except Exception as e:
                    if loop_count % 100 == 1:  # Log errors occasionally
                        print(f'[{timestamp}] ⚠️  {strat_name} error: {e}')
            
            if not candidates:
                continue
            
            # Pick best candidate (highest confidence)
            best = max(candidates, key=lambda c: getattr(c, 'confidence', 0.5))
            best_conf = _norm_conf(getattr(best, 'confidence', 0.5))
            setattr(best, 'confidence', best_conf)
            print(f'[{timestamp}] 🏆 BEST: {best.strategy_name} (confidence: {best_conf:.2%})')
            
            # ═══════════════════════════════════════════════════════════════
            # CRITICAL: CHECK POSITION LIMITS BEFORE PLACING ANY ORDER
            # ═══════════════════════════════════════════════════════════════
            can_trade, block_reason = can_trade_symbol(sym)
            if not can_trade:
                if loop_count % 60 == 1:  # Only log occasionally to reduce spam
                    print(f'[{timestamp}] 🛡️  BLOCKED: {sym} - {block_reason}')
                continue
            
            # Risk check
            from multi_broker_phoenix.risk.trade_risk_gate import can_open_trade
            dec = can_open_trade(best, account_equity=rm.state.equity_now or 100000.0, rm=rm)
            if not dec.allowed:
                print(f'[{timestamp}] 🚫 BLOCKED: {dec.reason}')
                continue
            
            # Calculate position size
            risk_usd = float(os.getenv('MAX_RISK_USD_PER_TRADE', '10.0'))
            stop_dist = abs(best.entry_price - best.stop_loss)
            if stop_dist > 0:
                size = risk_usd / stop_dist
            else:
                size = coin.min_trade_usd / price
            
            # Place order on the appropriate broker
            try:
                result = place_broker_order(connector, best, size, price)
                if result.get('success'):
                    broker_name = 'Coinbase' if connector == coin else ('OANDA' if connector == oanda else 'IBKR')
                    mode_label = 'LIVE' if getattr(connector, 'paper_mode', True) is False else 'PAPER'
                    print(f'[{timestamp}] 💰 ORDER PLACED: {best.strategy_name} {sym} {best.side} size={size:.6f} @ ${price:,.2f} ({broker_name} {mode_label})')
                    print(f'              Stop: ${best.stop_loss:,.2f} ({stop_dist/price*100:.2f}%)')
                    # ═══════════════════════════════════════════════════════════════
                    # CRITICAL: RECORD TRADE TO PREVENT DUPLICATES
                    # ═══════════════════════════════════════════════════════════════
                    record_trade(sym, best.side, price, size)
                else:
                    print(f'[{timestamp}] ❌ ORDER FAILED: {result.get("error")}')
            except Exception as e:
                print(f'[{timestamp}] ❌ ORDER ERROR: {e}')
        
        # Status update every minute
        if loop_count % (60 // int(poll_interval)) == 0:
            perf = coin.get_performance_summary()
            pos_list = ', '.join([f'{s}:{p["side"]}' for s, p in open_positions.items()]) or 'None'
            print(f'\n📊 STATUS: Tier {perf["tier"]} ({perf["tier_name"]}) | '
                  f'Trades: {daily_trade_count}/{DAILY_TRADES_LIMIT} | Win rate: {perf["win_rate"]:.1%} | '
                  f'Profit: ${perf["total_profit"]:.2f}')
            print(f'📍 POSITIONS ({len(open_positions)}/{MAX_TOTAL_POSITIONS}): {pos_list}\n')
        
        time.sleep(poll_interval)

except KeyboardInterrupt:
    print('\n🛑 Stopped by user')
except Exception as e:
    print(f'\n❌ Fatal error: {e}')
    import traceback
    traceback.print_exc()
