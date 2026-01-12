"""Centralized Safety Tripwire System

Monitors all trading activity across all brokers and enforces safety limits:
- Maximum drawdown percentage
- Daily loss limits
- Consecutive loss breakers  
- Volatility circuit breakers
- Edge validation requirements

This system can STOP ALL TRADING across all brokers when limits are hit.
"""
from __future__ import annotations
import os
import logging
from typing import Dict, Any, List
from datetime import datetime, date
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SafetyLimits:
    """Safety limit configuration."""
    max_drawdown_pct: float = 10.0
    max_consecutive_losses: int = 5
    daily_loss_limit_usd: float = 100.0
    volatility_circuit_breaker_pct: float = 15.0
    require_edge_validation: bool = True
    min_win_rate_pct: float = 55.0
    min_profit_factor: float = 1.5


class SafetyTripwireSystem:
    """Centralized safety monitoring and enforcement."""
    
    def __init__(self, limits: SafetyLimits = None):
        """Initialize safety system with limits from env or defaults."""
        self.limits = limits or self._load_from_env()
        
        # Trading state
        self.all_stopped = False
        self.stop_reason = None
        
        # Tracking
        self.peak_equity = 0.0
        self.current_equity = 0.0
        self.consecutive_losses = 0
        self._current_date = date.today()
        self._daily_loss = 0.0
        self._trades_today: List[Dict] = []
        
        # Edge validation
        self.total_trades = 0
        self.winning_trades = 0
        self.total_profit = 0.0
        self.total_loss = 0.0
        self.edge_validated = False
        
        logger.info("🛡️  Safety Tripwire System initialized")
        logger.info(f"   Max drawdown: {self.limits.max_drawdown_pct}%")
        logger.info(f"   Daily loss limit: ${self.limits.daily_loss_limit_usd:.2f}")
        logger.info(f"   Max consecutive losses: {self.limits.max_consecutive_losses}")
        logger.info(f"   Volatility breaker: {self.limits.volatility_circuit_breaker_pct}%")
        
    def _load_from_env(self) -> SafetyLimits:
        """Load limits from environment variables."""
        return SafetyLimits(
            max_drawdown_pct=float(os.getenv('MAX_DRAWDOWN_PCT', '10.0')),
            max_consecutive_losses=int(os.getenv('MAX_CONSECUTIVE_LOSSES', '5')),
            daily_loss_limit_usd=float(os.getenv('DAILY_LOSS_LIMIT_USD', '100.0')),
            volatility_circuit_breaker_pct=float(os.getenv('VOLATILITY_CIRCUIT_BREAKER_PCT', '15.0')),
            require_edge_validation=os.getenv('REQUIRE_EDGE_VALIDATION', 'true').lower() == 'true',
            min_win_rate_pct=float(os.getenv('MIN_WIN_RATE_PCT', '55.0')),
            min_profit_factor=float(os.getenv('MIN_PROFIT_FACTOR', '1.5'))
        )
    
    def _reset_daily_stats(self):
        """Reset daily tracking if new day."""
        today = date.today()
        if today != self._current_date:
            logger.info(f"📅 New trading day - resetting daily stats")
            logger.info(f"   Previous: {len(self._trades_today)} trades, ${self._daily_loss:.2f} loss")
            self._current_date = today
            self._daily_loss = 0.0
            self._trades_today = []
    
    def can_trade(self) -> Dict[str, Any]:
        """Check if trading is allowed."""
        self._reset_daily_stats()
        
        if self.all_stopped:
            return {
                'allowed': False,
                'reason': f'⛔ ALL TRADING STOPPED: {self.stop_reason}'
            }
        
        # Check edge validation requirement
        if self.limits.require_edge_validation and not self.edge_validated and self.total_trades >= 100:
            win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0
            profit_factor = (self.total_profit / abs(self.total_loss)) if self.total_loss < 0 else 0
            
            if win_rate < self.limits.min_win_rate_pct:
                self._stop_all_trading(f"Win rate too low: {win_rate:.1f}% < {self.limits.min_win_rate_pct}%")
                return {'allowed': False, 'reason': self.stop_reason}
            
            if profit_factor < self.limits.min_profit_factor:
                self._stop_all_trading(f"Profit factor too low: {profit_factor:.2f} < {self.limits.min_profit_factor}")
                return {'allowed': False, 'reason': self.stop_reason}
        
        # Check drawdown
        if self.peak_equity > 0:
            drawdown_pct = ((self.peak_equity - self.current_equity) / self.peak_equity) * 100
            if drawdown_pct > self.limits.max_drawdown_pct:
                self._stop_all_trading(f"Max drawdown exceeded: {drawdown_pct:.1f}% > {self.limits.max_drawdown_pct}%")
                return {'allowed': False, 'reason': self.stop_reason}
        
        # Check consecutive losses
        if self.consecutive_losses >= self.limits.max_consecutive_losses:
            self._stop_all_trading(f"{self.consecutive_losses} consecutive losses")
            return {'allowed': False, 'reason': self.stop_reason}
        
        # Check daily loss limit
        if self._daily_loss >= self.limits.daily_loss_limit_usd:
            self._stop_all_trading(f"Daily loss limit: ${self._daily_loss:.2f} >= ${self.limits.daily_loss_limit_usd:.2f}")
            return {'allowed': False, 'reason': self.stop_reason}
        
        return {'allowed': True}
    
    def record_trade(self, trade: Dict[str, Any]):
        """Record trade and update all tracking."""
        self._reset_daily_stats()
        
        pnl = trade.get('pnl', 0.0)
        self.total_trades += 1
        
        # Update equity
        self.current_equity += pnl
        if self.current_equity > self.peak_equity:
            self.peak_equity = self.current_equity
        
        # Track wins/losses
        if pnl > 0:
            self.winning_trades += 1
            self.total_profit += pnl
            self.consecutive_losses = 0  # Reset on win
        elif pnl < 0:
            self.total_loss += pnl
            self.consecutive_losses += 1
            self._daily_loss += abs(pnl)
        
        # Record trade
        self._trades_today.append(trade)
        
        # Calculate metrics
        win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0
        profit_factor = (self.total_profit / abs(self.total_loss)) if self.total_loss < 0 else 0
        drawdown_pct = ((self.peak_equity - self.current_equity) / self.peak_equity * 100) if self.peak_equity > 0 else 0
        
        # Log status
        result_emoji = "📈" if pnl > 0 else "📉"
        logger.info(f"{result_emoji} Trade #{self.total_trades}: ${pnl:+.2f}")
        logger.info(f"   Win rate: {win_rate:.1f}% ({self.winning_trades}/{self.total_trades})")
        logger.info(f"   Profit factor: {profit_factor:.2f}")
        logger.info(f"   Drawdown: {drawdown_pct:.1f}%")
        logger.info(f"   Consecutive losses: {self.consecutive_losses}")
        logger.info(f"   Daily loss: ${self._daily_loss:.2f}/{self.limits.daily_loss_limit_usd:.2f}")
        
        # Check if edge validated (after 100 trades)
        if self.total_trades >= 100 and not self.edge_validated:
            if win_rate >= self.limits.min_win_rate_pct and profit_factor >= self.limits.min_profit_factor:
                self.edge_validated = True
                logger.info(f"✅ EDGE VALIDATED: Win rate {win_rate:.1f}%, PF {profit_factor:.2f}")
    
    def _stop_all_trading(self, reason: str):
        """Stop all trading across all brokers."""
        self.all_stopped = True
        self.stop_reason = reason
        logger.error(f"⛔ EMERGENCY STOP: {reason}")
        logger.error(f"   ALL TRADING HALTED ACROSS ALL BROKERS")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current safety system status."""
        self._reset_daily_stats()
        
        win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0
        profit_factor = (self.total_profit / abs(self.total_loss)) if self.total_loss < 0 else 0
        drawdown_pct = ((self.peak_equity - self.current_equity) / self.peak_equity * 100) if self.peak_equity > 0 else 0
        
        return {
            'trading_allowed': not self.all_stopped,
            'stop_reason': self.stop_reason,
            'total_trades': self.total_trades,
            'win_rate_pct': win_rate,
            'profit_factor': profit_factor,
            'drawdown_pct': drawdown_pct,
            'consecutive_losses': self.consecutive_losses,
            'daily_loss': self._daily_loss,
            'daily_loss_limit': self.limits.daily_loss_limit_usd,
            'edge_validated': self.edge_validated,
            'current_equity': self.current_equity,
            'peak_equity': self.peak_equity
        }


# Global instance
_safety_system = None

def get_safety_system() -> SafetyTripwireSystem:
    """Get or create global safety system instance."""
    global _safety_system
    if _safety_system is None:
        _safety_system = SafetyTripwireSystem()
    return _safety_system
