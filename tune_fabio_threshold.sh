#!/usr/bin/env bash
set -e

# Quick tuning script for Fabio AAA Full absorption threshold
# This temporarily lowers the hard-coded 50 to your chosen value for testing
# It targets the common patterns: < 50 in checks and logs
# WARNING: This is a rough sed replace - assumes the threshold is only used for absorption
# If it changes unrelated 50s, revert from backup and tell me (or paste the file for precise patch)

if [ $# -ne 1 ]; then
  echo "Usage: $0 <new_threshold>"
  echo "Examples:"
  echo "  $0 40   # Conservative - likely a few more trades"
  echo "  $0 35   # Moderate - should open up good setups"
  echo "  $0 30   # Aggressive - more trades, monitor win rate/PF"
  echo "  $0 50   # Revert to original"
  exit 1
fi

NEW_THRESH="$1"
FILE="/home/ing/RICK/MULTI_BROKER_PHOENIX/MULTI_BROKER_PHOENIX/multi_broker_phoenix/strategies/fabio_aaa_full.py"

if [ ! -f "$FILE" ]; then
  echo "ERROR: File not found: $FILE"
  echo "Adjust the path if your repo layout is different."
  exit 1
fi

# Backup with timestamp
BACKUP="${FILE}.bak_threshold_$(date +%Y%m%d_%H%M%S)"
cp "$FILE" "$BACKUP"
echo "✅ Backed up original to: $BACKUP"

# Replace the threshold in condition checks and log strings
sed -i "s/< 50[ )]*/< $NEW_THRESH/g" "$FILE"
sed -i "s/< 50)/< $NEW_THRESH)/g" "$FILE"

echo "✅ Absorption threshold tuned to $NEW_THRESH"
echo ""
echo "Next steps:"
echo "1. Run the backtest to see results:"
echo "   cd /home/ing/RICK/RICK_PHOENIX"
echo "   source hive_real/.venv/bin/activate"
echo "   python3 tools/backtest_strategy_pack.py --csv-file /tmp/demo_zones_500candles.csv --symbol EUR_USD --capital 10000 --strategies FABIO_AAA_FULL"
echo ""
echo "2. Compare trades, win rate, P&L, PF vs previous runs."
echo "   Goal: ≥10-12 trades, win rate >60%, positive PF, low DD"
echo ""
echo "3. Try values in order: 40 → 35 → 30"
echo "   Rerun this script with new value each time."
echo ""
echo "To revert any time:"
echo "   cp $BACKUP $FILE"
echo ""
echo "Once we find the sweet spot, I'll give you a clean patch to make it truly configurable (self.min_absorb_score from metadata/.env)."
echo "If the sed touched wrong lines or broke something, revert and paste the full file content so I can do a precise overwrite."
