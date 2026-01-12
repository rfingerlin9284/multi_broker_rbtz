#!/usr/bin/env python3
"""Deep audit of OANDA trading performance."""
import os
import requests
import json
from datetime import datetime, timedelta

# Load token directly
with open('/home/ing/RICK/MULTI_BROKER_PHOENIX/.env') as f:
    for line in f:
        if line.startswith('OANDA_API_TOKEN='):
            token = line.strip().split('=', 1)[1]
            break

headers = {'Authorization': f'Bearer {token}'}
acct = '101-001-31210531-001'
base = 'https://api-fxpractice.oanda.com/v3'

# Get account summary
resp = requests.get(f'{base}/accounts/{acct}/summary', headers=headers)
summary = resp.json().get('account', {})
print("=" * 70)
print("ACCOUNT SUMMARY")
print("=" * 70)
print(f"NAV: ${float(summary.get('NAV', 0)):.2f}")
print(f"Balance: ${float(summary.get('balance', 0)):.2f}")
print(f"Realized P/L: ${float(summary.get('pl', 0)):.2f}")
print(f"Unrealized P/L: ${float(summary.get('unrealizedPL', 0)):.2f}")
print(f"Open Trades: {summary.get('openTradeCount', 0)}")
print(f"Margin Used: ${float(summary.get('marginUsed', 0)):.2f}")

# Get open trades
resp = requests.get(f'{base}/accounts/{acct}/openTrades', headers=headers)
open_trades = resp.json().get('trades', [])
print(f"\n{'='*70}")
print(f"OPEN TRADES ({len(open_trades)})")
print("=" * 70)
for t in open_trades:
    inst = t.get('instrument')
    units = t.get('currentUnits')
    entry = t.get('price')
    pl = float(t.get('unrealizedPL', 0))
    print(f"  {inst}: {units} units @ {entry}, P/L: ${pl:.2f}")

# Get closed trades
resp = requests.get(f'{base}/accounts/{acct}/trades?state=CLOSED&count=200', headers=headers)
closed = resp.json().get('trades', [])
print(f"\n{'='*70}")
print(f"CLOSED TRADES ANALYSIS (Last {len(closed)})")
print("=" * 70)

total_pl = 0
wins = 0
losses = 0
by_instrument = {}
by_day = {}
by_hour = {}
avg_win = 0
avg_loss = 0
win_amounts = []
loss_amounts = []
hold_times = []

for t in closed:
    inst = t.get('instrument', 'UNK')
    pl = float(t.get('realizedPL', 0))
    total_pl += pl
    
    # Parse times
    open_time = t.get('openTime', '')
    close_time = t.get('closeTime', '')
    
    if open_time and close_time:
        try:
            ot = datetime.fromisoformat(open_time.replace('Z', '+00:00'))
            ct = datetime.fromisoformat(close_time.replace('Z', '+00:00'))
            hold_time = (ct - ot).total_seconds() / 60  # minutes
            hold_times.append(hold_time)
            
            day_key = ct.strftime('%Y-%m-%d')
            hour_key = ct.hour
            
            if day_key not in by_day:
                by_day[day_key] = {'pl': 0, 'count': 0, 'wins': 0}
            by_day[day_key]['pl'] += pl
            by_day[day_key]['count'] += 1
            if pl > 0:
                by_day[day_key]['wins'] += 1
                
            if hour_key not in by_hour:
                by_hour[hour_key] = {'pl': 0, 'count': 0, 'wins': 0}
            by_hour[hour_key]['pl'] += pl
            by_hour[hour_key]['count'] += 1
            if pl > 0:
                by_hour[hour_key]['wins'] += 1
        except:
            pass
    
    if pl > 0:
        wins += 1
        win_amounts.append(pl)
    elif pl < 0:
        losses += 1
        loss_amounts.append(pl)
    
    if inst not in by_instrument:
        by_instrument[inst] = {'pl': 0, 'count': 0, 'wins': 0, 'losses': 0, 'win_amt': 0, 'loss_amt': 0}
    by_instrument[inst]['pl'] += pl
    by_instrument[inst]['count'] += 1
    if pl > 0:
        by_instrument[inst]['wins'] += 1
        by_instrument[inst]['win_amt'] += pl
    elif pl < 0:
        by_instrument[inst]['losses'] += 1
        by_instrument[inst]['loss_amt'] += pl

print(f"\nTotal Realized P/L: ${total_pl:.2f}")
print(f"Wins: {wins}, Losses: {losses}")
if (wins+losses) > 0:
    print(f"Win Rate: {wins/(wins+losses)*100:.1f}%")
if win_amounts:
    print(f"Avg Win: ${sum(win_amounts)/len(win_amounts):.2f}")
if loss_amounts:
    print(f"Avg Loss: ${sum(loss_amounts)/len(loss_amounts):.2f}")
if win_amounts and loss_amounts:
    avg_w = sum(win_amounts)/len(win_amounts)
    avg_l = abs(sum(loss_amounts)/len(loss_amounts))
    print(f"Risk/Reward Ratio: {avg_w/avg_l:.2f}:1" if avg_l > 0 else "N/A")
if hold_times:
    print(f"Avg Hold Time: {sum(hold_times)/len(hold_times):.1f} minutes")

print(f"\n{'='*70}")
print("P/L BY INSTRUMENT (sorted by P/L)")
print("=" * 70)
for inst, data in sorted(by_instrument.items(), key=lambda x: x[1]['pl'], reverse=True):
    wr = data['wins']/data['count']*100 if data['count'] > 0 else 0
    avg_w = data['win_amt']/data['wins'] if data['wins'] > 0 else 0
    avg_l = data['loss_amt']/data['losses'] if data['losses'] > 0 else 0
    status = "✅ KEEP" if data['pl'] > 0 else "⚠️ REVIEW" if data['pl'] > -10 else "❌ REMOVE"
    print(f"{inst}: ${data['pl']:.2f} | {data['count']} trades | {wr:.0f}% WR | AvgW: ${avg_w:.2f} AvgL: ${avg_l:.2f} | {status}")

print(f"\n{'='*70}")
print("P/L BY DAY (recent first)")
print("=" * 70)
for day, data in sorted(by_day.items(), reverse=True)[:10]:
    wr = data['wins']/data['count']*100 if data['count'] > 0 else 0
    status = "🟢" if data['pl'] > 0 else "🔴"
    print(f"{day}: ${data['pl']:.2f} | {data['count']} trades | {wr:.0f}% WR {status}")

print(f"\n{'='*70}")
print("P/L BY HOUR (UTC)")
print("=" * 70)
for hour in sorted(by_hour.keys()):
    data = by_hour[hour]
    wr = data['wins']/data['count']*100 if data['count'] > 0 else 0
    bar = "█" * int(abs(data['pl']) / 5) if data['pl'] > 0 else ""
    neg_bar = "░" * int(abs(data['pl']) / 5) if data['pl'] < 0 else ""
    print(f"{hour:02d}:00 | ${data['pl']:>7.2f} | {data['count']:>3} trades | {wr:>3.0f}% WR | {bar}{neg_bar}")

# Recommendations
print(f"\n{'='*70}")
print("🎯 RECOMMENDATIONS")
print("=" * 70)

# Find worst performers
losers = [(k, v) for k, v in by_instrument.items() if v['pl'] < 0]
if losers:
    print("\n🔴 UNDERPERFORMING PAIRS (consider removing):")
    for inst, data in sorted(losers, key=lambda x: x[1]['pl']):
        print(f"   - {inst}: ${data['pl']:.2f} loss over {data['count']} trades")

# Find best performers
winners = [(k, v) for k, v in by_instrument.items() if v['pl'] > 0]
if winners:
    print("\n🟢 TOP PERFORMERS (increase allocation):")
    for inst, data in sorted(winners, key=lambda x: x[1]['pl'], reverse=True)[:5]:
        print(f"   + {inst}: ${data['pl']:.2f} profit over {data['count']} trades")

# Best/worst hours
if by_hour:
    best_hour = max(by_hour.items(), key=lambda x: x[1]['pl'])
    worst_hour = min(by_hour.items(), key=lambda x: x[1]['pl'])
    print(f"\n⏰ TIMING:")
    print(f"   Best hour: {best_hour[0]:02d}:00 UTC (${best_hour[1]['pl']:.2f})")
    print(f"   Worst hour: {worst_hour[0]:02d}:00 UTC (${worst_hour[1]['pl']:.2f})")
