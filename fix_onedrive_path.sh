#!/usr/bin/env bash
set -euo pipefail

# Set your Windows username explicitly if it differs from $USER in WSL
WIN_USER="${WIN_USER:-$USER}"

ONEDRIVE="/mnt/c/Users/$WIN_USER/OneDrive"
SRC="$ONEDRIVE/Pictures/RBT_DEV_FOLDER/backup_20250708_015816"
DEST_ROOT="/mnt/c/ibkr_backups"
DEST="$DEST_ROOT/backup_20250708_015816"

echo "Windows user   : $WIN_USER"
echo "OneDrive path  : $ONEDRIVE"
echo "Source (to move): $SRC"
echo "Destination    : $DEST"
echo

# Verify OneDrive exists
if [[ ! -d "$ONEDRIVE" ]]; then
  echo "❌ OneDrive path not found: $ONEDRIVE"
  echo "   Set WIN_USER to your Windows username, e.g.: WIN_USER=YourName ./fix_onedrive_path.sh"
  exit 1
fi

# List the parent folder so you can see what’s actually there
echo "Listing RBT_DEV_FOLDER contents:"
ls -la "$ONEDRIVE/Pictures/RBT_DEV_FOLDER" || true
echo

# Verify source exists
if [[ ! -d "$SRC" ]]; then
  echo "❌ Source folder not found: $SRC"
  echo "   If the name differs, set SRC to the exact folder shown above, then rerun."
  exit 1
fi

# Create destination root if missing
mkdir -p "$DEST_ROOT"

echo "Moving..."
mv "$SRC" "$DEST"

echo "✅ Done. Now click ‘Try again’ in OneDrive to clear the path-too-long warning."