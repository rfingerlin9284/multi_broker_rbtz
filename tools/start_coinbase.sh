#!/bin/bash
# Quick start script for Coinbase RBOTzilla headless mode

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=================================================="
echo "  Coinbase RBOTzilla - Headless Quick Start"
echo "=================================================="
echo ""

# Auto-fix `.env` duplicates up-front (never prints secrets)
if [ -f "$PROJECT_ROOT/.env" ]; then
    "$PROJECT_ROOT/tools/env_preflight.py" --fix --quiet || true
fi

# Check if .env exists
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    echo "⚠️  No .env file found. Copying from .env.example..."
    cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
    echo "✓ Created .env file"
fi

# Verify critical settings
echo "Checking configuration..."
if ! grep -q "HEADLESS_MODE=coinbase-only" "$PROJECT_ROOT/.env"; then
    echo "⚠️  Setting HEADLESS_MODE=coinbase-only"
    sed -i 's/^HEADLESS_MODE=.*/HEADLESS_MODE=coinbase-only/' "$PROJECT_ROOT/.env"
fi

if ! grep -q "FEED_SYMBOLS=BTC-USD,ETH-USD" "$PROJECT_ROOT/.env"; then
    echo "⚠️  Setting FEED_SYMBOLS=BTC-USD,ETH-USD"
    if grep -q "^FEED_SYMBOLS=" "$PROJECT_ROOT/.env"; then
        sed -i 's/^FEED_SYMBOLS=.*/FEED_SYMBOLS=BTC-USD,ETH-USD/' "$PROJECT_ROOT/.env"
    else
        echo "FEED_SYMBOLS=BTC-USD,ETH-USD" >> "$PROJECT_ROOT/.env"
    fi
fi

echo "✓ Configuration verified"
echo ""

# Run validation
echo "Running validation tests..."
export PYTHONPATH="$PROJECT_ROOT/MULTI_BROKER_PHOENIX:$PYTHONPATH"
if "$PROJECT_ROOT/tools/py_venv.sh" "$PROJECT_ROOT/tools/validate_coinbase.py"; then
    echo ""
    echo "✓ Validation passed!"
    echo ""
    echo "=================================================="
    echo "  Ready to start Coinbase RBOTzilla!"
    echo "=================================================="
    echo ""
    echo "Starting headless runner in 3 seconds..."
    echo "Press Ctrl+C to cancel"
    sleep 3
    echo ""
    
    # Start headless runner
    "$PROJECT_ROOT/tools/py_venv.sh" "$PROJECT_ROOT/MULTI_BROKER_PHOENIX/tools/run_headless.py" --mode coinbase-only
else
    echo ""
    echo "✗ Validation failed. Please check errors above."
    exit 1
fi
