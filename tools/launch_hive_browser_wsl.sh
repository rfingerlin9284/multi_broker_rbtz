#!/bin/bash
# Launch Chrome on Windows (for WSL users) with remote debugging

echo "=========================================="
echo "🪟 HIVE BROWSER LAUNCHER (WSL → Windows)"
echo "=========================================="
echo ""
echo "🚀 STEP 1: Launch Chrome on WINDOWS"
echo ""
echo "   Open PowerShell or CMD on Windows and run:"
echo ""
echo '   "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir=C:\temp\chrome_hive https://chatgpt.com/'
echo ""
echo "   OR if using Chrome Beta/Dev:"
echo ""
echo '   "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir=C:\temp\chrome_hive https://chatgpt.com/'
echo ""
echo "📋 This will:"
echo "   1. Open a visible Chrome window on Windows"
echo "   2. Navigate to ChatGPT"
echo "   3. Enable remote debugging on port 9222"
echo ""
echo "⏳ Waiting for you to launch Chrome on Windows..."
echo "   (Press Ctrl+C to cancel)"
echo ""

# Wait for Chrome to be available
while true; do
    # Try to connect via Windows host IP
    HOST_IP=$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}')
    
    if curl -s "http://${HOST_IP}:9222/json/version" &>/dev/null; then
        echo "✅ Chrome detected at ${HOST_IP}:9222"
        break
    fi
    
    echo -n "."
    sleep 2
done

echo ""
echo ""
echo "🔐 STEP 2: Log into ChatGPT in the Chrome window"
echo ""
echo "⏳ Waiting for you to log in..."
echo "   (Script will continue once logged in)"
echo ""

BASE_DIR="/home/ing/RICK/MULTI_BROKER_PHOENIX"
HIVE_DIR="$BASE_DIR/hive_real"

# Ensure directories
mkdir -p "$HIVE_DIR/inbox"
mkdir -p "$HIVE_DIR/outbox"

# Stop old worker if running
if [ -f "$HIVE_DIR/worker.pid" ]; then
    OLD_PID=$(cat "$HIVE_DIR/worker.pid")
    kill -9 "$OLD_PID" 2>/dev/null || true
fi

echo "🤖 STEP 3: Starting browser worker..."
echo ""

cd "$HIVE_DIR"

# Set CDP URL to Windows host
export HIVE_USE_CDP=1
export HIVE_CDP_URL="http://${HOST_IP}:9222"

source "$BASE_DIR/.venv/bin/activate"
nohup python3 hive_chatgpt_worker.py --poll 0.5 > worker.log 2>&1 &
WORKER_PID=$!
echo $WORKER_PID > worker.pid

echo "✅ Worker started (PID: $WORKER_PID)"
echo ""
echo "🎯 HIVE BROWSER READY!"
echo ""
echo "📊 Status:"
echo "   Chrome (Windows): ${HOST_IP}:9222"
echo "   Worker (WSL): PID $WORKER_PID"
echo "   Logs: tail -f $HIVE_DIR/worker.log"
echo ""
echo "✅ COMPLETE: Worker is now controlling your Windows Chrome!"
