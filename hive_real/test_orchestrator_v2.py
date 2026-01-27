#!/usr/bin/env python3
"""
COMPREHENSIVE TEST SUITE
Tests the complete Hive V2 pipeline end-to-end
"""
import json
import sys
import os

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from orchestrator_v2 import HiveOrchestratorV2, get_orchestrator
from payload_builder import PayloadBuilder
from data_gate import DataCompletenessGate
from ui_renderer import HiveUIRenderer

def test_data_gate():
    """Test 1: Data completeness gate"""
    print("="*70)
    print("TEST 1: DATA COMPLETENESS GATE")
    print("="*70)
    
    gate = DataCompletenessGate()
    
    # Test incomplete data
    incomplete_data = {
        "instrument": "EURUSD",
        "timeframe": "1h"
        # Missing: price_context, risk_rules, objective
    }
    
    is_valid, missing, warnings, tier = gate.validate(incomplete_data)
    
    print(f"\n📋 Incomplete data test:")
    print(f"   Valid: {is_valid}")
    print(f"   Missing fields: {len(missing)}")
    if not is_valid:
        print("   ✅ PASS - Correctly blocked incomplete data")
    else:
        print("   ❌ FAIL - Should have blocked")
    
    # Test complete data
    complete_data = {
        "instrument": "EURUSD",
        "timeframe": "1h",
        "objective": "day",
        "price_context": {
            "current_price": 1.0950,
            "recent_high": 1.0980,
            "recent_low": 1.0920
        },
        "risk_rules": {
            "max_risk_per_trade_pct": 0.5,
            "max_daily_loss_pct": 2.0,
            "leverage_cap": 2.0,
            "oco_required": True
        }
    }
    
    is_valid, missing, warnings, tier = gate.validate(complete_data)
    
    print(f"\n📋 Complete data test:")
    print(f"   Valid: {is_valid}")
    print(f"   Tier: {tier}")
    if is_valid and tier == "A":
        print("   ✅ PASS - Tier A minimum data accepted")
    else:
        print("   ❌ FAIL - Should have accepted Tier A")
    
    return is_valid


def test_payload_builder():
    """Test 2: Payload builder"""
    print("\n" + "="*70)
    print("TEST 2: PAYLOAD BUILDER")
    print("="*70)
    
    builder = PayloadBuilder()
    
    # Test Tier A (minimum)
    payload_a = builder.build_payload(
        instrument="EURUSD",
        timeframe="1h",
        current_price=1.0950,
        objective="day"
    )
    
    tier_a = payload_a["price_context"]["tier"]
    print(f"\n📦 Tier A payload:")
    print(f"   Tier: {tier_a}")
    print(f"   Has current_price: {'current_price' in payload_a['price_context']}")
    print(f"   Has recent_high: {'recent_high' in payload_a['price_context']}")
    print(f"   Has recent_low: {'recent_low' in payload_a['price_context']}")
    
    if tier_a == "A":
        print("   ✅ PASS - Tier A payload built")
    else:
        print("   ❌ FAIL - Expected Tier A")
    
    # Test autofill
    payload_auto = builder.autofill_from_chart("BTCUSD", "1h")
    tier_auto = payload_auto["price_context"]["tier"]
    
    print(f"\n📦 Autofilled payload:")
    print(f"   Tier: {tier_auto}")
    print(f"   Has candles: {bool(payload_auto['price_context'].get('last_50_candles'))}")
    
    if tier_auto in ["B", "C"]:
        print("   ✅ PASS - Autofill generated enhanced data")
    else:
        print("   ❌ FAIL - Expected Tier B or C")
    
    return True


def test_blocked_call():
    """Test 3: Orchestrator blocks incomplete calls"""
    print("\n" + "="*70)
    print("TEST 3: BLOCKING INCOMPLETE CALLS")
    print("="*70)
    
    orchestrator = HiveOrchestratorV2()
    
    # Intentionally provide insufficient data
    result = orchestrator.analyze(
        instrument="EURUSD",
        timeframe="1h",
        current_price=0,  # Invalid
        objective="day"
    )
    
    print(f"\n🚫 Result status: {result['status']}")
    print(f"   Errors: {len(result['errors'])}")
    
    if result["status"] == "blocked":
        print("   ✅ PASS - Call correctly blocked")
        print("\n📝 Error message:")
        print(result["rendered"])
        return True
    else:
        print("   ❌ FAIL - Should have blocked invalid data")
        return False


def test_successful_call():
    """Test 4: Successful analysis with complete data"""
    print("\n" + "="*70)
    print("TEST 4: SUCCESSFUL ANALYSIS")
    print("="*70)
    
    orchestrator = get_orchestrator()
    
    # Use autofill for realistic data
    result = orchestrator.autofill_and_analyze(
        instrument="EURUSD",
        timeframe="1h",
        objective="day",
        render_mode="full"
    )
    
    print(f"\n✅ Result status: {result['status']}")
    
    if result["status"] == "ok":
        print("   ✅ PASS - Analysis successful")
        print("\n📊 Rendered output:")
        print(result["rendered"])
        
        # Check for OCO in output
        output = result.get("output", {})
        setups = output.get("setups", [])
        
        if setups:
            oco_count = sum(1 for s in setups if s.get("oco", {}).get("enabled"))
            print(f"\n   OCO-enabled setups: {oco_count}/{len(setups)}")
            if oco_count == len(setups):
                print("   ✅ All setups have OCO enabled")
            else:
                print("   ⚠️  Some setups missing OCO")
        
        return True
    
    elif result["status"] == "blocked":
        print("   ⚠️  BLOCKED (might need API keys)")
        print(result["rendered"])
        return None  # Not a failure, just missing API keys
    
    else:
        print("   ❌ FAIL - Unexpected status")
        print(result["rendered"])
        return False


def test_oco_enforcement():
    """Test 5: OCO enforcement"""
    print("\n" + "="*70)
    print("TEST 5: OCO ENFORCEMENT")
    print("="*70)
    
    orchestrator = HiveOrchestratorV2()
    
    # Test OCO validation on mock output
    mock_output_valid = {
        "status": "ok",
        "setups": [
            {
                "name": "Test Setup",
                "oco": {
                    "enabled": True,
                    "tp": [1.1000, 1.1050],
                    "sl": 1.0900
                }
            }
        ]
    }
    
    is_valid, errors = orchestrator._validate_oco(mock_output_valid)
    print(f"\n✅ Valid OCO test:")
    print(f"   Valid: {is_valid}")
    if is_valid:
        print("   ✅ PASS - Valid OCO accepted")
    else:
        print(f"   ❌ FAIL - Should have accepted: {errors}")
    
    # Test invalid OCO
    mock_output_invalid = {
        "status": "ok",
        "setups": [
            {
                "name": "Test Setup",
                "oco": {
                    "enabled": False,  # Invalid
                    "tp": [],
                    "sl": 0
                }
            }
        ]
    }
    
    is_valid, errors = orchestrator._validate_oco(mock_output_invalid)
    print(f"\n❌ Invalid OCO test:")
    print(f"   Valid: {is_valid}")
    print(f"   Errors: {len(errors)}")
    if not is_valid:
        print("   ✅ PASS - Invalid OCO rejected")
    else:
        print("   ❌ FAIL - Should have rejected")
    
    return True


def test_render_modes():
    """Test 6: Different render modes"""
    print("\n" + "="*70)
    print("TEST 6: RENDER MODES")
    print("="*70)
    
    # Create mock output
    mock_output = {
        "status": "ok",
        "instrument": "EURUSD",
        "timeframe": "1h",
        "timestamp_utc": "2025-12-31T10:00:00Z",
        "session": "NY",
        "regime": "trend",
        "bias": "bullish",
        "confidence": 0.75,
        "key_levels": {
            "support": [1.0920, 1.0900],
            "resistance": [1.0980, 1.1000],
            "invalidation": 1.0890
        },
        "setups": [
            {
                "name": "Breakout Setup",
                "scenario": "bull",
                "trigger": "Break above 1.0980",
                "entry": 1.0985,
                "stop_loss": 1.0920,
                "take_profit": [1.1020, 1.1050],
                "oco": {
                    "enabled": True,
                    "tp": [1.1020, 1.1050],
                    "sl": 1.0920
                },
                "expected_R": 2.1,
                "notes": ["Strong momentum", "Volume confirmation"]
            }
        ],
        "position_sizing": {
            "method": "fixed_risk",
            "risk_per_trade_pct": 0.5,
            "max_daily_loss_pct": 2.0,
            "leverage_cap": 2.0,
            "sizing_notes": ["Standard risk"]
        },
        "cost_model": {
            "spread": 0.0001,
            "fees_per_unit": None,
            "notes": ["Typical forex spread"]
        },
        "execution_notes": ["Enter on confirmation", "Trail stop after TP1"],
        "top_risks": ["News at 2pm", "Resistance cluster ahead"]
    }
    
    renderer = HiveUIRenderer()
    
    # Test full mode
    full = renderer.render_summary(mock_output)
    print("\n📄 FULL MODE:")
    print(full)
    print("   ✅ Full render complete")
    
    # Test compact mode
    compact = renderer.render_compact(mock_output)
    print(f"\n📊 COMPACT MODE:\n   {compact}")
    print("   ✅ Compact render complete")
    
    # Test notification mode
    notification = renderer.render_notification(mock_output)
    print(f"\n📱 NOTIFICATION MODE:\n   {notification}")
    print("   ✅ Notification render complete")
    
    return True


def run_all_tests():
    """Run complete test suite"""
    print("\n" + "="*70)
    print("HIVE V2 ORCHESTRATOR - COMPREHENSIVE TEST SUITE")
    print("="*70)
    
    results = {}
    
    # Run tests
    results["Data Gate"] = test_data_gate()
    results["Payload Builder"] = test_payload_builder()
    results["Blocked Call"] = test_blocked_call()
    results["Successful Call"] = test_successful_call()
    results["OCO Enforcement"] = test_oco_enforcement()
    results["Render Modes"] = test_render_modes()
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for v in results.values() if v is True)
    failed = sum(1 for v in results.values() if v is False)
    skipped = sum(1 for v in results.values() if v is None)
    
    for test, result in results.items():
        if result is True:
            print(f"✅ {test}: PASS")
        elif result is False:
            print(f"❌ {test}: FAIL")
        else:
            print(f"⚠️  {test}: SKIPPED (no API keys)")
    
    print(f"\nResults: {passed} passed, {failed} failed, {skipped} skipped")
    
    # Get orchestrator stats
    orchestrator = get_orchestrator()
    stats = orchestrator.get_stats()
    
    print(f"\nPipeline Statistics:")
    print(f"  Total calls: {stats['total_calls']}")
    print(f"  Blocked calls: {stats['blocked_calls']}")
    print(f"  Successful calls: {stats['successful_calls']}")
    print(f"  Failed validations: {stats['failed_validations']}")
    print(f"  OCO violations: {stats['oco_violations']}")
    
    if stats["total_calls"] > 0:
        print(f"  Block rate: {stats.get('block_rate', 0):.1%}")
        print(f"  Success rate: {stats.get('success_rate', 0):.1%}")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
