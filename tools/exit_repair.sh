#!/usr/bin/env bash
#======================================================================
# exit_repair.sh - Fix wrong-scale exit orders on open positions
#
# Identifies and repairs TP/SL orders that have incorrect pip scaling
# (e.g., 100× off due to misunderstanding pip size).
#
# Usage:
#   ./exit_repair.sh              # Scan and report issues
#   ./exit_repair.sh --fix        # Actually repair issues
#   ./exit_repair.sh --json       # JSON output for integration
#======================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Source environment if available
if [[ -f "$PROJECT_ROOT/tools/rbot_env_exec.sh" ]]; then
    source "$PROJECT_ROOT/tools/rbot_env_exec.sh"
fi

OUTPUT_FORMAT="text"
FIX_MODE=false

for arg in "$@"; do
    case "$arg" in
        --json) OUTPUT_FORMAT="json" ;;
        --fix) FIX_MODE=true ;;
    esac
done

# Python script to perform the scan and repair
python3 - "$OUTPUT_FORMAT" "$FIX_MODE" <<'PYEOF'
import sys
import os
import json
from datetime import datetime

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

output_format = sys.argv[1] if len(sys.argv) > 1 else 'text'
fix_mode = sys.argv[2].lower() == 'true' if len(sys.argv) > 2 else False

def pip_size(pair):
    """Return pip size for a currency pair."""
    pair_upper = pair.upper().replace('-', '_').replace('/', '_')
    if pair_upper.endswith('JPY') or '_JPY' in pair_upper:
        return 0.01
    return 0.0001

def analyze_exit_scale(entry, sl, tp, pair, side):
    """Analyze if SL/TP are at reasonable distances.
    
    Returns:
        dict with 'sl_pips', 'tp_pips', 'sl_issue', 'tp_issue'
    """
    pip = pip_size(pair)
    
    result = {
        'sl_pips': 0,
        'tp_pips': 0,
        'sl_issue': None,
        'tp_issue': None,
        'reasonable': True
    }
    
    if sl and entry:
        sl_dist = abs(float(sl) - float(entry))
        result['sl_pips'] = sl_dist / pip
        
        # Flag if SL is unreasonably small (<1 pip) or large (>500 pips)
        if result['sl_pips'] < 1:
            result['sl_issue'] = 'too_tight'
            result['reasonable'] = False
        elif result['sl_pips'] > 500:
            result['sl_issue'] = 'too_wide'
            result['reasonable'] = False
        
        # Check if SL is on wrong side of entry
        if side == 'long' and float(sl) > float(entry):
            result['sl_issue'] = 'wrong_side'
            result['reasonable'] = False
        elif side == 'short' and float(sl) < float(entry):
            result['sl_issue'] = 'wrong_side'
            result['reasonable'] = False
    
    if tp and entry:
        tp_dist = abs(float(tp) - float(entry))
        result['tp_pips'] = tp_dist / pip
        
        # Flag if TP is unreasonably small (<1 pip) or large (>1000 pips)
        if result['tp_pips'] < 1:
            result['tp_issue'] = 'too_tight'
            result['reasonable'] = False
        elif result['tp_pips'] > 1000:
            result['tp_issue'] = 'too_wide'
            result['reasonable'] = False
        
        # Check if TP is on wrong side of entry
        if side == 'long' and float(tp) < float(entry):
            result['tp_issue'] = 'wrong_side'
            result['reasonable'] = False
        elif side == 'short' and float(tp) > float(entry):
            result['tp_issue'] = 'wrong_side'
            result['reasonable'] = False
    
    return result

def run_repair():
    results = {
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'total_positions': 0,
        'ok': 0,
        'issues': [],
        'repairs': [],
        'errors': []
    }
    
    try:
        from multi_broker_phoenix.brokers.oanda_connector import OandaConnector
        from multi_broker_phoenix.config import get_config
        
        config = get_config()
        connector = OandaConnector(config)
        
        trades = connector.get_open_trades() or []
        results['total_positions'] = len(trades)
        
        for trade in trades:
            trade_id = trade.get('id', 'unknown')
            instrument = trade.get('instrument', 'unknown')
            units = float(trade.get('currentUnits', trade.get('initialUnits', 0)))
            entry = float(trade.get('price', trade.get('averagePrice', 0)))
            side = 'long' if units > 0 else 'short'
            
            # Get SL/TP prices
            sl_order = trade.get('stopLossOrder', {})
            tp_order = trade.get('takeProfitOrder', {})
            sl_price = sl_order.get('price') if sl_order else None
            tp_price = tp_order.get('price') if tp_order else None
            
            # Analyze
            analysis = analyze_exit_scale(entry, sl_price, tp_price, instrument, side)
            
            if analysis['reasonable']:
                results['ok'] += 1
            else:
                issue = {
                    'trade_id': trade_id,
                    'instrument': instrument,
                    'side': side,
                    'entry': entry,
                    'sl_price': sl_price,
                    'tp_price': tp_price,
                    'sl_pips': round(analysis['sl_pips'], 1),
                    'tp_pips': round(analysis['tp_pips'], 1),
                    'sl_issue': analysis['sl_issue'],
                    'tp_issue': analysis['tp_issue']
                }
                results['issues'].append(issue)
                
                if fix_mode:
                    # Attempt repair
                    repair_result = repair_position(connector, trade, analysis)
                    issue['repair'] = repair_result
                    if repair_result.get('success'):
                        results['repairs'].append(trade_id)
    
    except ImportError as e:
        results['errors'].append(f"Import error: {str(e)}")
    except Exception as e:
        results['errors'].append(f"Repair error: {str(e)}")
    
    return results

def repair_position(connector, trade, analysis):
    """Attempt to repair a position with exit issues.
    
    Strategy:
    - If SL/TP are 100× off, adjust by factor of 100
    - If on wrong side, flip direction
    """
    result = {'success': False, 'action': 'none', 'message': ''}
    
    try:
        trade_id = trade.get('id')
        instrument = trade.get('instrument')
        entry = float(trade.get('price', trade.get('averagePrice', 0)))
        units = float(trade.get('currentUnits', 0))
        side = 'long' if units > 0 else 'short'
        pip = pip_size(instrument)
        
        sl_order = trade.get('stopLossOrder', {})
        tp_order = trade.get('takeProfitOrder', {})
        sl_price = float(sl_order.get('price', 0)) if sl_order else 0
        tp_price = float(tp_order.get('price', 0)) if tp_order else 0
        
        new_sl = None
        new_tp = None
        
        # Determine correct SL/TP
        if analysis['sl_issue'] == 'too_wide' and analysis['sl_pips'] > 100:
            # Likely 100× scale error - reduce distance by 100
            sl_dist = abs(sl_price - entry)
            correct_dist = sl_dist / 100
            if side == 'long':
                new_sl = entry - correct_dist
            else:
                new_sl = entry + correct_dist
            result['action'] = 'scale_correction'
        
        if analysis['sl_issue'] == 'wrong_side':
            # Flip to correct side with default 30 pip SL
            default_sl_pips = 30
            if side == 'long':
                new_sl = entry - (default_sl_pips * pip)
            else:
                new_sl = entry + (default_sl_pips * pip)
            result['action'] = 'side_correction'
        
        if analysis['tp_issue'] == 'too_wide' and analysis['tp_pips'] > 100:
            tp_dist = abs(tp_price - entry)
            correct_dist = tp_dist / 100
            if side == 'long':
                new_tp = entry + correct_dist
            else:
                new_tp = entry - correct_dist
        
        if analysis['tp_issue'] == 'wrong_side':
            default_tp_pips = 50
            if side == 'long':
                new_tp = entry + (default_tp_pips * pip)
            else:
                new_tp = entry - (default_tp_pips * pip)
        
        # Apply corrections
        modifications = {}
        if new_sl:
            modifications['stopLoss'] = {'price': str(round(new_sl, 5))}
        if new_tp:
            modifications['takeProfit'] = {'price': str(round(new_tp, 5))}
        
        if modifications:
            if hasattr(connector, 'modify_trade'):
                connector.modify_trade(trade_id, **modifications)
                result['success'] = True
                result['message'] = f"Applied: {list(modifications.keys())}"
                result['new_sl'] = new_sl
                result['new_tp'] = new_tp
            else:
                result['message'] = 'No modify_trade method on connector'
        else:
            result['message'] = 'No automatic fix available'
    
    except Exception as e:
        result['message'] = str(e)
    
    return result

def print_text_report(results):
    print("=" * 60)
    print(" Exit Order Repair Report")
    print("=" * 60)
    print(f" Timestamp:  {results['timestamp']}")
    print(f" Positions:  {results['total_positions']}")
    print(f" OK:         {results['ok']}")
    print(f" Issues:     {len(results['issues'])}")
    print(f" Repaired:   {len(results['repairs'])}")
    print("=" * 60)
    
    if results['issues']:
        print("\n⚠️  EXIT ISSUES:")
        for issue in results['issues']:
            print(f"\n  Trade: {issue['trade_id']} ({issue['instrument']} {issue['side']})")
            print(f"    Entry: {issue['entry']}")
            if issue['sl_price']:
                print(f"    SL: {issue['sl_price']} ({issue['sl_pips']} pips) {issue['sl_issue'] or ''}")
            if issue['tp_price']:
                print(f"    TP: {issue['tp_price']} ({issue['tp_pips']} pips) {issue['tp_issue'] or ''}")
            if 'repair' in issue:
                r = issue['repair']
                status = '✅' if r.get('success') else '❌'
                print(f"    Repair: {status} {r.get('action', '')} - {r.get('message', '')}")
    else:
        print("\n✅ All exit orders appear correctly scaled")
    
    if results['errors']:
        print("\n❌ ERRORS:")
        for e in results['errors']:
            print(f"  • {e}")
    
    print("")

def main():
    results = run_repair()
    
    if output_format == 'json':
        print(json.dumps(results, indent=2))
    else:
        print_text_report(results)
    
    # Exit with error if issues found and not all repaired
    if results['issues'] and len(results['repairs']) < len(results['issues']):
        sys.exit(1)
    sys.exit(0)

if __name__ == '__main__':
    main()
PYEOF
