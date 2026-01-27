#!/usr/bin/env python3
"""
🎯 $400/DAY HUNTER - Aggressive Trading Mode

Launches real trading engine configured to hit $400/day target.

REQUIREMENTS:
- Starting capital: $5,000+
- Win rate: 38%+
- Trade frequency: 5-8 quality trades/day
- Trading hours: 12+ hours/day

FEATURES ENABLED:
- HIVE threshold lowered to 30% (more trades)
- Risk per trade: 3.5% ($175 on $5k)
- Hedging, sniping, pyramiding all maxed
- Real-time target tracking
- Auto-halt at -$200 daily loss
"""

import sys
import os
import time
from datetime import datetime, timedelta

# Add project to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from multi_broker_phoenix.config.daily_target_mode import (
    DailyTargetConfig, DailyTargetTracker, get_config_for_capital,
    calculate_daily_requirements
)
from multi_broker_phoenix.strategies.base import get_strategy, list_strategies


def print_banner():
    """Show startup banner"""
    print("=" * 70)
    print("🎯 $400/DAY HUNTER - REAL MONEY TRADING MODE")
    print("=" * 70)
    print()
    

def validate_setup(capital: float):
    """Validate system is ready for $400/day target"""
    print("🔍 VALIDATING SETUP...")
    
    issues = []
    
    # Check capital
    if capital < 5000:
        issues.append(f"⚠️  Capital too low: ${capital:.0f} (need $5k minimum)")
    
    # Check strategies loaded
    strategies = list_strategies()
    if not strategies:
        issues.append("⚠️  No strategies loaded")
    else:
        print(f"✅ {len(strategies)} strategies loaded: {', '.join(strategies.keys())}")
    
    # Check HIVE components
    try:
        from multi_broker_phoenix.engines.hive_consensus import HiveConsensusEngine
        print("✅ HIVE consensus engine available")
    except ImportError as e:
        issues.append(f"⚠️  HIVE engine not found: {e}")
    
    # Check smart aggression
    try:
        from multi_broker_phoenix.config.smart_aggression import DEFAULT_SMART_AGGRESSION
        print("✅ Smart aggression config loaded")
    except ImportError as e:
        issues.append(f"⚠️  Smart aggression not found: {e}")
    
    if issues:
        print("\n❌ VALIDATION FAILED:")
        for issue in issues:
            print(f"   {issue}")
        return False
    
    print("✅ All systems ready\n")
    return True


def show_daily_plan(capital: float):
    """Show the daily trading plan"""
    reqs = calculate_daily_requirements(capital, 400)
    
    print("📋 DAILY TRADING PLAN")
    print("-" * 70)
    print(f"   Starting Capital: ${capital:,.0f}")
    print(f"   Daily Target: ${reqs['daily_target']:.0f}")
    print(f"   Risk/Trade: ${reqs['risk_per_trade']:.2f} ({reqs['risk_per_trade']/capital*100:.1f}%)")
    print(f"   Win Amount: ${reqs['win_amount']:.2f}")
    print(f"   Loss Amount: ${reqs['loss_amount']:.2f}")
    print(f"   Expected Value/Trade: ${reqs['ev_per_trade']:.2f}")
    print()
    print(f"   🎯 Trades Needed: {reqs['trades_needed']} quality trades")
    print(f"      ├─ Expected wins: {reqs['expected_wins']:.1f}")
    print(f"      ├─ Expected losses: {reqs['expected_losses']:.1f}")
    print(f"      └─ Trade every ~{60*12/reqs['trades_needed']:.0f} minutes")
    print()
    print(f"   💰 Example Profitable Day:")
    wins = int(reqs['expected_wins']) + 1
    losses = int(reqs['expected_losses'])
    profit = wins * reqs['win_amount'] - losses * reqs['loss_amount']
    print(f"      {wins} wins × ${reqs['win_amount']:.0f} - {losses} losses × ${reqs['loss_amount']:.0f} = ${profit:.0f}")
    print("-" * 70)
    print()


def run_simulation_day(capital: float, num_trades: int = 8):
    """Simulate one trading day"""
    import random
    
    config = get_config_for_capital(capital)
    tracker = DailyTargetTracker(config)
    tracker.reset_day(capital)
    
    print(f"🎮 SIMULATING TRADING DAY ({num_trades} trades)")
    print("=" * 70)
    
    trade_num = 0
    while trade_num < num_trades and not tracker.should_halt_trading():
        trade_num += 1
        
        # Simulate trade with 38% win rate
        is_win = random.random() < 0.38
        risk = capital * config.risk_per_trade_pct / 100
        
        if is_win:
            pnl = risk * 3.0  # 3:1 R:R
            result = "WIN"
            symbol = "✅"
        else:
            pnl = -risk
            result = "LOSS"
            symbol = "❌"
        
        tracker.record_trade(pnl)
        
        print(f"\nTrade #{trade_num}: {symbol} {result}")
        print(f"   P&L: ${pnl:+.2f}")
        print(f"   Daily P&L: ${tracker.daily_pnl:+.2f}")
        print(f"   Progress: {tracker.daily_pnl/config.target_daily_profit*100:.1f}% of target")
        
        # Show recommendation every few trades
        if trade_num % 3 == 0:
            rec = tracker.get_recommendation()
            print(f"   📊 {rec}")
        
        # Simulate time between trades (2-3 hours average)
        time.sleep(0.5)  # Speed up simulation
    
    # Final status
    print("\n" + "=" * 70)
    print("📊 END OF DAY SUMMARY")
    print("=" * 70)
    status = tracker.get_status()
    print(f"   Daily P&L: ${tracker.daily_pnl:+.2f}")
    print(f"   Target: ${config.target_daily_profit:.0f}")
    print(f"   Achievement: {status['pct_of_target']:.1f}%")
    print(f"   Trades: {status['trades']} ({status['wins']}W-{status['losses']}L)")
    print(f"   Win Rate: {status['win_rate']:.1f}%")
    
    if tracker.daily_pnl >= config.target_daily_profit:
        print("\n   🎉 TARGET HIT! Excellent work.")
    elif tracker.daily_pnl >= config.min_acceptable_profit:
        print("\n   ✅ Acceptable profit. Keep grinding.")
    elif tracker.daily_pnl > 0:
        print("\n   📈 Small profit. Need more trades tomorrow.")
    else:
        print("\n   ❌ Red day. Review trades and adjust.")
    
    print("=" * 70)
    

def main():
    """Main entry point"""
    print_banner()
    
    # Get starting capital
    capital = 5000  # Default
    if len(sys.argv) > 1:
        try:
            capital = float(sys.argv[1])
        except ValueError:
            print(f"⚠️  Invalid capital: {sys.argv[1]}")
            sys.exit(1)
    
    # Validate setup
    if not validate_setup(capital):
        print("\n❌ Setup validation failed. Fix issues and try again.")
        sys.exit(1)
    
    # Show daily plan
    show_daily_plan(capital)
    
    # Ask to run simulation
    print("Would you like to run a simulated day? (yes/no)")
    response = input("> ").strip().lower()
    
    if response in ['yes', 'y']:
        print()
        run_simulation_day(capital)
    else:
        print("\n✅ Ready for live trading. Launch with:")
        print("   python3 -m multi_broker_phoenix.engines.real_trading_engine --mode daily_target")
    
    print()


if __name__ == "__main__":
    main()
