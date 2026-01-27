#!/bin/bash
# Quick start script for HIVE with real browser

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
HIVE_DIR="$PROJECT_DIR/hive_real"

echo "========================================"
echo "🐝 HIVE REAL BROWSER - Quick Start"
echo "========================================"
echo

# Check if hive_chatgpt_worker.py exists
if [ ! -f "$HIVE_DIR/hive_chatgpt_worker.py" ]; then
    echo "❌ hive_chatgpt_worker.py not found in $HIVE_DIR"
    echo
    echo "📝 You need to:"
    echo "   1. Copy hive_chatgpt_worker.py to $HIVE_DIR/"
    echo "   2. Copy hive_llm_queue.py to $HIVE_DIR/"
    echo
    echo "These scripts handle the browser automation."
    exit 1
fi

# Create directories
mkdir -p "$HIVE_DIR/inbox"
mkdir -p "$HIVE_DIR/outbox"
mkdir -p "$HIVE_DIR/browser_profile"

echo "✅ Directories ready"
echo

# Check if browser worker is already running
if pgrep -f "hive_chatgpt_worker.py" > /dev/null; then
    echo "⚠️  Browser worker already running"
    PID=$(pgrep -f "hive_chatgpt_worker.py")
    echo "   PID: $PID"
    echo
    read -p "Kill and restart? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        kill $PID
        sleep 2
    else
        echo "Keeping existing worker"
        exit 0
    fi
fi

# Check if Chrome is running with remote debugging
if ! lsof -i:9222 > /dev/null 2>&1; then
    echo "⚠️  No browser on port 9222"
    echo
    echo "📝 You need to launch Chrome/Chromium with remote debugging:"
    echo
    echo "Linux/WSL:"
    echo "  chromium-browser --remote-debugging-port=9222 \\"
    echo "    --user-data-dir=$HIVE_DIR/browser_profile \\"
    echo "    https://chatgpt.com/ &"
    echo
    echo "Windows:"
    echo "  chrome.exe --remote-debugging-port=9222 \\"
    echo "    --user-data-dir=C:\\ChromeProfile\\RickPhoenix \\"
    echo "    https://chatgpt.com/"
    echo
    read -p "Launch browser now? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Try to launch browser
        if command -v chromium-browser &> /dev/null; then
            chromium-browser --remote-debugging-port=9222 \
                --user-data-dir="$HIVE_DIR/browser_profile" \
                https://chatgpt.com/ &
            echo "✅ Browser launched"
            sleep 3
        elif command -v google-chrome &> /dev/null; then
            google-chrome --remote-debugging-port=9222 \
                --user-data-dir="$HIVE_DIR/browser_profile" \
                https://chatgpt.com/ &
            echo "✅ Browser launched"
            sleep 3
        else
            echo "❌ Chrome/Chromium not found. Please launch manually."
            exit 1
        fi
    else
        exit 1
    fi
fi

echo "✅ Browser detected on port 9222"
echo

# Start browser worker
echo "🚀 Starting browser worker..."
cd "$HIVE_DIR"

export HIVE_USE_CDP=1
export HIVE_CDP_PORT=9222

nohup python3 hive_chatgpt_worker.py \
    --poll 0.5 \
    --timeout 60.0 \
    > worker.log 2>&1 &

WORKER_PID=$!
echo $WORKER_PID > worker.pid

echo "✅ Browser worker started (PID: $WORKER_PID)"
echo

# Wait a bit and check status
sleep 2

if ps -p $WORKER_PID > /dev/null; then
    echo "✅ Worker is running!"
    echo
    echo "📊 Logs:"
    echo "   tail -f $HIVE_DIR/worker.log"
    echo
    echo "🛑 Stop:"
    echo "   kill $WORKER_PID"
    echo
    echo "📝 Login to ChatGPT:"
    echo "   1. Go to browser window"
    echo "   2. Log in with your business account"
    echo "   3. Worker will detect and start processing"
    echo
    echo "🎯 Test:"
    echo "   python3 $PROJECT_DIR/MULTI_BROKER_PHOENIX/multi_broker_phoenix/engines/hive_browser_bridge.py"
else
    echo "❌ Worker failed to start"
    echo "Check log: $HIVE_DIR/worker.log"
    exit 1
fi

echo
echo "========================================"
echo "✅ HIVE Real Browser Ready!"
echo "========================================"
