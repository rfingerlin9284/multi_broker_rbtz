#!/usr/bin/env bash
# Install git hooks from .githooks/ into .git/hooks/
set -e
ROOT="$(git rev-parse --show-toplevel)"
SRC="$ROOT/.githooks"
DST="$ROOT/.git/hooks"
if [ ! -d "$SRC" ]; then
  echo ".githooks directory not found" >&2
  exit 1
fi
mkdir -p "$DST"
for f in "$SRC"/*; do
  bn=$(basename "$f")
  cp "$f" "$DST/$bn"
  chmod +x "$DST/$bn"
  echo "Installed $bn -> .git/hooks/$bn"
done
echo "✅ Hooks installed"
