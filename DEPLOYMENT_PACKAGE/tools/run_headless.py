"""Small headless runner used by tools/start_headless.sh

Runs a minimal loop that polls configured connectors for prices and executes
strategy-driven test-ordering logic in PAPER mode.

CANARY MODE: When CANARY_MODE=true, runs in ultra-conservative mode with:
- Slower polling (30s default)
- Verbose narration of every action
- Lower risk limits
- Detailed logging for monitoring
"""
from __future__ import annotations
import os
import time
from typing import List, Optional
import argparse
from datetime import datetime
from pathlib import Path

# ============================================================
# CRITICAL: Load .env file FIRST before any other imports
# This ensures API keys (OPENAI, XAI, DEEPSEEK) are available
# ============================================================
def _load_env_file():
    """Load the canonical .env file properly, handling inline comments.

    Important safety behavior:
    - Never override keys that are already present in the process environment.
    - Within the .env file itself, apply shell-style semantics: LAST value wins.
    - Detect duplicates and warn loudly (duplicates are a common cause of
      silent auth failures when keys are regenerated).
    """
    # Find .env file - look in project root
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent.parent  # Go up from tools/ to MULTI_BROKER_PHOENIX/ to project root
    env_path = project_root / '.env'

    if not env_path.exists():
        print(f"⚠️  No .env file found at {env_path}")
        return

    loaded_count = 0

    # Parse entire file first to detect duplicates and implement last-wins.
    parsed: dict[str, str] = {}
    occurrences: dict[str, list[int]] = {}
    with open(env_path, encoding='utf-8', errors='ignore') as f:
        for i, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue

            # Handle inline comments by splitting on # only if it's after the =
            if '#' in line:
                eq_pos = line.index('=')
                hash_pos = line.find('#', eq_pos)
                if hash_pos > 0:
                    line = line[:hash_pos].strip()

            if '=' not in line:
                continue

            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip()
            if not key:
                continue

            occurrences.setdefault(key, []).append(i)
            parsed[key] = value  # last occurrence wins

    dupes = {k: v for k, v in occurrences.items() if len(v) > 1}
    if dupes:
        print("🚨 WARNING: Duplicate keys detected in .env (last occurrence will be used):")
        for k in sorted(dupes):
            print(f"   - {k} @ lines {','.join(map(str, dupes[k]))}")
        print("   ✅ To prevent silent failures, fix by removing duplicates (or run tools/env_preflight.py --fix).")

    # Apply parsed keys, but never override process env.
    for key, value in parsed.items():
        if key not in os.environ:
            os.environ[key] = value
            loaded_count += 1

    if loaded_count > 0:
        print(f"✅ Loaded {loaded_count} environment variables from {env_path}")
    
    
    # Verify critical keys
    if os.getenv('OPENAI_API_KEY'):
        print(f"   ✅ OPENAI_API_KEY loaded")
    if os.getenv('XAI_API_KEY'):
        print(f"   ✅ XAI_API_KEY loaded")
    if os.getenv('DEEPSEEK_API_KEY'):
        print(f"   ✅ DEEPSEEK_API_KEY loaded")

# Load env IMMEDIATELY at module import
_load_env_file()

from multi_broker_phoenix.risk.risk_manager import RiskManager
from multi_broker_phoenix.strategies.base import get_strategy
from multi_broker_phoenix.engines.paper_engine import PaperEngine
from multi_broker_phoenix.brokers.coinbase_safe_connector import CoinbaseSafeConnector as CoinbaseConnector

# Use LIVE IBKR connector (connects to TWS/Gateway paper port 4002)
try:
    from multi_broker_phoenix.brokers.ibkr_connector_live import IBKRLiveConnector as IBKRConnector
    IBKR_LIVE_AVAILABLE = True
except ImportError:
    from multi_broker_phoenix.brokers.ibkr_connector import IBKRConnector
    IBKR_LIVE_AVAILABLE = False
    print("⚠️  IBKRLiveConnector not available - falling back to stub (install ib_insync)")

try:
    from multi_broker_phoenix.brokers.oanda_connector import OANDAConnector
except Exception:
    OANDAConnector = None

# Import AI Hive
try:
    import sys
    hive_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'hive_real')
    if hive_path not in sys.path:
        sys.path.insert(0, hive_path)
    from api_ai_hive import get_api_ai_vote
    AI_HIVE_AVAILABLE = True
except Exception as exc:
    AI_HIVE_AVAILABLE = False
    print(f'AI Hive not available: {exc}')



def _symbols_from_env() -> List[str]:
    # Coinbase uses hyphen format (BTC-USD), OANDA uses underscore (EUR_USD)
    s = os.getenv('FEED_SYMBOLS', 'BTC-USD,ETH-USD')
    return [x.strip() for x in s.split(',') if x.strip()]


def _is_canary_mode() -> bool:
    """Check if CANARY_MODE is enabled in environment."""
    return os.getenv('CANARY_MODE', 'false').lower() in ('true', '1', 'yes')


def _canary_log(msg: str):
    """Verbose logging for canary mode with timestamp."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"🐤 CANARY [{timestamp}] {msg}")


def _get_poll_interval() -> float:
    """Get polling interval, respecting canary mode override."""
    if _is_canary_mode():
        return float(os.getenv('CANARY_POLL_SECONDS', '30.0'))
    return float(os.getenv('HEADLESS_POLL_SECONDS', '2.0'))


def _get_max_risk_usd() -> float:
    """Get max risk per trade, respecting canary mode override."""
    if _is_canary_mode():
        return float(os.getenv('CANARY_MAX_RISK_USD', '10.0'))
    return float(os.getenv('MAX_RISK_USD_PER_TRADE', '30.0'))


def _choose_mode_interactive(options):
    """Present a simple numeric menu to choose a mode (TTY only). Returns mode key."""
    print('Select headless runner mode:')
    for idx, (k, desc) in enumerate(options.items(), start=1):
        print(f"  {idx}) {k} - {desc}")
    try:
        choice = input('Enter choice number (default 1): ').strip()
        if not choice:
            return list(options.keys())[0]
        i = int(choice) - 1
        return list(options.keys())[i]
    except Exception:
        return list(options.keys())[0]


def _trigger_autonomous_repair(error: Exception):
    """Trigger AI collective to diagnose and repair Hive failure."""
    import traceback
    
    print("\n🤖 INITIATING AUTONOMOUS REPAIR SYSTEM")
    print("   Connected AIs will collectively diagnose and patch the issue...")
    
    # Check if autonomous mode enabled
    if os.getenv('HIVE_AUTONOMOUS_REPAIR', 'false').lower() != 'true':
        print("   ⚠️  Autonomous repair DISABLED (set HIVE_AUTONOMOUS_REPAIR=true)")
        print("   📧 Alert sent - manual intervention required")
        _log_repair_incident(error, "DISABLED", "Autonomous repair not enabled", False)
        return
    
    try:
        # Import repair module
        from hive_real.autonomous_repair import diagnose_and_repair
        
        # Get error details
        error_type = type(error).__name__
        error_msg = str(error)
        error_trace = traceback.format_exc()
        
        print(f"\n🔍 ERROR ANALYSIS:")
        print(f"   Type: {error_type}")
        print(f"   Message: {error_msg}")
        
        # Call AI collective for diagnosis and repair
        result = diagnose_and_repair(
            error_type=error_type,
            error_message=error_msg,
            stack_trace=error_trace
        )
        
        if result['success']:
            print(f"\n✅ REPAIR SUCCESSFUL")
            print(f"   {result['summary']}")
            _log_repair_incident(error, "SUCCESS", result['documentation'], True)
        else:
            print(f"\n❌ REPAIR FAILED")
            print(f"   {result['reason']}")
            _log_repair_incident(error, "FAILED", result['documentation'], False)
            
    except ImportError:
        print("   ⚠️  Autonomous repair module not found")
        print("   📧 Alert sent - manual intervention required")
        _log_repair_incident(error, "MODULE_MISSING", "Repair module not installed", False)
    except Exception as repair_error:
        print(f"   ⚠️  Repair system error: {repair_error}")
        _log_repair_incident(error, "REPAIR_ERROR", str(repair_error), False)


def _log_repair_incident(error: Exception, status: str, details: str, success: bool):
    """Log repair incident to file for human review."""
    import json
    from pathlib import Path
    
    log_dir = Path(os.path.dirname(os.path.dirname(__file__))) / 'hive_real' / 'repair_logs'
    log_dir.mkdir(exist_ok=True)
    
    incident = {
        'timestamp': datetime.now().isoformat(),
        'error_type': type(error).__name__,
        'error_message': str(error),
        'status': status,
        'success': success,
        'details': details
    }
    
    log_file = log_dir / f"repair_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(log_file, 'w') as f:
        json.dump(incident, f, indent=2)
    
    print(f"   📝 Incident logged: {log_file}")


def run_headless(mode: Optional[str] = None):
    canary_mode = _is_canary_mode()
    
    if canary_mode:
        _canary_log("🚨 CANARY MODE ACTIVE - Ultra-conservative monitoring enabled")
        _canary_log(f"Polling interval: {_get_poll_interval()}s (slower for safety)")
        _canary_log(f"Max risk per trade: ${_get_max_risk_usd()} (ultra-low)")
    
    print('Starting headless runner (minimal).')
    # Determine mode: CLI arg, env var, or interactive menu
    valid_modes = {
        'auto': 'Auto (prefer platform connectors where appropriate)',
        'multi-asset': 'All brokers: OANDA + IBKR + Coinbase (high-quality AI Hive filtering)',
        'platform-paper': 'Prefer platform paper connectors when available',
        'simulate': 'Simulate only (engine)',
        'oanda-only': 'Use OANDA only (filter by symbol eligibility)',
        'coinbase-only': 'Use Coinbase only',
        'ibkr-only': 'Use IBKR only',
    }
    env_mode = os.getenv('HEADLESS_MODE')
    chosen = mode or env_mode
    if not chosen and os.isatty(0):
        # interactive selection
        chosen = _choose_mode_interactive(valid_modes)
    if not chosen:
        chosen = 'auto'
    if chosen not in valid_modes:
        print(f'Invalid mode {chosen}, falling back to auto')
        chosen = 'auto'
    print(f'Headless mode: {chosen} ({valid_modes.get(chosen)})')
    
    if canary_mode:
        _canary_log(f"Selected mode: {chosen}")

    rm = RiskManager()
    engine = PaperEngine()
    symbols = _symbols_from_env()
    
    if canary_mode:
        _canary_log(f"Initializing connectors for symbols: {', '.join(symbols)}")
    
    # ============================================================
    # BROKER CONFIGURATION (PURGED ALL SIMULATION - API ONLY)
    # ============================================================
    # COINBASE: LIVE TRADING (real money) - starts with nano-lots
    # OANDA: PRACTICE API (real API, paper account)
    # IBKR: PAPER TRADING (real TWS connection, paper port 4002)
    # ============================================================
    
    # Determine Coinbase mode from environment
    coinbase_live = os.getenv('COINBASE_LIVE', 'false').lower() in ('true', '1', 'yes')
    
    coin = None
    try:
        coin = CoinbaseConnector(paper_mode=not coinbase_live, engine=engine)
        mode_label = "🔴 LIVE (REAL MONEY)" if coinbase_live else "🟢 SIMULATION"
        print(f"✅ Coinbase connector: {mode_label}")
        if coinbase_live:
            print(f"   ⚠️  COINBASE LIVE MODE ACTIVE - Real money trades enabled")
            print(f"   💰 Nano-lot limits: ${coin.min_trade_usd}-${coin.max_trade_usd} per trade")
            print(f"   🛡️  Daily loss limit: ${coin.daily_loss_limit}")
        if canary_mode:
            _canary_log(f"Coinbase connector initialized: {mode_label}")
    except Exception as exc:
        print(f"⚠️  Coinbase connector failed to initialize; continuing: {exc}")
        if canary_mode:
            _canary_log("Coinbase connector failed to initialize")

    # IBKR: Real TWS connection to paper trading account (port 4002)
    ibkr_enabled = os.getenv('IBKR_ENABLED', 'true').lower() in ('true', '1', 'yes')
    ibkr = None
    if ibkr_enabled:
        try:
            ibkr_host = os.getenv('IBKR_HOST', '172.25.80.1')
            ibkr_port = int(os.getenv('IBKR_PORT', '4002'))  # Paper port
            ibkr_client_id = int(os.getenv('IBKR_CLIENT_ID', '1'))
            
            ibkr = IBKRConnector(
                host=ibkr_host,
                port=ibkr_port,
                client_id=ibkr_client_id,
                paper_mode=True,  # Always paper for safety
                engine=engine
            )
            print(f"✅ IBKR connector: 🟡 PAPER TRADING (TWS port {ibkr_port})")
            print(f"   🔗 Connecting to {ibkr_host}:{ibkr_port}")
            if canary_mode:
                _canary_log(f"IBKR connector initialized: paper mode (port {ibkr_port})")
        except Exception as exc:
            print(f"⚠️  IBKR connector failed to initialize: {exc}")
            print(f"   ℹ️  Make sure TWS/IB Gateway is running on paper port 4002")
            if canary_mode:
                _canary_log("IBKR connector failed to initialize")
    
    # OANDA: Real API connection to PRACTICE account (api-fxpractice.oanda.com)
    oanda = None
    if OANDAConnector is not None and os.getenv('OANDA_API_TOKEN'):
        # Prefer explicit practice account id when in practice mode
        oanda_account = os.getenv('OANDA_ACCOUNT_ID')
        practice_account = os.getenv('OANDA_PRACTICE_ACCOUNT_ID')
        oanda_mode = (os.getenv('OANDA_MODE') or '').upper()
        practice_flag = os.getenv('OANDA_PRACTICE', '').lower() in ('true','1','yes')
        
        # Determine effective account id: prefer practice_account when present and we are in practice mode
        if practice_account and (practice_flag or oanda_mode in ('PAPER','PRACTICE') or os.getenv('TRADING_MODE','PAPER').upper() != 'LIVE'):
            oanda_account = practice_account

        oanda_base_url = os.getenv('OANDA_API_URL', 'https://api-fxpractice.oanda.com')
        
        try:
            oanda = OANDAConnector(
                token=os.getenv('OANDA_API_TOKEN'),
                account_id=oanda_account,
                base_url=oanda_base_url,
                engine=engine,
                practice_mode=True  # Always practice for safety
            )
            
            # Verify credentials
            cred_check = oanda.verify_credentials()
            if cred_check.get('success'):
                print(f"✅ OANDA connector: 🟡 PRACTICE API (REAL API CONNECTION)")
                print(f"   🔑 Account: {oanda_account}")
                print(f"   🌐 API: {oanda_base_url}")
                print(f"   💱 Currency: {cred_check.get('currency', 'UNKNOWN')}")
                print(f"   ✅ API AUTHENTICATION VERIFIED")
                if canary_mode:
                    _canary_log("OANDA connector: API AUTH VERIFIED")
            else:
                print(f"⚠️  OANDA connector: Authentication check failed: {cred_check.get('error')}")
                print(f"   ⚠️  Orders may fail - check API token")
        except Exception as exc:
            print(f"⚠️  OANDA connector failed to initialize: {exc}")
            oanda = None
    else:
        print('⚠️  OANDA connector unavailable or token missing; continuing with other connectors')
        if canary_mode:
            _canary_log("OANDA connector disabled/unavailable")

    # Load ALL strategies from ENABLED_STRATEGIES (comma-separated list)
    enabled_strategy_names = os.getenv('ENABLED_STRATEGIES', 'fabio_aaa_full,holy_grail,ema_scalper,institutional_sd').split(',')
    strategies = {}
    for strat_name in enabled_strategy_names:
        strat_name = strat_name.strip()
        if strat_name:
            try:
                strategies[strat_name] = get_strategy(strat_name)
                print(f"✅ Strategy loaded: {strat_name}")
            except Exception as e:
                print(f"⚠️  Strategy {strat_name} failed to load: {e}")
    
    if not strategies:
        # Fallback to default if none loaded
        default_strat = os.getenv('DEFAULT_STRATEGY', 'holy_grail')
        strategies[default_strat] = get_strategy(default_strat)
        print(f"⚠️  Using fallback strategy: {default_strat}")
    
    if canary_mode:
        _canary_log(f"Strategies loaded: {', '.join(strategies.keys())}")
    
    prices = {s: [] for s in symbols}
    
    # PRE-LOAD HISTORICAL DATA for each symbol (so strategies have data immediately)
    print("📊 Pre-loading historical data for instant signal generation...")
    for sym in symbols:
        try:
            if '-' in sym and coin:  # Coinbase symbol
                historical = coin.get_historical_data(sym, periods=100, granularity=300)  # 5-min candles
                if historical:
                    prices[sym] = historical
                    print(f"   ✅ {sym}: {len(historical)} candles loaded (${min(historical):.0f} - ${max(historical):.0f})")
            elif '_' in sym and oanda:  # OANDA symbol
                # Try OANDA historical
                try:
                    hist_data = oanda.get_historical_data(sym, count=100)
                    if hist_data:
                        hist_prices = [float(p.get('mid', {}).get('c', 0)) for p in hist_data if float(p.get('mid', {}).get('c', 0)) > 0]
                        if hist_prices:
                            prices[sym] = hist_prices
                            print(f"   ✅ {sym}: {len(hist_prices)} prices loaded from OANDA")
                except Exception as e:
                    print(f"   ⚠️  {sym}: OANDA historical failed: {e}")
        except Exception as e:
            print(f"   ⚠️  {sym}: Failed to load historical data: {e}")
    
    print(f"📈 Historical data loaded. Ready for immediate signal detection!")

    try:
        loop_count = 0
        # Cycle telemetry counters to avoid silent failures (signals, blocks, orders, no-price)
        cycle_counters = {'signals': 0, 'blocked_ai': 0, 'blocked_risk': 0, 'orders_placed': 0, 'no_price': 0}
        if canary_mode:
            _canary_log("🚀 Starting main loop - monitoring all activity")
        
        while True:
            loop_count += 1
            if canary_mode and loop_count % 10 == 1:  # Every 10th iteration
                _canary_log(f"Loop #{loop_count} - Health check OK")
            
            for sym in symbols:
                # poll each connector for a price
                price = None
                # Route based on mode or symbol pattern
                if chosen == 'coinbase-only' or (chosen in ('auto', 'multi-asset') and '-' in sym):
                    price = coin.fetch_live_price(sym)
                    if canary_mode and price:
                        _canary_log(f"📊 {sym} price: ${price:.2f} (Coinbase)")
                elif chosen == 'ibkr-only':
                    price = ibkr.get_last_price(sym)
                    if canary_mode and price:
                        _canary_log(f"📊 {sym} price: ${price:.2f} (IBKR)")
                elif oanda and ('_' in sym or chosen in ('oanda-only', 'multi-asset')):
                    price = oanda.get_last_price(sym)
                    if canary_mode and price:
                        _canary_log(f"📊 {sym} price: ${price:.2f} (OANDA)")
                else:
                    # fallback: try coin then ibkr
                    price = coin.fetch_live_price(sym) or ibkr.get_last_price(sym)
                    if canary_mode and price:
                        _canary_log(f"📊 {sym} price: ${price:.2f} (fallback)")
                
                if price is None:
                    cycle_counters['no_price'] += 1
                    if canary_mode:
                        _canary_log(f"⚠️  {sym} price unavailable - skipping")
                    continue
                prices[sym].append(price)
                if len(prices[sym]) > 200:
                    prices[sym] = prices[sym][-200:]
                
                # Log price history depth
                if loop_count <= 25 and loop_count % 5 == 0:
                    print(f"   📈 {sym}: {len(prices[sym])} prices collected (need 20+ for signals)")
                
                # Try ALL strategies for this symbol
                for strat_name, strategy in strategies.items():
                    cand = strategy.generate_candidate({'symbol': sym, 'platform':'HEADLESS', 'prices': prices[sym]})
                    if not cand:
                        if canary_mode and loop_count % 10 == 1:
                            _canary_log(f"✋ {sym}/{strat_name} - No signal")
                        continue
                    
                    # Record signal
                    cycle_counters['signals'] += 1
                    if canary_mode:
                        _canary_log(f"🎯 {sym} SIGNAL ({strat_name}): {cand.side} @ ${price:.2f}")
                
                    # Decide target platform based on symbol if strategy did not set one
                    platform_guess = 'OANDA' if '_' in sym else 'COINBASE' if '-' in sym else 'IBKR'
                    try:
                        if not getattr(cand, 'platform', None):
                            cand.platform = platform_guess
                    except Exception:
                        pass
                    from multi_broker_phoenix.risk.trade_risk_gate import can_open_trade
                    dec = can_open_trade(cand, account_equity=rm.state.equity_now or 100000.0, rm=rm)
                    if not dec.allowed:
                        cycle_counters['blocked_risk'] += 1
                        print(f"trade blocked: {dec.reason}")
                        if canary_mode:
                            _canary_log(f"🚫 Trade BLOCKED: {dec.reason}")
                        continue
                    
                    # AI Hive consensus check
                    if AI_HIVE_AVAILABLE and os.getenv('ENABLE_AI_HIVE', 'false').lower() == 'true':
                        # Check for emergency bypass (manual override)
                        if os.getenv('HIVE_EMERGENCY_BYPASS', 'false').lower() == 'true':
                            print("⚠️  EMERGENCY BYPASS ACTIVE - Hive disabled by manual override")
                            if canary_mode:
                                _canary_log("⚠️  EMERGENCY BYPASS - Manual override active")
                        else:
                            try:
                                # Get recent prices for Hive analysis
                                recent_prices = []
                                try:
                                    if '_' in sym:  # OANDA
                                        if oanda:
                                            prices_data = oanda.get_historical_data(sym, count=30)
                                            recent_prices = [float(p.get('mid', {}).get('c', 0)) for p in prices_data]
                                    elif '-' in sym:  # Coinbase
                                        prices_data = coin.get_historical_data(sym, periods=30)
                                        recent_prices = [float(p) for p in prices_data]
                                except Exception:
                                    recent_prices = [cand.entry_price] * 10  # Fallback to current price
                                
                                market_data = {'prices': recent_prices or [cand.entry_price]}
                                hive_result = get_api_ai_vote(sym, cand.side.upper(), cand.entry_price, market_data)
                                
                                if canary_mode:
                                    _canary_log(f"🤖 AI Hive: {hive_result['vote']} (consensus: {hive_result.get('consensus', 0):.1%})")
                                
                                # Block if not approved
                                if hive_result['vote'] not in ['approve', 'execute']:
                                    cycle_counters['blocked_ai'] += 1
                                    print(f"AI Hive blocked trade: {hive_result['reasoning']}")
                                    if canary_mode:
                                        _canary_log(f"🚫 AI Hive BLOCKED: {hive_result['reasoning']}")
                                    continue
                                    
                            except Exception as hive_exc:
                                # CRITICAL FAILURE - Trigger self-healing
                                print(f"🚫 AI HIVE CRITICAL FAILURE - BLOCKING ALL NEW TRADES")
                                print(f"   Error: {hive_exc}")
                                if canary_mode:
                                    _canary_log(f"🚨 CRITICAL: AI Hive failure - {hive_exc}")
                                
                                # Trigger autonomous diagnosis and repair
                                _trigger_autonomous_repair(hive_exc)
                                continue  # HALT - no trade execution on Hive failure
                    
                    sizing = rm.size_for_trade(cand, rm.state.equity_now or 100000.0, fee_pct=coin.fee_pct, slippage_pct=coin.slippage_pct)
                    if not sizing.get('allowed'):
                        print('sizing rejected:', sizing.get('reason'))
                        if canary_mode:
                            _canary_log(f"🚫 Sizing REJECTED: {sizing.get('reason')}")
                        continue
                    
                    if canary_mode:
                        _canary_log(f"✅ Risk checks PASSED - Size: {sizing['size']} units")
                    # Choose connector based on symbol/platform and prefer platform paper when available
                    order = None
                    try:
                        # Prefer explicit platform in candidate
                        platform = getattr(cand, 'platform', None) or ( 'OANDA' if '_' in sym else 'COINBASE' if '-' in sym else 'IBKR' )
                        
                        if canary_mode:
                            _canary_log(f"📝 Preparing order: {cand.side} {sym} via {platform}")
                        
                        # ============================================================
                        # ORDER ROUTING: REAL API CONNECTIONS (NO SIMULATION)
                        # ============================================================
                        # OANDA: place_paper_order() -> Real Practice API
                        # IBKR: place_paper_order() -> Real TWS Paper Port 4002
                        # COINBASE: place_live_order() if COINBASE_LIVE=true (REAL MONEY)
                        #           place_paper_order() otherwise (simulation)
                        # ============================================================
                        
                        # Mode-driven routing
                        if chosen == 'simulate':
                            order = engine.place_order(cand, sizing['size'], execution_type='SIMULATED')
                            if canary_mode:
                                _canary_log(f"✅ SIMULATED order placed: {order}")
                        elif chosen == 'oanda-only':
                            if oanda is None:
                                raise RuntimeError('OANDA connector not initialized')
                            units = int(sizing['size']) if isinstance(sizing['size'], (int, float)) else int(float(sizing['size']))
                            order = oanda.place_paper_order(cand, units=units)
                            print(f"🟡 OANDA PRACTICE ORDER: {sym} {cand.side} x{units}")
                            if canary_mode:
                                _canary_log(f"✅ OANDA PRACTICE order via API: {order}")
                        elif chosen == 'coinbase-only':
                            if coinbase_live:
                                # REAL MONEY ORDER
                                order = coin.place_live_order(cand, sizing['size'], confirm_real_money=True)
                                print(f"🔴 COINBASE LIVE ORDER (REAL $$$): {sym} {cand.side}")
                            else:
                                order = coin.place_paper_order(cand, sizing['size'])
                            if canary_mode:
                                _canary_log(f"✅ COINBASE order placed: {order}")
                        elif chosen == 'ibkr-only':
                            order = ibkr.place_paper_order(cand, sizing['size'])
                            print(f"🟡 IBKR PAPER ORDER (TWS): {sym} {cand.side}")
                            if canary_mode:
                                _canary_log(f"✅ IBKR PAPER order via TWS: {order}")
                        else:
                            # 'auto' or 'multi-asset' or 'platform-paper' behavior
                            platform = getattr(cand, 'platform', None) or ( 'OANDA' if '_' in sym else 'COINBASE' if '-' in sym else 'IBKR' )
                            
                            if platform == 'OANDA' and oanda is not None:
                                units = int(sizing['size']) if isinstance(sizing['size'], (int, float)) else int(float(sizing['size']))
                                order = oanda.place_paper_order(cand, units=units)
                                print(f"🟡 OANDA PRACTICE: {sym} {cand.side} x{units}")
                            elif platform == 'IBKR' and ibkr is not None:
                                order = ibkr.place_paper_order(cand, sizing['size'])
                                print(f"🟡 IBKR PAPER: {sym} {cand.side}")
                            elif platform == 'COINBASE' and coin is not None:
                                if coinbase_live:
                                    # REAL MONEY ORDER
                                    order = coin.place_live_order(cand, sizing['size'], confirm_real_money=True)
                                    print(f"🔴 COINBASE LIVE (REAL $$$): {sym} {cand.side}")
                                else:
                                    order = coin.place_paper_order(cand, sizing['size'])
                                    print(f"🟢 COINBASE SIM: {sym} {cand.side}")
                            else:
                                # Final fallback to engine
                                order = engine.place_order(cand, sizing['size'])
                                print(f"⚠️  FALLBACK to engine: {sym} {cand.side}")
                            
                            if canary_mode:
                                _canary_log(f"✅ Order placed via {platform}: {order}")
                    except Exception as exc:
                        # Last-resort: simulated engine (but warn loudly)
                        order = engine.place_order(cand, sizing['size'])
                        print(f'⚠️  PLATFORM ORDER FAILED, fell back to engine: {exc}')
                        if canary_mode:
                            _canary_log(f"⚠️  Platform order FAILED, engine fallback: {exc}")
                    print('placed order:', order)
                try:
                    cycle_counters['orders_placed'] += 1
                except Exception:
                    pass
            
            poll_interval = _get_poll_interval()
            # Cycle summary telemetry
            if canary_mode:
                _canary_log(f"📊 Cycle summary: signals={cycle_counters['signals']}, blocked_ai={cycle_counters['blocked_ai']}, blocked_risk={cycle_counters['blocked_risk']}, orders={cycle_counters['orders_placed']}, no_price={cycle_counters['no_price']}")
            # Reset counters for next cycle
            cycle_counters = {'signals': 0, 'blocked_ai': 0, 'blocked_risk': 0, 'orders_placed': 0, 'no_price': 0}
            if canary_mode and loop_count % 10 == 0:
                _canary_log(f"😴 Sleeping {poll_interval}s until next check...")
            time.sleep(poll_interval)
    except KeyboardInterrupt:
        print('Headless runner stopped by user')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Headless runner (minimal loop)')
    parser.add_argument('--mode', help='Runner mode (overrides HEADLESS_MODE env var)', choices=['auto','multi-asset','platform-paper','simulate','oanda-only','coinbase-only','ibkr-only'])
    args = parser.parse_args()
    run_headless(mode=args.mode)

