#!/usr/bin/env bash
set -euo pipefail

# Safe to start anytime (even before the engine creates the file).
LOG="/tmp/trades.db.log"

mkdir -p "$(dirname "$LOG")"
touch "$LOG"

# -F follows by name and retries if the file is rotated/recreated
exec tail -F "$LOG"
