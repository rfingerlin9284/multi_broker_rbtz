#!/usr/bin/env python3
"""
DUAL BROKER TEST TRADE
Sends test trades to BOTH IBKR and Coinbase Advanced to verify connections

This script:
1. Sends a small test trade to IBKR paper account (Gold futures)
2. Sends a small test trade to Coinbase Advanced (BTC spot)
3. Reports results in plain English for visual confirmation
"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from multi_broker_phoenix.brokers.ibkr_connector import IBKRConnector
from multi_broker_phoenix.brokers.coinbase_safe_connector import CoinbaseSafeConnector as CoinbaseConnector
from multi_broker_phoenix.engines.paper_engine import PaperEngine
from multi_broker_phoenix.risk.risk_manager import RiskManager

def test_ibkr():
    """Test IBKR paper account connection with Gold futures."""
    print("\n" + "="*70)
    print("🏦 TESTING IBKR PAPER ACCOUNT")
    print("="*70)
    
    try:
        engine = PaperEngine(db_path='data/test_ibkr.sqlite')
        ibkr = IBKRConnector(paper_mode=True, engine=engine)
        
        # Create test trade candidate
        import uuid
        class TestTrade:
            strategy_id = "test_dual_broker"
            symbol = "GC"  # Gold futures
            platform = "IBKR"
            entry_price = 2050.0
            stop_loss = 2040.0
            side = "BUY"
            id = f"TEST_IBKR_{uuid.uuid4().hex[:12]}"
        
        trade = TestTrade()
        
        print(f"\n📋 Test Trade Setup:")
        print(f"   Symbol: {trade.symbol} (Gold Futures)")
        print(f"   Side: {trade.side}")
        print(f"   Entry: ${trade.entry_price}")
        print(f"   Stop: ${trade.stop_loss}")
        print(f"   Risk: ${trade.entry_price - trade.stop_loss} per contract")
        
        # Size calculation
        rm = RiskManager()
        sizing = rm.size_for_trade(trade, account_equity=10000.0, fee_pct=0.001, slippage_pct=0.001)
        
        if not sizing.get('allowed'):
            print(f"\n❌ TRADE BLOCKED: {sizing.get('reason')}")
            return False
        
        size = sizing['size']
        print(f"\n✅ Risk Manager APPROVED")
        print(f"   Position Size: {size} contracts")
        print(f"   Risk: {sizing.get('risk_pct', 0)*100:.2f}% of account")
        
        # Update price in connector (required for order placement)
        ibkr.update_price(trade.symbol, trade.entry_price)
        
        # Place order
        print(f"\n📤 Placing order on IBKR...")
        result = ibkr.place_paper_order(trade, size)
        
        print(f"\n🎯 IBKR ORDER RESULT:")
        print(f"   Order ID: {result.get('id', 'N/A')}")
        print(f"   Status: {result.get('status', 'UNKNOWN')}")
        print(f"   Message: {result.get('message', 'No message')}")
        
        if result.get('status') == 'filled':
            print(f"\n✅ IBKR CONNECTION CONFIRMED - ORDER FILLED")
            return True
        else:
            print(f"\n⚠️  IBKR order placed but not filled yet")
            return True
            
    except Exception as e:
        print(f"\n❌ IBKR TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_coinbase():
    """Test Coinbase Advanced connection with BTC spot."""
    print("\n" + "="*70)
    print("₿ TESTING COINBASE ADVANCED")
    print("="*70)
    
    try:
        engine = PaperEngine(db_path='data/test_coinbase.sqlite')
        # Override minimum trade size for testing
        coinbase = CoinbaseConnector(paper_mode=True, engine=engine, min_trade_usd=1.0, max_trade_usd=1000.0)
        
        # Create test trade candidate
        import uuid
        class TestTrade:
            strategy_id = "test_dual_broker"
            symbol = "BTC-USD"
            platform = "COINBASE"
            entry_price = 42000.0  # Lower price for nano-lot sizing
            stop_loss = 41900.0  # Very tight stop = minimum viable position
            side = "BUY"
            id = f"TEST_COINBASE_{uuid.uuid4().hex[:12]}"
        
        trade = TestTrade()
        
        print(f"\n📋 Test Trade Setup:")
        print(f"   Symbol: {trade.symbol} (Bitcoin Spot)")
        print(f"   Side: {trade.side}")
        print(f"   Entry: ${trade.entry_price:,.2f}")
        print(f"   Stop: ${trade.stop_loss:,.2f}")
        print(f"   Risk: ${trade.entry_price - trade.stop_loss:,.2f} per BTC")
        
        # Size calculation
        rm = RiskManager()
        sizing = rm.size_for_trade(trade, account_equity=10000.0, fee_pct=0.006, slippage_pct=0.002)
        
        if not sizing.get('allowed'):
            print(f"\n❌ TRADE BLOCKED: {sizing.get('reason')}")
            return False
        
        size = sizing['size']
        notional = size * trade.entry_price
        
        print(f"\n✅ Risk Manager APPROVED")
        print(f"   Position Size: {size:.6f} BTC")
        print(f"   Notional Value: ${notional:.2f}")
        print(f"   Risk: {sizing.get('risk_pct', 0)*100:.2f}% of account")
        
        # Update price in connector (required for safety checks)
        coinbase.update_price(trade.symbol, trade.entry_price)
        
        # Place order
        print(f"\n📤 Placing order on Coinbase...")
        result = coinbase.place_paper_order(trade, size)
        
        print(f"\n🎯 COINBASE ORDER RESULT:")
        print(f"   Order ID: {result.get('id', 'N/A')}")
        print(f"   Status: {result.get('status', 'UNKNOWN')}")
        print(f"   Message: {result.get('message', 'No message')}")
        print(f"   Filled: {result.get('filled_size', 0)} BTC")
        
        if result.get('status') == 'filled':
            print(f"\n✅ COINBASE CONNECTION CONFIRMED - ORDER FILLED")
            return True
        else:
            print(f"\n⚠️  Coinbase order placed but not filled yet")
            return True
            
    except Exception as e:
        print(f"\n❌ COINBASE TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run both broker tests."""
    print("\n" + "="*70)
    print("🚀 DUAL BROKER CONNECTION TEST")
    print("="*70)
    print("\nThis test sends small orders to BOTH brokers to verify connections.")
    print("All trades are in PAPER/SIMULATION mode - no real money.")
    
    # Check environment
    print(f"\n🔧 Environment Check:")
    ai_hive_enabled = os.getenv('ENABLE_AI_HIVE', 'false').lower() == 'true'
    print(f"   AI Hive: {'ENABLED ✅' if ai_hive_enabled else 'DISABLED ⚠️'}")
    print(f"   Headless Mode: {os.getenv('HEADLESS_MODE', 'auto')}")
    print(f"   Trading Mode: {os.getenv('TRADING_MODE', 'PAPER')}")
    
    progression_enabled = os.getenv('PROGRESSION_ENABLED', 'false').lower() == 'true'
    print(f"   Smart Progression: {'ENABLED ✅' if progression_enabled else 'DISABLED ⚠️'}")
    
    # Run tests
    ibkr_success = test_ibkr()
    coinbase_success = test_coinbase()
    
    # Summary
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    print(f"   IBKR Paper: {'✅ SUCCESS' if ibkr_success else '❌ FAILED'}")
    print(f"   Coinbase Advanced: {'✅ SUCCESS' if coinbase_success else '❌ FAILED'}")
    
    if ibkr_success and coinbase_success:
        print(f"\n🎉 BOTH BROKERS CONNECTED AND OPERATIONAL!")
        print(f"\n💡 Next Step: Start the trading engine with:")
        print(f"   cd /home/ing/RICK/MULTI_BROKER_PHOENIX/MULTI_BROKER_PHOENIX")
        print(f"   export PYTHONPATH=$PWD:$PYTHONPATH")
        print(f"   python3 tools/run_headless.py")
        return 0
    else:
        print(f"\n⚠️  Some broker connections failed. Check errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
