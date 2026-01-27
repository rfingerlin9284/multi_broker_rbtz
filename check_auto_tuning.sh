#!/bin/bash
# Quick commands to monitor auto-tuning system

case "${1:-help}" in
  status)
    echo "Checking auto-tuning status..."
    python3 /home/ing/RICK/MULTI_BROKER_PHOENIX/view_auto_tuning.py
    ;;
  logs)
    echo "Watching for ATR auto-tuning logs..."
    tail -f /home/ing/RICK/MULTI_BROKER_PHOENIX/live_extreme_engine.log | grep -E "AUTO-TUNE|ATR TRAIL|INITIALIZED"
    ;;
  json)
    echo "Raw tuning data:"
    cat /home/ing/RICK/MULTI_BROKER_PHOENIX/atr_tuning_metrics.json 2>/dev/null | python3 -m json.tool 2>/dev/null || echo "⏳ No trades yet - waiting for first entry..."
    ;;
  clear)
    echo "🔄 Clearing auto-tuning data..."
    rm -f /home/ing/RICK/MULTI_BROKER_PHOENIX/atr_tuning_metrics.json
    echo "✅ Cleared! System will start learning from scratch on next trade."
    ;;
  *)
    cat << 'EOF'
🤖 AUTO-TUNING MONITOR

Usage:
  ./check_auto_tuning.sh status   - Show tuning dashboard
  ./check_auto_tuning.sh logs     - Watch auto-tuning logs
  ./check_auto_tuning.sh json     - Show raw tuning data
  ./check_auto_tuning.sh clear    - Clear all learning (start fresh)

Examples:
  # Check what system learned so far
  ./check_auto_tuning.sh status

  # Watch logs in real-time
  ./check_auto_tuning.sh logs

  # See raw JSON data
  ./check_auto_tuning.sh json

The system automatically learns optimal ATR multipliers for each symbol.
No coding or manual tuning needed! 🚀
EOF
    ;;
esac
