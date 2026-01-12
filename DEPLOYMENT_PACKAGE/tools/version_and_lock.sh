#!/usr/bin/env bash
set -euo pipefail

FILE="${1:?provide a file path}"
DIR="$(dirname "$FILE")"
BASE="$(basename "$FILE")"
OLDER="${DIR}/older_versions"
mkdir -p "$OLDER"

next_ver() {
  local max=0
  shopt -s nullglob
  for f in "$OLDER/${BASE%.*}"_v*.${BASE##*.} "$OLDER/${BASE}"_v*; do
    bn="$(basename "$f")"
    num="$(echo "$bn" | sed -n 's/.*_v\([0-9][0-9][0-9]\).*/\1/p')"
    if [[ -n "${num}" ]]; then
      if ((10#$num > max)); then max=$((10#$num)); fi
    fi
  done
  printf "%03d" $((max+1))
}

VER="$(next_ver)"
ARCHIVE_NAME="${OLDER}/${BASE%.*}_v${VER}.${BASE##*.}"

if [[ -f "$FILE" ]]; then
  cp -a "$FILE" "$ARCHIVE_NAME"
fi

if [[ -f "${FILE}.new" ]]; then
  mv -f "${FILE}.new" "$FILE"
fi

chmod 444 "$FILE"

if [[ "${ENABLE_IMMUTABLE:-0}" == "1" ]]; then
  if command -v chattr >/dev/null 2>&1; then
    chattr +i "$FILE" || true
  fi
fi

echo "OK: archived -> $ARCHIVE_NAME"
echo "OK: locked -> $FILE"
