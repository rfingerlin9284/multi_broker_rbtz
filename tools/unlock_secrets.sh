#!/usr/bin/env bash
# Unlock canonical secrets files after verifying approval id with HISTORICAL_CHANGE_LOG.md
set -e
ROOT="$(git rev-parse --show-toplevel)"
HISTORY="$ROOT/HISTORICAL_CHANGE_LOG.md"
if [ -z "$1" ]; then
  echo "Usage: $0 <approval-id>" >&2
  exit 2
fi
ID="$1"
if ! grep -q "$ID" "$HISTORY"; then
  echo "Approval id $ID not found in HISTORICAL_CHANGE_LOG.md" >&2
  exit 3
fi
OPS="$ROOT/ops"
FILES=(secrets.env secrets_1.env secrets_backtest.env)
for f in "${FILES[@]}"; do
  p="$OPS/$f"
  if [ -f "$p" ]; then
    chmod 600 "$p"
    rm -f "$p.locked" || true
    echo "Unlocked $p"
  fi
done

echo "✅ Secrets unlocked using approval id: $ID"