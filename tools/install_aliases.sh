#!/bin/bash
# Add RICK aliases to .bashrc for easy access

BASHRC="$HOME/.bashrc"

echo "🔧 Adding RICK aliases to $BASHRC..."
echo ""

# Check if aliases already exist
if grep -q "rick-positions" "$BASHRC" 2>/dev/null; then
    echo "✅ Aliases already exist in .bashrc"
    echo "   To update, manually edit: nano ~/.bashrc"
else
    # Append aliases
    cat >> "$BASHRC" << 'ALIAS_EOF'

# ═══════════════════════════════════════════════════════════
# RICK TRADING BATTLESTATION ALIASES
# ═══════════════════════════════════════════════════════════

# View live positions with ticket numbers and trailing stops
alias rick-positions='bash ~/RICK/MULTI_BROKER_PHOENIX/tools/show_positions.sh'

# Watch live position updates in real-time
alias rick-watch='tail -f ~/RICK/MULTI_BROKER_PHOENIX/logs/rick_battlestation.log | grep -E "(POSITION|STOP|TICKET|SL)"'

# Check market status (which markets are open)
alias rick-status='bash ~/RICK/MULTI_BROKER_PHOENIX/tools/status.sh'

# Start autonomous trading
alias rick-start='cd ~/RICK/MULTI_BROKER_PHOENIX && source .venv/bin/activate && source <(grep -E "^(OPENAI_API_KEY|XAI_API_KEY|DEEPSEEK_API_KEY)=" .env | sed "s/^/export /") && export PYTHONPATH="$PWD:$PWD/MULTI_BROKER_PHOENIX" && nohup python3 -u tools/autonomous_trading.py > logs/auto.log 2>&1 & echo "🚀 Started PID: $!" && sleep 3 && tail -30 logs/auto.log'

# Stop trading
alias rick-stop='pkill -f autonomous_trading && echo "⏸️  Stopped"'

# View live logs
alias rick-logs='tail -f ~/RICK/MULTI_BROKER_PHOENIX/logs/auto.log'

# Quick battlestation launch
alias rick='cd ~/RICK/MULTI_BROKER_PHOENIX'

ALIAS_EOF

    echo "✅ Aliases added to .bashrc"
    echo ""
    echo "🔄 Reload with: source ~/.bashrc"
    echo ""
    echo "📋 Available commands:"
    echo "   rick-positions  → Show all open positions with SL tracking"
    echo "   rick-watch      → Live stream of position updates"
    echo "   rick-status     → Check which markets are open"
    echo "   rick-start      → Launch autonomous trading"
    echo "   rick-stop       → Stop trading"
    echo "   rick-logs       → View live logs"
    echo "   rick            → Navigate to RICK directory"
fi

echo ""
echo "💡 Run 'source ~/.bashrc' to activate now"
echo ""
