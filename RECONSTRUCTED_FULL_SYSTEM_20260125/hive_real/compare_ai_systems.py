#!/usr/bin/env python3
"""
REAL vs FAKE AI COMPARISON TEST
Direct comparison showing the quality difference
"""
import sys
import os
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]
engine_root = repo_root / "MULTI_BROKER_PHOENIX"
sys.path.append(str(engine_root))
sys.path.append(str(repo_root))

def compare_hive_systems():
    """Compare the three HIVE systems side by side."""
    
    print("🔍 REAL vs FAKE AI HIVE COMPARISON")
    print("=" * 60)
    
    # Sample trade data
    symbol = "EURUSD"
    direction = "BUY"
    entry_price = 1.0985
    market_data = {
        "prices": [1.0950, 1.0960, 1.0970, 1.0975, 1.0980, 1.0985],
        "volume": [1000, 1200, 900, 1100, 1300, 1050],
        "close": [1.0950, 1.0960, 1.0970, 1.0975, 1.0980, 1.0985]
    }
    
    print(f"📊 SAMPLE TRADE:")
    print(f"   Symbol: {symbol}")
    print(f"   Direction: {direction}")
    print(f"   Entry: {entry_price}")
    print(f"   Recent prices: {market_data['prices'][-3:]}")
    print()
    
    # Test 1: Simple HIVE (Fake Python Math)
    print("1️⃣  SIMPLE HIVE (FAKE - Python Math)")
    print("-" * 40)
    try:
        from hive_real.simple_hive import get_hive_vote
        import time
        
        start_time = time.time()
        fake_result = get_hive_vote(symbol, direction, entry_price, market_data)
        fake_time = time.time() - start_time
        
        print(f"   ⚡ Response time: {fake_time:.3f} seconds (INSTANT = FAKE)")
        print(f"   🎯 Decision: {fake_result['vote']}")
        print(f"   📊 Confidence: {fake_result['confidence']:.1%}")
        print(f"   📝 Reasoning: {fake_result['reasoning']}")
        print(f"   🔍 Analysis: Mathematical calculations, no real intelligence")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print()
    
    # Test 2: API-based Real AI
    print("2️⃣  API-BASED REAL AI (with API keys)")
    print("-" * 40)
    try:
        from hive_real.api_ai_hive import get_api_ai_vote
        
        start_time = time.time()
        api_result = get_api_ai_vote(symbol, direction, entry_price, market_data)
        api_time = time.time() - start_time
        
        print(f"   ⏱️  Response time: {api_time:.3f} seconds (would be 30-120s with real APIs)")
        print(f"   🎯 Decision: {api_result['vote']}")
        print(f"   📊 Confidence: {api_result['confidence']:.1%}")
        
        if 'votes' in api_result:
            print(f"   🧠 Individual AI votes:")
            for vote in api_result['votes']:
                print(f"       {vote['ai']} ({vote['agent']}): {vote['signal']} ({vote['confidence']:.1%})")
                print(f"         Reasoning: {vote['reasoning']}")
        
        print(f"   🔍 Analysis: Would use real ChatGPT/Claude APIs with proper keys")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print()
    
    # Test 3: Browser-based Real AI (Currently broken)
    print("3️⃣  BROWSER-BASED REAL AI (WSL incompatible)")
    print("-" * 40)
    try:
        from hive_real.real_ai_hive import get_real_ai_vote
        
        start_time = time.time()
        browser_result = get_real_ai_vote(symbol, direction, entry_price, market_data)
        browser_time = time.time() - start_time
        
        print(f"   ⏱️  Response time: {browser_time:.3f} seconds")
        print(f"   🎯 Decision: {browser_result['vote']}")
        print(f"   📊 Confidence: {browser_result['confidence']:.1%}")
        
        if 'votes' in browser_result:
            real_votes = [v for v in browser_result['votes'] if v['ai'] in ['ChatGPT']]
            fake_votes = [v for v in browser_result['votes'] if v['ai'] not in ['ChatGPT']]
            
            if real_votes:
                print(f"   ✅ REAL AI responses: {len(real_votes)}")
                for vote in real_votes:
                    print(f"       {vote['ai']}: {vote['reasoning'][:60]}...")
            else:
                print(f"   ❌ NO REAL AI responses")
                
            if fake_votes:
                print(f"   ⚠️  Placeholder responses: {len(fake_votes)}")
        
        print(f"   🔍 Analysis: Browser automation failed in WSL")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print()
    print("📋 COMPARISON SUMMARY:")
    print("=" * 60)
    print("✅ REAL AI INDICATORS:")
    print("   - 30-120 second response times")
    print("   - Detailed reasoning (100+ characters)")
    print("   - Individual AI votes with names")
    print("   - Complex analysis mentioning fundamentals/technicals")
    print("   - API keys or business account login required")
    print()
    print("❌ FAKE AI INDICATORS:")
    print("   - Instant responses (under 1 second)")
    print("   - Short reasoning (under 50 characters)")
    print("   - Generic mathematical explanations")
    print("   - No actual AI service connections")
    print("   - 'Simple HIVE' or 'WSL compatible' labels")
    print()
    print("🎯 CONCLUSION:")
    print("   The current system defaults to FAKE AI (Simple HIVE)")
    print("   To get REAL AI: Configure API keys or fix browser automation")
    print("   API-based approach is best for WSL environment")

if __name__ == "__main__":
    compare_hive_systems()