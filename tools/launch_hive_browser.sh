#!/bin/bash
# Launch HIVE Real Browser for ChatGPT Integration

set -e

BASE_DIR="/home/ing/RICK/MULTI_BROKER_PHOENIX"
HIVE_DIR="$BASE_DIR/hive_real"
PROFILE_DIR="$HIVE_DIR/browser_profile"

echo "=========================================="
echo "🐝 HIVE BROWSER LAUNCHER"
echo "=========================================="
echo ""

# Ensure directories exist
mkdir -p "$HIVE_DIR/inbox"
mkdir -p "$HIVE_DIR/outbox"
mkdir -p "$PROFILE_DIR"

# Check if browser already running on port 9222
if curl -s http://127.0.0.1:9222/json/version &>/dev/null; then
    echo "✅ Chrome already running on port 9222"
else
    echo "🚀 Launching Chrome with remote debugging..."
    echo ""
    echo "📋 YOU WILL SEE A CHROME WINDOW:"
    echo "   1. Log into ChatGPT business account"
    echo "   2. Get to main chat interface"
    echo "   3. LEAVE WINDOW OPEN"
    echo ""
    
    # Launch Chrome in background
    chromium-browser \
        --remote-debugging-port=9222 \
        --user-data-dir="$PROFILE_DIR" \
        "https://chatgpt.com/" \
        > /dev/null 2>&1 &
    
    CHROME_PID=$!
    echo "✅ Chrome launched (PID: $CHROME_PID)"
    sleep 3
fi

# Check if worker already running
if [ -f "$HIVE_DIR/worker.pid" ]; then
    OLD_PID=$(cat "$HIVE_DIR/worker.pid")
    if ps -p "$OLD_PID" &>/dev/null; then
        echo "✅ Worker already running (PID: $OLD_PID)"
        echo ""
        echo "🎯 HIVE BROWSER READY!"
        echo "   Chrome: http://127.0.0.1:9222"
        echo "   Logs: tail -f $HIVE_DIR/worker.log"
        exit 0
    fi
fi

echo ""
echo "⏳ Waiting for Chrome to be ready..."
for i in {1..10}; do
    if curl -s http://127.0.0.1:9222/json/version &>/dev/null; then
        echo "✅ Chrome is ready!"
        break
    fi
    sleep 1
done

# Check if Playwright installed
if ! python3 -c "import playwright" 2>/dev/null; then
    echo ""
    echo "⚠️  Playwright not installed!"
    echo ""
    echo "📦 Run these commands:"
    echo "   pip install playwright"
    echo "   playwright install chromium"
    echo ""
    exit 1
fi

echo ""
echo "🤖 Starting browser worker..."
cd "$HIVE_DIR"

export HIVE_USE_CDP=1
export HIVE_CDP_PORT=9222

nohup python3 hive_chatgpt_worker.py --poll 0.5 > worker.log 2>&1 &
WORKER_PID=$!
echo $WORKER_PID > worker.pid

echo "✅ Worker started (PID: $WORKER_PID)"
echo ""
echo "🎯 HIVE BROWSER READY!"
echo ""
echo "📊 Status:"
echo "   Chrome: http://127.0.0.1:9222"
echo "   Worker: PID $WORKER_PID"
echo "   Logs: tail -f $HIVE_DIR/worker.log"
echo ""
echo "🔐 NEXT: Log into ChatGPT in the Chrome window!"
