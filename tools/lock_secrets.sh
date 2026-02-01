#!/usr/bin/env bash
# Lock canonical secrets files by making them read-only and recording a .locked sentinel.
set -e
ROOT="$(git rev-parse --show-toplevel)"
OPS="$ROOT/ops"
FILES=(secrets.env secrets_1.env secrets_backtest.env)
for f in "${FILES[@]}"; do
  p="$OPS/$f"
  if [ -f "$p" ]; then
    chmod 400 "$p"
    echo "locked" > "$p.locked"
    echo "Locked $p"
  fi
done

echo "✅ Secrets locked (read-only). To unlock, use tools/unlock_secrets.sh with approval."