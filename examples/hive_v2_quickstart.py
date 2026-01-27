#!/usr/bin/env python3
"""
HIVE V2 QUICK START DEMO
Shows the complete pipeline in action
"""
import sys
import os

# Add to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'hive_real'))

from orchestrator_v2 import get_orchestrator

def demo_1_basic():
    """Demo 1: Basic usage with autofill"""
    print("="*70)
    print("DEMO 1: BASIC USAGE WITH AUTOFILL")
    print("="*70)
    print()
    
    orchestrator = get_orchestrator()
    
    result = orchestrator.autofill_and_analyze(
        instrument="EURUSD",
        timeframe="1h",
        objective="day",
        render_mode="full"
    )
    
    print(result["rendered"])
    print()
    print(f"Status: {result['status']}")
    print(f"Errors: {len(result['errors'])}")


def demo_2_manual_data():
    """Demo 2: Manual data entry"""
    print("\n" + "="*70)
    print("DEMO 2: MANUAL DATA ENTRY")
    print("="*70)
    print()
    
    orchestrator = get_orchestrator()
    
    # Simulate getting data from your chart/feed
    current_price = 1.0950
    recent_closes = [1.0920 + i*0.0002 for i in range(20)]
    
    result = orchestrator.analyze(
        instrument="EURUSD",
        timeframe="1h",
        current_price=current_price,
        prices=recent_closes,
        recent_high=max(recent_closes),
        recent_low=min(recent_closes),
        objective="day",
        risk_rules={
            "max_risk_per_trade_pct": 0.5,
            "max_daily_loss_pct": 2.0,
            "leverage_cap": 2.0,
            "oco_required": True
        },
        render_mode="compact"
    )
    
    print(result["rendered"])


def demo_3_blocked_call():
    """Demo 3: Showing data gate blocking incomplete calls"""
    print("\n" + "="*70)
    print("DEMO 3: DATA COMPLETENESS GATE (BLOCKING)")
    print("="*70)
    print()
    
    orchestrator = get_orchestrator()
    
    # Intentionally provide incomplete data
    result = orchestrator.analyze(
        instrument="BTCUSD",
        timeframe="1h",
        current_price=0,  # Invalid
        objective="scalp"
    )
    
    print(result["rendered"])
    print()
    print(f"Call Status: {result['status']}")
    if result['status'] == 'blocked':
        print("✅ System correctly blocked incomplete data!")


def demo_4_different_objectives():
    """Demo 4: Different trading objectives"""
    print("\n" + "="*70)
    print("DEMO 4: DIFFERENT OBJECTIVES (SCALP vs SWING)")
    print("="*70)
    
    orchestrator = get_orchestrator()
    
    for objective in ["scalp", "swing"]:
        print(f"\n--- {objective.upper()} TRADING ---")
        result = orchestrator.autofill_and_analyze(
            instrument="BTCUSD",
            timeframe="5m" if objective == "scalp" else "4h",
            objective=objective,
            render_mode="compact"
        )
        print(result["rendered"])


def demo_5_statistics():
    """Demo 5: Pipeline statistics"""
    print("\n" + "="*70)
    print("DEMO 5: PIPELINE STATISTICS")
    print("="*70)
    print()
    
    orchestrator = get_orchestrator()
    stats = orchestrator.get_stats()
    
    print("Pipeline Performance:")
    print(f"  Total calls: {stats['total_calls']}")
    print(f"  Blocked calls: {stats['blocked_calls']}")
    print(f"  Successful calls: {stats['successful_calls']}")
    print(f"  Failed validations: {stats['failed_validations']}")
    print(f"  OCO violations: {stats['oco_violations']}")
    
    if stats["total_calls"] > 0:
        print(f"\n  Block rate: {stats.get('block_rate', 0)*100:.1f}%")
        print(f"  Success rate: {stats.get('success_rate', 0)*100:.1f}%")
    
    print("\nKey Insight:")
    print("  Block rate should be ~0% with autofill")
    print("  OCO violations should always be 0 (enforced)")


def main():
    """Run all demos"""
    print("\n" + "="*70)
    print("HIVE V2 ORCHESTRATOR - QUICK START DEMOS")
    print("="*70)
    print()
    print("This demonstrates the complete pipeline:")
    print("  1. Data gate blocks incomplete calls")
    print("  2. Payload builder creates comprehensive context")
    print("  3. AI agents receive proper data")
    print("  4. OCO enforcement validates outputs")
    print("  5. UI renderer creates human-readable results")
    print()
    input("Press ENTER to start demos...")
    
    try:
        demo_1_basic()
        input("\nPress ENTER for next demo...")
        
        demo_2_manual_data()
        input("\nPress ENTER for next demo...")
        
        demo_3_blocked_call()
        input("\nPress ENTER for next demo...")
        
        demo_4_different_objectives()
        input("\nPress ENTER for final demo...")
        
        demo_5_statistics()
        
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
    except Exception as e:
        print(f"\n\nDemo error: {e}")
    
    print("\n" + "="*70)
    print("DEMOS COMPLETE")
    print("="*70)
    print()
    print("Next steps:")
    print("  1. Connect to your live price feeds")
    print("  2. Integrate with your UI/browser")
    print("  3. Load risk rules from settings")
    print("  4. Start with paper trading")
    print()


if __name__ == "__main__":
    main()
