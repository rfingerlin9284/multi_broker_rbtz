#!/usr/bin/env bash
#STABILITY LOCK - Prevents accidental code changes during 2-week reliable run period
# Usage: ./tools/stability_lock.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

BASELINE_FILE="ops/state/stability_baseline_$(date +%Y%m%d_%H%M%S).json"

echo "🔒 STABILITY LOCK — Locking critical runtime code for 2-week stable run"
echo ""

# Get git commit hash if available
GIT_HASH=""
if command -v git &> /dev/null && [[ -d .git ]]; then
    GIT_HASH=$(git rev-parse HEAD 2>/dev/null || echo "NO_GIT")
fi

# Create baseline snapshot
mkdir -p ops/state
cat > "$BASELINE_FILE" <<JSON
{
  "locked_at_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "git_commit": "${GIT_HASH:-NO_GIT}",
  "locked_by": "${USER}@$(hostname)",
  "purpose": "two_week_stable_run_oanda_paper",
  "unlock_command": "./tools/stability_unlock.sh"
}
JSON

echo "✅ Baseline snapshot: $BASELINE_FILE"
echo ""

# Lock critical runtime modules (make read-only)
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

echo "🔒 Locking critical paths (read-only)..."
for path in "${CRITICAL_PATHS[@]}"; do
    if [[ -e "$REPO_ROOT/$path" ]]; then
        chmod -R a-w "$REPO_ROOT/$path" 2>/dev/null || {
            echo "⚠️  Could not lock $path (may require sudo)"
        }
        echo "  ✓ Locked: $path"
    fi
done

echo ""
echo "✅ STABILITY LOCK ACTIVE"
echo ""
echo "📋 What's locked:"
echo "   - Core framework (broker_supervisor, gates, orchestrator, interfaces)"
echo "   - Safety monitors (exit_manager, pnl_kill_switch, protect_loop)"
echo "   - Adapters (OANDA/Coinbase/IBKR connectors)"
echo "   - Runners (supervised broker engines)"
echo "   - Control scripts (start/stop/status)"
echo ""
echo "📋 What's still writable:"
echo "   - config/ (toggles, environment settings)"
echo "   - ops/state/ (heartbeats, state files)"
echo "   - logs/ (log outputs)"
echo "   - tools/stability_unlock.sh (emergency unlock)"
echo ""
echo "⚠️  To make code changes, run: ./tools/stability_unlock.sh"
echo ""
echo "📌 Recommended 2-week workflow:"
echo "   1. Start OANDA SAFE mode"
echo "   2. Verify gates pass"
echo "   3. Enable paper autonomy (unlock guard + AUTO_ARM)"
echo "   4. Monitor daily (2 min): ./tools/status_full_system.sh"
echo "   5. DO NOT touch code unless critical bug found"
echo "   6. After 2 weeks: collect data, analyze, plan next improvements"
echo ""
