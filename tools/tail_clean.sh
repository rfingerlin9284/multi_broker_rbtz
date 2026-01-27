#!/bin/bash
# RBOTzilla Clean Log Tail - Filters out noise, shows meaningful activity
# Usage: ./tools/tail_clean.sh

cd "$(dirname "$0")/.." || exit 1

LOG_FILE="${1:-logs/oanda/engine.log}"

# Filter patterns to EXCLUDE (noisy, unhelpful)
EXCLUDE_PATTERNS=(
    "OANDA Practice client initialized"
    "No trade modification method found"
    "EXIT_MANAGER_TICK positions"
    "PROTECT_LOOP_TICK timestamp"
    "prices collected"
)

# Build grep exclusion pattern
EXCLUDE=""
for p in "${EXCLUDE_PATTERNS[@]}"; do
    if [ -z "$EXCLUDE" ]; then
        EXCLUDE="$p"
    else
        EXCLUDE="$EXCLUDE|$p"
    fi
done

echo "═══════════════════════════════════════════════════════════════════════"
echo "  🤖 RBOTzilla CLEAN LOG (filtering noise)"
echo "  File: $LOG_FILE"
echo "═══════════════════════════════════════════════════════════════════════"
echo ""

# Tail with filtering
tail -f "$LOG_FILE" 2>/dev/null | grep -Ev "$EXCLUDE" | while IFS= read -r line; do
    # Colorize based on content
    if [[ "$line" == *"ERROR"* ]] || [[ "$line" == *"FATAL"* ]] || [[ "$line" == *"❌"* ]]; then
        echo -e "\033[0;31m$line\033[0m"  # Red
    elif [[ "$line" == *"WARNING"* ]] || [[ "$line" == *"⚠️"* ]]; then
        echo -e "\033[1;33m$line\033[0m"  # Yellow
    elif [[ "$line" == *"✅"* ]] || [[ "$line" == *"PASS"* ]] || [[ "$line" == *"ACTIVE"* ]]; then
        echo -e "\033[0;32m$line\033[0m"  # Green
    elif [[ "$line" == *"OCO"* ]] || [[ "$line" == *"TRADE"* ]] || [[ "$line" == *"ORDER"* ]]; then
        echo -e "\033[0;36m$line\033[0m"  # Cyan
    elif [[ "$line" == *"🤖"* ]] || [[ "$line" == *"AI"* ]] || [[ "$line" == *"Hive"* ]]; then
        echo -e "\033[0;35m$line\033[0m"  # Magenta
    elif [[ "$line" == *"═"* ]] || [[ "$line" == *"🚀"* ]] || [[ "$line" == *"🔄"* ]]; then
        echo -e "\033[1m$line\033[0m"     # Bold
    else
        echo "$line"
    fi
done
