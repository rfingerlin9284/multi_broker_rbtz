#!/usr/bin/env bash
# ================================================================
# Confirm Hive Status - Verify AI agents are responding
# ================================================================
# Checks all configured HIVE AI seats (Grok, DeepSeek, OpenAI)
# and reports their health status.
#
# Exit codes:
#   0 = All configured seats healthy
#   1 = One or more seats unhealthy
# ================================================================
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

# Load environment deterministically
source "${PROJECT_ROOT}/tools/env_load.sh"

# Legacy .env loading removed - env_load handles this
    set +a
fi

echo "================================================================"
echo " RBOTzilla: HIVE Status Check"
echo "================================================================"
echo ""

FAILURES=0

get_endpoint() {
    local seat="$1"
    python3 - <<PY
import json
import os
seat = "$seat"
path = os.getenv('HIVE_ENDPOINTS_FILE', '/home/ing/RICK/MULTI_BROKER_PHOENIX/config/hive_endpoints.json')
try:
    data = json.load(open(path))
except Exception:
    data = {}
cfg = data.get(seat, {}) or {}
base = cfg.get('base_url', '')
health = cfg.get('health_path', '')
base = (base or '').rstrip('/')
if health and not health.startswith('/'):
    health = '/' + health
print(base + health)
PY
}

# Check Grok/xAI
if [[ -n "${XAI_API_KEY:-}" ]]; then
    echo -n "Grok/xAI: "
    GROK_URL="${GROK_HEALTH_URL:-}"
    if [[ -z "$GROK_URL" ]]; then
        GROK_URL="$(get_endpoint xai)"
    fi
    RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -m 10 \
        -H "Authorization: Bearer $XAI_API_KEY" \
        "$GROK_URL" 2>/dev/null || echo "000")
    if [[ "$RESPONSE" == "200" ]]; then
        echo "✅ OK"
    elif [[ "$RESPONSE" == "401" ]] || [[ "$RESPONSE" == "403" ]]; then
        echo "❌ AUTH FAIL (HTTP $RESPONSE)"
        FAILURES=$((FAILURES + 1))
    else
        echo "❌ UNREACHABLE (HTTP $RESPONSE)"
        FAILURES=$((FAILURES + 1))
    fi
else
    echo "Grok/xAI: ⚪ Not configured (no XAI_API_KEY)"
fi

# Check DeepSeek
if [[ -n "${DEEPSEEK_API_KEY:-}" ]]; then
    echo -n "DeepSeek: "
    DEEPSEEK_URL="${DEEPSEEK_HEALTH_URL:-}"
    if [[ -z "$DEEPSEEK_URL" ]]; then
        DEEPSEEK_URL="$(get_endpoint deepseek)"
    fi
    RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -m 10 \
        -H "Authorization: Bearer $DEEPSEEK_API_KEY" \
        "$DEEPSEEK_URL" 2>/dev/null || echo "000")
    if [[ "$RESPONSE" == "200" ]]; then
        echo "✅ OK"
    elif [[ "$RESPONSE" == "401" ]] || [[ "$RESPONSE" == "403" ]]; then
        echo "❌ AUTH FAIL (HTTP $RESPONSE)"
        FAILURES=$((FAILURES + 1))
    else
        echo "❌ UNREACHABLE (HTTP $RESPONSE)"
        FAILURES=$((FAILURES + 1))
    fi
else
    echo "DeepSeek: ⚪ Not configured (no DEEPSEEK_API_KEY)"
fi

# Check OpenAI
if [[ -n "${OPENAI_API_KEY:-}" ]]; then
    echo -n "OpenAI:   "
    OPENAI_URL="${OPENAI_HEALTH_URL:-}"
    if [[ -z "$OPENAI_URL" ]]; then
        OPENAI_URL="$(get_endpoint openai)"
    fi
    RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -m 10 \
        -H "Authorization: Bearer $OPENAI_API_KEY" \
        "$OPENAI_URL" 2>/dev/null || echo "000")
    if [[ "$RESPONSE" == "200" ]]; then
        echo "✅ OK"
    elif [[ "$RESPONSE" == "401" ]] || [[ "$RESPONSE" == "403" ]]; then
        echo "❌ AUTH FAIL (HTTP $RESPONSE)"
        FAILURES=$((FAILURES + 1))
    else
        echo "❌ UNREACHABLE (HTTP $RESPONSE)"
        FAILURES=$((FAILURES + 1))
    fi
else
    echo "OpenAI:   ⚪ Not configured (no OPENAI_API_KEY)"
fi

# Check Ollama (local brain seat)
OLLAMA_URL="${OLLAMA_URL:-http://127.0.0.1:11434}"
OLLAMA_MODEL="${OLLAMA_MODEL:-llama3.1:8b}"
echo -n "Ollama:   "
OLLAMA_STATUS=$(curl -s -o /tmp/ollama_tags.$$ -w "%{http_code}" -m 5 \
    "$OLLAMA_URL/api/tags" 2>/dev/null || echo "000")
if [[ "$OLLAMA_STATUS" == "200" ]]; then
    if python3 - <<PY
import json
import sys
path = '/tmp/ollama_tags.$$'
model = '$OLLAMA_MODEL'
try:
    data = json.load(open(path))
    names = [m.get('name') for m in data.get('models', []) if isinstance(m, dict)]
    sys.exit(0 if model in names else 1)
except Exception:
    sys.exit(1)
PY
    then
        echo "✅ OK"
    else
        echo "❌ MODEL MISSING ($OLLAMA_MODEL)"
        FAILURES=$((FAILURES + 1))
    fi
else
    echo "❌ UNREACHABLE (HTTP $OLLAMA_STATUS)"
    FAILURES=$((FAILURES + 1))
fi
rm -f /tmp/ollama_tags.$$ || true

# Check OANDA broker
if [[ -n "${OANDA_PRACTICE_TOKEN:-}" ]] || [[ -n "${OANDA_TOKEN:-}" ]]; then
    TOKEN="${OANDA_TOKEN:-${OANDA_PRACTICE_TOKEN:-}}"
    ACCOUNT="${OANDA_ACCOUNT_ID:-${OANDA_PRACTICE_ACCOUNT_ID:-}}"
    BASE="${OANDA_BASE_URL:-https://api-fxpractice.oanda.com}"
    
    echo -n "OANDA:    "
    if [[ -n "$TOKEN" ]] && [[ -n "$ACCOUNT" ]]; then
        RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -m 10 \
            -H "Authorization: Bearer $TOKEN" \
            "$BASE/v3/accounts/$ACCOUNT/summary" 2>/dev/null || echo "000")
        if [[ "$RESPONSE" == "200" ]]; then
            echo "✅ OK"
        elif [[ "$RESPONSE" == "401" ]] || [[ "$RESPONSE" == "403" ]]; then
            echo "❌ AUTH FAIL (HTTP $RESPONSE)"
            FAILURES=$((FAILURES + 1))
        else
            echo "❌ UNREACHABLE (HTTP $RESPONSE)"
            FAILURES=$((FAILURES + 1))
        fi
    else
        echo "⚪ Missing token or account ID"
    fi
else
    echo "OANDA:    ⚪ Not configured"
fi

echo ""
echo "================================================================"
if [[ $FAILURES -eq 0 ]]; then
    echo " ✅ HIVE STATUS: ALL CONFIGURED SERVICES HEALTHY"
    echo "================================================================"
    exit 0
else
    echo " ❌ HIVE STATUS: $FAILURES SERVICE(S) UNHEALTHY"
    echo "================================================================"
    exit 1
fi
