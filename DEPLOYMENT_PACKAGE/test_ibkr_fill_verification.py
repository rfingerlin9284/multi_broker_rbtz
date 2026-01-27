#!/usr/bin/env python3
"""
Test IBKR Fill Verification Implementation
Verifies that the new fill tracking is working correctly
"""

import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add project to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_ibkr_fill_verification():
    """Test IBKR connector fill verification."""
    
    logger.info("="*70)
    logger.info("🧪 TESTING IBKR FILL VERIFICATION")
    logger.info("="*70)
    
    try:
        from multi_broker_phoenix.brokers.ibkr_connector_enhanced import IBKRConnector
        logger.info("✅ Successfully imported IBKRConnector")
    except Exception as e:
        logger.error(f"❌ Failed to import IBKRConnector: {e}")
        return False
    
    # Test 1: Instantiation
    logger.info("\n[TEST 1] Instantiating IBKR connector...")
    try:
        connector = IBKRConnector(
            account_id='DU123456',
            paper_mode=True,
            host='127.0.0.1',
            port=7497
        )
        logger.info("✅ Connector instantiated successfully")
    except Exception as e:
        logger.error(f"❌ Failed to instantiate: {e}")
        return False
    
    # Test 2: Check tracking variables exist
    logger.info("\n[TEST 2] Checking tracking variables...")
    checks = {
        '_total_filled_orders': hasattr(connector, '_total_filled_orders'),
        '_filled_orders': hasattr(connector, '_filled_orders'),
        '_pending_fills': hasattr(connector, '_pending_fills'),
    }
    
    for var_name, exists in checks.items():
        status = "✅" if exists else "❌"
        logger.info(f"{status} {var_name}: {exists}")
    
    if not all(checks.values()):
        logger.error("❌ Missing tracking variables")
        return False
    
    # Test 3: Check methods exist
    logger.info("\n[TEST 3] Checking fill verification methods...")
    methods = {
        'verify_order_filled': hasattr(connector, 'verify_order_filled'),
        'get_filled_orders_count': hasattr(connector, 'get_filled_orders_count'),
        'get_filled_orders': hasattr(connector, 'get_filled_orders'),
    }
    
    for method_name, exists in methods.items():
        status = "✅" if exists else "❌"
        logger.info(f"{status} {method_name}(): {exists}")
    
    if not all(methods.values()):
        logger.error("❌ Missing fill verification methods")
        return False
    
    # Test 4: Test initial state
    logger.info("\n[TEST 4] Testing initial state...")
    try:
        filled_count = connector.get_filled_orders_count()
        filled_orders = connector.get_filled_orders()
        
        logger.info(f"✅ Filled count: {filled_count}")
        logger.info(f"✅ Filled orders: {filled_orders}")
        
        if filled_count != 0:
            logger.error(f"❌ Expected 0 filled orders initially, got {filled_count}")
            return False
    except Exception as e:
        logger.error(f"❌ Failed to get initial state: {e}")
        return False
    
    # Test 5: Test simulated order placement and verification
    logger.info("\n[TEST 5] Testing order placement and fill verification...")
    try:
        # Simulate placing an order
        test_order_id = "IBKR-TEST-001"
        test_order_data = {
            'order_id': test_order_id,
            'symbol': 'AAPL',
            'qty': 10,
            'price': 150.50,
            'timestamp': __import__('datetime').datetime.now().isoformat()
        }
        
        # Manually add to pending (simulating placement)
        connector._pending_fills[test_order_id] = test_order_data
        logger.info(f"✅ Simulated order placement: {test_order_id}")
        
        # Verify the order
        is_filled = connector.verify_order_filled(test_order_id)
        logger.info(f"✅ Order verified: {is_filled}")
        
        # Check updated count
        filled_count = connector.get_filled_orders_count()
        logger.info(f"✅ Filled count after verification: {filled_count}")
        
        if filled_count != 1:
            logger.error(f"❌ Expected 1 filled order, got {filled_count}")
            return False
        
        # Check filled orders
        filled_orders = connector.get_filled_orders()
        if test_order_id not in filled_orders:
            logger.error(f"❌ Order {test_order_id} not in filled orders")
            return False
        
        logger.info(f"✅ Order found in filled orders: {filled_orders[test_order_id]}")
        
    except Exception as e:
        logger.error(f"❌ Order verification test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 6: Test callable methods
    logger.info("\n[TEST 6] Testing method callability...")
    try:
        # These should be callable
        assert callable(connector.verify_order_filled), "verify_order_filled not callable"
        assert callable(connector.get_filled_orders_count), "get_filled_orders_count not callable"
        assert callable(connector.get_filled_orders), "get_filled_orders not callable"
        
        logger.info("✅ All methods are callable")
    except Exception as e:
        logger.error(f"❌ Method callability test failed: {e}")
        return False
    
    # Summary
    logger.info("\n" + "="*70)
    logger.info("✅ ALL TESTS PASSED - IBKR FILL VERIFICATION WORKING!")
    logger.info("="*70)
    logger.info("\nSummary:")
    logger.info("  ✅ Connector instantiation")
    logger.info("  ✅ Tracking variables initialized")
    logger.info("  ✅ Fill verification methods present")
    logger.info("  ✅ Initial state correct")
    logger.info("  ✅ Order placement and verification working")
    logger.info("  ✅ All methods callable")
    
    return True

if __name__ == '__main__':
    success = test_ibkr_fill_verification()
    sys.exit(0 if success else 1)
