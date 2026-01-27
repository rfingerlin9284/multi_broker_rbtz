#!/usr/bin/env bash
# ================================================================
# Start OANDA engine LIVE mode (PIN required)
# ================================================================
# DANGER: This starts the LIVE trading engine with REAL MONEY.
# Requires PIN verification before starting.
#
# Prerequisites:
#   - .env must have OANDA_LIVE_TOKEN and OANDA_LIVE_ACCOUNT_ID
#   - HIVE confirmation must pass
# ================================================================
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

# Banner with warning
echo "================================================================"
echo " ⚠️  RBOTzilla: LIVE TRADING MODE (REAL MONEY) ⚠️"
echo "================================================================"
echo ""

# Require PIN confirmation
read -p "Enter PIN to confirm LIVE trading: " -s PIN
echo ""

if [[ "$PIN" != "${RBOT_GUARD_PIN:-841921}" ]]; then
    echo "❌ ERROR: Invalid PIN. Aborting LIVE start."
    exit 1
fi

echo "✅ PIN verified"
echo ""

# Load .env if exists
if [[ -f "$PROJECT_ROOT/.env" ]]; then
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
fi

# Verify we have LIVE credentials
if [[ -z "${OANDA_LIVE_TOKEN:-}" ]] || [[ -z "${OANDA_LIVE_ACCOUNT_ID:-}" ]]; then
    echo "❌ ERROR: OANDA_LIVE_TOKEN and OANDA_LIVE_ACCOUNT_ID must be set"
    exit 1
fi

# Set LIVE mode
export TRADING_MODE="LIVE"
export OANDA_TOKEN="$OANDA_LIVE_TOKEN"
export OANDA_ACCOUNT_ID="$OANDA_LIVE_ACCOUNT_ID"
export OANDA_BASE_URL="https://api-fxtrade.oanda.com"
export HEADLESS_MODE="${HEADLESS_MODE:-oanda-only}"
export ENABLE_OANDA="true"
export ENABLE_COINBASE="false"
export ENABLE_IBKR="false"

# Confirm HIVE before starting
echo "ℹ️  Running HIVE confirmation..."
if ! "$PROJECT_ROOT/tools/confirm_hive.sh"; then
    echo "❌ ERROR: HIVE confirmation failed. Cannot start LIVE."
    exit 1
fi
echo "✅ HIVE confirmed"
echo ""

# Final confirmation
echo "⚠️  FINAL WARNING: You are about to start LIVE trading with REAL MONEY."
read -p "Type 'CONFIRM LIVE' to proceed: " CONFIRM
if [[ "$CONFIRM" != "CONFIRM LIVE" ]]; then
    echo "❌ Aborted by user."
    exit 1
fi

echo ""
echo "🚀 Starting LIVE engine..."
echo ""

# Run the engine
cd "$PROJECT_ROOT/MULTI_BROKER_PHOENIX"
exec python3 -m tools.run_headless
