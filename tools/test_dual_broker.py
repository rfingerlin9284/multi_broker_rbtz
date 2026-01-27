#!/usr/bin/env python3
"""
Dual-Broker Test Script
Tests both IBKR (paper) and Coinbase (simulation) with all safety limits
"""
import os
import sys

# Add to path
sys.path.insert(0, '/home/ing/RICK/MULTI_BROKER_PHOENIX/MULTI_BROKER_PHOENIX')
sys.path.insert(0, '/home/ing/RICK/MULTI_BROKER_PHOENIX')

from multi_broker_phoenix.brokers.ibkr_connector_live import IBKRLiveConnector
from multi_broker_phoenix.brokers.coinbase_safe_connector import CoinbaseSafeConnector
from multi_broker_phoenix.risk.safety_tripwires import get_safety_system

def test_ibkr():
    """Test IBKR paper trading connection."""
    print("\n" + "=" * 70)
    print("🟢 TESTING IBKR PAPER TRADING (Port 4002)")
    print("=" * 70)
    
    try:
        connector = IBKRLiveConnector(port=4002, paper_mode=True)
        
        if connector.connect():
            print("✅ Connected to TWS!")
            
            # Get account
            account = connector.get_account_summary()
            print(f"\n💰 Account: ${account.get('net_liquidation', 0):,.2f} (Paper)")
            
            # Get price
            print("\n📊 Fetching SPY price...")
            price = connector.get_last_price('SPY')
            if price:
                print(f"   SPY: ${price:.2f}")
            
            connector.disconnect()
            return True
        else:
            print("❌ Connection failed - TWS may need restart")
            return False
    
    except Exception as e:
        print(f"❌ IBKR Error: {e}")
        print("\n🔧 Troubleshooting:")
        print("   1. Make sure TWS is running")
        print("   2. API → Settings → Enable ActiveX and Socket Clients")
        print("   3. Socket port: 4002")
        print("   4. Restart TWS after enabling")
        return False

def test_coinbase():
    """Test Coinbase with safety limits (simulation)."""
    print("\n" + "=" * 70)
    print("🔴 TESTING COINBASE NANO-LOT SIMULATION")
    print("=" * 70)
    
    try:
        connector = CoinbaseSafeConnector(paper_mode=True)
        
        # Fetch prices
        print("\n📊 Fetching live prices...")
        btc_price = connector.fetch_live_price('BTC-USD')
        eth_price = connector.fetch_live_price('ETH-USD')
        
        if btc_price and eth_price:
            print(f"   ✅ BTC-USD: ${btc_price:,.2f}")
            print(f"   ✅ ETH-USD: ${eth_price:,.2f}")
        
        # Show safety limits
        print("\n🛡️  Safety Configuration:")
        print(f"   Min trade: ${connector.min_trade_usd:.2f}")
        print(f"   Max trade: ${connector.max_trade_usd:.2f}")
        print(f"   Daily loss limit: ${connector.daily_loss_limit:.2f}")
        print(f"   Max trades/day: {connector.max_trades_per_day}")
        print(f"   Consecutive loss breaker: {connector.stop_on_consecutive_losses}")
        
        # Current stats
        stats = connector.get_daily_stats()
        print("\n📈 Current Status:")
        print(f"   Trades today: {stats['trades_today']}/{connector.max_trades_per_day}")
        print(f"   Daily loss: ${stats['daily_loss']:.2f}/${connector.daily_loss_limit:.2f}")
        print(f"   Remaining budget: ${stats['remaining_loss_budget']:.2f}")
        print(f"   Trading status: {'⛔ STOPPED' if stats['stopped'] else '✅ Active'}")
        
        return True
    
    except Exception as e:
        print(f"❌ Coinbase Error: {e}")
        return False

def test_safety_system():
    """Test centralized safety tripwire system."""
    print("\n" + "=" * 70)
    print("🛡️  TESTING CENTRALIZED SAFETY SYSTEM")
    print("=" * 70)
    
    try:
        safety = get_safety_system()
        
        # Check if trading allowed
        check = safety.can_trade()
        print(f"\n📊 Trading Status: {'✅ ALLOWED' if check['allowed'] else '⛔ BLOCKED'}")
        if not check['allowed']:
            print(f"   Reason: {check['reason']}")
        
        # Show configuration
        print("\n⚙️  Safety Limits:")
        print(f"   Max Drawdown: {safety.limits.max_drawdown_pct}%")
        print(f"   Max Consecutive Losses: {safety.limits.max_consecutive_losses}")
        print(f"   Daily Loss Limit: ${safety.limits.daily_loss_limit_usd:.2f}")
        print(f"   Volatility Breaker: {safety.limits.volatility_circuit_breaker_pct}%")
        print(f"   Edge Validation: {'Required' if safety.limits.require_edge_validation else 'Optional'}")
        
        # Show current stats
        status = safety.get_status()
        print("\n📈 Current Metrics:")
        print(f"   Total Trades: {status['total_trades']}")
        print(f"   Win Rate: {status['win_rate_pct']:.1f}%")
        print(f"   Profit Factor: {status['profit_factor']:.2f}")
        print(f"   Drawdown: {status['drawdown_pct']:.1f}%")
        print(f"   Consecutive Losses: {status['consecutive_losses']}")
        print(f"   Edge Validated: {'✅ Yes' if status['edge_validated'] else '⏳ Pending (need 100 trades)'}")
        
        return True
    
    except Exception as e:
        print(f"❌ Safety System Error: {e}")
        return False

def main():
    print("\n" + "🚀" * 35)
    print("DUAL-BROKER TESTING SUITE")
    print("Testing IBKR Paper + Coinbase Nano-Lot with Safety Systems")
    print("🚀" * 35)
    
    results = {
        'ibkr': test_ibkr(),
        'coinbase': test_coinbase(),
        'safety': test_safety_system()
    }
    
    print("\n" + "=" * 70)
    print("📊 TEST SUMMARY")
    print("=" * 70)
    print(f"   IBKR Paper:        {'✅ PASSED' if results['ibkr'] else '❌ FAILED (needs TWS restart)'}")
    print(f"   Coinbase Nano:     {'✅ PASSED' if results['coinbase'] else '❌ FAILED'}")
    print(f"   Safety System:     {'✅ PASSED' if results['safety'] else '❌ FAILED'}")
    
    if all(results.values()):
        print("\n🎉 ALL SYSTEMS OPERATIONAL!")
        print("   Ready to start dual-broker testing")
    elif results['coinbase'] and results['safety']:
        print("\n⚠️  Coinbase ready, IBKR needs TWS restart")
        print("   Can proceed with Coinbase simulation while fixing IBKR")
    else:
        print("\n⚠️  Some systems need attention")
    
    print("=" * 70)

if __name__ == '__main__':
    main()
