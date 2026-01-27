#!/usr/bin/env python3
"""
AUTO-TUNING DASHBOARD
View what the system is learning about optimal ATR multipliers
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

def print_tuning_status():
    """Display current auto-tuning status."""
    
    tuning_file = Path("/home/ing/RICK/MULTI_BROKER_PHOENIX/atr_tuning_metrics.json")
    
    if not tuning_file.exists():
        print("⏳ Auto-tuning system starting... (waiting for first trades)")
        return
    
    try:
        with open(tuning_file, 'r') as f:
            metrics = json.load(f)
    except:
        print("❌ Error reading tuning file")
        return
    
    print("\n" + "="*80)
    print("🤖 ATR AUTO-TUNER - LEARNING DASHBOARD")
    print("="*80)
    print(f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    if not metrics:
        print("⏳ Waiting for first trades... System will learn optimal multipliers automatically.")
        print("="*80 + "\n")
        return
    
    total_trades = 0
    
    for symbol, data in sorted(metrics.items()):
        trades = len(data.get('trades', []))
        if trades == 0:
            continue
        
        total_trades += trades
        wins = data.get('win_count', 0)
        losses = data.get('loss_count', 0)
        total = wins + losses
        win_rate = (wins / total * 100) if total > 0 else 0
        
        current_mult = data.get('current_multiplier', 2.5)
        optimal_mult = data.get('optimal_multiplier', 2.5)
        adjustments = data.get('adjustment_count', 0)
        
        # Color code multiplier changes
        if current_mult > optimal_mult * 1.1:
            mult_status = f"📈 {current_mult:.2f}x (tightening too much)"
        elif current_mult < optimal_mult * 0.9:
            mult_status = f"📉 {current_mult:.2f}x (loosening too much)"
        else:
            mult_status = f"✅ {current_mult:.2f}x (optimal)"
        
        # Get recent P/L trend
        recent_trades = data.get('trades', [])[-5:]
        if recent_trades:
            recent_pnl = [t['pnl_pct'] for t in recent_trades]
            recent_win_rate = sum(1 for p in recent_pnl if p > 0.1) / len(recent_pnl) * 100
            trend = f" | Last 5: {recent_win_rate:.0f}% wins"
        else:
            trend = ""
        
        print(f"   {symbol}")
        print(f"      Multiplier: {mult_status}")
        print(f"      Record: {wins}W-{losses}L ({win_rate:.0f}% win rate){trend}")
        print(f"      Adjustments: {adjustments} | Trades: {trades}")
        
        # Show recent trades
        if recent_trades and len(recent_trades) >= 3:
            print(f"      Recent: ", end="")
            for trade in recent_trades[-3:]:
                pnl = trade['pnl_pct']
                symbol_emoji = "✅" if pnl > 0.1 else "❌"
                print(f"{symbol_emoji}{pnl:+.1f}% ", end="")
            print()
        
        print()
    
    print("="*80)
    print(f"📊 SYSTEM STATS: {total_trades} trades analyzed")
    print(f"🎯 LEARNING: System automatically adjusts multipliers to improve win rate")
    print(f"📈 TREND: Optimal multipliers will converge as more data is collected")
    print("="*80)
    print("\nThe system is learning! Each trade outcome teaches it which multipliers work best.")
    print("Tighter multipliers (1.5x-2.0x): Protect profits in choppy markets")
    print("Looser multipliers (2.8x-3.5x): Allow profits to run in trending markets")
    print("\n")

if __name__ == "__main__":
    print_tuning_status()
