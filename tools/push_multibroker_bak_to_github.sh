#!/usr/bin/env bash
# Push MULTIBROKER_BAK to GitHub repository
# Usage: bash push_multibroker_bak_to_github.sh <path_to_zip>

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <path_to_backup_zip>"
  exit 1
fi

BACKUP_ZIP="$1"
GITHUB_REPO="https://github.com/rfingerlin9284/MUILTIBROKER_OANDA_REPO.git"
TEMP_CLONE="/tmp/multibroker_github_push_$$"

if [[ ! -f "$BACKUP_ZIP" ]]; then
  echo "❌ Backup file not found: $BACKUP_ZIP"
  exit 1
fi

echo "========================================="
echo " Pushing to GitHub"
echo "========================================="
echo "Backup: $BACKUP_ZIP"
echo "Repo: $GITHUB_REPO"
echo ""

# Clone or init repo
if git ls-remote "$GITHUB_REPO" &>/dev/null; then
  echo "Cloning existing repository..."
  git clone "$GITHUB_REPO" "$TEMP_CLONE"
else
  echo "Initializing new repository..."
  mkdir -p "$TEMP_CLONE"
  cd "$TEMP_CLONE"
  git init
  git remote add origin "$GITHUB_REPO"
fi

cd "$TEMP_CLONE"

# Copy backup file
echo ""
echo "Copying backup..."
cp "$BACKUP_ZIP" .
BACKUP_FILENAME=$(basename "$BACKUP_ZIP")

# Create/update README
cat > README.md <<'EOF'
# MULTIBROKER_OANDA_REPO

Backup repository for multi-broker trading bot essentials.

## Latest Backup

See the most recent `MULTIBROKER_BAK_*.zip` file for the complete trading bot code and configuration.

## Contents

Each backup contains:
- Complete Python source code for bot engine
- AI router and LLM gate services
- Signal brain and execution modules
- Configuration templates
- All operational tools and scripts
- Complete documentation

## Restore Instructions

1. Download the latest `MULTIBROKER_BAK_*.zip`
2. Extract and follow `BACKUP_README.md` inside
3. Configure `ops/secrets.env` with your API keys
4. Run `bash tools/env_doctor.sh` to verify
5. Start with `bash tools/resume_paper_now.sh`

## Security

⚠️ API keys are NOT included in backups for security.
Store your `ops/secrets.env` separately and securely.

## Repository Purpose

This repository serves as version-controlled storage for complete bot snapshots,
allowing rapid deployment to new systems or recovery from failures.

---
Last updated: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
EOF

# Stage files
git add "$BACKUP_FILENAME" README.md

# Check if there are changes
if git diff --staged --quiet; then
  echo ""
  echo "ℹ️ No changes to commit (backup already exists)"
else
  # Commit and push
  COMMIT_MSG="Add backup: $BACKUP_FILENAME"
  echo ""
  echo "Committing: $COMMIT_MSG"
  git commit -m "$COMMIT_MSG"
  
  echo ""
  echo "Pushing to GitHub..."
  git push -u origin main || git push -u origin master
  
  echo ""
  echo "========================================="
  echo " ✅ Successfully pushed to GitHub"
  echo "========================================="
  echo "Repository: $GITHUB_REPO"
  echo "File: $BACKUP_FILENAME"
fi

# Cleanup
cd /
rm -rf "$TEMP_CLONE"

echo ""
echo "✅ GitHub push complete!"
