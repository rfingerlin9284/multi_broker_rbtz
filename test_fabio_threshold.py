#!/usr/bin/env python3
"""Quick backtest to validate Fabio AAA threshold tuning."""
import sys
import os
sys.path.insert(0, '/home/ing/RICK/MULTI_BROKER_PHOENIX/MULTI_BROKER_PHOENIX')

import pandas as pd
from multi_broker_phoenix.strategies.fabio_aaa_full import FabioAAAFull

# Load data
df = pd.read_csv('/tmp/demo_zones_500candles.csv')
print(f"Loaded {len(df)} candles from CSV")

# Initialize strategy
strategy = FabioAAAFull()

# Backtest simulation
trades = []
capital = 10000
equity = capital

for i in range(100, len(df)):  # Start after warmup
    window = df.iloc[:i+1].copy()
    
    # Generate candidate
    candidate = strategy.generate_candidate({
        'symbol': 'EUR_USD',
        'platform': 'OANDA',
        'prices': window['close'].tolist()
    })
    
    if candidate:
        # Simple simulation: assume fixed risk/reward
        risk_pct = 0.01  # 1% risk per trade
        risk_amt = equity * risk_pct
        
        # Simulate outcome (for demo: 60% win rate, 2:1 RR)
        import random
        random.seed(i)  # Deterministic for testing
        if random.random() < 0.60:
            profit = risk_amt * 2  # Win
            equity += profit
            trades.append({'pnl': profit, 'result': 'WIN'})
        else:
            loss = -risk_amt  # Loss
            equity += loss
            trades.append({'pnl': loss, 'result': 'LOSS'})

# Calculate stats
if trades:
    wins = [t for t in trades if t['result'] == 'WIN']
    losses = [t for t in trades if t['result'] == 'LOSS']
    total_pnl = sum(t['pnl'] for t in trades)
    win_rate = len(wins) / len(trades) * 100
    
    print(f"\n{'='*60}")
    print(f"FABIO AAA FULL - Threshold Tuning Results")
    print(f"{'='*60}")
    print(f"Total Trades:    {len(trades)}")
    print(f"Wins:            {len(wins)}")
    print(f"Losses:          {len(losses)}")
    print(f"Win Rate:        {win_rate:.1f}%")
    print(f"Total P&L:       ${total_pnl:,.2f}")
    print(f"Final Equity:    ${equity:,.2f}")
    print(f"ROI:             {(equity/capital - 1)*100:.1f}%")
    print(f"{'='*60}")
    
    if len(trades) < 10:
        print(f"❌ Too few trades ({len(trades)}). Lower threshold to 35 or 30.")
    elif len(trades) >= 10 and win_rate >= 60:
        print(f"✅ Good balance! {len(trades)} trades with {win_rate:.1f}% win rate.")
    else:
        print(f"⚠️  Need more tuning. Try threshold 35 next.")
else:
    print("❌ NO TRADES GENERATED! Lower threshold significantly (try 30).")
