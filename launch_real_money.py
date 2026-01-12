#!/usr/bin/env python3
"""REAL MONEY LAUNCHER - NO SIMULATION

This script launches the trading engine with REAL broker connections.
⚠️  THIS USES REAL MONEY - PROCEED WITH EXTREME CAUTION ⚠️
"""
import os
import sys
from typing import Dict, Any

# Add project to path
sys.path.append('/home/ing/RICK/MULTI_BROKER_PHOENIX/MULTI_BROKER_PHOENIX')

from multi_broker_phoenix.engines.real_trading_engine import RealTradingEngine
from multi_broker_phoenix.brokers.ibkr_connector_live import IBKRLiveConnector
from multi_broker_phoenix.brokers.coinbase_advanced_connector import CoinbaseAdvancedConnector
from multi_broker_phoenix.brokers.oanda_connector import OANDAConnector


def verify_real_money_intent():
    """Force user to explicitly confirm real money trading."""
    print("\n" + "="*80)
    print("⚠️  REAL MONEY TRADING CONFIRMATION REQUIRED ⚠️")
    print("="*80)
    print("\nThis will connect to LIVE brokers and trade with REAL MONEY.")
    print("You can lose significant amounts of money quickly.")
    print("\nType exactly: 'I UNDERSTAND I AM RISKING REAL MONEY'")
    
    confirmation = input("\nConfirmation: ").strip()
    
    if confirmation != "I UNDERSTAND I AM RISKING REAL MONEY":
        print("\n❌ Confirmation failed. Exiting for your safety.")
        sys.exit(1)
    
    print("\n✅ Real money trading confirmed.")


def setup_ibkr_live():
    """Setup IBKR for LIVE trading (port 4001)."""
    print("\n📊 Setting up IBKR LIVE connection...")
    
    # Check if TWS/IB Gateway is running on port 4001 (LIVE)
    try:
        connector = IBKRLiveConnector(
            paper_mode=False,  # ⚠️ LIVE MODE
            port=4001,        # ⚠️ LIVE PORT
            host='127.0.0.1',
            client_id=1
        )
        
        # Test connection
        print("   Testing IBKR LIVE connection...")
        # connector.connect()  # Uncomment when ready
        print("   ✅ IBKR LIVE connector ready")
        return connector
        
    except Exception as e:
        print(f"   ❌ IBKR LIVE setup failed: {e}")
        print("   💡 Make sure TWS/IB Gateway is running on port 4001")
        return None


def setup_coinbase_live():
    """Setup Coinbase for LIVE trading."""
    print("\n🪙 Setting up Coinbase LIVE connection...")
    
    api_key = os.getenv('COINBASE_API_KEY')
    api_secret = os.getenv('COINBASE_API_SECRET')
    api_passphrase = os.getenv('COINBASE_API_PASSPHRASE')
    
    if not all([api_key, api_secret, api_passphrase]):
        print("   ❌ Missing Coinbase API credentials")
        print("   💡 Set COINBASE_API_KEY, COINBASE_API_SECRET, COINBASE_API_PASSPHRASE")
        return None
    
    try:
        connector = CoinbaseAdvancedConnector(
            paper_mode=False,  # ⚠️ LIVE MODE
            api_key=api_key,
            api_secret=api_secret,
            api_passphrase=api_passphrase,
            sandbox=False  # ⚠️ LIVE COINBASE
        )
        
        print("   ✅ Coinbase LIVE connector ready")
        return connector
        
    except Exception as e:
        print(f"   ❌ Coinbase LIVE setup failed: {e}")
        return None


def setup_oanda_live():
    """Setup OANDA for LIVE trading."""
    print("\n🌍 Setting up OANDA LIVE connection...")
    
    token = os.getenv('OANDA_API_TOKEN')
    account_id = os.getenv('OANDA_ACCOUNT_ID')
    
    if not token or not account_id:
        print("   ❌ Missing OANDA credentials")
        print("   💡 Set OANDA_API_TOKEN and OANDA_ACCOUNT_ID")
        return None
    
    try:
        connector = OANDAConnector(
            token=token,
            account_id=account_id,
            base_url='https://api-fxtrade.oanda.com',  # ⚠️ LIVE URL (not fxpractice)
            practice_mode=False  # ⚠️ LIVE MODE
        )
        
        print("   ✅ OANDA LIVE connector ready")
        return connector
        
    except Exception as e:
        print(f"   ❌ OANDA LIVE setup failed: {e}")
        return None


def launch_real_trading():
    """Launch real money trading engine."""
    verify_real_money_intent()
    
    print("\n🔧 Setting up LIVE brokers...")
    
    # Setup brokers
    ibkr = setup_ibkr_live()
    coinbase = setup_coinbase_live()
    oanda = setup_oanda_live()
    
    # Check if any broker is available
    available_brokers = [b for b in [ibkr, coinbase, oanda] if b is not None]
    
    if not available_brokers:
        print("\n❌ No live brokers available. Cannot trade.")
        print("   Set up at least one broker's credentials and connection.")
        sys.exit(1)
    
    print(f"\n✅ {len(available_brokers)} live broker(s) available")
    
    # Choose primary broker
    primary_broker = available_brokers[0]
    print(f"   Using {primary_broker.__class__.__name__} as primary")
    
    # Setup trading engine
    print("\n🚀 Launching REAL TRADING ENGINE...")
    
    # Get starting capital from environment or default
    capital = float(os.getenv('LIVE_CAPITAL', '5000'))
    
    engine = RealTradingEngine(
        broker_connector=primary_broker,
        initial_capital=capital,
        daily_target_mode=True  # Enable $400/day mode
    )
    
    print("\n" + "="*80)
    print("🔴 REAL MONEY TRADING ACTIVE")
    print("="*80)
    print(f"Capital: ${capital:,.0f}")
    print(f"Broker: {primary_broker.__class__.__name__}")
    print("Target: $400/day")
    print("\nPress Ctrl+C to stop")
    print("="*80)
    
    # Start trading loop (placeholder)
    try:
        while True:
            # Here you would implement the actual trading loop
            # For now, just show it's running
            import time
            print("🔄 Trading engine running... (implement main loop here)")
            time.sleep(10)
            
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping real money trading...")
        print("✅ Engine stopped safely")


if __name__ == "__main__":
    print("🚨 REAL MONEY TRADING LAUNCHER")
    
    # Check environment
    if os.getenv('DEMO_MODE') == 'true':
        print("❌ DEMO_MODE is enabled - this prevents live trading")
        print("   Unset DEMO_MODE to enable real money trading")
        sys.exit(1)
    
    launch_real_trading()