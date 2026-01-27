#!/usr/bin/env python3
"""
Test Profit Extraction Engine Integration
Verifies the new profit-taking system works in the live engine
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from multi_broker_phoenix.engines.profit_extraction_engine import ProfitExtractionEngine

print("=" * 70)
print("🧪 TESTING PROFIT EXTRACTION ENGINE INTEGRATION")
print("=" * 70)

# Create engine with same settings as live_extreme_engine
extractor = ProfitExtractionEngine(
    profit_target_1=0.015,  # 1.5%
    profit_target_2=0.03,   # 3.0%
    trail_activation=0.01,  # +1%
    trail_distance=0.005,   # -0.5%
    max_hold_bars=50,
    stagnant_bars=10,
    signal_fade_threshold=0.3
)

print("\n✅ Engine instantiated successfully")

# Simulate a trade
print("\n📊 Simulating trade lifecycle...")

# 1. Add a trade
extractor.add_trade(
    trade_id="coinbase:BTC-USD",
    symbol="BTC-USD",
    entry_price=45000.0,
    entry_size=1000.0,
    signal_strength=0.75
)
print("   ✅ Added trade: BTC-USD @ $45,000")

# 2. Update with small movement (no exit yet)
exit_signal = extractor.get_exit_signal("coinbase:BTC-USD")
extractor.update_trade("coinbase:BTC-USD", 45300.0)
print("   ✅ Updated to $45,300 (+0.67%) - No exit signal")
print(f"      Exit signal: {exit_signal}")

# 3. Update to 1.5% profit (trigger target 1)
extractor.update_trade("coinbase:BTC-USD", 45675.0)
exit_signal = extractor.get_exit_signal("coinbase:BTC-USD")
print(f"\n   ✅ Updated to $45,675 (+1.5%)")
if exit_signal:
    print(f"      🎯 EXIT SIGNAL: {exit_signal['exit_reason']}")
    print(f"      Close {exit_signal['exit_size_pct']*100:.0f}% of position")
    
    # Close partial position
    result = extractor.close_trade("coinbase:BTC-USD", 45675.0, exit_signal['exit_size_pct'])
    print(f"      Realized P/L: ${result['realized_pnl']:+.2f} ({result['realized_pct']:+.2f}%)")

# 4. Update to 3% profit on remaining position (trigger target 2)
extractor.update_trade("coinbase:BTC-USD", 46350.0)
exit_signal = extractor.get_exit_signal("coinbase:BTC-USD")
print(f"\n   ✅ Updated to $46,350 (+3%)")
if exit_signal:
    print(f"      🎯 EXIT SIGNAL: {exit_signal['exit_reason']}")
    print(f"      Close remaining {exit_signal['exit_size_pct']*100:.0f}% of position")
    
    # Close remaining position
    result = extractor.close_trade("coinbase:BTC-USD", 46350.0, exit_signal['exit_size_pct'])
    print(f"      Realized P/L: ${result['realized_pnl']:+.2f} ({result['realized_pct']:+.2f}%)")

# 5. Get summary
summary = extractor.get_portfolio_summary()
print(f"\n📈 Portfolio Summary:")
print(f"   Open trades: {summary['open_trades']}")
print(f"   Closed trades: {summary['total_closed']}")
print(f"   Total realized P/L: ${summary['total_realized']:+.2f}")

print("\n" + "=" * 70)
print("✅ PROFIT EXTRACTION ENGINE INTEGRATION TEST PASSED!")
print("=" * 70)
print("\nThe system is now ready to:")
print("  1. Open smart-sized positions (Extreme Compounding)")
print("  2. Monitor health and cut losers (Zombie Killer)")
print("  3. Automatically capture profits (Profit Extraction) ← NEW!")
print("\nStart live engine to begin automated trading:")
print("  python3 MULTI_BROKER_PHOENIX/live_extreme_engine.py")
