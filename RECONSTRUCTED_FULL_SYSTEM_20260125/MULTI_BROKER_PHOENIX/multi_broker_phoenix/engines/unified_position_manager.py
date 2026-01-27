"""
UNIFIED POSITION MANAGER - Multi-Broker Position Awareness
Tracks ALL open positions across Coinbase, OANDA, IBKR in real-time
Enforces time-based rules, signals exit conditions, integrates hive counsel
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json
import os

logger = logging.getLogger(__name__)

class UnifiedPositionManager:
    """
    Central position tracking across ALL brokers.
    Ensures no position is overlooked regardless of broker.
    Enforces time-based exit rules automatically.
    """
    
    def __init__(self, hive_counsel=None):
        """
        Initialize unified position tracker.
        
        Args:
            hive_counsel: Optional HiveCounsel instance for guidance
        """
        self.positions: Dict[str, Dict[str, Any]] = {}  # {pos_id: position_data}
        self.hive_counsel = hive_counsel
        self.max_hold_hours = int(os.getenv('MAX_POSITION_HOLD_HOURS', '8'))
        self.day_trade_max_hours = int(os.getenv('DAY_TRADE_MAX_HOURS', '6'))
        
        logger.info(f"🌐 Unified Position Manager initialized")
        logger.info(f"   Max hold time: {self.max_hold_hours} hours")
        logger.info(f"   Day trade max: {self.day_trade_max_hours} hours")
        logger.info(f"   Hive counsel: {'🧠 ACTIVE' if hive_counsel else '❌ DISABLED'}")
    
    def register_position(self, broker: str, symbol: str, side: str, entry_price: float, 
                         entry_size: float, entry_time: datetime, strategy: str = None,
                         stop_loss: float = None, target_price: float = None) -> str:
        """
        Register a new position across ANY broker.
        
        Args:
            broker: 'coinbase', 'oanda', or 'ibkr'
            symbol: Trading pair (BTC-USD, EUR/USD, etc)
            side: 'BUY', 'SELL', 'LONG', 'SHORT'
            entry_price: Entry price
            entry_size: Position size
            entry_time: When position was opened
            strategy: Strategy name
            stop_loss: Stop loss price
            target_price: Take-profit price
        
        Returns:
            position_id for tracking
        """
        # Generate unique position ID across all brokers
        position_id = f"{broker}:{symbol}:{int(entry_time.timestamp())}"
        
        self.positions[position_id] = {
            'broker': broker,
            'symbol': symbol,
            'side': side,
            'entry_price': entry_price,
            'entry_size': entry_size,
            'entry_time': entry_time,
            'current_price': entry_price,
            'highest_price': entry_price,
            'lowest_price': entry_price,
            'strategy': strategy,
            'stop_loss': stop_loss,
            'target_price': target_price,
            'hours_open': 0,
            'unrealized_pnl': 0.0,
            'unrealized_pnl_pct': 0.0,
            'status': 'OPEN',
            'exit_reason': None,
            'exit_signal': None,
            'registered_time': datetime.now()
        }
        
        logger.info(f"📍 Position registered: {position_id}")
        logger.info(f"   Broker: {broker} | Symbol: {symbol} | Side: {side}")
        logger.info(f"   Entry: ${entry_price:.2f} | Size: {entry_size}")
        logger.info(f"   Strategy: {strategy}")
        
        return position_id
    
    def update_position(self, position_id: str, current_price: float) -> Optional[Dict[str, Any]]:
        """
        Update position with current price and check exit conditions.
        
        Args:
            position_id: Position identifier
            current_price: Current market price
        
        Returns:
            Position data if exists
        """
        if position_id not in self.positions:
            logger.warning(f"⚠️  Position not found: {position_id}")
            return None
        
        pos = self.positions[position_id]
        
        # Update prices
        pos['current_price'] = current_price
        if current_price > pos['highest_price']:
            pos['highest_price'] = current_price
        if current_price < pos['lowest_price']:
            pos['lowest_price'] = current_price
        
        # Calculate P/L
        if pos['side'] in ('BUY', 'LONG'):
            pnl = (current_price - pos['entry_price']) * pos['entry_size']
            pnl_pct = ((current_price - pos['entry_price']) / pos['entry_price']) * 100
        else:  # SELL/SHORT
            pnl = (pos['entry_price'] - current_price) * pos['entry_size']
            pnl_pct = ((pos['entry_price'] - current_price) / pos['entry_price']) * 100
        
        pos['unrealized_pnl'] = pnl
        pos['unrealized_pnl_pct'] = pnl_pct
        
        # Update hold time
        hold_time = datetime.now() - pos['entry_time']
        pos['hours_open'] = hold_time.total_seconds() / 3600
        
        return pos
    
    def check_exit_conditions(self, position_id: str) -> Optional[Dict[str, Any]]:
        """
        Check if position should exit based on:
        1. Max hold time exceeded
        2. Stop loss hit
        3. Target price hit
        4. Hive counsel signal
        
        Returns:
            Exit signal dict or None
        """
        if position_id not in self.positions:
            return None
        
        pos = self.positions[position_id]
        
        # ❌ CONDITION 1: Max hold time exceeded
        if pos['hours_open'] > self.max_hold_hours:
            exit_signal = {
                'should_exit': True,
                'reason': 'MAX_HOLD_TIME_EXCEEDED',
                'hours_held': pos['hours_open'],
                'max_hours': self.max_hold_hours,
                'severity': 'CRITICAL'
            }
            
            logger.critical(f"🛑 MAX HOLD TIME EXCEEDED: {position_id}")
            logger.critical(f"   Hours held: {pos['hours_open']:.1f} > {self.max_hold_hours}")
            logger.critical(f"   Action: MUST EXIT IMMEDIATELY")
            
            # Alert hive counsel
            if self.hive_counsel:
                counsel = self.hive_counsel.get_emergency_exit_guidance(
                    position=pos,
                    reason='max_hold_time_exceeded'
                )
                exit_signal['hive_counsel'] = counsel
            
            pos['exit_signal'] = exit_signal
            return exit_signal
        
        # ⚠️  CONDITION 2: Approaching max hold time (warn at 80%)
        if pos['hours_open'] > (self.max_hold_hours * 0.8):
            logger.warning(f"⏰ APPROACHING MAX HOLD TIME: {position_id}")
            logger.warning(f"   {pos['hours_open']:.1f}/{self.max_hold_hours} hours")
            logger.warning(f"   ACTION: Prepare exit strategy")
            
            if self.hive_counsel:
                guidance = self.hive_counsel.get_exit_guidance(
                    position=pos,
                    reason='approaching_max_hold'
                )
                logger.info(f"   Hive Counsel: {guidance}")
        
        # 🛑 CONDITION 3: Stop loss hit
        if pos['stop_loss'] is not None:
            if pos['side'] in ('BUY', 'LONG'):
                if pos['current_price'] <= pos['stop_loss']:
                    exit_signal = {
                        'should_exit': True,
                        'reason': 'STOP_LOSS_HIT',
                        'exit_price': pos['current_price'],
                        'stop_loss': pos['stop_loss'],
                        'severity': 'HIGH'
                    }
                    
                    logger.warning(f"🛑 STOP LOSS HIT: {position_id}")
                    logger.warning(f"   Price: ${pos['current_price']:.2f} <= Stop: ${pos['stop_loss']:.2f}")
                    
                    pos['exit_signal'] = exit_signal
                    return exit_signal
            else:  # SHORT
                if pos['current_price'] >= pos['stop_loss']:
                    exit_signal = {
                        'should_exit': True,
                        'reason': 'STOP_LOSS_HIT',
                        'exit_price': pos['current_price'],
                        'stop_loss': pos['stop_loss'],
                        'severity': 'HIGH'
                    }
                    
                    logger.warning(f"🛑 STOP LOSS HIT: {position_id}")
                    logger.warning(f"   Price: ${pos['current_price']:.2f} >= Stop: ${pos['stop_loss']:.2f}")
                    
                    pos['exit_signal'] = exit_signal
                    return exit_signal
        
        # 💰 CONDITION 4: Target price hit
        if pos['target_price'] is not None:
            if pos['side'] in ('BUY', 'LONG'):
                if pos['current_price'] >= pos['target_price']:
                    exit_signal = {
                        'should_exit': True,
                        'reason': 'TARGET_HIT',
                        'exit_price': pos['current_price'],
                        'target_price': pos['target_price'],
                        'severity': 'NORMAL'
                    }
                    
                    logger.info(f"💰 TARGET HIT: {position_id}")
                    logger.info(f"   Price: ${pos['current_price']:.2f} >= Target: ${pos['target_price']:.2f}")
                    
                    pos['exit_signal'] = exit_signal
                    return exit_signal
            else:  # SHORT
                if pos['current_price'] <= pos['target_price']:
                    exit_signal = {
                        'should_exit': True,
                        'reason': 'TARGET_HIT',
                        'exit_price': pos['current_price'],
                        'target_price': pos['target_price'],
                        'severity': 'NORMAL'
                    }
                    
                    logger.info(f"💰 TARGET HIT: {position_id}")
                    logger.info(f"   Price: ${pos['current_price']:.2f} <= Target: ${pos['target_price']:.2f}")
                    
                    pos['exit_signal'] = exit_signal
                    return exit_signal
        
        # 🧠 CONDITION 5: Hive counsel guidance (if available)
        if self.hive_counsel:
            counsel_signal = self.hive_counsel.should_exit_position(position=pos)
            if counsel_signal:
                logger.info(f"🧠 HIVE COUNSEL EXIT SIGNAL: {position_id}")
                logger.info(f"   Reason: {counsel_signal.get('reason')}")
                logger.info(f"   Confidence: {counsel_signal.get('confidence', 'unknown')}")
                
                pos['exit_signal'] = counsel_signal
                return counsel_signal
        
        # No exit condition met
        return None
    
    def close_position(self, position_id: str, exit_price: float, exit_reason: str) -> Dict[str, Any]:
        """
        Close a position and calculate final P/L.
        
        Args:
            position_id: Position to close
            exit_price: Exit price
            exit_reason: Reason for exit
        
        Returns:
            Final position data with P/L
        """
        if position_id not in self.positions:
            return {'error': f'Position {position_id} not found'}
        
        pos = self.positions[position_id]
        
        # Calculate final P/L
        if pos['side'] in ('BUY', 'LONG'):
            pnl = (exit_price - pos['entry_price']) * pos['entry_size']
            pnl_pct = ((exit_price - pos['entry_price']) / pos['entry_price']) * 100
        else:  # SELL/SHORT
            pnl = (pos['entry_price'] - exit_price) * pos['entry_size']
            pnl_pct = ((pos['entry_price'] - exit_price) / pos['entry_price']) * 100
        
        hold_time = datetime.now() - pos['entry_time']
        hold_hours = hold_time.total_seconds() / 3600
        
        pos['status'] = 'CLOSED'
        pos['exit_reason'] = exit_reason
        pos['unrealized_pnl'] = pnl  # Now realized
        pos['unrealized_pnl_pct'] = pnl_pct
        pos['closed_time'] = datetime.now()
        
        logger.info(f"📤 Position closed: {position_id}")
        logger.info(f"   Entry: ${pos['entry_price']:.2f} | Exit: ${exit_price:.2f}")
        logger.info(f"   P/L: ${pnl:+.2f} ({pnl_pct:+.2f}%)")
        logger.info(f"   Hold time: {hold_hours:.2f} hours")
        logger.info(f"   Reason: {exit_reason}")
        
        return pos
    
    def get_all_open_positions(self) -> List[Dict[str, Any]]:
        """Get all currently open positions across all brokers."""
        return [p for p in self.positions.values() if p['status'] == 'OPEN']
    
    def get_positions_by_broker(self, broker: str) -> List[Dict[str, Any]]:
        """Get all open positions for specific broker."""
        return [p for p in self.positions.values() 
                if p['status'] == 'OPEN' and p['broker'] == broker]
    
    def get_positions_exceeding_hold_time(self) -> List[Dict[str, Any]]:
        """Get all positions that have exceeded max hold time (CRITICAL)."""
        exceeding = []
        for pos in self.get_all_open_positions():
            if pos['hours_open'] > self.max_hold_hours:
                exceeding.append(pos)
                logger.critical(f"🚨 OVERSTAY POSITION: {pos['symbol']} held {pos['hours_open']:.1f}h")
        
        return exceeding
    
    def get_positions_near_hold_limit(self) -> List[Dict[str, Any]]:
        """Get all positions approaching max hold time (WARNING)."""
        near_limit = []
        for pos in self.get_all_open_positions():
            if pos['hours_open'] > (self.max_hold_hours * 0.75):
                near_limit.append(pos)
        
        return near_limit
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get overall portfolio status."""
        open_positions = self.get_all_open_positions()
        
        total_pnl = sum(p['unrealized_pnl'] for p in open_positions)
        total_pnl_pct = sum(p['unrealized_pnl_pct'] for p in open_positions)
        
        critical = len(self.get_positions_exceeding_hold_time())
        warning = len(self.get_positions_near_hold_limit())
        
        summary = {
            'total_open': len(open_positions),
            'by_broker': {
                'coinbase': len(self.get_positions_by_broker('coinbase')),
                'oanda': len(self.get_positions_by_broker('oanda')),
                'ibkr': len(self.get_positions_by_broker('ibkr'))
            },
            'portfolio_pnl': total_pnl,
            'portfolio_pnl_pct': total_pnl_pct,
            'alerts': {
                'critical_overstay': critical,
                'warning_near_limit': warning
            }
        }
        
        return summary
    
    def print_position_report(self):
        """Print comprehensive position report."""
        open_pos = self.get_all_open_positions()
        
        logger.info("")
        logger.info("="*70)
        logger.info("📊 UNIFIED POSITION REPORT")
        logger.info("="*70)
        
        if not open_pos:
            logger.info("No open positions")
            return
        
        for pos in open_pos:
            status_icon = "⏰" if pos['hours_open'] > (self.max_hold_hours * 0.8) else "✅"
            logger.info(f"{status_icon} {pos['broker']:8} | {pos['symbol']:10} | {pos['side']:5}")
            logger.info(f"   Entry: ${pos['entry_price']:.2f} | Current: ${pos['current_price']:.2f}")
            logger.info(f"   P/L: ${pos['unrealized_pnl']:+.2f} ({pos['unrealized_pnl_pct']:+.2f}%)")
            logger.info(f"   Hold: {pos['hours_open']:.2f}/{self.max_hold_hours}h")
        
        summary = self.get_portfolio_summary()
        logger.info("")
        logger.info(f"Total: ${summary['portfolio_pnl']:+.2f} ({summary['portfolio_pnl_pct']:+.2f}%)")
        
        if summary['alerts']['critical_overstay'] > 0:
            logger.critical(f"⚠️  CRITICAL: {summary['alerts']['critical_overstay']} position(s) exceeded max hold time!")
        
        logger.info("="*70)
        logger.info("")
