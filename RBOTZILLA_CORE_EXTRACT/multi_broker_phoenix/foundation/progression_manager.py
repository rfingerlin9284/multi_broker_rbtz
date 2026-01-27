"""Autonomous Progression Manager - Path B Implementation

Automatically graduates trader through phases:
Phase 1: Spot nano-lots ($5-10) - Prove edge
Phase 2: Spot scaling ($10-50) - Validate consistency  
Phase 3: 2x-3x leverage - Cautious amplification
Phase 4: 5x leverage - Intermediate scaling
Phase 5: 10x+ leverage - Advanced (only if crushing it)

Each phase requires proven performance metrics before graduation.
"""
from __future__ import annotations
import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import json

logger = logging.getLogger(__name__)


@dataclass
class PerformanceStats:
    """Track performance metrics for graduation criteria."""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_profit: float = 0.0
    total_loss: float = 0.0
    max_drawdown_pct: float = 0.0
    consecutive_wins: int = 0
    consecutive_losses: int = 0
    max_consecutive_losses: int = 0
    start_capital: float = 0.0
    current_capital: float = 0.0
    phase_start_time: datetime = None
    last_trade_time: datetime = None
    
    @property
    def win_rate(self) -> float:
        """Calculate win rate percentage."""
        if self.total_trades == 0:
            return 0.0
        return (self.winning_trades / self.total_trades) * 100
    
    @property
    def profit_factor(self) -> float:
        """Calculate profit factor (gross profit / gross loss)."""
        if self.total_loss == 0:
            return float('inf') if self.total_profit > 0 else 0.0
        return abs(self.total_profit / self.total_loss)
    
    @property
    def net_profit(self) -> float:
        """Calculate net profit/loss."""
        return self.total_profit + self.total_loss  # loss is negative
    
    @property
    def roi_pct(self) -> float:
        """Calculate ROI percentage."""
        if self.start_capital == 0:
            return 0.0
        return ((self.current_capital - self.start_capital) / self.start_capital) * 100
    
    @property
    def average_win(self) -> float:
        """Average winning trade size."""
        if self.winning_trades == 0:
            return 0.0
        return self.total_profit / self.winning_trades
    
    @property
    def average_loss(self) -> float:
        """Average losing trade size (as positive number)."""
        if self.losing_trades == 0:
            return 0.0
        return abs(self.total_loss / self.losing_trades)
    
    @property
    def risk_reward_ratio(self) -> float:
        """Average win / average loss."""
        if self.average_loss == 0:
            return float('inf') if self.average_win > 0 else 0.0
        return self.average_win / self.average_loss


@dataclass
class PhaseRequirements:
    """Requirements to graduate to next phase."""
    name: str
    min_trades: int
    min_win_rate_pct: float
    min_profit_factor: float
    max_drawdown_pct: float
    min_days_active: int
    max_consecutive_losses: int
    min_roi_pct: float
    position_size_usd: float
    leverage: float
    description: str


class ProgressionManager:
    """Manages autonomous progression through trading phases."""
    
    PHASES = {
        1: PhaseRequirements(
            name="NANO_SPOT",
            min_trades=100,
            min_win_rate_pct=55.0,
            min_profit_factor=1.5,
            max_drawdown_pct=10.0,
            min_days_active=14,
            max_consecutive_losses=5,
            min_roi_pct=10.0,  # 10% gain to graduate
            position_size_usd=10.0,
            leverage=1.0,
            description="Prove edge with $5-10 spot trades"
        ),
        2: PhaseRequirements(
            name="SCALED_SPOT",
            min_trades=50,
            min_win_rate_pct=57.0,
            min_profit_factor=1.6,
            max_drawdown_pct=12.0,
            min_days_active=10,
            max_consecutive_losses=5,
            min_roi_pct=15.0,
            position_size_usd=50.0,
            leverage=1.0,
            description="Scale to $50 trades, maintain performance"
        ),
        3: PhaseRequirements(
            name="LOW_LEVERAGE",
            min_trades=50,
            min_win_rate_pct=58.0,
            min_profit_factor=1.7,
            max_drawdown_pct=15.0,
            min_days_active=10,
            max_consecutive_losses=4,
            min_roi_pct=20.0,
            position_size_usd=100.0,
            leverage=3.0,
            description="2x-3x leverage, cautious amplification"
        ),
        4: PhaseRequirements(
            name="MID_LEVERAGE",
            min_trades=50,
            min_win_rate_pct=60.0,
            min_profit_factor=1.8,
            max_drawdown_pct=18.0,
            min_days_active=10,
            max_consecutive_losses=4,
            min_roi_pct=25.0,
            position_size_usd=200.0,
            leverage=5.0,
            description="5x leverage, intermediate scaling"
        ),
        5: PhaseRequirements(
            name="HIGH_LEVERAGE",
            min_trades=100,
            min_win_rate_pct=62.0,
            min_profit_factor=2.0,
            max_drawdown_pct=20.0,
            min_days_active=20,
            max_consecutive_losses=3,
            min_roi_pct=30.0,
            position_size_usd=500.0,
            leverage=10.0,
            description="10x leverage, advanced trader only"
        )
    }
    
    def __init__(self, starting_capital: float = 10.0, starting_phase: int = 1):
        """Initialize progression manager.
        
        Args:
            starting_capital: Initial capital to track
            starting_phase: Starting phase (default: 1 - NANO_SPOT)
        """
        self.current_phase = starting_phase
        self.stats = PerformanceStats(
            start_capital=starting_capital,
            current_capital=starting_capital,
            phase_start_time=datetime.now()
        )
        self.phase_history: List[Dict] = []
        self._state_file = os.getenv('PROGRESSION_STATE_FILE', 'data/progression_state.json')
        
        # Load previous state if exists
        self._load_state()
        
        logger.info(f"🎯 Progression Manager initialized")
        logger.info(f"   Starting Phase: {self.current_phase} - {self.PHASES[self.current_phase].name}")
        logger.info(f"   Starting Capital: ${starting_capital:.2f}")
        logger.info(f"   Graduation Requirements:")
        self._log_phase_requirements()
    
    def _log_phase_requirements(self):
        """Log current phase requirements."""
        req = self.PHASES[self.current_phase]
        logger.info(f"      • {req.min_trades}+ trades")
        logger.info(f"      • {req.min_win_rate_pct}%+ win rate")
        logger.info(f"      • {req.min_profit_factor}+ profit factor")
        logger.info(f"      • <{req.max_drawdown_pct}% max drawdown")
        logger.info(f"      • {req.min_days_active}+ days active")
        logger.info(f"      • {req.min_roi_pct}%+ ROI")
    
    def record_trade(self, pnl: float, capital_after: float):
        """Record trade result and update stats.
        
        Args:
            pnl: Profit/loss for the trade (positive = win, negative = loss)
            capital_after: Total capital after trade
        """
        self.stats.total_trades += 1
        self.stats.current_capital = capital_after
        self.stats.last_trade_time = datetime.now()
        
        if pnl > 0:
            self.stats.winning_trades += 1
            self.stats.total_profit += pnl
            self.stats.consecutive_wins += 1
            self.stats.consecutive_losses = 0
            logger.info(f"📈 Win #{self.stats.winning_trades}: ${pnl:.2f} (consecutive: {self.stats.consecutive_wins})")
        else:
            self.stats.losing_trades += 1
            self.stats.total_loss += pnl  # pnl is negative
            self.stats.consecutive_losses += 1
            self.stats.consecutive_wins = 0
            self.stats.max_consecutive_losses = max(
                self.stats.max_consecutive_losses,
                self.stats.consecutive_losses
            )
            logger.warning(f"📉 Loss #{self.stats.losing_trades}: ${pnl:.2f} (consecutive: {self.stats.consecutive_losses})")
        
        # Update max drawdown
        if self.stats.start_capital > 0:
            current_drawdown = ((self.stats.start_capital - capital_after) / self.stats.start_capital) * 100
            self.stats.max_drawdown_pct = max(self.stats.max_drawdown_pct, current_drawdown)
        
        # Log progress
        if self.stats.total_trades % 10 == 0:
            self._log_progress()
        
        # Save state
        self._save_state()
        
        # Check for graduation
        self._check_graduation()
    
    def _log_progress(self):
        """Log current progress towards graduation."""
        req = self.PHASES[self.current_phase]
        logger.info(f"📊 Phase {self.current_phase} Progress ({self.stats.total_trades} trades):")
        logger.info(f"   Win Rate: {self.stats.win_rate:.1f}% (need {req.min_win_rate_pct}%)")
        logger.info(f"   Profit Factor: {self.stats.profit_factor:.2f} (need {req.min_profit_factor})")
        logger.info(f"   ROI: {self.stats.roi_pct:.1f}% (need {req.min_roi_pct}%)")
        logger.info(f"   Max Drawdown: {self.stats.max_drawdown_pct:.1f}% (max {req.max_drawdown_pct}%)")
        logger.info(f"   Capital: ${self.stats.current_capital:.2f}")
    
    def _check_graduation(self):
        """Check if performance meets graduation criteria."""
        if self.current_phase >= len(self.PHASES):
            return  # Already at max phase
        
        req = self.PHASES[self.current_phase]
        
        # Calculate days active
        if self.stats.phase_start_time:
            days_active = (datetime.now() - self.stats.phase_start_time).days
        else:
            days_active = 0
        
        # Check all criteria
        criteria_met = {
            'trades': self.stats.total_trades >= req.min_trades,
            'win_rate': self.stats.win_rate >= req.min_win_rate_pct,
            'profit_factor': self.stats.profit_factor >= req.min_profit_factor,
            'drawdown': self.stats.max_drawdown_pct <= req.max_drawdown_pct,
            'days': days_active >= req.min_days_active,
            'consecutive_losses': self.stats.max_consecutive_losses <= req.max_consecutive_losses,
            'roi': self.stats.roi_pct >= req.min_roi_pct
        }
        
        all_met = all(criteria_met.values())
        
        if all_met:
            self._graduate_to_next_phase()
        else:
            # Log what's still needed
            missing = [k for k, v in criteria_met.items() if not v]
            if self.stats.total_trades % 25 == 0:  # Log every 25 trades
                logger.info(f"⏳ Graduation pending. Still need: {', '.join(missing)}")
    
    def _graduate_to_next_phase(self):
        """Graduate to next trading phase."""
        old_phase = self.current_phase
        old_req = self.PHASES[old_phase]
        
        # Record phase completion
        self.phase_history.append({
            'phase': old_phase,
            'name': old_req.name,
            'completed_at': datetime.now().isoformat(),
            'stats': asdict(self.stats),
            'days_taken': (datetime.now() - self.stats.phase_start_time).days
        })
        
        # Move to next phase
        self.current_phase += 1
        new_req = self.PHASES[self.current_phase]
        
        # Reset phase-specific stats
        self.stats.start_capital = self.stats.current_capital
        self.stats.total_trades = 0
        self.stats.winning_trades = 0
        self.stats.losing_trades = 0
        self.stats.total_profit = 0.0
        self.stats.total_loss = 0.0
        self.stats.max_drawdown_pct = 0.0
        self.stats.consecutive_wins = 0
        self.stats.consecutive_losses = 0
        self.stats.max_consecutive_losses = 0
        self.stats.phase_start_time = datetime.now()
        
        logger.warning("=" * 80)
        logger.warning(f"🎓 GRADUATION! Phase {old_phase} → Phase {self.current_phase}")
        logger.warning(f"   FROM: {old_req.name} ({old_req.leverage}x leverage, ${old_req.position_size_usd} positions)")
        logger.warning(f"   TO: {new_req.name} ({new_req.leverage}x leverage, ${new_req.position_size_usd} positions)")
        logger.warning(f"   Starting Capital: ${self.stats.start_capital:.2f}")
        logger.warning(f"   🎯 NEW REQUIREMENTS:")
        self._log_phase_requirements()
        logger.warning("=" * 80)
        
        self._save_state()
    
    def get_current_phase_config(self) -> PhaseRequirements:
        """Get current phase configuration."""
        return self.PHASES[self.current_phase]
    
    def get_position_size(self) -> float:
        """Get recommended position size for current phase."""
        return self.PHASES[self.current_phase].position_size_usd
    
    def get_leverage(self) -> float:
        """Get leverage for current phase."""
        return self.PHASES[self.current_phase].leverage
    
    def should_use_futures(self) -> bool:
        """Check if current phase should use futures (leverage > 1)."""
        return self.PHASES[self.current_phase].leverage > 1.0
    
    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive progression summary."""
        req = self.PHASES[self.current_phase]
        days_active = (datetime.now() - self.stats.phase_start_time).days if self.stats.phase_start_time else 0
        
        return {
            'current_phase': self.current_phase,
            'phase_name': req.name,
            'phase_description': req.description,
            'leverage': req.leverage,
            'position_size': req.position_size_usd,
            'use_futures': self.should_use_futures(),
            'stats': {
                'total_trades': self.stats.total_trades,
                'win_rate': round(self.stats.win_rate, 2),
                'profit_factor': round(self.stats.profit_factor, 2),
                'roi_pct': round(self.stats.roi_pct, 2),
                'max_drawdown_pct': round(self.stats.max_drawdown_pct, 2),
                'net_profit': round(self.stats.net_profit, 2),
                'current_capital': round(self.stats.current_capital, 2),
                'days_active': days_active
            },
            'requirements': {
                'min_trades': req.min_trades,
                'min_win_rate_pct': req.min_win_rate_pct,
                'min_profit_factor': req.min_profit_factor,
                'max_drawdown_pct': req.max_drawdown_pct,
                'min_days_active': req.min_days_active,
                'min_roi_pct': req.min_roi_pct
            },
            'progress': {
                'trades_complete': f"{self.stats.total_trades}/{req.min_trades}",
                'win_rate_met': self.stats.win_rate >= req.min_win_rate_pct,
                'profit_factor_met': self.stats.profit_factor >= req.min_profit_factor,
                'roi_met': self.stats.roi_pct >= req.min_roi_pct,
                'drawdown_ok': self.stats.max_drawdown_pct <= req.max_drawdown_pct,
                'days_met': days_active >= req.min_days_active
            },
            'phase_history': self.phase_history
        }
    
    def save_state(self):
        """Public method to save progression state."""
        self._save_state()
    
    def _save_state(self):
        """Save progression state to file."""
        try:
            os.makedirs(os.path.dirname(self._state_file), exist_ok=True)
            state = {
                'current_phase': self.current_phase,
                'stats': asdict(self.stats),
                'phase_history': self.phase_history,
                'last_updated': datetime.now().isoformat()
            }
            # Convert datetime objects to strings
            if state['stats']['phase_start_time']:
                state['stats']['phase_start_time'] = state['stats']['phase_start_time'].isoformat()
            if state['stats']['last_trade_time']:
                state['stats']['last_trade_time'] = state['stats']['last_trade_time'].isoformat()
            
            with open(self._state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save progression state: {e}")
    
    def _load_state(self):
        """Load progression state from file."""
        try:
            if os.path.exists(self._state_file):
                with open(self._state_file, 'r') as f:
                    state = json.load(f)
                
                self.current_phase = state['current_phase']
                stats_dict = state['stats']
                # Convert datetime strings back to datetime
                if stats_dict['phase_start_time']:
                    stats_dict['phase_start_time'] = datetime.fromisoformat(stats_dict['phase_start_time'])
                if stats_dict['last_trade_time']:
                    stats_dict['last_trade_time'] = datetime.fromisoformat(stats_dict['last_trade_time'])
                
                self.stats = PerformanceStats(**stats_dict)
                self.phase_history = state.get('phase_history', [])
                
                logger.info(f"📂 Loaded progression state from {self._state_file}")
        except Exception as e:
            logger.warning(f"Could not load progression state: {e}. Starting fresh.")
