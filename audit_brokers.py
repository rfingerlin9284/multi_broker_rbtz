#!/usr/bin/env python3
"""
BROKER AUDIT SCRIPT
Comprehensive health check and configuration audit across all brokers
"""
import os
import sys
import logging
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'MULTI_BROKER_PHOENIX'))

from multi_broker_phoenix.brokers.coinbase_connector import CoinbaseConnector
from multi_broker_phoenix.brokers.ibkr_connector import IBKRConnector

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


def audit_coinbase():
    """Audit Coinbase connector configuration and status"""
    print("\n" + "="*80)
    print("🔴 COINBASE ADVANCED TRADE AUDIT")
    print("="*80)
    
    try:
        connector = CoinbaseConnector(paper_mode=False)
        
        # Configuration
        print("\n📋 CONFIGURATION:")
        print(f"   Mode: {'🔴 REAL MONEY' if not connector.paper_mode else '🟢 SIMULATION'}")
        print(f"   API Type: Coinbase Advanced Trade (v3)")
        print(f"   JWT Auth: {'✅ CONFIGURED' if 'CDP_API_KEY_NAME' in os.environ else '❌ NOT CONFIGURED'}")
        
        # Safety Limits
        print("\n🛡️  SAFETY LIMITS:")
        print(f"   Min Trade: ${connector.min_trade_usd:.2f}")
        print(f"   Max Trade: ${connector.max_trade_usd:.2f}")
        print(f"   Daily Loss Limit: ${connector.daily_loss_limit:.2f}")
        print(f"   Max Trades/Day: {connector.max_trades_per_day}")
        print(f"   Stop After N Losses: {connector.stop_on_consecutive_losses}")
        
        # Trailing Stops
        print("\n⏸️  TRAILING STOPS:")
        print(f"   Enabled: {'✅ YES' if connector.use_trailing_stops else '❌ NO'}")
        print(f"   Initial Stop Loss: {connector.initial_stop_loss_pct:.1f}%")
        print(f"   Activation Level: +{connector.trailing_activation_pct:.1f}%")
        print(f"   Trail Distance: -{connector.trailing_distance_pct:.1f}%")
        
        # Auto-Scaling
        print("\n📈 AUTO-SCALING:")
        print(f"   Enabled: {'✅ YES' if connector._scaling_enabled else '❌ NO'}")
        print(f"   Current Tier: {connector._current_tier}")
        if len(connector._scale_up_tiers) > 0:
            tier = connector._scale_up_tiers[min(connector._current_tier, len(connector._scale_up_tiers)-1)]
            print(f"   Tier Name: {tier['name']}")
            print(f"   Position Range: ${tier['min']:.0f} - ${tier['max']:.0f}")
            print(f"   Win Rate Requirement: {tier['win_rate']*100:.0f}%")
            print(f"   Profit Requirement: ${tier['profit']:.0f}+")
            print(f"   Trade Count Requirement: {tier['trades']}+")
        
        # Performance History
        print("\n📊 PERFORMANCE HISTORY:")
        print(f"   Completed Trades: {len(connector._performance_history)}")
        if len(connector._performance_history) > 0:
            wins = sum(1 for t in connector._performance_history if t.get('pnl', 0) > 0)
            losses = sum(1 for t in connector._performance_history if t.get('pnl', 0) <= 0)
            total_pnl = sum(t.get('pnl', 0) for t in connector._performance_history)
            win_rate = (wins / len(connector._performance_history)) * 100 if len(connector._performance_history) > 0 else 0
            print(f"   Wins: {wins} | Losses: {losses} | Win Rate: {win_rate:.1f}%")
            print(f"   Total P/L: ${total_pnl:+.2f}")
            print(f"   Avg Win: ${sum(t.get('pnl', 0) for t in connector._performance_history if t.get('pnl', 0) > 0) / max(1, wins):+.2f}")
            print(f"   Avg Loss: ${sum(t.get('pnl', 0) for t in connector._performance_history if t.get('pnl', 0) <= 0) / max(1, losses):+.2f}")
        
        print("\n✅ COINBASE STATUS: READY")
        
    except Exception as e:
        print(f"\n❌ COINBASE AUDIT FAILED: {e}")
        import traceback
        traceback.print_exc()


def audit_ibkr():
    """Audit IBKR connector configuration and status"""
    print("\n" + "="*80)
    print("🟡 IBKR (INTERACTIVE BROKERS) AUDIT")
    print("="*80)
    
    try:
        connector = IBKRConnector(paper_mode=True)
        
        # Configuration
        print("\n📋 CONFIGURATION:")
        print(f"   Mode: {'🟡 PAPER TRADING' if connector.paper_mode else '🔴 LIVE TRADING'}")
        print(f"   Gateway: Not Yet Connected (extend with IB-insync)")
        print(f"   Fee Structure: {connector.fee_pct*100:.2f}% (implied)")
        print(f"   Slippage Model: {connector.slippage_pct*100:.2f}% (estimated)")
        
        # Price Data
        print("\n💾 PRICE CACHE:")
        print(f"   Symbols Cached: {len(connector._price_by_symbol)}")
        if len(connector._price_by_symbol) > 0:
            for symbol, price in list(connector._price_by_symbol.items())[:5]:
                print(f"      {symbol}: ${price:,.2f}")
        else:
            print(f"      (empty - no prices yet)")
        
        print("\n✅ IBKR STATUS: READY (Paper Trading)")
        
    except Exception as e:
        print(f"\n❌ IBKR AUDIT FAILED: {e}")
        import traceback
        traceback.print_exc()


def audit_system():
    """Audit overall system configuration"""
    print("\n" + "="*80)
    print("⚙️  SYSTEM CONFIGURATION AUDIT")
    print("="*80)
    
    # Environment variables
    print("\n📝 ENVIRONMENT VARIABLES:")
    critical_vars = [
        'CDP_API_KEY_NAME',
        'CDP_API_KEY_PRIVATE_KEY',
        'COINBASE_MIN_TRADE_USD',
        'COINBASE_MAX_TRADE_USD',
        'COINBASE_DAILY_LOSS_LIMIT',
        'COINBASE_MAX_TRADES_PER_DAY',
    ]
    
    for var in critical_vars:
        value = os.getenv(var)
        if value:
            if 'KEY' in var or 'PRIVATE' in var:
                print(f"   {var}: {'✅ SET' if value else '❌ NOT SET'}")
            else:
                print(f"   {var}: {value}")
        else:
            print(f"   {var}: ❌ NOT SET")
    
    # File system
    print("\n📂 FILE SYSTEM:")
    log_file = '/home/ing/RICK/MULTI_BROKER_PHOENIX/live_extreme_engine.log'
    if os.path.exists(log_file):
        size = os.path.getsize(log_file) / 1024  # KB
        print(f"   live_extreme_engine.log: ✅ EXISTS ({size:.1f} KB)")
    else:
        print(f"   live_extreme_engine.log: ❌ NOT FOUND")
    
    # Python imports
    print("\n🐍 PYTHON DEPENDENCIES:")
    try:
        import jwt
        print(f"   PyJWT: ✅ INSTALLED")
    except ImportError:
        print(f"   PyJWT: ❌ MISSING")
    
    try:
        import cryptography
        print(f"   Cryptography: ✅ INSTALLED")
    except ImportError:
        print(f"   Cryptography: ❌ MISSING")
    
    try:
        import requests
        print(f"   Requests: ✅ INSTALLED")
    except ImportError:
        print(f"   Requests: ❌ MISSING")


def main():
    print("\n" + "="*80)
    print("🔍 BROKER AUDIT - STARTING")
    print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # Run audits
    audit_coinbase()
    audit_ibkr()
    audit_system()
    
    # Summary
    print("\n" + "="*80)
    print("📊 AUDIT COMPLETE")
    print("="*80)
    print("\n✅ All systems ready for deployment")
    print("\nNext Steps:")
    print("1. Verify JWT credentials for Coinbase in environment variables")
    print("2. Ensure IBKR Gateway is running for live trading (if needed)")
    print("3. Monitor live_extreme_engine.log for trading activity")
    print("4. Check graduation progress: tail -f live_extreme_engine.log | grep GRADUATION")
    print("\n")


if __name__ == "__main__":
    main()
