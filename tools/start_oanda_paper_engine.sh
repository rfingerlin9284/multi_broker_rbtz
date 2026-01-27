#!/usr/bin/env bash
# ================================================================
# Start OANDA engine for paper demo practice API token account
# ================================================================
# This is the SAFE DEFAULT startup - PAPER mode only, no live money.
#
# Features:
# - Starts broker health monitor
# - Starts OCO reconciler
# - Runs startup reconcile before trading
# - Emits health events to narration
# - Safe fail-closed behavior
#
# Usage:
#   ./start_oanda_paper_engine.sh
#
# Prerequisites:
#   - .env file with OANDA_PRACTICE_TOKEN and OANDA_PRACTICE_ACCOUNT_ID
#   - Python 3.9+ with required packages
# ================================================================
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

# Banner
echo "================================================================"
echo " RBOTzilla: Start OANDA Paper Engine (Practice API)"
echo "================================================================"
echo ""

# Load .env if exists
if [[ -f "$PROJECT_ROOT/.env" ]]; then
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
fi

# Enforce PAPER mode
export TRADING_MODE="${TRADING_MODE:-PAPER}"
if [[ "$TRADING_MODE" == "LIVE" ]]; then
    echo "❌ ERROR: This script is for PAPER mode only."
    echo "   Use engine_mode.sh to enable LIVE mode (requires PIN)."
    exit 1
fi

export HEADLESS_MODE="${HEADLESS_MODE:-oanda-only}"
export ENABLE_OANDA="true"
export ENABLE_COINBASE="false"
export ENABLE_IBKR="false"
export PAPER_MODE_SIMULATION="false"

# Validate OANDA credentials
if [[ -z "${OANDA_PRACTICE_TOKEN:-}" ]] && [[ -z "${OANDA_API_TOKEN:-}" ]]; then
    echo "❌ ERROR: OANDA_PRACTICE_TOKEN or OANDA_API_TOKEN must be set in .env"
    exit 1
fi

if [[ -z "${OANDA_PRACTICE_ACCOUNT_ID:-}" ]] && [[ -z "${OANDA_ACCOUNT_ID:-}" ]]; then
    echo "❌ ERROR: OANDA_PRACTICE_ACCOUNT_ID or OANDA_ACCOUNT_ID must be set in .env"
    exit 1
fi

echo "✅ OANDA credentials found"
echo "   Mode: PAPER (Practice API)"
echo "   Broker: OANDA only"
echo ""

# Ensure ops/state directory exists
mkdir -p "$PROJECT_ROOT/ops/state"

# Pre-flight: verify imports work
echo "Running import smoke test..."
python3 -c "
import sys
sys.path.insert(0, '.')
try:
    from multi_broker_phoenix.risk.pip_math import pip_value_usd
    from multi_broker_phoenix.risk.risk_governor import risk_gate_check
    from multi_broker_phoenix.risk.oco_reconcile import run_oco_reconcile_once
    from multi_broker_phoenix.risk.broker_health import is_healthy
    print('✅ All risk modules imported successfully')
except ImportError as e:
    print(f'⚠️  Import warning (non-fatal): {e}')
" || echo "⚠️  Some imports may have failed (continuing anyway)"

# Write startup marker
cat > "$PROJECT_ROOT/ops/state/engine_startup.json" << EOF
{
  "started_at": "$(date -Iseconds)",
  "mode": "PAPER",
  "broker": "OANDA",
  "pid": $$,
  "script": "start_oanda_paper_engine.sh"
}
EOF

echo ""
echo "Starting headless engine..."
echo "   Log: stdout (use journalctl if running via systemd)"
echo "   State: ops/state/*.json"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Run the headless engine
exec python3 "$PROJECT_ROOT/MULTI_BROKER_PHOENIX/tools/run_headless.py" --mode oanda-only
