#!/bin/bash
# RICK HUD Management Script

HUD_PID_FILE="/tmp/hud_server.pid"
HUD_PORT=8889
HUD_DIR="/home/ing/RICK/MULTI_BROKER_PHOENIX/hive_dashboard"

case "$1" in
    start)
        echo "🚀 Starting RICK Clean HUD..."
        
        # Kill any existing server on the port
        lsof -ti:$HUD_PORT | xargs kill -9 2>/dev/null
        
        # Start new server
        cd "$HUD_DIR" && nohup python3 -m http.server $HUD_PORT --bind 127.0.0.1 > /tmp/hud_server.log 2>&1 &
        echo $! > "$HUD_PID_FILE"
        
        sleep 1
        
        echo "✅ Clean HUD server started (PID: $(cat $HUD_PID_FILE))"
        echo ""
        echo "🎯 OPEN IN YOUR BROWSER:"
        echo "   http://127.0.0.1:$HUD_PORT/clean_hud.html"
        echo ""
        ;;
        
    stop)
        echo "🛑 Stopping RICK HUD..."
        
        if [ -f "$HUD_PID_FILE" ]; then
            PID=$(cat "$HUD_PID_FILE")
            kill -9 $PID 2>/dev/null && echo "✅ Stopped HUD server (PID: $PID)"
            rm -f "$HUD_PID_FILE"
        fi
        
        # Also kill any process on the port
        lsof -ti:$HUD_PORT | xargs kill -9 2>/dev/null
        
        echo "✅ HUD server stopped"
        ;;
        
    restart)
        $0 stop
        sleep 1
        $0 start
        ;;
        
    status)
        if [ -f "$HUD_PID_FILE" ]; then
            PID=$(cat "$HUD_PID_FILE")
            if ps -p $PID > /dev/null 2>&1; then
                echo "✅ HUD server is running (PID: $PID)"
                echo "   URL: http://127.0.0.1:$HUD_PORT/clean_hud.html"
            else
                echo "❌ HUD server is not running (stale PID file)"
                rm -f "$HUD_PID_FILE"
            fi
        else
            echo "❌ HUD server is not running"
        fi
        ;;
        
    *)
        echo "RICK HUD Management"
        echo ""
        echo "Usage: $0 {start|stop|restart|status}"
        echo ""
        echo "Commands:"
        echo "  start   - Start the clean HUD server"
        echo "  stop    - Stop the HUD server"
        echo "  restart - Restart the HUD server"
        echo "  status  - Check if HUD server is running"
        echo ""
        exit 1
        ;;
esac

exit 0
