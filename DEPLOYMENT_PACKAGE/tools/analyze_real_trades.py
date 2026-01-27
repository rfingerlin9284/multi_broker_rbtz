#!/usr/bin/env python3
"""
ANALYZE REAL TRADING DATA
Parse actual OANDA transactions to see what REALLY happened
"""
import csv
import sys
from datetime import datetime
from collections import defaultdict

def analyze_oanda_transactions(csv_path):
    """Parse OANDA transactions and calculate REAL performance"""
    
    trades = []
    balance_history = []
    
    with open(csv_path, 'r', encoding='utf-8-sig') as f:  # Handle BOM
        reader = csv.DictReader(f)
        for row in reader:
            ticket = row.get('TICKET', '')
            if not ticket or ticket.strip() == '':
                continue
                
            trans_type = row.get('TRANSACTION TYPE', '').strip()
            pl = row.get('PL', '').strip()
            balance = row.get('BALANCE', '').strip()
            instrument = row.get('INSTRUMENT', '').strip()
            direction = row.get('DIRECTION', '').strip()
            details = row.get('DETAILS', '').strip()
            
            # Track balance
            if balance and balance != '':
                try:
                    balance_history.append(float(balance))
                except:
                    pass
            
            # Track CLOSED trades (stop loss or take profit fills)
            if trans_type == 'ORDER_FILL' and ('STOP_LOSS' in details or 'TAKE_PROFIT' in details):
                if pl and pl != '':
                    try:
                        pnl = float(pl)
                        trades.append({
                            'date': row.get('TRANSACTION DATE', ''),
                            'instrument': instrument,
                            'direction': direction,
                            'pnl': pnl,
                            'balance': float(balance) if balance else 0,
                            'type': details
                        })
                    except Exception as e:
                        print(f"Error parsing trade: {e}, row: {row}")
                        pass
    
    if not trades:
        print("❌ No trades with P&L found")
        return
    
    # Calculate statistics
    total_trades = len(trades)
    wins = [t for t in trades if t['pnl'] > 0]
    losses = [t for t in trades if t['pnl'] < 0]
    
    total_pnl = sum(t['pnl'] for t in trades)
    win_rate = len(wins) / total_trades * 100 if total_trades > 0 else 0
    
    avg_win = sum(t['pnl'] for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t['pnl'] for t in losses) / len(losses) if losses else 0
    
    profit_factor = abs(sum(t['pnl'] for t in wins) / sum(t['pnl'] for t in losses)) if losses and sum(t['pnl'] for t in losses) != 0 else 0
    
    # Calculate max drawdown
    peak = balance_history[0] if balance_history else 0
    max_dd = 0
    for balance in balance_history:
        if balance > peak:
            peak = balance
        dd = (peak - balance) / peak * 100 if peak > 0 else 0
        if dd > max_dd:
            max_dd = dd
    
    # Starting and ending balance
    start_balance = balance_history[0] if balance_history else 0
    end_balance = balance_history[-1] if balance_history else 0
    total_return = (end_balance - start_balance) / start_balance * 100 if start_balance > 0 else 0
    
    print("\n" + "="*60)
    print("🎯 REAL OANDA TRADING RESULTS")
    print("="*60)
    print(f"\n📊 OVERALL PERFORMANCE:")
    print(f"   Starting Balance: ${start_balance:,.2f}")
    print(f"   Ending Balance: ${end_balance:,.2f}")
    print(f"   Total Return: {total_return:+.2f}%")
    print(f"   Total P&L: ${total_pnl:+,.2f}")
    print(f"   Max Drawdown: {max_dd:.2f}%")
    
    print(f"\n📈 TRADE STATISTICS:")
    print(f"   Total Trades: {total_trades}")
    print(f"   Wins: {len(wins)} ({win_rate:.1f}%)")
    print(f"   Losses: {len(losses)} ({100-win_rate:.1f}%)")
    print(f"   Profit Factor: {profit_factor:.2f}")
    
    print(f"\n💰 PER-TRADE AVERAGES:")
    print(f"   Average Win: ${avg_win:+.2f}")
    print(f"   Average Loss: ${avg_loss:+.2f}")
    print(f"   Avg Win/Loss Ratio: {abs(avg_win/avg_loss):.2f}" if avg_loss != 0 else "   Avg Win/Loss Ratio: N/A")
    
    # Instrument breakdown
    print(f"\n📉 BY INSTRUMENT:")
    instrument_stats = defaultdict(lambda: {'trades': 0, 'pnl': 0, 'wins': 0})
    for t in trades:
        inst = t['instrument']
        instrument_stats[inst]['trades'] += 1
        instrument_stats[inst]['pnl'] += t['pnl']
        if t['pnl'] > 0:
            instrument_stats[inst]['wins'] += 1
    
    for inst, stats in sorted(instrument_stats.items(), key=lambda x: x[1]['pnl'], reverse=True):
        wr = stats['wins'] / stats['trades'] * 100 if stats['trades'] > 0 else 0
        print(f"   {inst}: {stats['trades']} trades, ${stats['pnl']:+.2f} P&L, {wr:.0f}% WR")
    
    # Show worst trades
    print(f"\n❌ WORST 5 TRADES:")
    worst = sorted(trades, key=lambda x: x['pnl'])[:5]
    for t in worst:
        print(f"   {t['date']}: {t['instrument']} {t['direction']} → ${t['pnl']:.2f}")
    
    # Show best trades
    print(f"\n✅ BEST 5 TRADES:")
    best = sorted(trades, key=lambda x: x['pnl'], reverse=True)[:5]
    for t in best:
        print(f"   {t['date']}: {t['instrument']} {t['direction']} → ${t['pnl']:.2f}")
    
    print(f"\n{'='*60}")
    print("🎯 CRITICAL INSIGHTS:")
    print("="*60)
    
    if win_rate < 50:
        print(f"⚠️  Win rate {win_rate:.1f}% is BELOW 50% - strategy losing on accuracy")
    else:
        print(f"✅ Win rate {win_rate:.1f}% is above 50%")
    
    if profit_factor < 1.5:
        print(f"⚠️  Profit factor {profit_factor:.2f} is BELOW 1.5 - not enough edge")
    else:
        print(f"✅ Profit factor {profit_factor:.2f} shows decent edge")
    
    if total_return < 0:
        print(f"❌ LOSING MONEY: {total_return:.2f}% total return")
    else:
        print(f"✅ Making money: {total_return:.2f}% total return")
    
    if max_dd > 20:
        print(f"⚠️  Max drawdown {max_dd:.2f}% is HIGH - risky")
    else:
        print(f"✅ Max drawdown {max_dd:.2f}% is acceptable")
    
    print(f"\n💡 BOTTOM LINE:")
    if win_rate > 55 and profit_factor > 1.5 and total_return > 5:
        print("   ✅ Strategy HAS EDGE - keep trading with risk management")
    elif total_return > 0:
        print("   ⚠️  Strategy is MARGINALLY profitable - needs improvement")
    else:
        print("   ❌ Strategy is LOSING MONEY - STOP and fix it")
    
    print()

if __name__ == '__main__':
    csv_file = '/mnt/c/Users/RFing/Downloads/transactions_101-001-31210531-002.csv'
    
    print("🎯 ANALYZING REAL OANDA TRADING DATA")
    print("This shows what ACTUALLY happened, not synthetic backtests\n")
    
    analyze_oanda_transactions(csv_file)
