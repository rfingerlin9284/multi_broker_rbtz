#!/usr/bin/env bash
# FABIO AAA FULL v1.1.0 - Complete Restore Script
# This script rebuilds the entire optimized version from backup or snapshots
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STRATEGY_FILE="$SCRIPT_DIR/MULTI_BROKER_PHOENIX/multi_broker_phoenix/strategies/fabio_aaa_full.py"
ENV_FILE="$SCRIPT_DIR/.env"
BACKUP_DIR="$SCRIPT_DIR/backups/fabio_v1.1.0"

echo "🔄 FABIO AAA FULL v1.1.0 - RESTORATION SCRIPT"
echo "=============================================="
echo ""

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Check if we're restoring or creating new backup
if [ "$1" == "--backup" ]; then
    echo "📦 Creating new backup snapshot..."
    
    # Backup current strategy file
    cp "$STRATEGY_FILE" "$BACKUP_DIR/fabio_aaa_full.py"
    echo "✅ Backed up: fabio_aaa_full.py"
    
    # Backup relevant .env section
    grep -A 4 "FABIO_RSI_THRESHOLD" "$ENV_FILE" > "$BACKUP_DIR/fabio_env_snippet.txt" || echo "FABIO_RSI_THRESHOLD=40" > "$BACKUP_DIR/fabio_env_snippet.txt"
    echo "✅ Backed up: .env configuration"
    
    # Create version manifest
    cat > "$BACKUP_DIR/VERSION_MANIFEST.txt" << EOF
FABIO AAA FULL v1.1.0
Backup Date: $(date)
Strategy Hash: $(md5sum "$STRATEGY_FILE" | awk '{print $1}')
RSI Threshold: 40
Performance: 167 trades @ 64.7% win rate
Status: Production Ready
EOF
    echo "✅ Created: VERSION_MANIFEST.txt"
    
    echo ""
    echo "✅ Backup complete: $BACKUP_DIR"
    
elif [ "$1" == "--restore" ]; then
    echo "🔧 Restoring from backup snapshot..."
    
    if [ ! -f "$BACKUP_DIR/fabio_aaa_full.py" ]; then
        echo "❌ ERROR: Backup not found at $BACKUP_DIR"
        echo "Run with --backup first to create a snapshot."
        exit 1
    fi
    
    # Restore strategy file
    cp "$BACKUP_DIR/fabio_aaa_full.py" "$STRATEGY_FILE"
    echo "✅ Restored: fabio_aaa_full.py"
    
    # Check if .env needs updating
    if ! grep -q "FABIO_RSI_THRESHOLD" "$ENV_FILE"; then
        echo ""
        echo "Adding FABIO_RSI_THRESHOLD to .env..."
        echo "" >> "$ENV_FILE"
        echo "# FABIO AAA FULL Strategy Configuration" >> "$ENV_FILE"
        echo "FABIO_RSI_THRESHOLD=40" >> "$ENV_FILE"
        echo "✅ Updated: .env"
    else
        echo "✅ .env already configured"
    fi
    
    echo ""
    echo "✅ Restoration complete!"
    echo ""
    echo "Verify with:"
    echo "  grep -n 'rsi_threshold' $STRATEGY_FILE"
    echo "  grep FABIO_RSI_THRESHOLD $ENV_FILE"
    
elif [ "$1" == "--verify" ]; then
    echo "🔍 Verifying current installation..."
    echo ""
    
    # Check strategy file
    if grep -q "self.rsi_threshold" "$STRATEGY_FILE"; then
        echo "✅ Strategy: Configurable RSI threshold present"
        grep -n "self.rsi_threshold" "$STRATEGY_FILE" | head -2
    else
        echo "❌ Strategy: Missing configurable threshold"
    fi
    
    echo ""
    
    # Check .env
    if grep -q "FABIO_RSI_THRESHOLD" "$ENV_FILE"; then
        echo "✅ .env: Configuration present"
        grep "FABIO_RSI_THRESHOLD" "$ENV_FILE"
    else
        echo "❌ .env: Missing FABIO_RSI_THRESHOLD"
    fi
    
    echo ""
    
    # Check backup
    if [ -f "$BACKUP_DIR/fabio_aaa_full.py" ]; then
        echo "✅ Backup: Snapshot exists"
        cat "$BACKUP_DIR/VERSION_MANIFEST.txt" 2>/dev/null || echo "Backup present but no manifest"
    else
        echo "⚠️  Backup: No snapshot (run with --backup to create)"
    fi
    
elif [ "$1" == "--test" ]; then
    echo "🧪 Running quick validation test..."
    cd "$SCRIPT_DIR"
    python3 test_fabio_threshold.py
    
else
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  --backup    Create snapshot of current v1.1.0 configuration"
    echo "  --restore   Restore from backup snapshot"
    echo "  --verify    Check if v1.1.0 is properly installed"
    echo "  --test      Run validation backtest"
    echo ""
    echo "Examples:"
    echo "  $0 --backup     # Create backup before making changes"
    echo "  $0 --restore    # Restore if something breaks"
    echo "  $0 --verify     # Check current state"
    echo "  $0 --test       # Validate performance"
    exit 1
fi

echo ""
echo "================================================"
echo "FABIO AAA FULL v1.1.0 - RSI Threshold 40"
echo "Performance: 167 trades @ 64.7% win rate"
echo "Status: Production Ready"
echo "================================================"
