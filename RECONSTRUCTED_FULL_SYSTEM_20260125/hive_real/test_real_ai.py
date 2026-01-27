#!/usr/bin/env python3
"""
REAL AI SYSTEM VALIDATOR
Tests connections to your REAL AI business accounts

This validates that the HIVE is actually using your:
- ChatGPT Business account
- Grok account
- DeepSeek account
"""
import json
import time
from datetime import datetime
from real_ai_hive import get_real_ai_vote

def test_real_ai_connections():
    """Test all AI connections with a sample trade."""
    
    print("🔍 TESTING REAL AI CONNECTIONS")
    print("=" * 50)
    print(f"Timestamp: {datetime.now()}")
    print()
    
    # Sample trade data
    symbol = "EURUSD"
    direction = "BUY"
    entry_price = 1.0985
    market_data = {
        "prices": [1.0950, 1.0960, 1.0970, 1.0975, 1.0980, 1.0985],
        "volume": [1000, 1200, 900, 1100, 1300, 1050]
    }
    
    print(f"📊 SAMPLE TRADE:")
    print(f"   Symbol: {symbol}")
    print(f"   Direction: {direction}")  
    print(f"   Entry: {entry_price}")
    print(f"   Recent prices: {market_data['prices'][-3:]}")
    print()
    
    print("🤖 QUERYING REAL AI SYSTEMS...")
    print("   This will test your actual business accounts")
    print()
    
    # Get AI analysis
    start_time = time.time()
    result = get_real_ai_vote(symbol, direction, entry_price, market_data)
    end_time = time.time()
    
    print(f"⏱️  Analysis completed in {end_time - start_time:.1f} seconds")
    print()
    
    # Display results
    print("📋 REAL AI ANALYSIS RESULTS:")
    print("=" * 30)
    
    print(f"Final Decision: {result['vote'].upper()}")
    print(f"Confidence: {result['confidence']:.1%}")
    print(f"Consensus: {result.get('consensus', 0):.1%}")
    print(f"Reasoning: {result['reasoning']}")
    print()
    
    # Show individual AI votes
    if 'votes' in result:
        print("🧠 INDIVIDUAL AI VOTES:")
        for vote in result['votes']:
            print(f"   {vote['ai']} ({vote['agent']}):")
            print(f"      Signal: {vote['signal'].upper()}")
            print(f"      Confidence: {vote['confidence']:.1%}")
            print(f"      Reasoning: {vote['reasoning'][:100]}...")
            print()
    
    # Validation checks
    print("✅ VALIDATION RESULTS:")
    
    # Check if we got real AI responses
    real_ais_responded = []
    if 'votes' in result:
        for vote in result['votes']:
            ai_name = vote['ai']
            if ai_name in ['ChatGPT', 'Grok', 'DeepSeek']:
                real_ais_responded.append(ai_name)
    
    if real_ais_responded:
        print(f"   ✅ Real AI responses from: {', '.join(real_ais_responded)}")
    else:
        print("   ❌ No real AI responses detected")
    
    # Check response quality
    if 'votes' in result and len(result['votes']) > 0:
        avg_reasoning_length = sum(len(v['reasoning']) for v in result['votes']) / len(result['votes'])
        if avg_reasoning_length > 50:
            print(f"   ✅ Quality reasoning (avg {avg_reasoning_length:.0f} chars)")
        else:
            print(f"   ⚠️  Short reasoning (avg {avg_reasoning_length:.0f} chars)")
    
    # Check timing
    if end_time - start_time < 120:
        print(f"   ✅ Reasonable response time ({end_time - start_time:.1f}s)")
    else:
        print(f"   ⚠️  Slow response time ({end_time - start_time:.1f}s)")
    
    print()
    
    # Summary
    if real_ais_responded:
        print("🎯 CONCLUSION: Real AI connections CONFIRMED")
        print(f"   Your {', '.join(real_ais_responded)} business accounts are responding")
    else:
        print("❌ CONCLUSION: Using fallback logic (NOT real AI)")
        print("   Check browser workers and account login status")
    
    return result

def test_specific_ai(ai_name: str):
    """Test connection to specific AI."""
    print(f"🔍 Testing {ai_name} connection...")
    
    # This would be implemented per AI type
    # For now, just show what would happen
    print(f"   💡 Would test your {ai_name} business account")
    print(f"   💡 Would verify login status")
    print(f"   💡 Would send test query")
    print(f"   💡 Would validate response authenticity")

if __name__ == "__main__":
    print("REAL AI HIVE VALIDATION")
    print("Testing your business account connections...")
    print()
    
    # Test all connections
    result = test_real_ai_connections()
    
    print()
    print("🔧 TROUBLESHOOTING:")
    print("   If no real AI responses:")
    print("   1. Run: python3 launch_all_ais.py")
    print("   2. Check browser windows open to ChatGPT")
    print("   3. Verify you're logged into business accounts")
    print("   4. Check WSL X11 forwarding if using GUI")
    
    print()
    print("📋 FULL RESULT JSON:")
    print(json.dumps(result, indent=2))