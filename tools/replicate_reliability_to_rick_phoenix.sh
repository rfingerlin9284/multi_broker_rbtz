#!/usr/bin/env bash
# Replicate reliability files (broker-link + systemd units + scripts) to /home/ing/RICK/RICK_PHOENIX if it exists
set -euo pipefail
TARGET="/home/ing/RICK/RICK_PHOENIX"
if [ ! -d "$TARGET" ]; then
  echo "Target $TARGET not found; skipping replication"
  exit 0
fi
# Files to copy
FILES=(
  "tools/systemd/rbotzilla-broker-link.service"
  "tools/systemd/rbotzilla-engine-paper.service"
  "tools/systemd/rbotzilla-engine-live.service"
  "tools/run_broker_link.sh"
  "tools/run_engine_paper.sh"
  "tools/run_engine_live.sh"
  "tools/start_paper_engine.sh"
  "tools/confirm_hive.sh"
  "multi_broker_phoenix/services/broker_link.py"
)
for f in "${FILES[@]}"; do
  src="$PWD/$f"
  dst="$TARGET/$(basename $f)"
  if [ -f "$src" ]; then
    cp "$src" "$dst"
    echo "Copied $f -> $dst"
  else
    echo "Missing $src; skipping"
  fi
done

echo "Replication complete. You still need to run install_autoboot.sh in the target repo to install units."
