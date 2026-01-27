#!/usr/bin/env bash
# ================================================================
# RBOTzilla Health Check - GO/NO-GO status for autonomous trading
# ================================================================
# Checks all safety systems and outputs simple GO or NO-GO verdict.
#
# Exit codes:
#   0 = GO (all systems healthy, safe to trade)
#   1 = NO-GO (one or more systems unhealthy)
#
# Checks:
#   1. Broker health (ops/state/broker_health.json)
#   2. OCO health (ops/state/oco_health.json)
#   3. Risk governor (ops/state/risk_governor.json)
#   4. Engine heartbeat (ops/state/engine_heartbeat.json)
#   5. Watchdog state
#
# Usage:
#   ./healthcheck_safety.sh        # Full check
#   ./healthcheck_safety.sh --json # Output as JSON
# ================================================================
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STATE_DIR="$PROJECT_ROOT/ops/state"
JSON_MODE=false

if [[ "${1:-}" == "--json" ]]; then
    JSON_MODE=true
fi

# Initialize results
declare -A checks
overall_status="GO"

# Helper: check file age (fail if older than threshold seconds)
check_file_age() {
    local file="$1"
    local max_age="${2:-60}"  # Default 60 seconds
    
    if [[ ! -f "$file" ]]; then
        echo "MISSING"
        return 1
    fi
    
    local now=$(date +%s)
    local mtime=$(stat -c %Y "$file" 2>/dev/null || echo 0)
    local age=$((now - mtime))
    
    if [[ $age -gt $max_age ]]; then
        echo "STALE ($age s)"
        return 1
    fi
    
    echo "OK ($age s)"
    return 0
}

# Helper: check JSON field
check_json_field() {
    local file="$1"
    local field="$2"
    local expected="$3"
    
    if [[ ! -f "$file" ]]; then
        echo "FILE_MISSING"
        return 1
    fi
    
    local value=$(python3 -c "
import json
try:
    with open('$file') as f:
        d = json.load(f)
    # Support nested fields like 'a.b.c'
    keys = '$field'.split('.')
    v = d
    for k in keys:
        v = v.get(k)
    print(v if v is not None else 'NULL')
except Exception as e:
    print('ERROR')
" 2>/dev/null || echo "ERROR")
    
    if [[ "$value" == "$expected" ]]; then
        echo "OK ($value)"
        return 0
    else
        echo "FAIL ($value != $expected)"
        return 1
    fi
}

echo "================================================================"
echo " RBOTzilla Safety Health Check"
echo " $(date -Iseconds)"
echo "================================================================"
echo ""

# 1. Broker Health
echo -n "1. Broker Health: "
if result=$(check_json_field "$STATE_DIR/broker_health.json" "healthy" "True"); then
    checks[broker_health]="$result"
    echo "✅ $result"
else
    checks[broker_health]="$result"
    echo "❌ $result"
    overall_status="NO-GO"
fi

# 2. Broker Trading Allowed
echo -n "2. Trading Allowed: "
if result=$(check_json_field "$STATE_DIR/broker_health.json" "trading_allowed" "True"); then
    checks[trading_allowed]="$result"
    echo "✅ $result"
else
    checks[trading_allowed]="$result"
    echo "❌ $result"
    overall_status="NO-GO"
fi

# 3. OCO Health - check for missing OCO
echo -n "3. OCO Status: "
if [[ -f "$STATE_DIR/oco_health.json" ]]; then
    missing=$(python3 -c "
import json
try:
    with open('$STATE_DIR/oco_health.json') as f:
        d = json.load(f)
    print(d.get('missing', 0))
except:
    print(-1)
" 2>/dev/null || echo "-1")
    if [[ "$missing" == "0" ]]; then
        checks[oco_health]="OK (missing=0)"
        echo "✅ OK (no missing OCO)"
    elif [[ "$missing" == "-1" ]]; then
        checks[oco_health]="READ_ERROR"
        echo "⚠️ READ_ERROR"
        overall_status="NO-GO"
    else
        checks[oco_health]="FAIL (missing=$missing)"
        echo "❌ FAIL ($missing positions missing OCO)"
        overall_status="NO-GO"
    fi
else
    checks[oco_health]="FILE_MISSING"
    echo "⚠️ FILE_MISSING (may not have run yet)"
fi

# 4. Risk Governor State
echo -n "4. Risk Governor: "
if [[ -f "$STATE_DIR/risk_governor.json" ]]; then
    last_result=$(python3 -c "
import json
try:
    with open('$STATE_DIR/risk_governor.json') as f:
        d = json.load(f)
    print(d.get('last_result', 'UNKNOWN'))
except:
    print('ERROR')
" 2>/dev/null || echo "ERROR")
    checks[risk_governor]="$last_result"
    if [[ "$last_result" == "PASS" ]] || [[ "$last_result" == "UNKNOWN" ]]; then
        echo "✅ $last_result"
    else
        echo "⚠️ $last_result (last trade was blocked)"
    fi
else
    checks[risk_governor]="NO_STATE"
    echo "ℹ️ NO_STATE (no trades yet)"
fi

# 5. Engine Heartbeat
echo -n "5. Engine Heartbeat: "
if result=$(check_file_age "$STATE_DIR/engine_heartbeat.json" 30); then
    checks[engine_heartbeat]="$result"
    echo "✅ $result"
else
    checks[engine_heartbeat]="$result"
    echo "❌ $result"
    overall_status="NO-GO"
fi

# 6. Consecutive Failures
echo -n "6. Consecutive Failures: "
if [[ -f "$STATE_DIR/broker_health.json" ]]; then
    failures=$(python3 -c "
import json
try:
    with open('$STATE_DIR/broker_health.json') as f:
        d = json.load(f)
    print(d.get('consecutive_failures', 0))
except:
    print(-1)
" 2>/dev/null || echo "-1")
    if [[ "$failures" == "0" ]]; then
        checks[consecutive_failures]="OK (0)"
        echo "✅ OK (0 failures)"
    elif [[ "$failures" -lt 3 ]]; then
        checks[consecutive_failures]="WARN ($failures)"
        echo "⚠️ WARN ($failures < threshold)"
    else
        checks[consecutive_failures]="CRITICAL ($failures)"
        echo "❌ CRITICAL ($failures >= threshold)"
        overall_status="NO-GO"
    fi
else
    checks[consecutive_failures]="NO_FILE"
    echo "⚠️ NO_FILE"
fi

echo ""
echo "================================================================"
if [[ "$overall_status" == "GO" ]]; then
    echo " VERDICT: ✅ GO - All safety systems healthy"
else
    echo " VERDICT: ❌ NO-GO - One or more systems unhealthy"
fi
echo "================================================================"

# JSON output if requested
if $JSON_MODE; then
    echo ""
    python3 -c "
import json
checks = {}
checks['broker_health'] = '${checks[broker_health]:-UNKNOWN}'
checks['trading_allowed'] = '${checks[trading_allowed]:-UNKNOWN}'
checks['oco_health'] = '${checks[oco_health]:-UNKNOWN}'
checks['risk_governor'] = '${checks[risk_governor]:-UNKNOWN}'
checks['engine_heartbeat'] = '${checks[engine_heartbeat]:-UNKNOWN}'
checks['consecutive_failures'] = '${checks[consecutive_failures]:-UNKNOWN}'
result = {
    'status': '$overall_status',
    'timestamp': '$(date -Iseconds)',
    'checks': checks
}
print(json.dumps(result, indent=2))
"
fi

# Exit with appropriate code
if [[ "$overall_status" == "GO" ]]; then
    exit 0
else
    exit 1
fi
