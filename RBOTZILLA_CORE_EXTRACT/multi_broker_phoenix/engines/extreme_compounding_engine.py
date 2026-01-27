#!/usr/bin/env python3
"""
EXTREME COMPOUNDING ENGINE
Dynamic position sizing with Kelly Criterion, leverage scaling, and aggressive reinvestment
"""
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class AccountState:
    """Current account state for compounding calculations"""
    starting_balance: float
    current_balance: float
    peak_balance: float
    drawdown_pct: float
    consecutive_wins: int
    consecutive_losses: int
    win_rate_30d: float
    avg_win_pct: float
    avg_loss_pct: float


class ExtremeCompoundingEngine:
    """
    Aggressive position sizing with dynamic leverage and Kelly Criterion
    
    Features:
    - Kelly Criterion for optimal bet sizing
    - Win-streak leverage scaling (up to 5x on hot streaks)
    - Geometric compounding (profits reinvested immediately)
    - Dynamic max position based on account growth
    """
    
    def __init__(self,
                 base_risk_pct: float = 1.0,
                 max_leverage: float = 5.0,
                 kelly_fraction: float = 0.5,  # Half Kelly for safety
                 compound_threshold: float = 1.05):  # Start compounding at 5% profit
        """
        Args:
            base_risk_pct: Base risk per trade (% of current balance)
            max_leverage: Maximum leverage multiplier
            kelly_fraction: Fraction of Kelly Criterion to use (0.5 = Half Kelly)
            compound_threshold: Balance growth needed to start compounding (1.05 = 5%)
        """
        self.base_risk_pct = base_risk_pct
        self.max_leverage = max_leverage
        self.kelly_fraction = kelly_fraction
        self.compound_threshold = compound_threshold
        
        logger.info("🔥 EXTREME COMPOUNDING ENGINE ACTIVATED")
        logger.info(f"   Base Risk: {base_risk_pct}% per trade")
        logger.info(f"   Max Leverage: {max_leverage}x")
        logger.info(f"   Kelly Fraction: {kelly_fraction}")
        logger.info(f"   Compound Threshold: {(compound_threshold-1)*100:.1f}%")
    
    def calculate_position_size(self, 
                                account: AccountState,
                                signal_strength: float,
                                win_probability: float) -> Dict[str, Any]:
        """
        Calculate aggressive position size with dynamic leverage
        
        Args:
            account: Current account state
            signal_strength: Trade signal quality (0.0-1.0)
            win_probability: Estimated win probability (0.0-1.0)
        
        Returns:
            {
                'base_size': float,  # Base position size ($)
                'leverage': float,   # Applied leverage multiplier
                'total_size': float, # Final position size ($)
                'risk_pct': float,   # Actual risk as % of balance
                'kelly_optimal': float,  # Kelly-optimal size
                'reason': str       # Explanation
            }
        """
        # 1. Calculate Kelly Criterion optimal size
        kelly_optimal = self._kelly_criterion(
            win_probability,
            account.avg_win_pct,
            abs(account.avg_loss_pct)
        )
        
        # 2. Apply Kelly fraction for safety
        kelly_size = kelly_optimal * self.kelly_fraction
        
        # 3. Calculate base position (% of current balance)
        base_risk = self.base_risk_pct / 100.0
        
        # 4. Adjust for signal strength
        signal_multiplier = 0.5 + (signal_strength * 1.5)  # 0.5x to 2.0x
        adjusted_risk = base_risk * signal_multiplier
        
        # 5. Apply win-streak leverage
        leverage = self._calculate_leverage(account)
        
        # 6. Compound if account is growing
        compound_mult = self._compound_multiplier(account)
        
        # 7. Calculate final sizes
        base_size = account.current_balance * adjusted_risk
        leveraged_size = base_size * leverage * compound_mult
        
        # 8. Cap at Kelly optimal (safety limit)
        kelly_cap = account.current_balance * kelly_size
        final_size = min(leveraged_size, kelly_cap)
        
        # 9. Emergency brake if in drawdown
        if account.drawdown_pct > 10.0:
            final_size *= 0.5  # Cut size in half during drawdown
            reason = f"⚠️ DRAWDOWN PROTECTION: {account.drawdown_pct:.1f}% DD"
        elif leverage > 1.5:
            reason = f"🔥 WIN STREAK: {account.consecutive_wins} wins, {leverage:.1f}x leverage"
        elif compound_mult > 1.0:
            reason = f"📈 COMPOUNDING: {(compound_mult-1)*100:.1f}% growth boost"
        else:
            reason = "📊 STANDARD: Base sizing"
        
        actual_risk_pct = (final_size / account.current_balance) * 100
        
        return {
            'base_size': base_size,
            'leverage': leverage,
            'total_size': final_size,
            'risk_pct': actual_risk_pct,
            'kelly_optimal': kelly_cap,
            'compound_multiplier': compound_mult,
            'signal_multiplier': signal_multiplier,
            'reason': reason
        }
    
    def _kelly_criterion(self, 
                        win_prob: float,
                        avg_win_pct: float,
                        avg_loss_pct: float) -> float:
        """
        Calculate Kelly Criterion optimal bet size
        
        Formula: f* = (p * b - q) / b
        where:
            p = probability of winning
            q = probability of losing (1 - p)
            b = ratio of average win to average loss
        """
        if avg_loss_pct == 0 or win_prob <= 0:
            return 0.0
        
        b = avg_win_pct / avg_loss_pct  # Win/loss ratio
        q = 1.0 - win_prob
        
        kelly = (win_prob * b - q) / b
        
        # Kelly can be negative (don't bet) or > 1.0 (bet more than bankroll)
        # We cap at reasonable limits
        return max(0.0, min(kelly, 0.5))  # Max 50% of bankroll
    
    def _calculate_leverage(self, account: AccountState) -> float:
        """
        Calculate dynamic leverage based on win streak
        
        Logic:
        - 3+ wins: 1.5x
        - 5+ wins: 2.0x
        - 7+ wins: 3.0x
        - 10+ wins: 5.0x (MAX)
        - Any loss: reset to 1.0x
        """
        if account.consecutive_losses > 0:
            return 1.0  # No leverage after losses
        
        wins = account.consecutive_wins
        
        if wins >= 10:
            return min(5.0, self.max_leverage)
        elif wins >= 7:
            return min(3.0, self.max_leverage)
        elif wins >= 5:
            return min(2.0, self.max_leverage)
        elif wins >= 3:
            return min(1.5, self.max_leverage)
        else:
            return 1.0
    
    def _compound_multiplier(self, account: AccountState) -> float:
        """
        Calculate compounding boost based on account growth
        
        Logic:
        - If balance > starting * compound_threshold: start compounding
        - Compound up to 2x when balance doubles
        """
        if account.current_balance <= account.starting_balance * self.compound_threshold:
            return 1.0  # No compounding yet
        
        growth_ratio = account.current_balance / account.starting_balance
        
        # Linear scale from 1.0 to 2.0 as balance grows from threshold to 2x
        compound_mult = 1.0 + min((growth_ratio - self.compound_threshold), 1.0)
        
        return compound_mult
    
    def should_scale_in(self,
                       account: AccountState,
                       current_profit_pct: float,
                       signal_improving: bool) -> Optional[float]:
        """
        Determine if we should scale into winning position
        
        Returns:
            Additional position size to add, or None
        """
        # Only scale winners
        if current_profit_pct < 2.0:
            return None
        
        # Only scale if signal is improving
        if not signal_improving:
            return None
        
        # Don't scale if already leveraged
        leverage = self._calculate_leverage(account)
        if leverage > 2.0:
            return None
        
        # Scale in with 50% of original size
        base_size = account.current_balance * (self.base_risk_pct / 100.0)
        scale_size = base_size * 0.5
        
        logger.info(f"📈 SCALING IN: +${scale_size:,.0f} to winning position")
        
        return scale_size
    
    def emergency_deleverage(self, account: AccountState) -> float:
        """
        Calculate emergency position reduction during drawdown
        
        Returns:
            Reduction multiplier (0.0-1.0)
        """
        if account.drawdown_pct < 5.0:
            return 1.0  # No reduction
        elif account.drawdown_pct < 10.0:
            return 0.75  # 25% reduction
        elif account.drawdown_pct < 15.0:
            return 0.50  # 50% reduction
        else:
            return 0.25  # 75% reduction - DANGER ZONE


# Example usage
if __name__ == "__main__":
    engine = ExtremeCompoundingEngine(
        base_risk_pct=2.0,  # 2% base risk (AGGRESSIVE)
        max_leverage=5.0,
        kelly_fraction=0.5
    )
    
    # Simulate hot streak
    account = AccountState(
        starting_balance=10000,
        current_balance=15000,  # +50% growth
        peak_balance=15000,
        drawdown_pct=0.0,
        consecutive_wins=7,
        consecutive_losses=0,
        win_rate_30d=0.75,
        avg_win_pct=5.0,
        avg_loss_pct=2.0
    )
    
    sizing = engine.calculate_position_size(
        account=account,
        signal_strength=0.9,
        win_probability=0.75
    )
    
    print(f"Base Size: ${sizing['base_size']:,.0f}")
    print(f"Leverage: {sizing['leverage']:.1f}x")
    print(f"Total Size: ${sizing['total_size']:,.0f}")
    print(f"Risk: {sizing['risk_pct']:.1f}%")
    print(f"Reason: {sizing['reason']}")
