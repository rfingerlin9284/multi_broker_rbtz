"""
Live Position Narrator
Real-time narration of open positions with trailing stop updates
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class PositionNarration:
    """Live position with trailing stop tracking."""
    ticket: str
    symbol: str
    side: str
    entry_price: float
    size: float
    initial_sl: float
    current_sl: float
    current_price: float
    unrealized_pnl: float
    sl_moved_count: int = 0
    last_sl_update: Optional[datetime] = None
    entry_time: datetime = None
    
    def get_distance_from_entry(self) -> float:
        """Calculate distance from entry in pips/points."""
        if self.side == 'BUY':
            return self.current_price - self.entry_price
        else:
            return self.entry_price - self.current_price
    
    def get_sl_distance(self) -> float:
        """Calculate current SL distance from price."""
        if self.side == 'BUY':
            return self.current_price - self.current_sl
        else:
            return self.current_sl - self.current_price


import json

class LivePositionNarrator:
    """Real-time narrator for position updates and trailing stops."""
    
    def __init__(self):
        self.positions: Dict[str, PositionNarration] = {}
        self.narration_enabled = True
        self.json_path = '/tmp/position_narration.jsonl'
        
    def _write_json(self, payload: Dict):
        try:
            with open(self.json_path, 'a') as fh:
                fh.write(json.dumps(payload) + "\n")
        except Exception as e:
            logger.debug(f"Could not write narration JSON: {e}")

    def narrate_new_position(self, ticket: str, symbol: str, side: str, 
                            entry_price: float, size: float, initial_sl: float):
        """Narrate new position entry."""
        position = PositionNarration(
            ticket=ticket,
            symbol=symbol,
            side=side,
            entry_price=entry_price,
            size=size,
            initial_sl=initial_sl,
            current_sl=initial_sl,
            current_price=entry_price,
            unrealized_pnl=0.0,
            sl_moved_count=0,
            entry_time=datetime.now()
        )
        
        self.positions[ticket] = position
        
        # Narrate entry
        logger.info("=" * 80)
        logger.info(f"📍 NEW POSITION OPENED")
        logger.info(f"   Ticket: {ticket}")
        logger.info(f"   Symbol: {symbol} | Side: {side}")
        logger.info(f"   Entry: ${entry_price:.4f} | Size: {size:.4f}")
        logger.info(f"   Initial SL: ${initial_sl:.4f}")
        logger.info(f"   Time: {position.entry_time.strftime('%H:%M:%S')}")
        logger.info("=" * 80)

        # Write JSON narration (human_summary included)
        self._write_json({
            'timestamp': position.entry_time.isoformat(),
            'event': 'new_position',
            'ticket': ticket,
            'symbol': symbol,
            'side': side,
            'entry_price': entry_price,
            'size': size,
            'initial_sl': initial_sl,
            'human_summary': f"New position {symbol} {side} entry ${entry_price:.4f} size {size:.4f}"
        })
        
    def update_position_price(self, ticket: str, current_price: float, unrealized_pnl: float):
        """Update current price and calculate unrealized P&L."""
        if ticket not in self.positions:
            return
        
        position = self.positions[ticket]
        position.current_price = current_price
        position.unrealized_pnl = unrealized_pnl
        
    def narrate_trailing_stop_update(self, ticket: str, new_sl: float, reason: str = ""):
        """Narrate trailing stop adjustment."""
        if ticket not in self.positions:
            logger.warning(f"⚠️  Cannot update SL - Ticket {ticket} not found")
            return
        
        position = self.positions[ticket]
        old_sl = position.current_sl
        
        # Only narrate if SL actually moved
        if abs(new_sl - old_sl) < 0.0001:
            return
        
        position.current_sl = new_sl
        position.sl_moved_count += 1
        position.last_sl_update = datetime.now()
        
        # Calculate movement
        sl_movement = abs(new_sl - old_sl)
        distance_from_entry = position.get_distance_from_entry()
        sl_distance = position.get_sl_distance()
        
        # Narrate the update
        logger.info("")
        logger.info("🔄 " + "━" * 76)
        logger.info(f"🛡️  TRAILING STOP UPDATED - Ticket {ticket}")
        logger.info(f"   Symbol: {position.symbol} {position.side}")
        logger.info(f"   Entry: ${position.entry_price:.4f} → Current: ${position.current_price:.4f}")
        logger.info(f"   SL Moved: ${old_sl:.4f} → ${new_sl:.4f} ({'+' if new_sl > old_sl else ''}{sl_movement:.4f})")
        logger.info(f"   Updates: {position.sl_moved_count} times | Distance from entry: {distance_from_entry:.4f}")
        logger.info(f"   Current protection: {sl_distance:.4f} points")
        logger.info(f"   Unrealized P&L: ${position.unrealized_pnl:+.2f}")
        if reason:
            logger.info(f"   Reason: {reason}")
        logger.info("🔄 " + "━" * 76)
        logger.info("")

        # Write JSON narration for UI / persistent terminal
        self._write_json({
            'timestamp': position.last_sl_update.isoformat(),
            'event': 'trailing_stop_update',
            'ticket': ticket,
            'symbol': position.symbol,
            'side': position.side,
            'old_sl': old_sl,
            'new_sl': new_sl,
            'unrealized_pnl': position.unrealized_pnl,
            'human_summary': f"Trailing stop for {position.symbol} updated {old_sl:.4f} → {new_sl:.4f}; P&L ${position.unrealized_pnl:+.2f}"
        })
        
    def narrate_position_close(self, ticket: str, exit_price: float, realized_pnl: float, reason: str = ""):
        """Narrate position closure."""
        if ticket not in self.positions:
            logger.warning(f"⚠️  Cannot close - Ticket {ticket} not found")
            return
        
        position = self.positions[ticket]
        duration = (datetime.now() - position.entry_time).total_seconds() / 60  # minutes
        
        outcome = "✅ WIN" if realized_pnl > 0 else "❌ LOSS" if realized_pnl < 0 else "⚖️  BREAKEVEN"
        
        logger.info("")
        logger.info("🏁 " + "=" * 76)
        logger.info(f"{outcome} - POSITION CLOSED")
        logger.info(f"   Ticket: {ticket}")
        logger.info(f"   Symbol: {position.symbol} {position.side}")
        logger.info(f"   Entry: ${position.entry_price:.4f} → Exit: ${exit_price:.4f}")
        logger.info(f"   Initial SL: ${position.initial_sl:.4f} | Final SL: ${position.current_sl:.4f}")
        logger.info(f"   SL Adjustments: {position.sl_moved_count} times")
        logger.info(f"   Duration: {duration:.1f} minutes")
        logger.info(f"   Realized P&L: ${realized_pnl:+.2f}")
        if reason:
            logger.info(f"   Close Reason: {reason}")
        logger.info("🏁 " + "=" * 76)
        logger.info("")

        # Write JSON narration for UI / persistent terminal
        self._write_json({
            'timestamp': datetime.now().isoformat(),
            'event': 'position_close',
            'ticket': ticket,
            'symbol': position.symbol,
            'side': position.side,
            'entry_price': position.entry_price,
            'exit_price': exit_price,
            'realized_pnl': realized_pnl,
            'duration_minutes': round(duration, 1),
            'human_summary': f"{outcome} {position.symbol} {position.side} closed at ${exit_price:.4f} P&L ${realized_pnl:+.2f} ({duration:.1f}m)"
        })
        
        # Remove from tracking
        del self.positions[ticket]
        
    def display_all_positions(self):
        """Display summary of all open positions."""
        if not self.positions:
            logger.info("📭 No open positions")
            return
        
        logger.info("")
        logger.info("╔" + "═" * 78 + "╗")
        logger.info("║" + " " * 25 + "📊 LIVE POSITIONS" + " " * 36 + "║")
        logger.info("╠" + "═" * 78 + "╣")
        
        for ticket, pos in self.positions.items():
            duration = (datetime.now() - pos.entry_time).total_seconds() / 60
            pnl_indicator = "🟢" if pos.unrealized_pnl > 0 else "🔴" if pos.unrealized_pnl < 0 else "⚪"
            
            logger.info(f"║ Ticket: {ticket:<15} | {pos.symbol:<8} {pos.side:<4} | {pnl_indicator} ${pos.unrealized_pnl:+7.2f}" + " " * 15 + "║")
            logger.info(f"║   Entry: ${pos.entry_price:8.4f} → Now: ${pos.current_price:8.4f} | Duration: {duration:5.1f}m" + " " * 14 + "║")
            logger.info(f"║   SL: ${pos.initial_sl:8.4f} → ${pos.current_sl:8.4f} | Moved: {pos.sl_moved_count} times" + " " * 17 + "║")
            logger.info("╠" + "─" * 78 + "╣")
        
        logger.info("╚" + "═" * 78 + "╝")
        logger.info("")
    
    def get_position_summary(self) -> Dict:
        """Get summary statistics of all positions."""
        if not self.positions:
            return {
                'total': 0,
                'total_pnl': 0.0,
                'winning': 0,
                'losing': 0
            }
        
        total_pnl = sum(p.unrealized_pnl for p in self.positions.values())
        winning = sum(1 for p in self.positions.values() if p.unrealized_pnl > 0)
        losing = sum(1 for p in self.positions.values() if p.unrealized_pnl < 0)
        
        return {
            'total': len(self.positions),
            'total_pnl': total_pnl,
            'winning': winning,
            'losing': losing,
            'positions': list(self.positions.values())
        }
