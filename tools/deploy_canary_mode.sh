#!/bin/bash
# PHASE 1: Deploy Coinbase Canary Mode Configuration
# This script safely updates .env for ultra-conservative canary testing

set -e

echo "🐤 PHASE 1: Coinbase Canary Mode Deployment"
echo "==========================================="
echo ""

# Backup existing .env
if [ -f .env ]; then
    echo "📦 Backing up existing .env to .env.backup.$(date +%Y%m%d_%H%M%S)"
    cp .env ".env.backup.$(date +%Y%m%d_%H%M%S)"
fi

# Enable canary mode in .env
echo "🔧 Enabling CANARY_MODE in .env..."
if grep -q "^CANARY_MODE=" .env 2>/dev/null; then
    sed -i 's/^CANARY_MODE=.*/CANARY_MODE=true/' .env
else
    echo "CANARY_MODE=true" >> .env
fi

# Ensure coinbase-only mode
echo "🔧 Setting HEADLESS_MODE to coinbase-only..."
sed -i 's/^HEADLESS_MODE=.*/HEADLESS_MODE=coinbase-only/' .env

# Verify critical settings
echo ""
echo "✅ Configuration Applied:"
echo "   - CANARY_MODE: $(grep '^CANARY_MODE=' .env || echo 'true (default)')"
echo "   - HEADLESS_MODE: $(grep '^HEADLESS_MODE=' .env)"
echo "   - DEFAULT_STRATEGY: $(grep '^DEFAULT_STRATEGY=' .env)"
echo "   - FEED_SYMBOLS: $(grep '^FEED_SYMBOLS=' .env)"
echo "   - CANARY_POLL_SECONDS: $(grep '^CANARY_POLL_SECONDS=' .env || echo '30.0 (default)')"
echo "   - CANARY_MAX_RISK_USD: $(grep '^CANARY_MAX_RISK_USD=' .env || echo '10.0 (default)')"
echo ""
echo "🚀 Ready to start canary mode!"
echo ""
echo "Next steps:"
echo "  1. Run: python3 MULTI_BROKER_PHOENIX/tools/run_headless.py --mode coinbase-only"
echo "  2. Or use VSCode task: 🐤 RBOTZILLA: Start Coinbase Canary Mode"
echo "  3. Monitor with: tail -f output in terminal"
echo ""
