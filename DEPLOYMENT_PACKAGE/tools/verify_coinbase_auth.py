#!/usr/bin/env python3
"""
Coinbase Authentication Verification Script

READ-ONLY credential check - NO orders placed!

This script safely verifies your Coinbase Advanced Trade API credentials
by making a read-only request to fetch account information.

Safety: This ONLY reads account data, it cannot place orders.
"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from multi_broker_phoenix.brokers.coinbase_safe_connector import CoinbaseSafeConnector


def main():
    print("""
╔══════════════════════════════════════════════════════════════════╗
║       COINBASE AUTHENTICATION VERIFICATION (READ-ONLY)           ║
╚══════════════════════════════════════════════════════════════════╝

This script will:
  ✓ Check if JWT libraries are installed
  ✓ Verify your API credentials are configured
  ✓ Make a READ-ONLY request to fetch account info
  ✗ NOT place any orders (safe to run)

""")
    
    # Check environment variables
    api_key = os.getenv('COINBASE_API_KEY')
    api_secret = os.getenv('COINBASE_API_SECRET')
    
    if not api_key:
        print("❌ COINBASE_API_KEY not found in environment")
        print("   Set it in your .env file\n")
        return 1
    
    if not api_secret:
        print("❌ COINBASE_API_SECRET not found in environment")
        print("   Set it in your .env file\n")
        return 1
    
    print(f"✅ API Key found: {api_key[:50]}...")
    print(f"✅ API Secret configured (EC private key)\n")
    
    # Create connector (paper mode - extra safety)
    print("Creating Coinbase connector...")
    connector = CoinbaseSafeConnector(
        paper_mode=True,  # Extra safety - forces simulation mode
        engine=None
    )
    
    print("\nAttempting read-only credential verification...\n")
    print("-" * 60)
    
    # Verify credentials (read-only)
    result = connector.verify_credentials()
    
    print("-" * 60)
    print("\n📋 VERIFICATION RESULT:\n")
    
    if result['success']:
        print("✅ SUCCESS - Credentials are valid!")
        print(f"   {result['details']}")
        print(f"\n🎯 Your Coinbase Advanced Trade API is properly authenticated.")
        print(f"   You can now place orders when ready (requires multiple safety gates).\n")
        return 0
    else:
        print("❌ FAILED - Could not verify credentials")
        print(f"   Error: {result['error']}")
        print(f"   Details: {result.get('details', 'Unknown error')}")
        print(f"\n🔧 Check your .env file and ensure:")
        print(f"   - COINBASE_API_KEY is correct (organizations/.../apiKeys/...)")
        print(f"   - COINBASE_API_SECRET contains full EC PRIVATE KEY with \\n escape sequences")
        print(f"   - API key has 'view' and 'trade' permissions enabled\n")
        return 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Verification cancelled by user\n")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
