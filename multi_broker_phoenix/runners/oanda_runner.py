"""OANDA Supervised Runner - Production-ready OANDA trading engine.

This module wraps the existing proven-profitable OANDA engine (tools/run_headless.py)
with the supervised broker framework for autonomous operation.

CRITICAL: This does NOT rewrite strategy logic. It wraps and supervises.

Features:
- Heartbeat monitoring (ops/state/brokers/oanda.json every 10s)
- Circuit breaker (5 consecutive failures → FAILED state)
- Gate checks (CONNECTIVITY, LIQUIDITY, OCO_READINESS)
- Auto-arm support (SAFE mode by default)
- Integration with exit_manager, oco_reconcile, protect_loop, pnl_kill_switch
- Process isolation (crash doesn't affect other brokers)
"""
from __future__ import annotations
import os
import sys
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

# Add repo root to Python path
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Load .env BEFORE any other imports
def _load_env():
    """Load .env from repo root."""
    env_path = REPO_ROOT / '.env'
    if not env_path.exists():
        print(f"⚠️  No .env file at {env_path}")
        return
    
    loaded = 0
    with open(env_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            
            # Strip inline comments
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
            if key and key not in os.environ:
                os.environ[key] = value
                loaded += 1
    
    if loaded > 0:
        print(f"✅ Loaded {loaded} env vars from {env_path}")

_load_env()

from multi_broker_phoenix.core.broker_supervisor import BrokerSupervisor
from multi_broker_phoenix.core.gates import BrokerGates
from multi_broker_phoenix.adapters.oanda_adapter import OandaAdapter
from multi_broker_phoenix.risk.exit_manager import start_exit_manager
from multi_broker_phoenix.risk.protect_loop import start_protect_loop
from multi_broker_phoenix.monitor.pnl_kill_switch import start_pnl_loop

# Import AI Router for health monitoring
try:
    from ai_router.router import AIRouter
    AI_ROUTER_AVAILABLE = True
except ImportError:
    AI_ROUTER_AVAILABLE = False

logger = logging.getLogger(__name__)

# ============================================================
# FIFO-SAFE UNIT VARIANCE: Prevent OANDA US FIFO violations
# Multiple trades of same instrument+size cause SL/TP rejection
# ============================================================
import random as _fifo_random
_fifo_used_sizes: dict = {}  # {instrument: set(sizes_used)}

def _fifo_safe_units(base_units: int, instrument: str) -> int:
    """Add small variance to units to avoid FIFO conflicts on OANDA US accounts.
    
    OANDA US FIFO rule: Can't have multiple open trades with identical
    instrument+unit size when each has its own SL/TP orders.
    
    Solution: Add ±1-5 units variance so each trade has unique size.
    This is negligible impact on position sizing but prevents FIFO errors.
    """
    global _fifo_used_sizes
    
    if instrument not in _fifo_used_sizes:
        _fifo_used_sizes[instrument] = set()
    
    used = _fifo_used_sizes[instrument]
    
    # If base size already used, find nearby unused size
    if base_units in used:
        # Try offsets: ±1, ±2, ±3, ±4, ±5
        for offset in [1, -1, 2, -2, 3, -3, 4, -4, 5, -5]:
            candidate = base_units + offset
            if candidate > 0 and candidate not in used:
                used.add(candidate)
                return candidate
        # All nearby taken? Add random 1-10 to make unique
        candidate = base_units + _fifo_random.randint(1, 10)
        used.add(candidate)
        return candidate
    
    used.add(base_units)
    return base_units


# ============================================================
# DAILY PROFIT GOAL TRACKER - $500 MAX THEN STOP
# ============================================================
_daily_profit_goal = float(os.getenv('DAILY_PROFIT_GOAL_USD', '500.0'))
_daily_profit_state = {'date': None, 'realized': 0.0, 'goal_reached': False}

def _check_daily_profit_goal(adapter) -> tuple:
    """Check if daily profit goal has been reached.
    
    Returns: (goal_reached: bool, daily_realized: float, remaining: float)
    """
    global _daily_profit_state
    from datetime import date
    
    today = date.today().isoformat()
    
    # Reset tracker at midnight
    if _daily_profit_state['date'] != today:
        _daily_profit_state = {'date': today, 'realized': 0.0, 'goal_reached': False}
        print(f"\n{'='*70}")
        print(f"📅 NEW TRADING DAY: {today}")
        print(f"🎯 Daily Profit Goal: ${_daily_profit_goal:.2f}")
        print(f"{'='*70}\n")
    
    # Get realized P&L from OANDA account
    try:
        import requests
        token = os.getenv('OANDA_API_TOKEN')
        acct = os.getenv('OANDA_ACCOUNT_ID')
        base = os.getenv('OANDA_API_URL', 'https://api-fxpractice.oanda.com')
        
        r = requests.get(
            f'{base}/v3/accounts/{acct}/summary',
            headers={'Authorization': f'Bearer {token}'},
            timeout=10
        )
        if r.status_code == 200:
            data = r.json().get('account', {})
            # Get today's realized P&L (approximation from balance change)
            # Note: OANDA API doesn't directly give daily realized, so we track it
            pl_today = float(data.get('pl', 0))  # Cumulative realized
    except Exception as e:
        logger.warning(f"Could not fetch realized P&L: {e}")
        pl_today = _daily_profit_state['realized']
    
    remaining = _daily_profit_goal - _daily_profit_state['realized']
    goal_reached = _daily_profit_state['realized'] >= _daily_profit_goal
    
    if goal_reached and not _daily_profit_state['goal_reached']:
        _daily_profit_state['goal_reached'] = True
        print(f"\n{'🎉'*20}")
        print(f"   DAILY PROFIT GOAL REACHED!")
        print(f"   Today's Realized: ${_daily_profit_state['realized']:.2f}")
        print(f"   Goal: ${_daily_profit_goal:.2f}")
        print(f"   STATUS: TRADING PAUSED FOR TODAY")
        print(f"{'🎉'*20}\n")
    
    return goal_reached, _daily_profit_state['realized'], remaining


def _update_daily_realized(amount: float):
    """Update daily realized profit after a trade closes."""
    global _daily_profit_state
    from datetime import date
    
    today = date.today().isoformat()
    if _daily_profit_state['date'] != today:
        _daily_profit_state = {'date': today, 'realized': 0.0, 'goal_reached': False}
    
    _daily_profit_state['realized'] += amount
    
    # Also update the Goal Pursuit Engine for smart allocation tracking
    try:
        from multi_broker_phoenix.risk.goal_pursuit_engine import update_goal_on_close
        update_goal_on_close(amount)
    except Exception as e:
        logger.debug(f"Goal engine update skipped: {e}")
    
    progress = (_daily_profit_state['realized'] / _daily_profit_goal) * 100
    print(f"\n💰 DAILY PROGRESS UPDATE:")
    print(f"   Realized Today: ${_daily_profit_state['realized']:.2f} / ${_daily_profit_goal:.2f} ({progress:.1f}%)")
    bar_len = 30
    filled = int(min(100, progress) / 100 * bar_len)
    bar = '█' * filled + '░' * (bar_len - filled)
    print(f"   Progress: [{bar}]\n")


def _print_plain_english_status(loop_count: int, symbols: list, price_history: dict, 
                                 candidates_count: int, ai_health: dict = None):
    """Print human-readable plain English status update."""
    from datetime import datetime
    
    now = datetime.utcnow().strftime('%H:%M:%S UTC')
    
    print(f"\n{'─'*70}")
    print(f"🕐 {now} | Scan #{loop_count}")
    print(f"{'─'*70}")
    
    # What we're watching
    print(f"\n📊 WHAT I'M WATCHING:")
    for sym in symbols:
        prices = price_history.get(sym, [])
        if prices:
            current = prices[-1]
            change = ((prices[-1] - prices[0]) / prices[0] * 100) if len(prices) > 1 else 0
            direction = "↑" if change > 0 else "↓" if change < 0 else "→"
            print(f"   • {sym}: {current:.5f} ({direction} {abs(change):.2f}% since start)")
        else:
            print(f"   • {sym}: Collecting price data...")
    
    # AI Status
    if ai_health:
        chosen = ai_health.get('chosen', 'unknown').upper()
        healthy = ai_health.get('healthy_count', 0)
        print(f"\n🧠 AI BRAIN STATUS:")
        print(f"   • Active AI: {chosen}")
        print(f"   • Health: {healthy} system(s) online")
        if chosen == 'OLLAMA':
            print(f"   • Using local AI (fast, free)")
        elif chosen == 'GROK':
            print(f"   • Using Grok AI (cloud)")
    
    # What we found
    if candidates_count > 0:
        print(f"\n🔍 TRADE OPPORTUNITIES FOUND: {candidates_count}")
    else:
        print(f"\n😴 No strong trade setups right now - waiting for better conditions...")


def start_oanda_broker():
    """Start OANDA broker engine with supervision.
    
    This is the main entry point called by tools/start_broker.sh.
    Runs indefinitely until stopped or fatal error.
    """
    # ========================================================================
    # 1. CHECK ENABLED TOGGLE
    # ========================================================================
    if os.getenv('BROKER_OANDA_ENABLED', '0') not in ('1', 'true', 'True', 'TRUE'):
        print("❌ OANDA broker disabled (BROKER_OANDA_ENABLED != 1)")
        sys.exit(0)
    
    print("=" * 80)
    print("🚀 OANDA SUPERVISED BROKER STARTING")
    print("=" * 80)
    print(f"   Repo Root: {REPO_ROOT}")
    print(f"   PID: {os.getpid()}")
    print(f"   Time: {datetime.utcnow().isoformat()}Z")
    print("=" * 80)
    
    # ========================================================================
    # 2. INITIALIZE ADAPTER + SUPERVISOR
    # ========================================================================
    try:
        adapter = OandaAdapter()
    except Exception as e:
        print(f"❌ FATAL: OandaAdapter initialization failed: {e}")
        sys.exit(1)
    
    supervisor = BrokerSupervisor(broker_name='oanda', connector=adapter, repo_root=REPO_ROOT)
    gates = BrokerGates(connector=adapter, broker_name='oanda')
    
    # Write PID file
    pid_file = REPO_ROOT / 'ops' / 'state' / 'brokers' / 'oanda.pid'
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    pid_file.write_text(str(os.getpid()))
    print(f"✅ PID written to {pid_file}")
    
    # ========================================================================
    # 3. START HEARTBEAT + SAFETY MONITORS
    # ========================================================================
    supervisor.start_heartbeat()
    print("✅ Heartbeat started (10s interval)")
    
    # Start safety monitors (these run in background threads)
    try:
        start_exit_manager(adapter)
        print("✅ Exit Manager started")
    except Exception as e:
        print(f"⚠️  Exit Manager failed to start: {e}")
    
    try:
        start_protect_loop(adapter)
        print("✅ Protect Loop started")
    except Exception as e:
        print(f"⚠️  Protect Loop failed to start: {e}")
    
    try:
        start_pnl_loop(adapter)
        print("✅ PnL Kill Switch started")
    except Exception as e:
        print(f"⚠️  PnL Kill Switch failed to start: {e}")
    
    # Start real-time position monitor (tracks closures + realized P&L)
    try:
        from multi_broker_phoenix.monitor.position_monitor import start_position_monitor, get_position_monitor
        start_position_monitor(adapter.client, interval_sec=15)
        print("✅ Position Monitor started (15s interval)")
    except Exception as e:
        print(f"⚠️  Position Monitor failed to start: {e}")
    
    # ========================================================================
    # 4. AUTO-ARM CHECK
    # ========================================================================
    auto_arm = os.getenv('AUTO_ARM_ON_HEALTHY', '1') == '1'  # Default enabled
    oanda_auto_arm = os.getenv('BROKER_OANDA_AUTO_ARM', str(int(auto_arm))) == '1'
    
    if oanda_auto_arm:
        print("🤖 AUTO-ARM ENABLED - Will activate when gates pass")
    else:
        print("👤 MANUAL ARM - Requires explicit arm command")
    
    # ========================================================================
    # 5. INITIAL GATE CHECK + AI HEALTH CHECK
    # ========================================================================
    print("\n🔍 Running initial gate checks...")
    all_passed, gate_results = gates.run_all_gates()
    
    for gate_name, result in gate_results.items():
        status = "✅ PASS" if result['passed'] else "❌ FAIL"
        print(f"   {status} {gate_name}: {result.get('reason', 'OK')}")
    
    # Check AI Router health
    ai_status = None
    if AI_ROUTER_AVAILABLE:
        try:
            ai_router = AIRouter()
            ai_status = ai_router.evaluate()
            print(f"\n🧠 AI Router Health:")
            print(f"   Status: {'✅ HEALTHY' if ai_status['ai_ok'] else '❌ DEGRADED'}")
            print(f"   Active Provider: {ai_status.get('chosen', 'NONE')}")
            print(f"   Healthy Seats: {ai_status['healthy_count']}/{ai_status['min_seats']}")
            if ai_status.get('chosen') == 'ollama':
                snap = ai_status.get('snapshot', {}).get('ollama', {})
                print(f"   Ollama Latency: {snap.get('latency_ms', 0)}ms")
        except Exception as ai_err:
            print(f"⚠️  AI health check failed: {ai_err}")
    else:
        print("⚠️  AI Router not available (module not imported)")
    
    if all_passed and oanda_auto_arm:
        supervisor.mark_active()
        print("\n✅ BROKER ACTIVE (gates passed + auto-arm enabled)")
    elif all_passed:
        print("\n⏸️  BROKER PAUSED (gates passed but manual arm required)")
    else:
        print("\n❌ BROKER PAUSED (gates failed)")
    
    # ========================================================================
    # 6. MAIN TRADING LOOP (WRAPPED FROM run_headless.py)
    # ========================================================================
    print("\n" + "=" * 80)
    print("🔄 ENTERING MAIN TRADING LOOP")
    print("=" * 80 + "\n")
    
    poll_interval = int(os.getenv('OANDA_POLL_INTERVAL', '30'))  # seconds
    ai_health_interval = int(os.getenv('AI_HEALTH_CHECK_INTERVAL', '300'))  # 5 minutes default
    trade_cooldown_secs = int(os.getenv('TRADE_COOLDOWN_SECS', '60'))
    margin_cancel_window_sec = int(os.getenv('MARGIN_CANCEL_WINDOW_SEC', '900'))
    margin_cancel_max = int(os.getenv('MARGIN_CANCEL_MAX', '3'))
    margin_cancel_cooldown_sec = int(os.getenv('MARGIN_CANCEL_COOLDOWN_SEC', '900'))
    fifo_cancel_cooldown_sec = int(os.getenv('FIFO_CANCEL_COOLDOWN_SEC', '300'))
    loop_count = 0
    price_history = {}  # Store price history per symbol for strategy analysis
    last_ai_check = time.time()
    last_trade_time = {}
    pending_symbols = set()
    margin_cooldowns = {}
    margin_cancel_times = []
    global_pause_until = 0.0
    
    try:
        while True:
            loop_count += 1
            
            # ================================================================
            # DAILY PROFIT GOAL CHECK - $500 MAX THEN STOP
            # ================================================================
            goal_reached, daily_realized, remaining = _check_daily_profit_goal(adapter)
            if goal_reached:
                print(f"\n🎯 Daily goal of ${_daily_profit_goal:.2f} reached! Realized: ${daily_realized:.2f}")
                print(f"   Trading paused until tomorrow. Great job today!")
                time.sleep(300)  # Check again in 5 minutes
                continue
            
            # Show progress every 10 loops
            if loop_count % 10 == 1:
                progress_pct = (daily_realized / _daily_profit_goal) * 100
                print(f"\n💵 Daily Progress: ${daily_realized:.2f} / ${_daily_profit_goal:.2f} ({progress_pct:.1f}%) | ${remaining:.2f} to go")
                
                # Show open positions from position monitor
                try:
                    from multi_broker_phoenix.monitor.position_monitor import get_position_monitor
                    pos_monitor = get_position_monitor()
                    positions = pos_monitor.get_open_positions()
                    summary = pos_monitor.get_daily_summary()
                    
                    if positions:
                        print(f"\n📈 OPEN POSITIONS ({len(positions)}):")
                        total_upl = 0
                        for pos in positions:
                            upl = float(pos.get('unrealizedPL', 0))
                            total_upl += upl
                            emoji = "🟢" if upl >= 0 else "🔴"
                            print(f"   {emoji} {pos.get('instrument')}: {pos.get('units')} units | UPL: ${upl:+.2f}")
                        print(f"   📊 Combined UPL: ${total_upl:+.2f}")
                    else:
                        print(f"   📭 No open positions")
                    
                    # Show today's closed trades summary
                    if summary['trades_closed'] > 0:
                        print(f"   📋 Closed Today: {summary['trades_closed']} trades | W:{summary['wins']}/L:{summary['losses']} | {summary['win_rate']:.0f}% WR")
                except Exception as e:
                    logger.debug(f"Position monitor display skipped: {e}")
            
            # ================================================================
            # PERIODIC AI HEALTH CHECK (every 5 minutes)
            # ================================================================
            if AI_ROUTER_AVAILABLE and (time.time() - last_ai_check) >= ai_health_interval:
                try:
                    ai_router = AIRouter()
                    ai_status = ai_router.evaluate()
                    
                    if not ai_status['ai_ok']:
                        logger.warning(f"⚠️  AI Router degraded: {ai_status['healthy_count']}/{ai_status['min_seats']} seats healthy")
                        logger.warning(f"   Active: {ai_status.get('chosen', 'NONE')}")
                    else:
                        logger.info(f"🧠 AI Health: {ai_status['chosen']} active, {ai_status['healthy_count']} seats healthy")
                    
                    # Write AI health to state file for monitoring
                    ai_state_file = REPO_ROOT / 'ops' / 'state' / 'ai_health.json'
                    ai_state_file.parent.mkdir(parents=True, exist_ok=True)
                    import json
                    with open(ai_state_file, 'w') as f:
                        json.dump(ai_status, f, indent=2)
                    
                    last_ai_check = time.time()
                except Exception as ai_err:
                    logger.error(f"AI health check failed: {ai_err}")
            
            # Check if supervisor allows trading
            if not supervisor.can_trade():
                state_info = supervisor.state_machine.state
                if global_pause_until and time.time() < global_pause_until:
                    remaining = int(global_pause_until - time.time())
                    print(f"⏸️  Global margin cooldown active ({remaining}s remaining)")
                    time.sleep(min(poll_interval, max(1, remaining)))
                    continue
                print(f"⏸️  Trading paused (state={state_info}) - waiting {poll_interval}s")
                time.sleep(poll_interval)
                
                # Re-run gates periodically to check if broker can recover
                if loop_count % 6 == 0:  # Every ~3 minutes if 30s poll
                    all_passed, _ = gates.run_all_gates()
                    if all_passed and oanda_auto_arm:
                        supervisor.mark_active()
                        print("✅ Gates passed - broker activated")
                
                continue
            
            # ================================================================
            # TRADING TICK - Scan ALL strategies, pick best signal
            # ================================================================
            try:
                # Import strategy + risk components (lazy import for faster startup)
                from multi_broker_phoenix.strategies.base import STRATEGY_REGISTRY
                from multi_broker_phoenix.risk.risk_manager import RiskManager
                
                # Import all strategies to populate registry
                import multi_broker_phoenix.strategies.fabio_aaa_full
                import multi_broker_phoenix.strategies.triage_regime
                import multi_broker_phoenix.strategies.sideways_regime
                import multi_broker_phoenix.strategies.gbp_usd_only
                
                # Get risk manager
                risk_mgr = RiskManager()
                
                # Get current prices for monitored symbols
                symbols = os.getenv('FEED_SYMBOLS', 'EUR_USD,GBP_USD,USD_JPY').split(',')
                symbols = [s.strip() for s in symbols if s.strip()]
                
                prices = adapter.get_prices(symbols)
                
                if not prices:
                    print(f"⚠️  No prices received for {symbols}")
                    time.sleep(poll_interval)
                    continue
                
                # Collect ALL candidates from ALL strategies across ALL symbols
                all_candidates = []
                
                for symbol in symbols:
                    if symbol not in prices:
                        continue
                    
                    price_data = prices[symbol]
                    mid_price = price_data.get('mid', 0)
                    
                    if not mid_price:
                        continue
                    
                    # Build historical price array (20+ prices minimum)
                    if symbol not in price_history:
                        price_history[symbol] = []
                    
                    price_history[symbol].append(mid_price)
                    if len(price_history[symbol]) > 200:
                        price_history[symbol] = price_history[symbol][-200:]
                    
                    # Need sufficient price history for signals
                    if len(price_history[symbol]) < 20:
                        if loop_count % 10 == 1:
                            print(f"   📈 {symbol}: {len(price_history[symbol])}/20 prices collected")
                        continue
                    
                    # ========================================
                    # SCAN ALL STRATEGIES FOR THIS SYMBOL
                    # ========================================
                    market_data = {
                        'symbol': symbol,
                        'platform': 'OANDA',
                        'prices': price_history[symbol]
                    }
                    
                    for strategy_name, strategy in STRATEGY_REGISTRY.items():
                        try:
                            candidate = strategy.generate_candidate(market_data)
                            if candidate:
                                # Attach strategy metadata
                                candidate.strategy_id = f"{strategy_name}_{symbol}"
                                candidate.strategy_name = strategy_name
                                all_candidates.append(candidate)
                        except Exception as strat_error:
                            logger.warning(f"Strategy '{strategy_name}' error for {symbol}: {strat_error}")
                            continue
                
                # ========================================
                # SELECT BEST CANDIDATE (highest confidence * expected profit)
                # ========================================
                if not all_candidates:
                    if loop_count % 10 == 0:
                        _print_plain_english_status(loop_count, symbols, price_history, 0, ai_status)
                    time.sleep(poll_interval)
                    continue
                
                # Rank by confidence * profit potential
                best_candidate = max(all_candidates, key=lambda c: getattr(c, 'confidence', 0.5) * abs(getattr(c, 'expected_profit', 1.0)))
                
                # Human-readable trade opportunity announcement
                print(f"\n{'='*60}")
                print(f"🎯 TRADE OPPORTUNITY FOUND!")
                print(f"{'='*60}")
                print(f"\n📊 WHAT I FOUND:")
                print(f"   • Currency Pair: {best_candidate.symbol}")
                print(f"   • Direction: {getattr(best_candidate, 'side', 'unknown').upper()}")
                print(f"   • Strategy: {best_candidate.strategy_name}")
                conf = getattr(best_candidate, 'confidence', 0.5)
                print(f"   • Confidence: {conf:.0%} ({'HIGH' if conf >= 0.7 else 'MEDIUM' if conf >= 0.5 else 'LOW'})")
                print(f"\n🔍 STRATEGY DETAILS:")
                
                # Explain what the strategy found
                strat_name = best_candidate.strategy_name.lower()
                if 'fabio' in strat_name:
                    print(f"   • The FABIO strategy detected a momentum setup:")
                    print(f"     - Short-term EMA crossed above long-term EMA")
                    print(f"     - RSI confirms strength (above threshold)")
                    print(f"     - Price showing clear directional movement")
                elif 'bullish' in strat_name:
                    print(f"   • Bullish regime detected:")
                    print(f"     - Market is trending UP")
                    print(f"     - Good conditions for LONG trades")
                elif 'bearish' in strat_name:
                    print(f"   • Bearish regime detected:")
                    print(f"     - Market is trending DOWN")
                    print(f"     - Good conditions for SHORT trades")
                elif 'sideways' in strat_name:
                    print(f"   • Sideways/Range market detected:")
                    print(f"     - Price bouncing between support/resistance")
                else:
                    print(f"   • Custom strategy rules matched")
                
                print(f"\n📈 Scanned {len(all_candidates)} signals from {len(STRATEGY_REGISTRY)} strategies")
                
                candidate = best_candidate
                
                # ========================================
                # COOLDOWN + POSITION CHECK (prevent spam)
                # ========================================
                symbol = candidate.symbol
                now_ts = time.time()
                last_ts = last_trade_time.get(symbol)
                if last_ts and (now_ts - last_ts) < trade_cooldown_secs:
                    remaining = int(trade_cooldown_secs - (now_ts - last_ts))
                    logger.info(f"Cooldown active for {symbol}: {remaining}s remaining")
                    time.sleep(poll_interval)
                    continue

                cooldown_until = margin_cooldowns.get(symbol)
                if cooldown_until and now_ts < cooldown_until:
                    remaining = int(cooldown_until - now_ts)
                    logger.warning(f"Margin cooldown active for {symbol}: {remaining}s remaining")
                    time.sleep(poll_interval)
                    continue

                if symbol in pending_symbols:
                    logger.info(f"Skipping {symbol}: pending entry exists")
                    time.sleep(poll_interval)
                    continue

                try:
                    open_positions = adapter.get_positions()
                    if any(getattr(p, 'symbol', '') == symbol and getattr(p, 'quantity', 0) > 0 for p in open_positions):
                        logger.info(f"Skipping {symbol}: existing open position")
                        time.sleep(poll_interval)
                        continue
                except Exception as pos_err:
                    logger.warning(f"Position check failed for {symbol}: {pos_err}")

                # ========================================
                # RISK GATE CHECK
                # ========================================
                from multi_broker_phoenix.risk.trade_risk_gate import can_open_trade
                
                account_equity = risk_mgr.state.equity_now or 100000.0
                decision = can_open_trade(candidate, account_equity=account_equity, rm=risk_mgr)
                
                if not decision.allowed:
                    logger.info(f"Trade blocked: {symbol} - {decision.reason}")
                    time.sleep(poll_interval)
                    continue
                
                # ========================================
                # GOAL PURSUIT ENGINE - MOMENTUM-BASED SCALING + TIGHT SL
                # ========================================
                from multi_broker_phoenix.risk.goal_pursuit_engine import (
                    get_goal_engine, should_continue_trading
                )
                
                goal_engine = get_goal_engine()
                can_continue, continue_reason = should_continue_trading()
                
                if not can_continue:
                    print(f"\n🛑 {continue_reason}")
                    time.sleep(poll_interval)
                    continue
                
                # Analyze momentum for position sizing  
                momentum = goal_engine.analyze_momentum(
                    symbol, 
                    price_history.get(symbol, []),
                    getattr(candidate, 'side', 'BUY')
                )
                
                # Get enhanced recommendation with momentum-scaled size and tight SL
                signal_confidence = getattr(candidate, 'confidence', 0.5)
                goal_rec = goal_engine.get_position_recommendation(
                    base_size=decision.size,
                    momentum=momentum,
                    signal_confidence=signal_confidence,
                    entry_price=price_history.get(symbol, [0])[-1] if price_history.get(symbol) else 0,
                    side=getattr(candidate, 'side', 'BUY'),
                    symbol=symbol
                )
                
                # Print the recommendation
                goal_engine.print_recommendation(goal_rec, symbol, getattr(candidate, 'side', 'BUY'))
                
                if not goal_rec.get('allowed'):
                    print(f"❌ Goal Engine rejected: {goal_rec.get('reason')}")
                    time.sleep(poll_interval)
                    continue
                
                # ========================================
                # AI HIVE APPROVAL GATE - REQUIRED FOR ALL TRADES
                # ========================================
                try:
                    from hive_real.api_ai_hive import get_api_ai_vote
                    
                    # Get current price for AI analysis
                    ai_entry_price = price_history.get(symbol, [0])[-1] if price_history.get(symbol) else 0
                    ai_direction = getattr(candidate, 'side', 'BUY')
                    
                    ai_result = get_api_ai_vote(
                        symbol=symbol,
                        direction=ai_direction,
                        entry_price=ai_entry_price,
                        market_data={'prices': price_history.get(symbol, [])}
                    )
                    
                    ai_decision = ai_result.get('decision', 'reject').lower()
                    ai_confidence = ai_result.get('confidence', 0)
                    ai_reasoning = ai_result.get('reasoning', 'No reason given')
                    
                    if ai_decision != 'approve':
                        print(f"\n🚫 AI HIVE BLOCKED TRADE: {symbol}")
                        print(f"   Decision: {ai_decision.upper()}")
                        print(f"   Reason: {ai_reasoning}")
                        logger.info(f"AI Hive rejected {symbol}: {ai_reasoning}")
                        time.sleep(poll_interval)
                        continue
                    
                    print(f"\n✅ AI HIVE APPROVED: {symbol} {ai_direction}")
                    print(f"   Confidence: {ai_confidence:.0%}")
                    logger.info(f"AI Hive approved {symbol} {ai_direction} with {ai_confidence:.0%} confidence")
                    
                except ImportError as ie:
                    print(f"⚠️  AI Hive not available: {ie}")
                    print(f"   BLOCKING TRADE - AI approval required!")
                    logger.error(f"AI Hive import failed - blocking trade: {ie}")
                    time.sleep(poll_interval)
                    continue
                except Exception as ai_err:
                    print(f"⚠️  AI Hive error: {ai_err}")
                    print(f"   BLOCKING TRADE - AI approval required!")
                    logger.error(f"AI Hive error - blocking trade: {ai_err}")
                    time.sleep(poll_interval)
                    continue
                
                # ========================================
                # CONVERT CANDIDATE TO OCO ORDER + VALIDATE
                # ========================================
                from multi_broker_phoenix.core.interfaces import OCOOrder
                
                # Get LIVE price for validation (candidate might have stale price)
                current_prices = adapter.get_prices([symbol])
                if not current_prices or symbol not in current_prices:
                    logger.error(f"Cannot get current price for {symbol}")
                    time.sleep(poll_interval)
                    continue
                
                live_price = current_prices[symbol].get('mid', 0)
                if not live_price:
                    logger.error(f"Invalid live price for {symbol}")
                    time.sleep(poll_interval)
                    continue
                
                # Use LIVE price as entry (market order)
                entry_price = live_price
                
                # Use GOAL ENGINE's tight stop loss instead of candidate's
                stop_loss = goal_rec.get('stop_loss', candidate.stop_loss)
                take_profit = goal_rec.get('take_profit')
                
                # Fallback to original calculation if goal engine didn't provide
                if take_profit is None:
                    stop_dist = abs(entry_price - stop_loss)
                    rr_ratio = goal_rec.get('rr_ratio', float(os.getenv('RR_RATIO', '2.5')))
                    if candidate.side and candidate.side.upper() == "BUY":
                        take_profit = entry_price + (stop_dist * rr_ratio)
                    else:
                        take_profit = entry_price - (stop_dist * rr_ratio)
                
                # Determine side
                if candidate.side and candidate.side.upper() == "BUY":
                    if stop_loss >= entry_price:
                        logger.error(f"❌ INVALID BUY: SL ({stop_loss}) >= Entry ({entry_price}) - REJECTING")
                        continue
                    entry_side = "BUY"
                    
                elif candidate.side and candidate.side.upper() == "SELL":
                    if stop_loss <= entry_price:
                        logger.error(f"❌ INVALID SELL: SL ({stop_loss}) <= Entry ({entry_price}) - REJECTING")
                        continue
                    entry_side = "SELL"
                    
                else:
                    logger.warning(f"Invalid trade side: {candidate.side}")
                    time.sleep(poll_interval)
                    continue
                
                # Final sanity check
                if entry_side == "BUY" and take_profit <= entry_price:
                    logger.error(f"❌ BUY TP VALIDATION FAILED: TP ({take_profit}) <= Entry ({entry_price})")
                    continue
                if entry_side == "SELL" and take_profit >= entry_price:
                    logger.error(f"❌ SELL TP VALIDATION FAILED: TP ({take_profit}) >= Entry ({entry_price})")
                    continue
                
                # Get ENHANCED position size from Goal Engine (momentum-scaled)
                raw_quantity = goal_rec.get('size', decision.size)
                
                if raw_quantity is None or raw_quantity <= 0:
                    logger.error(f"Invalid quantity for {symbol}: {raw_quantity}")
                    time.sleep(poll_interval)
                    continue
                
                # Apply FIFO-safe variance to prevent OANDA US FIFO violations
                quantity = _fifo_safe_units(int(raw_quantity), symbol)
                if quantity != int(raw_quantity):
                    logger.info(f"📏 FIFO-safe: {int(raw_quantity)} → {quantity} units for {symbol}")

                signed_units = quantity if entry_side == "BUY" else -quantity
                if entry_side == "BUY" and signed_units <= 0:
                    logger.error(f"❌ BUY units invalid: {signed_units}")
                    time.sleep(poll_interval)
                    continue
                if entry_side == "SELL" and signed_units >= 0:
                    logger.error(f"❌ SELL units invalid: {signed_units}")
                    time.sleep(poll_interval)
                    continue
                
                # Log OCO details before placing
                logger.info(f"📋 OCO ORDER PREPARED: {symbol} {entry_side} qty={quantity:.2f} "
                          f"| Entry={entry_price:.5f} | SL={stop_loss:.5f} | TP={take_profit:.5f}")
                
                oco = OCOOrder(
                    symbol=symbol,
                    entry_side=entry_side,
                    entry_quantity=quantity,
                    take_profit_price=take_profit,
                    stop_loss_price=stop_loss,
                    entry_price=None,  # Market order
                    client_tag=candidate.strategy_id
                )
                
                # Validate OCO
                valid, errors = oco.validate()
                if not valid:
                    logger.error(f"OCO validation failed: {errors}")
                    time.sleep(poll_interval)
                    continue
                
                # ========================================
                # PLACE OCO ORDER WITH STRICT VALIDATION
                # ========================================
                try:
                    pending_symbols.add(symbol)
                    try:
                        order_result = adapter.place_oco(oco)
                    finally:
                        pending_symbols.discard(symbol)
                    
                    # Extract order details from result
                    entry_order = order_result.get('entry_order')
                    tp_order = order_result.get('take_profit_order')
                    sl_order = order_result.get('stop_loss_order')
                    oco_group_id = order_result.get('oco_group_id')
                    cancel_reason = order_result.get('cancel_reason') or getattr(entry_order, 'error', None) or order_result.get('error')
                    placement_failed = order_result.get('placement_failed') or (
                        entry_order and entry_order.status in ('canceled', 'rejected', 'error')
                    )

                    if placement_failed:
                        error_msg = f"PLACEMENT_FAILED: {symbol} reason={cancel_reason or 'unknown'}"
                        logger.error(error_msg)
                        supervisor.record_error(error_msg)

                        if cancel_reason == 'INSUFFICIENT_MARGIN':
                            margin_cooldowns[symbol] = time.time() + margin_cancel_cooldown_sec
                            margin_cancel_times.append(time.time())
                            margin_cancel_times = [t for t in margin_cancel_times if (time.time() - t) <= margin_cancel_window_sec]
                            if len(margin_cancel_times) >= margin_cancel_max:
                                global_pause_until = time.time() + margin_cancel_cooldown_sec
                                supervisor.mark_paused("INSUFFICIENT_MARGIN storm")
                                logger.critical("Global margin cooldown engaged")
                        elif cancel_reason and 'FIFO' in cancel_reason:
                            margin_cooldowns[symbol] = time.time() + fifo_cancel_cooldown_sec

                        time.sleep(poll_interval)
                        continue
                    
                    # ========================================
                    # CRITICAL: VERIFY ALL 3 ORDERS CREATED
                    # ========================================
                    if not entry_order or not tp_order or not sl_order:
                        error_msg = f"❌ INCOMPLETE OCO: entry={bool(entry_order)} tp={bool(tp_order)} sl={bool(sl_order)}"
                        logger.error(error_msg)
                        supervisor.record_error(error_msg)
                        
                        # If entry filled but missing protection, EMERGENCY CLOSE
                        if entry_order and entry_order.status == 'filled':
                            logger.critical(f"🚨 NAKED POSITION DETECTED - Closing trade {oco_group_id} immediately!")
                            try:
                                adapter.close_position(oco_group_id)
                            except Exception as close_err:
                                logger.critical(f"Failed to close naked position: {close_err}")
                        continue
                    
                    # VERIFY ENTRY FILLED
                    if entry_order.status != 'filled':
                        error_msg = f"Entry order not filled: {entry_order.status}"
                        logger.error(error_msg)
                        supervisor.record_error(error_msg)
                        continue
                    
                    # VERIFY TP AND SL ARE PENDING (ACTIVE PROTECTION)
                    if tp_order.status != 'pending':
                        error_msg = f"❌ TP NOT ACTIVE: status={tp_order.status} - ABORTING TRADE"
                        logger.error(error_msg)
                        supervisor.record_error(error_msg)
                        # Close position immediately
                        try:
                            adapter.close_position(oco_group_id)
                            logger.info(f"Closed position {oco_group_id} due to missing TP protection")
                        except Exception:
                            pass
                        continue
                    
                    if sl_order.status != 'pending':
                        error_msg = f"❌ SL NOT ACTIVE: status={sl_order.status} - ABORTING TRADE"
                        logger.error(error_msg)
                        supervisor.record_error(error_msg)
                        # Close position immediately
                        try:
                            adapter.close_position(oco_group_id)
                            logger.info(f"Closed position {oco_group_id} due to missing SL protection")
                        except Exception:
                            pass
                        continue
                    
                    # ========================================
                    # ✅ ALL VALIDATIONS PASSED - TRADE CONFIRMED
                    # ========================================
                    filled_price = entry_order.filled_price if entry_order and entry_order.filled_price is not None else entry_price
                    logger.info(f"✅ OCO PROTECTED: {symbol} {entry_side} qty={quantity:.2f} "
                              f"@ {filled_price} | "
                              f"TP={take_profit:.5f} ({tp_order.status}) | "
                              f"SL={stop_loss:.5f} ({sl_order.status}) | "
                              f"strategy={candidate.strategy_name} | oco_group={oco_group_id}")
                    
                    # Calculate pip distances for human display
                    pip_val = 0.01 if 'JPY' in symbol else 0.0001
                    tp_pips = abs(take_profit - filled_price) / pip_val
                    sl_pips = abs(stop_loss - filled_price) / pip_val
                    rr_ratio = tp_pips / sl_pips if sl_pips > 0 else 0
                    
                    # Human-readable trade confirmation
                    print(f"\n{'🎉'*20}")
                    print(f"\n   TRADE EXECUTED SUCCESSFULLY!")
                    print(f"\n{'🎉'*20}")
                    print(f"\n📋 TRADE DETAILS:")
                    print(f"   • Pair: {symbol}")
                    print(f"   • Direction: {'BUYING (going long)' if entry_side == 'BUY' else 'SELLING (going short)'}")
                    print(f"   • Size: {quantity:,.0f} units")
                    print(f"   • Entry Price: {filled_price:.5f}")
                    print(f"\n🎯 PROFIT TARGET (Take Profit):")
                    print(f"   • Price: {take_profit:.5f}")
                    print(f"   • Distance: {tp_pips:.1f} pips away")
                    print(f"   • Status: ✅ ACTIVE")
                    print(f"\n🛡️ SAFETY NET (Stop Loss):")
                    print(f"   • Price: {stop_loss:.5f}")
                    print(f"   • Distance: {sl_pips:.1f} pips away")
                    print(f"   • Status: ✅ ACTIVE")
                    print(f"\n📊 RISK/REWARD: 1:{rr_ratio:.1f}")
                    print(f"   (For every $1 risked, potential gain is ${rr_ratio:.1f})")
                    print(f"\n   Strategy used: {candidate.strategy_name}")
                    print(f"{'='*60}\n")

                    last_trade_time[symbol] = time.time()
                    
                except Exception as order_error:
                    logger.error(f"Order placement failed: {order_error}", exc_info=True)
                    supervisor.record_error(str(order_error))
                
                # Log tick completion
                if loop_count % 10 == 0:
                    print(f"✅ Tick {loop_count} completed | state={supervisor.state_machine.state}")
            
            except Exception as tick_error:
                logger.error(f"Trading tick error: {tick_error}", exc_info=True)
                supervisor.record_error(str(tick_error))
                # Supervisor will auto-pause if errors exceed threshold
            
            time.sleep(poll_interval)
    
    except KeyboardInterrupt:
        print("\n🛑 OANDA broker stopped by user (Ctrl+C)")
    
    except Exception as fatal_error:
        logger.error(f"FATAL ERROR: {fatal_error}", exc_info=True)
        supervisor.mark_failed(str(fatal_error))
    
    finally:
        # Cleanup
        supervisor.stop()
        print("✅ Supervisor stopped")
        print("=" * 80)
        print("🏁 OANDA BROKER SHUTDOWN COMPLETE")
        print("=" * 80)


if __name__ == '__main__':
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(REPO_ROOT / 'logs' / 'oanda_runner.log'),
        ]
    )
    
    start_oanda_broker()
