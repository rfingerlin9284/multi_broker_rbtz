#!/usr/bin/env bash
# STABILITY UNLOCK - Restores write permissions for code changes
# Usage: ./tools/stability_unlock.sh
# WARNING: Only use if you need to make critical fixes!

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "🔓 STABILITY UNLOCK — Restoring write permissions"
echo ""
echo "⚠️  WARNING: You are exiting stability-lock mode!"
echo "   This means you may introduce changes that break 2-week reliability."
echo ""
read -p "Are you sure you want to unlock? (yes/no): " confirm

if [[ "$confirm" != "yes" ]]; then
    echo "❌ Unlock cancelled"
    exit 0
fi

# Restore write permissions
CRITICAL_PATHS=(
    "multi_broker_phoenix/core"
    "multi_broker_phoenix/risk"
    "multi_broker_phoenix/monitor"
    "multi_broker_phoenix/adapters"
    "multi_broker_phoenix/runners"
    "tools/start_broker.sh"
    "tools/start_full_system.sh"
    "tools/stop_broker.sh"
    "tools/status_full_system.sh"
)

echo "🔓 Restoring write permissions..."
for path in "${CRITICAL_PATHS[@]}"; do
    if [[ -e "$REPO_ROOT/$path" ]]; then
        chmod -R u+w "$REPO_ROOT/$path" 2>/dev/null || {
            echo "⚠️  Could not unlock $path (may require sudo)"
        }
        echo "  ✓ Unlocked: $path"
    fi
done

# Log the unlock event
UNLOCK_LOG="ops/state/stability_unlocks.log"
mkdir -p ops/state
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) | ${USER}@$(hostname) | UNLOCKED" >> "$UNLOCK_LOG"

echo ""
echo "✅ STABILITY LOCK REMOVED"
echo ""
echo "📋 Write permissions restored. Code is now editable."
echo ""
echo "⚠️  REMINDER: Re-lock after making fixes:"
echo "   ./tools/stability_lock.sh"
echo ""
