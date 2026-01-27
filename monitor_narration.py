#!/usr/bin/env python3
"""
🎬 LIVE NARRATION MONITOR
Real-time position and trade tracking across all brokers
"""
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from collections import defaultdict


def _pick_default_narration_file() -> Path:
    """Choose the most likely narration file in this repo."""
    candidates = [
        Path('/tmp/position_narration.jsonl'),
        Path('/home/ing/RICK/MULTI_BROKER_PHOENIX/narration.jsonl'),
        (Path(__file__).resolve().parent / 'narration.jsonl'),
    ]
    for p in candidates:
        if p.exists():
            return p
    # Prefer /tmp path even if not created yet (engine will create it)
    return candidates[0]


def _follow_lines(path: Path):
    """Yield new lines appended to a file, waiting for file creation."""
    while True:
        if not path.exists():
            time.sleep(1.0)
            continue

        try:
            with path.open('r') as f:
                # Start at end for follow; caller can read existing separately.
                f.seek(0, 2)
                while True:
                    line = f.readline()
                    if line:
                        yield line
                    else:
                        time.sleep(0.5)
        except FileNotFoundError:
            # file rotated/removed
            time.sleep(0.5)
        except Exception:
            time.sleep(1.0)

def monitor_narration(filepath, follow=False):
    """Monitor narration file for trading events."""
    
    stats = {
        'total_events': 0,
        'by_venue': defaultdict(int),
        'by_event_type': defaultdict(int),
        'filled_orders': 0,
        'total_pnl': 0.0,
        'by_venue_pnl': defaultdict(float),
    }
    
    print("\n" + "="*80)
    print("🎬 LIVE NARRATION MONITOR - All Broker Trading Events")
    print("="*80)
    print(f"File: {filepath}")
    print(f"Mode: {'LIVE TAIL' if follow else 'STATIC'}")
    print("="*80 + "\n")
    
    def handle_line(line: str):
        try:
            event = json.loads(line.strip())
        except json.JSONDecodeError:
            return

        stats['total_events'] += 1

        # Support multiple schemas
        ts = event.get('ts') or event.get('timestamp') or event.get('time') or 'unknown'
        event_type = event.get('event_type') or event.get('event') or event.get('type') or 'UNKNOWN'
        venue = event.get('venue') or event.get('broker') or 'unknown'

        stats['by_venue'][venue] += 1
        stats['by_event_type'][event_type] += 1

        # Prefer human summary if available
        human = event.get('human_summary')
        if human:
            print(f"🗣️  [{ts}] {human}")
            return

        details = event.get('details', {}) if isinstance(event.get('details', {}), dict) else {}

        if event_type == 'ORDER_FILLED':
            stats['filled_orders'] += 1
            symbol = event.get('symbol', '?')
            price = details.get('price', 0)
            size = details.get('size', 0)
            direction = details.get('direction', '?')
            pnl = details.get('pnl', 0)
            quality = details.get('quality_score', 0)
            strategy = details.get('strategy', '?')

            try:
                pnl_f = float(pnl)
            except Exception:
                pnl_f = 0.0

            stats['total_pnl'] += pnl_f
            stats['by_venue_pnl'][venue] += pnl_f

            pnl_str = f"+${pnl_f:.2f}" if pnl_f >= 0 else f"-${abs(pnl_f):.2f}"
            color = "🟢" if pnl_f >= 0 else "🔴"
            print(f"{color} {ts}")
            print(f"   📊 {str(venue).upper()} | {symbol} | {direction} {size} @ {price}")
            print(f"   💰 P&L: {pnl_str} | Quality: {float(quality):.1f}% | Strategy: {strategy}")
            print()
            return

        if event_type in ['TRADE_OPENED', 'TRADE_CLOSED', 'STOP_HIT', 'PROFIT_TAKEN']:
            symbol = event.get('symbol', '?')
            direction = details.get('direction', '?')
            print(f"📌 {ts} | {event_type} | {str(venue).upper()} {symbol} {direction}")
            print()

    path = Path(filepath)

    # Read existing file once (if present)
    if path.exists():
        try:
            with path.open('r') as f:
                for line in f:
                    handle_line(line)
        except Exception:
            pass

    # Follow appended lines
    if follow:
        for line in _follow_lines(path):
            handle_line(line)
    
    # Print summary
    print("\n" + "="*80)
    print("📊 SUMMARY")
    print("="*80)
    print(f"Total Events: {stats['total_events']}")
    print(f"Filled Orders: {stats['filled_orders']}")
    print(f"Total P&L: ${stats['total_pnl']:,.2f}")
    print()
    print("By Venue:")
    for venue in ['oanda', 'ibkr', 'coinbase', 'hive']:
        count = stats['by_venue'].get(venue, 0)
        pnl = stats['by_venue_pnl'].get(venue, 0)
        if count > 0:
            print(f"  {venue.upper()}: {count} events, P&L: ${pnl:,.2f}")
    print()
    print("By Event Type (Top 5):")
    for event_type, count in sorted(stats['by_event_type'].items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"  {event_type}: {count}")
    print("="*80 + "\n")


if __name__ == '__main__':
    # CLI flags
    follow = '--follow' in sys.argv or '-f' in sys.argv

    # Optional: --file /path/to/file
    file_arg = None
    if '--file' in sys.argv:
        try:
            file_arg = sys.argv[sys.argv.index('--file') + 1]
        except Exception:
            file_arg = None

    if file_arg:
        narration_file = Path(file_arg)
    else:
        # In live-follow mode, default to the real-time position narrator output.
        narration_file = Path('/tmp/position_narration.jsonl') if follow else _pick_default_narration_file()
    monitor_narration(str(narration_file), follow=follow)
