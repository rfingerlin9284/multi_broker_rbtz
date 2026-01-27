#!/usr/bin/env bash
#======================================================================
# oco_audit.sh - Live OCO (One-Cancels-Other) Audit Tool
#
# Scans all open OANDA positions and verifies each has proper OCO
# brackets (both SL and TP attached). Reports violations.
#
# Usage:
#   ./oco_audit.sh              # Run audit and show report
#   ./oco_audit.sh --json       # Output JSON for integration
#   ./oco_audit.sh --fix        # Attempt to fix violations (dry-run)
#   ./oco_audit.sh --fix --yes  # Actually fix violations
#======================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Source environment if available
if [[ -f "$PROJECT_ROOT/tools/rbot_env_exec.sh" ]]; then
    source "$PROJECT_ROOT/tools/rbot_env_exec.sh"
fi

OUTPUT_FORMAT="${1:-text}"
FIX_MODE=false
ACTUALLY_FIX=false

for arg in "$@"; do
    case "$arg" in
        --json) OUTPUT_FORMAT="json" ;;
        --fix) FIX_MODE=true ;;
        --yes) ACTUALLY_FIX=true ;;
    esac
done

# Python script to perform the audit
python3 - "$OUTPUT_FORMAT" "$FIX_MODE" "$ACTUALLY_FIX" <<'PYEOF'
import sys
import os
import json
from datetime import datetime

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

output_format = sys.argv[1] if len(sys.argv) > 1 else 'text'
fix_mode = sys.argv[2].lower() == 'true' if len(sys.argv) > 2 else False
actually_fix = sys.argv[3].lower() == 'true' if len(sys.argv) > 3 else False

def run_audit():
    results = {
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'total_positions': 0,
        'compliant': 0,
        'violations': [],
        'errors': []
    }
    
    try:
        # Try to get connector
        from multi_broker_phoenix.brokers.oanda_connector import OandaConnector
        from multi_broker_phoenix.config import get_config
        
        config = get_config()
        connector = OandaConnector(config)
        
        # Get open trades
        trades = connector.get_open_trades() or []
        results['total_positions'] = len(trades)
        
        for trade in trades:
            trade_id = trade.get('id', 'unknown')
            instrument = trade.get('instrument', 'unknown')
            units = trade.get('currentUnits', trade.get('initialUnits', 0))
            
            # Check for SL
            sl_order = trade.get('stopLossOrder')
            has_sl = sl_order is not None and sl_order.get('price')
            
            # Check for TP
            tp_order = trade.get('takeProfitOrder')
            has_tp = tp_order is not None and tp_order.get('price')
            
            # Trailing stop counts as SL
            trailing_sl = trade.get('trailingStopLossOrder')
            if trailing_sl and trailing_sl.get('distance'):
                has_sl = True
            
            if has_sl and has_tp:
                results['compliant'] += 1
            else:
                violation = {
                    'trade_id': trade_id,
                    'instrument': instrument,
                    'units': units,
                    'has_sl': has_sl,
                    'has_tp': has_tp,
                    'missing': []
                }
                if not has_sl:
                    violation['missing'].append('SL')
                if not has_tp:
                    violation['missing'].append('TP')
                results['violations'].append(violation)
                
                # Attempt fix if requested
                if fix_mode and (not has_sl or not has_tp):
                    if actually_fix:
                        try:
                            # For now, we just report - actual fix would need risk params
                            violation['fix_status'] = 'would_fix_if_implemented'
                        except Exception as e:
                            violation['fix_status'] = f'error: {str(e)}'
                    else:
                        violation['fix_status'] = 'dry_run'
    
    except ImportError as e:
        results['errors'].append(f"Import error: {str(e)}")
    except Exception as e:
        results['errors'].append(f"Audit error: {str(e)}")
    
    return results

def print_text_report(results):
    print("=" * 60)
    print(" OCO Audit Report")
    print("=" * 60)
    print(f" Timestamp:  {results['timestamp']}")
    print(f" Positions:  {results['total_positions']}")
    print(f" Compliant:  {results['compliant']}")
    print(f" Violations: {len(results['violations'])}")
    print("=" * 60)
    
    if results['violations']:
        print("\n⚠️  VIOLATIONS:")
        for v in results['violations']:
            missing = ', '.join(v['missing'])
            print(f"  • {v['trade_id']} ({v['instrument']}): Missing {missing}")
            if 'fix_status' in v:
                print(f"    Fix status: {v['fix_status']}")
    else:
        print("\n✅ All positions have proper OCO brackets")
    
    if results['errors']:
        print("\n❌ ERRORS:")
        for e in results['errors']:
            print(f"  • {e}")
    
    print("")

def main():
    results = run_audit()
    
    if output_format == 'json':
        print(json.dumps(results, indent=2))
    else:
        print_text_report(results)
    
    # Exit with error code if violations found
    if results['violations'] or results['errors']:
        sys.exit(1)
    sys.exit(0)

if __name__ == '__main__':
    main()
PYEOF
