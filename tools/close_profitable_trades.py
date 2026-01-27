#!/usr/bin/env python3
"""
🎯 OANDA PROFIT CAPTURE TOOL
Close profitable trades that have been sitting too long!
"""

import requests
from datetime import datetime, timezone
import sys

# OANDA Configuration - Using account -001 where the trades actually are!
OANDA_TOKEN = "15799c2f8f955465e457dd3c646641d7-f18a14a9d33eb6cffc080465dc9717de"
OANDA_ACCOUNT = "101-001-31210531-001"  # The CORRECT account!
BASE_URL = "https://api-fxpractice.oanda.com"

headers = {
    "Authorization": f"Bearer {OANDA_TOKEN}",
    "Content-Type": "application/json"
}


def get_open_trades():
    """Get all open trades from OANDA"""
    url = f"{BASE_URL}/v3/accounts/{OANDA_ACCOUNT}/openTrades"
    resp = requests.get(url, headers=headers)
    return resp.json().get('trades', [])


def close_trade(trade_id):
    """Close a specific trade"""
    url = f"{BASE_URL}/v3/accounts/{OANDA_ACCOUNT}/trades/{trade_id}/close"
    resp = requests.put(url, headers=headers)
    return resp.json()


def analyze_trades():
    """Analyze all open trades and identify ones to close"""
    trades = get_open_trades()
    now = datetime.now(timezone.utc)
    
    print("=" * 70)
    print("🎯 OANDA PROFIT CAPTURE ANALYSIS")
    print("=" * 70)
    print(f"\n📊 Found {len(trades)} open trades\n")
    
    profitable = []
    losers = []
    
    for trade in sorted(trades, key=lambda x: float(x.get('unrealizedPL', 0)), reverse=True):
        trade_id = trade.get('id')
        instrument = trade.get('instrument')
        units = int(float(trade.get('currentUnits', 0)))
        pnl = float(trade.get('unrealizedPL', 0))
        open_time_str = trade.get('openTime', '')
        
        # Calculate age
        if open_time_str:
            open_time = datetime.fromisoformat(open_time_str.replace('Z', '+00:00'))
            age_hours = (now - open_time).total_seconds() / 3600
        else:
            age_hours = 0
        
        if pnl > 0:
            status = "🟢"
            profitable.append({
                'id': trade_id,
                'instrument': instrument,
                'units': units,
                'pnl': pnl,
                'age_hours': age_hours
            })
        else:
            status = "🔴"
            losers.append({
                'id': trade_id,
                'instrument': instrument,
                'units': units,
                'pnl': pnl,
                'age_hours': age_hours
            })
        
        print(f"  {status} #{trade_id}: {instrument:8} | {units:>6} units | {age_hours:>5.1f}h | ${pnl:>7.2f}")
    
    total_profit = sum(t['pnl'] for t in profitable)
    total_loss = sum(t['pnl'] for t in losers)
    
    print(f"\n{'='*70}")
    print(f"📈 PROFITABLE: {len(profitable)} trades = ${total_profit:.2f}")
    print(f"📉 LOSING: {len(losers)} trades = ${total_loss:.2f}")
    print(f"💰 NET UNREALIZED: ${total_profit + total_loss:.2f}")
    
    return profitable, losers


def close_profitable_trades(min_profit=0.50, min_age_hours=1.0, dry_run=True):
    """Close all profitable trades meeting criteria"""
    trades = get_open_trades()
    now = datetime.now(timezone.utc)
    
    closed_count = 0
    total_realized = 0.0
    
    print(f"\n{'='*70}")
    if dry_run:
        print("🔍 DRY RUN - Showing trades that WOULD be closed:")
    else:
        print("🎯 CLOSING PROFITABLE TRADES:")
    print(f"   Criteria: P/L > ${min_profit:.2f} AND age > {min_age_hours:.1f} hours")
    print("=" * 70)
    
    for trade in trades:
        trade_id = trade.get('id')
        instrument = trade.get('instrument')
        pnl = float(trade.get('unrealizedPL', 0))
        open_time_str = trade.get('openTime', '')
        
        if open_time_str:
            open_time = datetime.fromisoformat(open_time_str.replace('Z', '+00:00'))
            age_hours = (now - open_time).total_seconds() / 3600
        else:
            age_hours = 0
        
        # Check criteria
        if pnl >= min_profit and age_hours >= min_age_hours:
            if dry_run:
                print(f"  📋 #{trade_id}: {instrument} | ${pnl:.2f} profit | {age_hours:.1f}h old")
                closed_count += 1
                total_realized += pnl
            else:
                print(f"  ⏳ Closing #{trade_id}: {instrument} | ${pnl:.2f} profit...")
                result = close_trade(trade_id)
                if 'orderFillTransaction' in result:
                    realized = float(result['orderFillTransaction'].get('pl', 0))
                    print(f"  ✅ CLOSED! Realized P/L: ${realized:.2f}")
                    closed_count += 1
                    total_realized += realized
                else:
                    print(f"  ❌ Failed: {result}")
    
    print(f"\n{'='*70}")
    if dry_run:
        print(f"💰 WOULD CLOSE: {closed_count} trades for ~${total_realized:.2f}")
        print(f"\n⚠️  To actually close, run with: --execute")
    else:
        print(f"✅ CLOSED: {closed_count} trades")
        print(f"💰 REALIZED P/L: ${total_realized:.2f}")
    
    return closed_count, total_realized


def close_all_losers(max_loss=-0.50, min_age_hours=6.0, dry_run=True):
    """Close stale losing trades (zombies)"""
    trades = get_open_trades()
    now = datetime.now(timezone.utc)
    
    closed_count = 0
    total_loss = 0.0
    
    print(f"\n{'='*70}")
    if dry_run:
        print("💀 DRY RUN - ZOMBIE TRADES (losers sitting too long):")
    else:
        print("💀 CUTTING ZOMBIE TRADES:")
    print(f"   Criteria: P/L < ${max_loss:.2f} AND age > {min_age_hours:.1f} hours")
    print("=" * 70)
    
    for trade in trades:
        trade_id = trade.get('id')
        instrument = trade.get('instrument')
        pnl = float(trade.get('unrealizedPL', 0))
        open_time_str = trade.get('openTime', '')
        
        if open_time_str:
            open_time = datetime.fromisoformat(open_time_str.replace('Z', '+00:00'))
            age_hours = (now - open_time).total_seconds() / 3600
        else:
            age_hours = 0
        
        # Check zombie criteria: losing AND old
        if pnl <= max_loss and age_hours >= min_age_hours:
            if dry_run:
                print(f"  💀 #{trade_id}: {instrument} | ${pnl:.2f} loss | {age_hours:.1f}h old")
                closed_count += 1
                total_loss += pnl
            else:
                print(f"  ⏳ Killing #{trade_id}: {instrument} | ${pnl:.2f} loss...")
                result = close_trade(trade_id)
                if 'orderFillTransaction' in result:
                    realized = float(result['orderFillTransaction'].get('pl', 0))
                    print(f"  💀 KILLED! Realized: ${realized:.2f}")
                    closed_count += 1
                    total_loss += realized
                else:
                    print(f"  ❌ Failed: {result}")
    
    if closed_count == 0:
        print("  (No zombie trades found)")
    
    print(f"\n{'='*70}")
    if dry_run:
        print(f"💀 WOULD CUT: {closed_count} zombies for ${total_loss:.2f}")
    else:
        print(f"💀 KILLED: {closed_count} zombies")
        print(f"📉 REALIZED LOSS: ${total_loss:.2f}")
    
    return closed_count, total_loss


def close_all_trades(dry_run=True):
    """Nuclear option - close ALL open trades"""
    trades = get_open_trades()
    
    print(f"\n{'='*70}")
    if dry_run:
        print("☢️  DRY RUN - WOULD CLOSE ALL TRADES:")
    else:
        print("☢️  CLOSING ALL TRADES:")
    print("=" * 70)
    
    total_pnl = 0.0
    for trade in trades:
        trade_id = trade.get('id')
        instrument = trade.get('instrument')
        pnl = float(trade.get('unrealizedPL', 0))
        total_pnl += pnl
        
        if dry_run:
            status = "🟢" if pnl > 0 else "🔴"
            print(f"  {status} #{trade_id}: {instrument} | ${pnl:.2f}")
        else:
            result = close_trade(trade_id)
            if 'orderFillTransaction' in result:
                realized = float(result['orderFillTransaction'].get('pl', 0))
                print(f"  ✅ #{trade_id}: ${realized:.2f}")
            else:
                print(f"  ❌ #{trade_id}: Failed")
    
    print(f"\n{'='*70}")
    print(f"💰 TOTAL P/L: ${total_pnl:.2f}")
    if dry_run:
        print(f"\n⚠️  To close ALL trades, run with: --close-all --execute")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="OANDA Profit Capture Tool")
    parser.add_argument('--analyze', action='store_true', help="Just analyze trades")
    parser.add_argument('--close-profitable', action='store_true', help="Close profitable trades")
    parser.add_argument('--close-zombies', action='store_true', help="Close stale losing trades")
    parser.add_argument('--close-all', action='store_true', help="Close ALL trades")
    parser.add_argument('--execute', action='store_true', help="Actually execute (not dry run)")
    parser.add_argument('--min-profit', type=float, default=0.50, help="Min profit to close (default: $0.50)")
    parser.add_argument('--min-age', type=float, default=1.0, help="Min age in hours (default: 1.0)")
    
    args = parser.parse_args()
    dry_run = not args.execute
    
    if args.analyze or (not args.close_profitable and not args.close_zombies and not args.close_all):
        analyze_trades()
    
    if args.close_profitable:
        close_profitable_trades(
            min_profit=args.min_profit,
            min_age_hours=args.min_age,
            dry_run=dry_run
        )
    
    if args.close_zombies:
        close_all_losers(
            max_loss=-0.50,
            min_age_hours=6.0,
            dry_run=dry_run
        )
    
    if args.close_all:
        close_all_trades(dry_run=dry_run)
    
    if dry_run and (args.close_profitable or args.close_zombies or args.close_all):
        print("\n" + "=" * 70)
        print("⚠️  This was a DRY RUN. Add --execute to actually close trades.")
        print("=" * 70)
