#!/usr/bin/env python3
"""Visual display of market sessions - shows which markets are open now"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'MULTI_BROKER_PHOENIX'))

from multi_broker_phoenix.config.market_sessions import (
    SESSIONS, get_active_sessions, is_session_overlap, 
    get_current_overlap, format_session_status
)
from datetime import datetime
import pytz


def draw_session_chart():
    """Draw visual chart of session status"""
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 15 + "MARKET SESSIONS STATUS" + " " * 21 + "║")
    print("╚" + "═" * 58 + "╝")
    print()
    
    active_sessions = get_active_sessions()
    
    sessions_display = [
        ('🇺🇸 NEW YORK', 'NEW_YORK', 'NYSE/NASDAQ', '9:30 AM - 4:00 PM EST'),
        ('🇬🇧 LONDON', 'LONDON', 'LSE', '8:00 AM - 4:30 PM GMT'),
        ('🇯🇵 TOKYO', 'TOKYO', 'TSE', '9:00 AM - 3:00 PM JST'),
        ('🇦🇺 SYDNEY', 'SYDNEY', 'ASX', '10:00 AM - 4:00 PM AEDT'),
        ('🇭🇰 HONG KONG', 'HONG_KONG', 'HKEX', '9:30 AM - 4:00 PM HKT'),
        ('🌐 CRYPTO', 'CRYPTO_24H', '24/7', 'Always Open'),
        ('💱 FOREX', 'FOREX_24H', '24/5', 'Mon-Fri'),
    ]
    
    for flag_name, session_key, exchange, hours in sessions_display:
        is_active = session_key in active_sessions
        status = "🟢 OPEN " if is_active else "🔴 CLOSED"
        
        # Get session object
        session = SESSIONS.get(session_key)
        if session and is_active:
            seconds_left = session.time_until_close()
            if seconds_left:
                hours_left = int(seconds_left // 3600)
                mins_left = int((seconds_left % 3600) // 60)
                time_str = f"({hours_left}h {mins_left}m left)"
            else:
                time_str = ""
        elif session and not is_active:
            seconds_until = session.time_until_open()
            if seconds_until:
                hours_until = int(seconds_until // 3600)
                mins_until = int((seconds_until % 3600) // 60)
                if hours_until < 24:
                    time_str = f"(opens in {hours_until}h {mins_until}m)"
                else:
                    days = hours_until // 24
                    time_str = f"(opens in {days}d {hours_until % 24}h)"
            else:
                time_str = ""
        else:
            time_str = ""
        
        print(f"{status} {flag_name:15s} {exchange:8s} {hours:25s} {time_str}")
    
    print()
    
    # Show overlap status
    overlap = get_current_overlap()
    if overlap:
        print("╔" + "═" * 58 + "╗")
        print("║" + "🔥 HIGH LIQUIDITY OVERLAP DETECTED".center(58) + "║")
        print("╚" + "═" * 58 + "╝")
        print(f"  {overlap['name']}: {overlap['description']}")
        print(f"  Optimal for: {', '.join(overlap['optimal_for'])}")
        print()
    elif is_session_overlap():
        print("⚡ Multiple sessions active (increased liquidity)")
        print()


def show_trading_recommendations():
    """Show which instruments to trade now"""
    from multi_broker_phoenix.config.market_sessions import should_trade_now
    
    print("╔" + "═" * 58 + "╗")
    print("║" + "TRADING RECOMMENDATIONS".center(58) + "║")
    print("╚" + "═" * 58 + "╝")
    print()
    
    instruments = [
        ('BTC-USD', 'Bitcoin'),
        ('ETH-USD', 'Ethereum'),
        ('EUR_USD', 'Euro/Dollar'),
        ('GBP_USD', 'Pound/Dollar'),
        ('USD_JPY', 'Dollar/Yen'),
        ('SPY', 'S&P 500 ETF'),
        ('QQQ', 'Nasdaq ETF'),
        ('GLD', 'Gold ETF'),
    ]
    
    for symbol, name in instruments:
        should_trade, reason = should_trade_now(symbol)
        status = "✓" if should_trade else "✗"
        color = "🟢" if should_trade else "🔴"
        print(f"{color} {status} {symbol:10s} {name:20s} - {reason}")
    
    print()


def main():
    """Main display"""
    now = datetime.now(pytz.UTC)
    
    print()
    print("═" * 60)
    print(f"Current Time (UTC): {now.strftime('%Y-%m-%d %H:%M:%S')}")
    local = now.astimezone()
    print(f"Local Time: {local.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print("═" * 60)
    print()
    
    draw_session_chart()
    show_trading_recommendations()
    
    print("═" * 60)
    print("Refresh this view anytime to see current market status")
    print("Command: python3 tools/market_session_display.py")
    print("═" * 60)


if __name__ == '__main__':
    main()
