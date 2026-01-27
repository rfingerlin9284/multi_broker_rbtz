#!/usr/bin/env bash
# Deterministic exit/position status - prints JSON snapshot
# Shows active positions, ages, and next exit rule to fire
set -euo pipefail

REPO="${REPO:-/home/ing/RICK/MULTI_BROKER_PHOENIX}"
cd "$REPO"

# Load environment deterministically
source "${REPO}/tools/env_load.sh"

_ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }
_age() {
    local file="$1"
    if [[ -f "$file" ]]; then
        local mod
        mod=$(stat -c %Y "$file" 2>/dev/null || stat -f %m "$file" 2>/dev/null)
        local now
        now=$(date +%s)
        echo $((now - mod))
    else
        echo "null"
    fi
}

# Activate venv if present
if [[ -f "$REPO/.venv/bin/activate" ]]; then
    source "$REPO/.venv/bin/activate"
fi

echo "{"
echo '  "timestamp": "'$(_ts)'",'

# Check state file ages (heartbeat status)
EXIT_STATE="${HEARTBEAT_EXIT_STATE_FILE:-ops/state/exit_manager_state.json}"
PROTECT_STATE="${HEARTBEAT_PROTECT_STATE_FILE:-ops/state/protect_loop.json}"
WATCHDOG_STATE="${HEARTBEAT_WATCHDOG_STATE_FILE:-ops/state/watchdog.json}"
MAX_SKEW="${HEARTBEAT_MAX_SKEW_SEC:-180}"

EXIT_AGE=$(_age "$REPO/$EXIT_STATE")
PROTECT_AGE=$(_age "$REPO/$PROTECT_STATE")
WATCHDOG_AGE=$(_age "$REPO/$WATCHDOG_STATE")

echo '  "heartbeat": {'
echo "    \"exit_manager_age_sec\": $EXIT_AGE,"
echo "    \"protect_loop_age_sec\": $PROTECT_AGE,"
echo "    \"watchdog_age_sec\": $WATCHDOG_AGE,"
echo "    \"max_skew_sec\": $MAX_SKEW"
echo '  },'

# Check if state files exist and are fresh
STALE=()
[[ "$EXIT_AGE" == "null" || "$EXIT_AGE" -gt "$MAX_SKEW" ]] && STALE+=("exit_manager")
[[ "$PROTECT_AGE" == "null" || "$PROTECT_AGE" -gt "$MAX_SKEW" ]] && STALE+=("protect_loop")
[[ "$WATCHDOG_AGE" == "null" || "$WATCHDOG_AGE" -gt "$MAX_SKEW" ]] && STALE+=("watchdog")

if [[ ${#STALE[@]} -eq 0 ]]; then
    echo '  "heartbeat_ok": true,'
else
    echo '  "heartbeat_ok": false,'
    echo '  "stale_components": ["'$(IFS=','; echo "${STALE[*]}" | sed 's/,/","/g')'"],'
fi

# Run Python to get position details
python3 - <<'PY'
import json
import os
import sys
from pathlib import Path
from datetime import datetime

def _read_json(path):
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception:
        return None

exit_state = _read_json(os.getenv('HEARTBEAT_EXIT_STATE_FILE', 'ops/state/exit_manager_state.json'))
if exit_state:
    print('  "exit_manager_state": ' + json.dumps(exit_state, sort_keys=True) + ',')
else:
    print('  "exit_manager_state": null,')

# Try to get live positions from connector
positions = []
try:
    from execution.oanda_practice_client import OandaPracticeClient
    client = OandaPracticeClient()
    trades = client.list_open_trades().get('trades', [])
    now = datetime.utcnow()
    
    for t in trades:
        open_time_str = t.get('openTime', '')
        age_hours = None
        if open_time_str:
            try:
                ot = datetime.fromisoformat(open_time_str.split('.')[0].replace('Z', '+00:00'))
                age_sec = (now - ot.replace(tzinfo=None)).total_seconds()
                age_hours = round(age_sec / 3600, 2)
            except:
                pass
        
        positions.append({
            'id': t.get('id'),
            'instrument': t.get('instrument'),
            'units': t.get('currentUnits'),
            'unrealizedPL': t.get('unrealizedPL'),
            'age_hours': age_hours,
            'has_sl': bool(t.get('stopLossOrder')),
            'has_tp': bool(t.get('takeProfitOrder')),
        })
    
    print('  "open_positions": ' + json.dumps(positions, sort_keys=True) + ',')
    print(f'  "position_count": {len(positions)},')
    
    # Find positions at risk (no OCO or too old)
    at_risk = []
    max_hold = float(os.getenv('EXIT_MAX_HOLD_HOURS', '8'))
    for p in positions:
        issues = []
        if not p['has_sl']:
            issues.append('MISSING_SL')
        if not p['has_tp']:
            issues.append('MISSING_TP')
        if p['age_hours'] and p['age_hours'] >= max_hold:
            issues.append(f'TIME_STOP_OVERDUE')
        elif p['age_hours'] and p['age_hours'] >= max_hold * 0.75:
            issues.append(f'TIME_STOP_SOON')
        if issues:
            at_risk.append({'id': p['id'], 'instrument': p['instrument'], 'issues': issues, 'age_hours': p['age_hours']})
    
    if at_risk:
        print('  "positions_at_risk": ' + json.dumps(at_risk, sort_keys=True) + ',')
    
except Exception as e:
    print(f'  "open_positions_error": "{e}",')

print('  "max_hold_hours": ' + os.getenv('EXIT_MAX_HOLD_HOURS', '8'))
PY

echo "}"
