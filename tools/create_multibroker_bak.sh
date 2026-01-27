#!/usr/bin/env bash
# Create MULTIBROKER_BAK - Essential files backup for trading bot
# Includes all code, configs, and documentation needed for operation

set -euo pipefail

REPO="/home/ing/RICK/MULTI_BROKER_PHOENIX"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="MULTIBROKER_BAK_${TIMESTAMP}"
TEMP_DIR="/tmp/${BACKUP_NAME}"
OUTPUT_ZIP="${BACKUP_NAME}.zip"

echo "========================================="
echo " Creating MULTIBROKER_BAK"
echo "========================================="
echo "Source: $REPO"
echo "Backup: $BACKUP_NAME"
echo ""

cd "$REPO" || exit 1

# Create temp directory structure
mkdir -p "$TEMP_DIR"

echo "Copying essential files..."

# Core Python packages
rsync -av --relative \
  ./MULTI_BROKER_PHOENIX/multi_broker_phoenix \
  ./MULTI_BROKER_PHOENIX/tools/run_headless.py \
  ./ai_router \
  ./llm_gate \
  ./core \
  ./execution \
  ./hive_real \
  "$TEMP_DIR/"

# Configuration files (exclude secrets)
rsync -av --relative \
  ./config/toggles.env \
  ./config/secrets.env.example \
  ./config/hive_endpoints.json \
  "$TEMP_DIR/" 2>/dev/null || true

# Tools and scripts
rsync -av --relative \
  ./tools/*.sh \
  ./tools/*.py \
  ./tools/tasks \
  "$TEMP_DIR/"

# Tests
rsync -av --relative \
  ./tests \
  "$TEMP_DIR/" 2>/dev/null || true

# Documentation
rsync -av --relative \
  ./*.md \
  ./*.txt \
  "$TEMP_DIR/" 2>/dev/null || true

# VS Code tasks
rsync -av --relative \
  ./.vscode/tasks.json \
  "$TEMP_DIR/" 2>/dev/null || true

# Git config
rsync -av --relative \
  ./.gitignore \
  "$TEMP_DIR/" 2>/dev/null || true

# Python project files
rsync -av --relative \
  ./pyproject.toml \
  ./global_config.py \
  "$TEMP_DIR/" 2>/dev/null || true

# Create structure directories
mkdir -p "$TEMP_DIR/ops/state"
mkdir -p "$TEMP_DIR/logs"

# Add README for backup
cat > "$TEMP_DIR/BACKUP_README.md" <<'EOF'
# MULTIBROKER_BAK - Essential Bot Files

## Contents

This backup contains all essential files needed for the trading bot to operate:

### Core Components
- `MULTI_BROKER_PHOENIX/` - Main bot engine code
- `ai_router/` - AI seat router with quorum logic
- `llm_gate/` - LLM gate service for trade validation
- `core/` - Signal brain and core strategies
- `execution/` - OANDA practice client and order execution
- `hive_real/` - AI hive integration

### Configuration
- `config/toggles.env` - Feature flags and non-secret config
- `config/secrets.env.example` - Template for API keys (fill in your keys)
- `config/hive_endpoints.json` - AI service endpoints

### Tools
- `tools/` - All operational scripts (env_load, env_doctor, bootstrap, etc.)
- `tools/tasks/` - Task scripts for status checks

### Documentation
- All `.md` files with setup guides, runbooks, charters
- All `.txt` files with quick references

### VS Code
- `.vscode/tasks.json` - VS Code task definitions

## Setup Instructions

1. **Extract backup:**
   ```bash
   unzip MULTIBROKER_BAK_*.zip
   cd MULTIBROKER_BAK_*
   ```

2. **Create virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt  # if exists, or install manually
   ```

3. **Configure secrets:**
   ```bash
   cp config/secrets.env.example ops/secrets.env
   nano ops/secrets.env  # Fill in your API keys
   chmod 600 ops/secrets.env
   ```

4. **Verify environment:**
   ```bash
   bash tools/env_doctor.sh
   ```

5. **Start trading (PAPER mode):**
   ```bash
   bash tools/resume_paper_now.sh
   ```

## What's NOT Included

- `ops/secrets.env` - Your actual API keys (security)
- `ops/state/` - Runtime state files (generated fresh)
- `logs/` - Historical logs (too large)
- `.venv/` - Virtual environment (reconstruct)
- `.git/` - Git history (too large)
- `__pycache__/` - Python cache (regenerated)

## Restore Checklist

- [ ] Extract backup
- [ ] Create .venv and install dependencies
- [ ] Copy `ops/secrets.env` from secure location OR fill template
- [ ] Run `bash tools/env_doctor.sh` (must show OK)
- [ ] Run `bash tools/resume_paper_now.sh` (must show PASS)

## Security Notes

- ⚠️ This backup does NOT contain your API keys
- ⚠️ Never commit ops/secrets.env to git
- ⚠️ Store API keys separately in secure location
- ✅ All secret presence is indicated as [SET]/[EMPTY] only

## Support

See individual .md files for detailed documentation:
- `RUNBOOK_ENV_KEYS.md` - Environment and key management
- `PRIME_SESSION_RECOVER_COMPLETE.md` - Session recovery guide
- `AGENT_CHARTER_RBOTZILLA.md` - Bot operational charter

EOF

echo "Creating ZIP archive..."
cd /tmp
zip -r "$OUTPUT_ZIP" "$BACKUP_NAME" -x "*.pyc" "*__pycache__*" "*.git*" 2>&1 | grep -v "adding:" || true

echo ""
echo "========================================="
echo " Backup Summary"
echo "========================================="
ls -lh "/tmp/$OUTPUT_ZIP"
echo ""
echo "Archive created: /tmp/$OUTPUT_ZIP"

# Copy to Windows desktop
WINDOWS_DESKTOP="/mnt/c/Users/$(whoami)/Desktop"
if [[ -d "$WINDOWS_DESKTOP" ]]; then
  echo ""
  echo "Copying to Windows Desktop..."
  cp "/tmp/$OUTPUT_ZIP" "$WINDOWS_DESKTOP/"
  echo "✅ Copied to: $WINDOWS_DESKTOP/$OUTPUT_ZIP"
else
  echo "⚠️ Windows Desktop not found at $WINDOWS_DESKTOP"
  echo "   Archive remains at: /tmp/$OUTPUT_ZIP"
fi

# Cleanup temp directory
rm -rf "$TEMP_DIR"

echo ""
echo "========================================="
echo " Next Steps"
echo "========================================="
echo "1. Archive saved to Windows Desktop"
echo "2. Ready to push to GitHub"
echo ""
echo "To push to GitHub, run:"
echo "  bash tools/push_multibroker_bak_to_github.sh /tmp/$OUTPUT_ZIP"
echo ""
echo "✅ Backup complete!"
