"""
OANDA POSITION MANAGER - Missing Component That Let Positions Overstay
Monitors and manages positions on OANDA broker
Enforces time-based exits that were not happening
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import os

logger = logging.getLogger(__name__)

class OANDAPositionManager:
    """
    Manages OANDA live positions with automatic exit enforcement.
    This was missing - causing positions to sit open indefinitely.
    """
    
    def __init__(self, oanda_connector=None, unified_manager=None):
        """
        Initialize OANDA position manager.
        
        Args:
            oanda_connector: Connection to OANDA broker
            unified_manager: UnifiedPositionManager for centralized tracking
        """
        self.connector = oanda_connector
        self.unified_manager = unified_manager
        self.tracked_positions: Dict[str, Dict[str, Any]] = {}
        self.max_hold_hours = int(os.getenv('MAX_POSITION_HOLD_HOURS', '8'))
        self.day_trade_max = int(os.getenv('DAY_TRADE_MAX_HOURS', '6'))
        
        logger.info(f"🌍 OANDA Position Manager initialized")
        logger.info(f"   Broker: OANDA (live FX/CFDs)")
        logger.info(f"   Max hold: {self.max_hold_hours} hours")
        logger.info(f"   Unified tracking: {'✅ ACTIVE' if unified_manager else '❌ DISABLED'}")
    
    def sync_live_positions(self) -> List[Dict[str, Any]]:
        """
        Fetch and sync all live OANDA positions with unified manager.
        This MUST be called on every iteration to prevent overstays.
        
        Returns:
            List of synced positions
        """
        if not self.connector:
            logger.warning("❌ OANDA connector not available")
            return []
        
        try:
            # Fetch from OANDA API
            live_positions = self.connector.get_open_positions()
            
            logger.info(f"🔄 Syncing OANDA positions: {len(live_positions)} found")
            
            for oanda_pos in live_positions:
                # Convert OANDA position format to unified format
                pos_id = f"oanda:{oanda_pos['instrument']}:{int(oanda_pos['openTime'].timestamp())}"
                
                # Register with unified manager
                if self.unified_manager and pos_id not in self.tracked_positions:
                    unified_id = self.unified_manager.register_position(
                        broker='oanda',
                        symbol=oanda_pos['instrument'],
                        side='BUY' if float(oanda_pos['units']) > 0 else 'SELL',
                        entry_price=float(oanda_pos['averagePrice']),
                        entry_size=abs(float(oanda_pos['units'])),
                        entry_time=oanda_pos['openTime'],
                        strategy=oanda_pos.get('strategy', 'manual'),
                        stop_loss=float(oanda_pos.get('stopLossPrice', 0)) or None,
                        target_price=float(oanda_pos.get('takeProfitPrice', 0)) or None
                    )
                    
                    self.tracked_positions[pos_id] = unified_id
                    logger.info(f"   ✅ Registered: {oanda_pos['instrument']}")
                
                # Update with current price
                if pos_id in self.tracked_positions:
                    unified_id = self.tracked_positions[pos_id]
                    current_price = float(oanda_pos['currentPrice'])
                    self.unified_manager.update_position(unified_id, current_price)
            
            return live_positions
        
        except Exception as e:
            logger.error(f"❌ Error syncing OANDA positions: {e}")
            return []
    
    def check_all_positions_for_exit(self) -> List[Dict[str, Any]]:
        """
        Check ALL OANDA positions for exit conditions.
        This is what should have been preventing the overstay.
        
        Returns:
            List of positions that should exit
        """
        exit_signals = []
        
        if not self.unified_manager:
            logger.warning("❌ Unified manager not available")
            return []
        
        oanda_positions = self.unified_manager.get_positions_by_broker('oanda')
        
        for pos in oanda_positions:
            # Check exit conditions
            exit_signal = self.unified_manager.check_exit_conditions(
                next(k for k, v in self.tracked_positions.items() if v == pos)
            )
            
            if exit_signal and exit_signal.get('should_exit'):
                exit_signals.append({
                    'symbol': pos['symbol'],
                    'signal': exit_signal,
                    'position': pos
                })
                
                logger.warning(f"🛑 OANDA EXIT SIGNAL: {pos['symbol']}")
                logger.warning(f"   Reason: {exit_signal['reason']}")
        
        return exit_signals
    
    def execute_exit(self, symbol: str, exit_reason: str) -> bool:
        """
        Execute exit for OANDA position.
        
        Args:
            symbol: Trading instrument (EUR/USD, GBP/USD, etc)
            exit_reason: Reason for exit
        
        Returns:
            True if exit executed successfully
        """
        if not self.connector:
            logger.error("❌ OANDA connector not available")
            return False
        
        try:
            logger.warning(f"📤 Executing OANDA exit: {symbol}")
            logger.warning(f"   Reason: {exit_reason}")
            
            # Get current position details
            positions = self.connector.get_open_positions()
            oanda_pos = next((p for p in positions if p['instrument'] == symbol), None)
            
            if not oanda_pos:
                logger.error(f"❌ Position not found: {symbol}")
                return False
            
            # Close position at market price
            close_result = self.connector.close_position(
                instrument=symbol,
                units=oanda_pos['units'],
                reason=exit_reason
            )
            
            if close_result.get('success'):
                logger.info(f"✅ OANDA position closed: {symbol}")
                logger.info(f"   Exit price: {close_result.get('exit_price')}")
                logger.info(f"   P/L: {close_result.get('pnl')}")
                return True
            else:
                logger.error(f"❌ OANDA close failed: {close_result}")
                return False
        
        except Exception as e:
            logger.error(f"❌ Error executing OANDA exit: {e}")
            return False
    
    def get_positions_summary(self) -> Dict[str, Any]:
        """Get summary of all OANDA positions."""
        if not self.unified_manager:
            return {'error': 'Unified manager not available'}
        
        oanda_pos = self.unified_manager.get_positions_by_broker('oanda')
        
        summary = {
            'total_open': len(oanda_pos),
            'total_pnl': sum(p['unrealized_pnl'] for p in oanda_pos),
            'overstayed': len([p for p in oanda_pos if p['hours_open'] > self.max_hold_hours]),
            'positions': [
                {
                    'symbol': p['symbol'],
                    'side': p['side'],
                    'entry': p['entry_price'],
                    'current': p['current_price'],
                    'pnl': p['unrealized_pnl'],
                    'hours_held': p['hours_open']
                }
                for p in oanda_pos
            ]
        }
        
        return summary
    
    def print_oanda_status(self):
        """Print OANDA position status."""
        summary = self.get_positions_summary()
        
        logger.info("")
        logger.info("="*70)
        logger.info("🌍 OANDA POSITION STATUS")
        logger.info("="*70)
        
        if summary.get('error'):
            logger.error(f"Error: {summary['error']}")
            return
        
        if summary['total_open'] == 0:
            logger.info("No open OANDA positions")
        else:
            logger.info(f"Open positions: {summary['total_open']}")
            logger.info(f"Portfolio P/L: {summary['total_pnl']:+.2f}")
            
            if summary['overstayed'] > 0:
                logger.critical(f"🚨 OVERSTAYED: {summary['overstayed']} position(s) exceeded max hold!")
            
            for pos in summary['positions']:
                hours_warn = " ⏰" if pos['hours_held'] > (self.max_hold_hours * 0.8) else ""
                logger.info(f"{pos['symbol']:10} | {pos['side']:5} | "
                           f"P/L: {pos['pnl']:+.2f} | Hold: {pos['hours_held']:.1f}h{hours_warn}")
        
        logger.info("="*70)
        logger.info("")
