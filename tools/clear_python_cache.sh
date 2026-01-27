#!/bin/bash
# Clear Python bytecode cache to force reimport of modules
# Use this after making code changes if imports are failing

REPO_ROOT="/home/ing/RICK/MULTI_BROKER_PHOENIX"

echo "🧹 Clearing Python bytecode cache..."

# Remove all .pyc files
find "$REPO_ROOT" -name "*.pyc" -type f -delete 2>/dev/null

# Remove all __pycache__ directories
find "$REPO_ROOT" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Count what we cleared
pyc_count=$(find "$REPO_ROOT" -name "*.pyc" -type f 2>/dev/null | wc -l)
pycache_count=$(find "$REPO_ROOT" -name "__pycache__" -type d 2>/dev/null | wc -l)

echo "✅ Cache cleared"
echo "   Remaining .pyc files: $pyc_count"
echo "   Remaining __pycache__ dirs: $pycache_count"

if [ "$pyc_count" -eq 0 ] && [ "$pycache_count" -eq 0 ]; then
    echo "✅ All cache files removed successfully"
else
    echo "⚠️  Some cache files still present (may be locked by running processes)"
fi

echo ""
echo "💡 TIP: If imports still fail, make sure no Python processes are running:"
echo "   ps aux | grep python"
echo "   pkill -f multi_broker_phoenix"
