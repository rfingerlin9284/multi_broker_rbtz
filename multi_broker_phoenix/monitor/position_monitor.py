#!/usr/bin/env python3
"""
Real-Time Position Monitor for OANDA
=====================================

Polls OANDA for:
1. Open positions (live tracking)
2. Closed trades (realized P&L)
3. Manual closures (user closed outside system)

Updates the Goal Pursuit Engine with realized P&L in real-time.
"""
import os
import json
import time
import logging
import threading
from datetime import datetime, date
from typing import Dict, Any, List, Optional, Set
from pathlib import Path

logger = logging.getLogger(__name__)

# State file for persistence across restarts
STATE_FILE = Path(os.getenv('POSITION_MONITOR_STATE', 'ops/state/position_monitor.json'))


class PositionMonitor:
    """
    Real-time position and transaction monitor.
    
    Tracks:
    - Currently open positions
    - Closed trades (detects when positions disappear)
    - Realized P&L from transactions
    - Manual closures by user
    """
    
    def __init__(self, client=None):
        self.client = client
        self._lock = threading.Lock()
        
        # Position tracking
        self._known_positions: Dict[str, Dict] = {}  # trade_id -> position_info
        self._last_transaction_id: Optional[str] = None
        
        # Daily P&L tracking
        self._daily_realized: float = 0.0
        self._daily_trades_closed: int = 0
        self._daily_wins: int = 0
        self._daily_losses: int = 0
        self._today: str = date.today().isoformat()
        
        # Closed trade log (for audit)
        self._closed_trades: List[Dict] = []
        
        # Track if we've synced account P&L on startup
        self._account_synced: bool = False
        
        # Load persisted state
        self._load_state()
        
    def _load_state(self):
        """Load state from disk."""
        try:
            if STATE_FILE.exists():
                with open(STATE_FILE, 'r') as f:
                    state = json.load(f)
                
                # Check if same day
                if state.get('date') == date.today().isoformat():
                    self._daily_realized = state.get('daily_realized', 0.0)
                    self._daily_trades_closed = state.get('daily_trades_closed', 0)
                    self._daily_wins = state.get('daily_wins', 0)
                    self._daily_losses = state.get('daily_losses', 0)
                    self._last_transaction_id = state.get('last_transaction_id')
                    self._known_positions = state.get('known_positions', {})
                    self._closed_trades = state.get('closed_trades', [])[-50:]  # Keep last 50
                    logger.info(f"PositionMonitor loaded state: ${self._daily_realized:.2f} realized today")
                else:
                    logger.info("PositionMonitor: New day, resetting counters")
        except Exception as e:
            logger.warning(f"Could not load position monitor state: {e}")
    
    def _save_state(self):
        """Persist state to disk."""
        try:
            STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            state = {
                'date': self._today,
                'daily_realized': self._daily_realized,
                'daily_trades_closed': self._daily_trades_closed,
                'daily_wins': self._daily_wins,
                'daily_losses': self._daily_losses,
                'last_transaction_id': self._last_transaction_id,
                'known_positions': self._known_positions,
                'closed_trades': self._closed_trades[-50:],
                'updated_at': datetime.utcnow().isoformat() + 'Z'
            }
            with open(STATE_FILE, 'w') as f:
                json.dump(state, f, indent=2, default=str)
        except Exception as e:
            logger.warning(f"Could not save position monitor state: {e}")
    
    def set_client(self, client):
        """Set or update the OANDA client."""
        self.client = client
    
    def sync_account_realized_pl(self) -> float:
        """
        Sync with OANDA account to get today's realized P&L.
        Called once on startup to catch trades closed before monitor started.
        
        Returns the account's realized P/L.
        """
        if not self.client or self._account_synced:
            return self._daily_realized
        
        try:
            summary = self.client.get_account_summary()
            account = summary.get('account', {})
            
            # Get realized P&L from account
            account_pl = float(account.get('pl', 0))
            
            # If our tracked realized is less than account's (we missed some trades)
            # BUT only update if it's reasonably close (within $1000 - to avoid
            # syncing historical P&L from past days)
            if account_pl > self._daily_realized and account_pl < 1000:
                missed_amount = account_pl - self._daily_realized
                if missed_amount > 0:
                    print(f"\n📊 SYNCING ACCOUNT P&L:")
                    print(f"   Account shows: ${account_pl:.2f}")
                    print(f"   We were tracking: ${self._daily_realized:.2f}")
                    print(f"   Adding missed: ${missed_amount:.2f}")
                    
                    self._daily_realized = account_pl
                    self._save_state()
            
            self._account_synced = True
            return self._daily_realized
            
        except Exception as e:
            logger.warning(f"Account P&L sync failed: {e}")
            self._account_synced = True  # Don't retry
            return self._daily_realized
    
    def sync_positions(self) -> Dict[str, Any]:
        """
        Sync with OANDA to detect:
        1. New positions
        2. Closed positions (disappeared from open list)
        3. Position changes
        
        Returns summary of what changed.
        """
        if not self.client:
            return {'error': 'No client configured'}
        
        # Sync account P/L on first run to catch trades closed before we started
        if not self._account_synced:
            self.sync_account_realized_pl()
        
        # Reset if new day
        today = date.today().isoformat()
        if today != self._today:
            self._reset_daily()
            self._today = today
        
        result = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'new_positions': [],
            'closed_positions': [],
            'position_updates': [],
            'realized_pnl': 0.0,
            'open_count': 0
        }
        
        try:
            # Get current open trades
            trades_resp = self.client.list_open_trades()
            current_trades = trades_resp.get('trades', [])
            current_ids = set()
            
            for trade in current_trades:
                trade_id = trade.get('id')
                if not trade_id:
                    continue
                current_ids.add(trade_id)
                
                # Check if new position
                if trade_id not in self._known_positions:
                    self._known_positions[trade_id] = {
                        'id': trade_id,
                        'instrument': trade.get('instrument'),
                        'units': trade.get('currentUnits'),
                        'price': trade.get('price'),
                        'unrealizedPL': trade.get('unrealizedPL'),
                        'openTime': trade.get('openTime'),
                        'first_seen': datetime.utcnow().isoformat()
                    }
                    result['new_positions'].append({
                        'id': trade_id,
                        'instrument': trade.get('instrument'),
                        'units': trade.get('currentUnits'),
                        'unrealizedPL': trade.get('unrealizedPL')
                    })
                else:
                    # Update unrealized P&L
                    old_upl = self._known_positions[trade_id].get('unrealizedPL', 0)
                    new_upl = trade.get('unrealizedPL', 0)
                    self._known_positions[trade_id]['unrealizedPL'] = new_upl
                    self._known_positions[trade_id]['units'] = trade.get('currentUnits')
                    
                    if old_upl != new_upl:
                        result['position_updates'].append({
                            'id': trade_id,
                            'instrument': trade.get('instrument'),
                            'old_upl': old_upl,
                            'new_upl': new_upl
                        })
            
            # Detect closed positions (were known, now gone)
            closed_ids = set(self._known_positions.keys()) - current_ids
            for trade_id in closed_ids:
                pos = self._known_positions.pop(trade_id, {})
                if pos:
                    result['closed_positions'].append(pos)
            
            result['open_count'] = len(current_trades)
            
            # Now fetch transactions to get actual realized P&L
            pnl_from_txns = self._fetch_transaction_pnl()
            result['realized_pnl'] = pnl_from_txns
            
            self._save_state()
            
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"Position sync error: {e}")
        
        return result
    
    def _fetch_transaction_pnl(self) -> float:
        """
        Fetch recent transactions and extract realized P&L from closed trades.
        Returns total realized P&L from new transactions.
        """
        if not self.client:
            return 0.0
        
        total_pnl = 0.0
        
        try:
            # Fetch transactions since last check
            if hasattr(self.client, 'get_transactions'):
                txn_resp = self.client.get_transactions(
                    since_id=self._last_transaction_id,
                    count=100
                )
            else:
                # Fallback: use account summary for realized PL
                return self._get_account_realized_pl()
            
            transactions = txn_resp.get('transactions', [])
            
            for txn in transactions:
                txn_id = txn.get('id')
                txn_type = txn.get('type', '')
                
                # Track last seen transaction
                if txn_id:
                    self._last_transaction_id = txn_id
                
                # Look for trade closures (ORDER_FILL that closes a trade)
                if txn_type in ('ORDER_FILL', 'TRADE_CLOSE'):
                    pl_str = txn.get('pl', txn.get('realizedPL', '0'))
                    try:
                        pl = float(pl_str)
                    except:
                        pl = 0.0
                    
                    if pl != 0:
                        total_pnl += pl
                        is_win = pl > 0
                        
                        # Record the closed trade
                        closed_info = {
                            'transaction_id': txn_id,
                            'type': txn_type,
                            'instrument': txn.get('instrument'),
                            'units': txn.get('units'),
                            'price': txn.get('price'),
                            'pl': pl,
                            'time': txn.get('time'),
                            'reason': txn.get('reason', 'unknown')
                        }
                        self._closed_trades.append(closed_info)
                        
                        # Update counters
                        self._daily_realized += pl
                        self._daily_trades_closed += 1
                        if is_win:
                            self._daily_wins += 1
                        else:
                            self._daily_losses += 1
                        
                        # Print announcement
                        self._print_trade_closed(closed_info, is_win)
                        
                        # Update Goal Pursuit Engine
                        self._update_goal_engine(pl, is_win)
            
        except Exception as e:
            logger.error(f"Transaction fetch error: {e}")
        
        return total_pnl
    
    def _get_account_realized_pl(self) -> float:
        """Fallback: Get realized P&L from account summary."""
        try:
            summary = self.client.get_account_summary()
            account = summary.get('account', {})
            realized = float(account.get('pl', 0))
            return realized
        except:
            return 0.0
    
    def _print_trade_closed(self, trade: Dict, is_win: bool):
        """Print human-readable trade closure announcement."""
        emoji = "✅ WIN" if is_win else "❌ LOSS"
        pl = trade.get('pl', 0)
        instrument = trade.get('instrument', 'Unknown')
        reason = trade.get('reason', 'closed')
        
        print(f"\n{'='*60}")
        print(f"💰 TRADE CLOSED: {emoji}")
        print(f"{'='*60}")
        print(f"   • Pair: {instrument}")
        print(f"   • P&L: ${pl:+.2f}")
        print(f"   • Reason: {reason}")
        print(f"\n📊 TODAY'S RUNNING TOTAL:")
        print(f"   • Realized P&L: ${self._daily_realized:+.2f}")
        print(f"   • Trades Closed: {self._daily_trades_closed}")
        print(f"   • Wins: {self._daily_wins} | Losses: {self._daily_losses}")
        if self._daily_trades_closed > 0:
            win_rate = (self._daily_wins / self._daily_trades_closed) * 100
            print(f"   • Win Rate: {win_rate:.1f}%")
        print(f"{'='*60}\n")
    
    def _update_goal_engine(self, pnl: float, is_win: bool):
        """Update the Goal Pursuit Engine with realized P&L."""
        try:
            from multi_broker_phoenix.risk.goal_pursuit_engine import update_goal_on_close
            update_goal_on_close(pnl)
        except Exception as e:
            logger.debug(f"Goal engine update skipped: {e}")
        
        # Also update oanda_runner's daily tracker
        try:
            from multi_broker_phoenix.runners.oanda_runner import _update_daily_realized
            _update_daily_realized(pnl)
        except Exception as e:
            logger.debug(f"Runner daily tracker update skipped: {e}")
    
    def _reset_daily(self):
        """Reset daily counters for new day."""
        print(f"\n{'='*60}")
        print(f"📅 NEW TRADING DAY!")
        print(f"{'='*60}")
        if self._daily_trades_closed > 0:
            print(f"   Yesterday's Final P&L: ${self._daily_realized:+.2f}")
            print(f"   Trades: {self._daily_trades_closed} (W:{self._daily_wins}/L:{self._daily_losses})")
        print(f"   Resetting counters to $0.00")
        print(f"{'='*60}\n")
        
        self._daily_realized = 0.0
        self._daily_trades_closed = 0
        self._daily_wins = 0
        self._daily_losses = 0
        self._closed_trades = []
    
    def get_open_positions(self) -> List[Dict]:
        """Return list of currently tracked open positions."""
        return list(self._known_positions.values())
    
    def get_daily_summary(self) -> Dict[str, Any]:
        """Return today's trading summary."""
        win_rate = 0.0
        if self._daily_trades_closed > 0:
            win_rate = (self._daily_wins / self._daily_trades_closed) * 100
        
        return {
            'date': self._today,
            'realized_pnl': self._daily_realized,
            'trades_closed': self._daily_trades_closed,
            'wins': self._daily_wins,
            'losses': self._daily_losses,
            'win_rate': win_rate,
            'open_positions': len(self._known_positions),
            'last_transaction_id': self._last_transaction_id
        }
    
    def print_status(self):
        """Print current position status."""
        summary = self.get_daily_summary()
        positions = self.get_open_positions()
        
        print(f"\n{'─'*60}")
        print(f"📊 POSITION MONITOR STATUS")
        print(f"{'─'*60}")
        print(f"   Today's Realized P&L: ${summary['realized_pnl']:+.2f}")
        print(f"   Trades Closed: {summary['trades_closed']}")
        print(f"   Win Rate: {summary['win_rate']:.1f}%")
        
        if positions:
            print(f"\n   📈 OPEN POSITIONS ({len(positions)}):")
            for pos in positions:
                upl = float(pos.get('unrealizedPL', 0))
                emoji = "🟢" if upl >= 0 else "🔴"
                print(f"   {emoji} {pos.get('instrument')}: {pos.get('units')} units | UPL: ${upl:+.2f}")
        else:
            print(f"\n   📭 No open positions")
        print(f"{'─'*60}\n")


# Global instance
_monitor: Optional[PositionMonitor] = None


def get_position_monitor() -> PositionMonitor:
    """Get or create the global position monitor."""
    global _monitor
    if _monitor is None:
        _monitor = PositionMonitor()
    return _monitor


def start_position_monitor(client, interval_sec: int = 15) -> threading.Thread:
    """
    Start background position monitoring thread.
    
    Args:
        client: OANDA client with list_open_trades() and get_transactions()
        interval_sec: How often to sync (default 15s)
    
    Returns:
        The monitoring thread
    """
    monitor = get_position_monitor()
    monitor.set_client(client)
    
    stop_event = threading.Event()
    
    def _run():
        logger.info(f"PositionMonitor started (interval={interval_sec}s)")
        while not stop_event.is_set():
            try:
                result = monitor.sync_positions()
                
                # Log significant events
                if result.get('closed_positions'):
                    for pos in result['closed_positions']:
                        logger.info(f"Position closed: {pos.get('instrument')} | UPL: {pos.get('unrealizedPL')}")
                
                if result.get('new_positions'):
                    for pos in result['new_positions']:
                        logger.info(f"New position detected: {pos.get('instrument')} {pos.get('units')} units")
                
            except Exception as e:
                logger.error(f"PositionMonitor error: {e}")
            
            stop_event.wait(interval_sec)
        
        logger.info("PositionMonitor stopped")
    
    thread = threading.Thread(target=_run, daemon=True, name='position_monitor')
    thread.start()
    return thread


def sync_positions_once(client) -> Dict[str, Any]:
    """Run a single position sync."""
    monitor = get_position_monitor()
    monitor.set_client(client)
    return monitor.sync_positions()


if __name__ == '__main__':
    # Test
    print("Position Monitor module loaded")
    monitor = PositionMonitor()
    monitor.print_status()
