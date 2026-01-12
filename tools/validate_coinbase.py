#!/usr/bin/env python3
"""Validate Coinbase connector functionality in paper mode

This script tests:
1. Live price fetching from Coinbase public API
2. Paper order placement
3. Integration with PaperEngine
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from multi_broker_phoenix.brokers.coinbase_connector import CoinbaseConnector
from multi_broker_phoenix.engines.paper_engine import PaperEngine


class MockCandidate:
    """Mock trade candidate for testing"""
    def __init__(self, symbol, side, entry_price, stop_loss, strategy_id='test'):
        self.symbol = symbol
        self.side = side
        self.entry_price = entry_price
        self.stop_loss = stop_loss
        self.strategy_id = strategy_id
        self.platform = 'COINBASE'


def test_price_fetching():
    """Test live price fetching from Coinbase public API"""
    print("=" * 60)
    print("TEST 1: Live Price Fetching")
    print("=" * 60)
    
    connector = CoinbaseConnector(paper_mode=True)
    
    test_symbols = ['BTC-USD', 'ETH-USD']
    results = []
    
    for symbol in test_symbols:
        print(f"\nFetching price for {symbol}...")
        price = connector.fetch_live_price(symbol)
        if price:
            print(f"✓ {symbol}: ${price:,.2f}")
            results.append(True)
        else:
            print(f"✗ {symbol}: Failed to fetch price")
            results.append(False)
    
    return all(results)


def test_paper_order():
    """Test paper order placement"""
    print("\n" + "=" * 60)
    print("TEST 2: Paper Order Placement")
    print("=" * 60)
    
    engine = PaperEngine()
    connector = CoinbaseConnector(paper_mode=True, engine=engine)
    
    # Fetch live price first
    symbol = 'BTC-USD'
    print(f"\nFetching live price for {symbol}...")
    price = connector.fetch_live_price(symbol)
    
    if not price:
        print(f"✗ Cannot test order placement - no price data")
        return False
    
    print(f"✓ Current price: ${price:,.2f}")
    
    # Create mock buy candidate
    print(f"\nPlacing paper BUY order...")
    candidate = MockCandidate(
        symbol=symbol,
        side='BUY',
        entry_price=price,
        stop_loss=price * 0.98  # 2% stop loss
    )
    
    try:
        order = connector.place_paper_order(candidate, size=0.001)  # Small size
        print(f"✓ Order placed successfully:")
        print(f"  Order ID: {order.get('id')}")
        print(f"  Symbol: {order.get('symbol')}")
        print(f"  Side: {order.get('side')}")
        print(f"  Fill Price: ${order.get('fill_price', 0):,.2f}")
        print(f"  Size: {order.get('size')}")
        print(f"  Fees: ${order.get('fees', 0):.4f}")
        print(f"  Status: {order.get('status')}")
        print(f"  Execution Type: {order.get('execution_type')}")
        return True
    except Exception as e:
        print(f"✗ Order placement failed: {e}")
        return False


def test_integration():
    """Test full integration with engine"""
    print("\n" + "=" * 60)
    print("TEST 3: Engine Integration")
    print("=" * 60)
    
    # Use separate engine for each test to avoid database conflicts
    engine = PaperEngine()
    connector = CoinbaseConnector(paper_mode=True, engine=engine)
    
    symbol = 'ETH-USD'
    price = connector.fetch_live_price(symbol)
    
    if not price:
        print(f"✗ Cannot test integration - no price data")
        return False
    
    print(f"\n✓ Current {symbol} price: ${price:,.2f}")
    
    # Place a single order to test engine integration
    print("\nPlacing test order through engine...")
    
    candidate = MockCandidate(
        symbol=symbol,
        side='BUY',
        entry_price=price,
        stop_loss=price * 0.98,
        strategy_id='integration_test'
    )
    
    try:
        order = connector.place_paper_order(candidate, size=0.01)
        print(f"  ✓ Order placed: {order.get('id')}")
        print(f"    Symbol: {order.get('symbol')}")
        print(f"    Side: {order.get('side')}")
        print(f"    Execution: {order.get('execution_type')}")
        return True
    except Exception as e:
        print(f"  ✗ Order failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all validation tests"""
    print("\n" + "=" * 60)
    print("COINBASE CONNECTOR VALIDATION")
    print("=" * 60)
    print("\nTesting Coinbase connector in PAPER mode")
    print("No API credentials required for public price data\n")
    
    results = {
        'Price Fetching': test_price_fetching(),
        'Paper Order Placement': test_paper_order(),
        'Engine Integration': test_integration()
    }
    
    # Summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{test_name}: {status}")
    
    all_passed = all(results.values())
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ ALL TESTS PASSED - Coinbase connector is operational!")
    else:
        print("✗ SOME TESTS FAILED - Check errors above")
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
