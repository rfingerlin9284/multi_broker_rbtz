#!/usr/bin/env python3
"""Verify ALL broker API authentication.

This script confirms that:
1. OANDA Practice API token is valid and working
2. IBKR TWS/Gateway paper connection is available
3. Coinbase Advanced Trade API JWT auth is configured

Run this BEFORE starting live trading to ensure all connections work.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Add repo root to path
_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / 'MULTI_BROKER_PHOENIX'))


def _load_env() -> None:
    """Load repo-root .env without overriding existing process environment."""
    env_path = _REPO_ROOT / '.env'
    if not env_path.exists():
        print(f"⚠️  No .env file found at {env_path}")
        return

    parsed: dict[str, str] = {}
    with env_path.open('r', encoding='utf-8', errors='ignore') as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            if '#' in line:
                eq = line.find('=')
                hp = line.find('#', eq)
                if hp > 0:
                    line = line[:hp].strip()
            if '=' not in line:
                continue
            k, v = line.split('=', 1)
            k = k.strip()
            v = v.strip()
            if not k:
                continue
            parsed[k] = v

    for k, v in parsed.items():
        if k not in os.environ:
            os.environ[k] = v
    
    print(f"✅ Loaded environment from {env_path}")


_load_env()


def verify_oanda() -> bool:
    """Verify OANDA Practice API authentication."""
    print("\n" + "="*60)
    print("🔶 OANDA PRACTICE API VERIFICATION")
    print("="*60)
    
    token = os.getenv('OANDA_API_TOKEN')
    account_id = os.getenv('OANDA_ACCOUNT_ID')
    base_url = os.getenv('OANDA_API_URL', 'https://api-fxpractice.oanda.com')
    
    if not token:
        print("❌ OANDA_API_TOKEN not set")
        return False
    
    if not account_id:
        print("❌ OANDA_ACCOUNT_ID not set")
        return False
    
    print(f"   Token: {token[:10]}...{token[-5:]}")
    print(f"   Account: {account_id}")
    print(f"   API URL: {base_url}")
    
    try:
        from multi_broker_phoenix.brokers.oanda_connector import OANDAConnector
        
        connector = OANDAConnector(
            token=token,
            account_id=account_id,
            base_url=base_url,
            practice_mode=True
        )
        
        result = connector.verify_credentials()
        
        if result.get('success'):
            print(f"\n✅ OANDA API AUTHENTICATION VERIFIED")
            print(f"   Currency: {result.get('currency')}")
            print(f"   Mode: {result.get('mode')}")
            
            # Test price fetch
            price = connector.get_last_price('EUR_USD')
            if price:
                print(f"   EUR_USD Price: {price:.5f}")
                print(f"\n🟢 OANDA READY FOR PRACTICE TRADING")
                return True
            else:
                print("   ⚠️  Price fetch failed but auth OK")
                return True
        else:
            print(f"\n❌ OANDA AUTH FAILED: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"\n❌ OANDA ERROR: {e}")
        return False


def verify_ibkr() -> bool:
    """Verify IBKR TWS/Gateway paper connection."""
    print("\n" + "="*60)
    print("🔷 IBKR PAPER TRADING VERIFICATION")
    print("="*60)
    
    host = os.getenv('IBKR_HOST', '172.25.80.1')
    port = int(os.getenv('IBKR_PORT', '4002'))
    client_id = int(os.getenv('IBKR_CLIENT_ID', '1'))
    enabled = os.getenv('IBKR_ENABLED', 'true').lower() in ('true', '1', 'yes')
    
    if not enabled:
        print("⚠️  IBKR_ENABLED=false - skipping")
        return True
    
    print(f"   Host: {host}")
    print(f"   Port: {port} (4002=paper, 4001=live)")
    print(f"   Client ID: {client_id}")
    
    try:
        from multi_broker_phoenix.brokers.ibkr_connector_live import IBKRLiveConnector
        
        connector = IBKRLiveConnector(
            host=host,
            port=port,
            client_id=client_id,
            paper_mode=True
        )
        
        if connector.connect():
            print(f"\n✅ IBKR TWS/GATEWAY CONNECTION VERIFIED")
            print(f"   Connected to paper trading account")
            print(f"\n🟢 IBKR READY FOR PAPER TRADING")
            connector.disconnect()
            return True
        else:
            print(f"\n⚠️  IBKR CONNECTION FAILED")
            print(f"   Make sure TWS or IB Gateway is running on port {port}")
            return False
            
    except ImportError:
        print("\n⚠️  ib_insync not installed")
        print("   Install with: pip install ib_insync")
        print("   IBKR connector will use stub mode (no real connection)")
        return False
    except Exception as e:
        print(f"\n⚠️  IBKR ERROR: {e}")
        print(f"   Make sure TWS/IB Gateway is running on {host}:{port}")
        return False


def verify_coinbase() -> bool:
    """Verify Coinbase Advanced Trade API authentication."""
    print("\n" + "="*60)
    print("🔴 COINBASE LIVE TRADING VERIFICATION")
    print("="*60)
    print("⚠️  WARNING: COINBASE USES REAL MONEY - NO PAPER ACCOUNT!")
    print("="*60)
    
    api_key = os.getenv('COINBASE_API_KEY')
    api_secret = os.getenv('COINBASE_API_SECRET', '')
    secret_file = os.getenv('COINBASE_API_SECRET_FILE', '')
    coinbase_live = os.getenv('COINBASE_LIVE', 'false').lower() in ('true', '1', 'yes')
    
    if not api_key:
        print("❌ COINBASE_API_KEY not set")
        return False
    
    print(f"   API Key: {api_key[:20]}...")
    print(f"   Secret File: {secret_file}")
    print(f"   Live Mode: {'🔴 ENABLED' if coinbase_live else '🟢 DISABLED'}")
    
    # Check if secret file exists
    if secret_file and os.path.exists(secret_file):
        print(f"   ✅ Secret file exists")
    else:
        print(f"   ⚠️  Secret file not found at {secret_file}")
        if not api_secret:
            print("   ❌ No COINBASE_API_SECRET provided either")
            return False
    
    try:
        from multi_broker_phoenix.brokers.coinbase_safe_connector import CoinbaseSafeConnector
        
        connector = CoinbaseSafeConnector(paper_mode=not coinbase_live)
        
        # Test public price fetch (no auth needed)
        price = connector.fetch_live_price('BTC-USD')
        
        if price:
            print(f"\n✅ COINBASE PUBLIC API VERIFIED")
            print(f"   BTC-USD Price: ${price:,.2f}")
            
            if connector._jwt_enabled:
                print(f"   ✅ JWT Authentication: READY")
                print(f"\n🔴 COINBASE READY FOR {'LIVE' if coinbase_live else 'SIMULATED'} TRADING")
                
                if coinbase_live:
                    print(f"\n   ⚠️  SAFETY LIMITS ACTIVE:")
                    print(f"   Min trade: ${connector.min_trade_usd}")
                    print(f"   Max trade: ${connector.max_trade_usd}")
                    print(f"   Daily loss limit: ${connector.daily_loss_limit}")
                    print(f"   Auto-scaling: {'ON' if connector._scaling_enabled else 'OFF'}")
                
                return True
            else:
                print(f"   ❌ JWT Authentication: NOT CONFIGURED")
                print(f"   Order placement will fail without JWT auth")
                return False
        else:
            print(f"\n❌ COINBASE PUBLIC API FAILED")
            return False
            
    except Exception as e:
        print(f"\n❌ COINBASE ERROR: {e}")
        return False


def main():
    print("\n" + "="*60)
    print("🤖 RBOTZILLA BROKER AUTHENTICATION VERIFICATION")
    print("="*60)
    print("Verifying all broker API connections...")
    print("")
    print("Configuration Summary:")
    print(f"  TRADING_MODE: {os.getenv('TRADING_MODE', 'PAPER')}")
    print(f"  OANDA: Practice API (real API, paper account)")
    print(f"  IBKR: Paper Trading (TWS port 4002)")
    print(f"  COINBASE: {'🔴 LIVE (REAL MONEY)' if os.getenv('COINBASE_LIVE', 'false').lower() in ('true', '1', 'yes') else '🟢 Simulation'}")
    
    results = {}
    
    # Verify each broker
    results['OANDA'] = verify_oanda()
    results['IBKR'] = verify_ibkr()
    results['COINBASE'] = verify_coinbase()
    
    # Summary
    print("\n" + "="*60)
    print("📊 VERIFICATION SUMMARY")
    print("="*60)
    
    all_ok = True
    for broker, ok in results.items():
        status = "✅ READY" if ok else "❌ FAILED"
        print(f"   {broker}: {status}")
        if not ok:
            all_ok = False
    
    print("")
    if all_ok:
        print("🟢 ALL BROKERS VERIFIED - READY TO TRADE")
        print("")
        print("To start trading:")
        print("  1. Run: python MULTI_BROKER_PHOENIX/tools/run_headless.py --mode multi-asset")
        print("  2. Or use VS Code task: 🚀 RBOTZILLA: Start ALL Brokers + Hive")
    else:
        print("🔴 SOME BROKERS FAILED VERIFICATION")
        print("")
        print("Check the errors above and fix before trading.")
    
    return 0 if all_ok else 1


if __name__ == '__main__':
    sys.exit(main())
