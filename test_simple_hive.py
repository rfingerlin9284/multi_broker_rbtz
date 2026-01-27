#!/usr/bin/env python3
"""Test the WSL-compatible HIVE integration"""

import sys
import os

# Add both paths for imports
sys.path.append('/home/ing/RICK/MULTI_BROKER_PHOENIX/MULTI_BROKER_PHOENIX')
sys.path.append('/home/ing/RICK/MULTI_BROKER_PHOENIX')

from multi_broker_phoenix.risk.trade_risk_gate import TradeCandidate
from multi_broker_phoenix.engines.real_trading_engine import RealTradingEngine

# Mock broker for testing
class MockBroker:
    def __init__(self):
        self.name = "WSL_Test_Broker"
    
    def __class__(self):
        return type('MockBroker', (), {'__name__': 'MockBroker'})

def test_simple_hive():
    print("🧪 Testing Simple HIVE Integration")
    print("=" * 50)
    
    # Create mock broker and engine in $400/day mode
    broker = MockBroker()
    engine = RealTradingEngine(
        broker_connector=broker,
        initial_capital=5000,
        daily_target_mode=True  # Enable $400/day mode
    )
    
    # Test data
    test_prices = [1.0950 + i*0.0001 + (i%3)*0.0002 for i in range(30)]
    market_data = {
        'prices': test_prices,
        'symbol': 'EURUSD',
        'platform': 'OANDA'
    }
    
    # Create test candidate
    candidate = TradeCandidate(
        strategy_id='holy_grail',
        symbol='EURUSD',
        platform='OANDA',
        entry_price=test_prices[-1],
        stop_loss=test_prices[-1] - 0.0030,  # 30 pip stop
        side='BUY'
    )
    
    print(f"\n📊 Test Trade:")
    print(f"   Symbol: {candidate.symbol}")
    print(f"   Side: {candidate.side}")
    print(f"   Entry: {candidate.entry_price:.5f}")
    print(f"   Stop: {candidate.stop_loss:.5f}")
    print(f"   Risk: {abs(candidate.entry_price - candidate.stop_loss):.5f}")
    
    # Test HIVE evaluation (without actual execution)
    print(f"\n🐝 Testing HIVE evaluation...")
    
    # Direct test of simple_hive
    from hive_real.simple_hive import get_hive_vote
    
    hive_result = get_hive_vote(
        candidate.symbol,
        candidate.side, 
        candidate.entry_price,
        market_data
    )
    
    print(f"\n📋 HIVE Results:")
    print(f"   Decision: {hive_result['vote']}")
    print(f"   Consensus: {hive_result['consensus']*100:.1f}%")
    print(f"   Confidence: {hive_result['confidence']*100:.1f}%")
    print(f"   Reasoning: {hive_result['reasoning']}")
    
    print(f"\n🔍 Individual Votes:")
    for vote in hive_result['votes']:
        print(f"   {vote['agent']:12} | {vote['signal']:7} | {vote['confidence']*100:5.1f}% | {vote['reasoning']}")
    
    print(f"\n✅ WSL Simple HIVE integration working!")
    
    return hive_result['vote'] == 'approve'

if __name__ == "__main__":
    try:
        success = test_simple_hive()
        print(f"\n🎯 Result: {'TRADE APPROVED' if success else 'TRADE REJECTED'}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()