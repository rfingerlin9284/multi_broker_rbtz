#!/usr/bin/env python3
"""Verify Prime Session Recover report JSON schema.

Tests that the report file has all required keys and valid types.
Does NOT test runtime behavior - only validates JSON structure.
"""
import json
import sys
from pathlib import Path


def test_report_schema():
    """Validate ops/state/prime_session_recover.json schema if it exists."""
    repo_root = Path(__file__).parent.parent.parent
    report_path = repo_root / "ops" / "state" / "prime_session_recover.json"
    
    if not report_path.exists():
        print(f"⚠️  Report file does not exist yet: {report_path}")
        print("   (This is OK if prime_session_recover.sh hasn't been run)")
        return True
    
    try:
        with open(report_path, 'r') as f:
            report = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in {report_path}: {e}")
        return False
    except Exception as e:
        print(f"❌ Failed to read {report_path}: {e}")
        return False
    
    # Required top-level keys
    required_keys = {
        'timestamp': str,
        'repo': str,
        'mode': str,
        'pid': int,
        'log_file': str,
        'proof_of_life': dict,
        'guard_locked': bool,
        'verdict': str,
    }
    
    missing = []
    wrong_type = []
    
    for key, expected_type in required_keys.items():
        if key not in report:
            missing.append(key)
        elif not isinstance(report[key], expected_type):
            wrong_type.append(f"{key} (expected {expected_type.__name__}, got {type(report[key]).__name__})")
    
    if missing:
        print(f"❌ Missing required keys: {', '.join(missing)}")
        return False
    
    if wrong_type:
        print(f"❌ Wrong types: {', '.join(wrong_type)}")
        return False
    
    # Validate proof_of_life sub-structure
    pol = report['proof_of_life']
    required_pol_keys = {'EXIT_MANAGER_TICK', 'PROTECT_LOOP_TICK'}
    
    missing_pol = required_pol_keys - set(pol.keys())
    if missing_pol:
        print(f"❌ Missing proof_of_life keys: {', '.join(missing_pol)}")
        return False
    
    for key in required_pol_keys:
        if not isinstance(pol[key], bool):
            print(f"❌ proof_of_life.{key} must be bool, got {type(pol[key]).__name__}")
            return False
    
    # Validate verdict is one of expected values
    if report['verdict'] not in ('PASS', 'FAIL'):
        print(f"❌ verdict must be 'PASS' or 'FAIL', got: {report['verdict']}")
        return False
    
    print(f"✅ Report schema valid: {report_path}")
    print(f"   timestamp: {report['timestamp']}")
    print(f"   mode: {report['mode']}")
    print(f"   pid: {report['pid']}")
    print(f"   verdict: {report['verdict']}")
    print(f"   EXIT_MANAGER_TICK: {'✅' if pol['EXIT_MANAGER_TICK'] else '❌'}")
    print(f"   PROTECT_LOOP_TICK: {'✅' if pol['PROTECT_LOOP_TICK'] else '❌'}")
    print(f"   guard_locked: {'🔒' if report['guard_locked'] else '🔓'}")
    
    return True


if __name__ == '__main__':
    success = test_report_schema()
    sys.exit(0 if success else 1)
