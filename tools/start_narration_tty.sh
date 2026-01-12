#!/usr/bin/env bash
# Starts a persistent narration terminal that refreshes every 10s and displays human-friendly summaries
JSONL="/tmp/position_narration.jsonl"
JQ_BIN=$(command -v jq || true)

if [ -z "$JQ_BIN" ]; then
    echo "Please install 'jq' to format narration JSON (sudo apt install jq)"
    exit 1
fi

clear
echo "📣 Starting Narration Terminal - showing last 20 entries (refresh every 10s)"
while true; do
    echo "════════════════════════════════════════════════════════════════"
    echo "Narration Snapshot: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "════════════════════════════════════════════════════════════════"
    if [ -f "$JSONL" ]; then
        tail -n 20 "$JSONL" | $JQ_BIN -r '. | "- [\(.timestamp)] \(.human_summary) (event: \(.event))"'
    else
        echo "No narration file found at $JSONL"
    fi
    sleep 10
    echo
done
