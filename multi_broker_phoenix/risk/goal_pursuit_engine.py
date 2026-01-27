"""
GOAL PURSUIT ENGINE - Smart $500/Day Achievement System

This module implements intelligent capital allocation to achieve the daily profit goal:

1. MOMENTUM-BASED SCALING: When momentum is strong, allocate MORE capital
2. TIGHT STOP LOSSES: Dynamic SL based on volatility (ATR-adaptive)
3. QUANT HEDGING: Place opposing positions to recapture losses efficiently
4. GOAL TRACKING: Adjust aggression based on progress toward daily target

Philosophy:
- When BEHIND target: Be more aggressive, larger positions on high-confidence setups
- When AHEAD of target: Lock in gains, reduce risk, stop early if goal met
- Strong momentum = opportunity to capture price quickly with tight SLs
- Losses get hedged to minimize drawdown and recapture efficiently
"""
import os
import json
import time
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field

# Configuration
DAILY_GOAL_USD = float(os.getenv('DAILY_PROFIT_GOAL_USD', '500.0'))
MAX_AGGRESSION_MULTIPLIER = float(os.getenv('MAX_AGGRESSION_MULT', '2.5'))  # Max 2.5x normal size
MIN_AGGRESSION_MULTIPLIER = float(os.getenv('MIN_AGGRESSION_MULT', '0.5'))  # Min 0.5x when protecting
MOMENTUM_SCALE_THRESHOLD = float(os.getenv('MOMENTUM_SCALE_THRESHOLD', '0.001'))  # 0.1% momentum triggers scaling
HEDGE_TRIGGER_PIPS = float(os.getenv('HEDGE_TRIGGER_PIPS', '15'))  # Hedge when position down 15 pips
HEDGE_SIZE_RATIO = float(os.getenv('HEDGE_SIZE_RATIO', '0.5'))  # Hedge at 50% of original position


@dataclass
class DailyGoalState:
    """Tracks progress toward daily profit goal."""
    date: str = ""
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    goal: float = DAILY_GOAL_USD
    trades_today: int = 0
    wins_today: int = 0
    losses_today: int = 0
    hedges_placed: int = 0
    hedges_recovered: float = 0.0
    goal_reached: bool = False
    peak_realized: float = 0.0
    
    @property
    def progress_pct(self) -> float:
        """Progress toward goal as percentage."""
        return (self.realized_pnl / self.goal * 100) if self.goal > 0 else 0
    
    @property
    def remaining(self) -> float:
        """Amount still needed to reach goal."""
        return max(0, self.goal - self.realized_pnl)
    
    @property
    def win_rate(self) -> float:
        """Today's win rate."""
        total = self.wins_today + self.losses_today
        return (self.wins_today / total * 100) if total > 0 else 0


@dataclass
class MomentumSignal:
    """Captures momentum characteristics for position sizing."""
    symbol: str
    momentum_pct: float  # Price change %
    momentum_strength: str  # WEAK, MODERATE, STRONG, EXTREME
    trend_alignment: bool  # Is momentum aligned with trade direction?
    volatility: float  # ATR-based volatility measure
    recommended_sl_pips: float  # Tight SL recommendation
    confidence_boost: float  # Additional confidence from momentum


@dataclass
class HedgeOpportunity:
    """Detected opportunity to hedge a losing position."""
    original_trade_id: str
    symbol: str
    original_side: str
    original_units: float
    current_loss_pips: float
    hedge_side: str
    hedge_units: float
    hedge_entry: float
    hedge_sl: float
    hedge_tp: float
    reason: str


class GoalPursuitEngine:
    """
    Smart engine that pursues the daily $500 profit goal with:
    - Momentum-scaled position sizing
    - Tight stop losses
    - Quant hedging for loss recovery
    """
    
    def __init__(self, repo_root: Path = None):
        self.repo_root = repo_root or Path(__file__).resolve().parents[2]
        self.state_file = self.repo_root / 'ops' / 'state' / 'daily_goal.json'
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state = self._load_state()
        self.active_hedges: Dict[str, Dict] = {}
        
    def _load_state(self) -> DailyGoalState:
        """Load or initialize daily state."""
        today = date.today().isoformat()
        
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    if data.get('date') == today:
                        return DailyGoalState(**data)
        except Exception:
            pass
        
        # New day
        state = DailyGoalState(date=today, goal=DAILY_GOAL_USD)
        self._print_new_day(state)
        return state
    
    def _save_state(self):
        """Persist state to disk."""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state.__dict__, f, indent=2)
        except Exception:
            pass
    
    def _print_new_day(self, state: DailyGoalState):
        """Print new trading day announcement."""
        print(f"\n{'='*70}")
        print(f"🌅 NEW TRADING DAY: {state.date}")
        print(f"{'='*70}")
        print(f"🎯 TODAY'S MISSION: Make ${state.goal:.2f} in realized profit")
        print(f"")
        print(f"📋 STRATEGY:")
        print(f"   • Strong momentum = BIGGER positions with TIGHT stops")
        print(f"   • Weak momentum = SMALLER positions, wait for better setup")
        print(f"   • Losing positions = HEDGE to recapture losses")
        print(f"   • Goal reached = STOP trading, protect profits")
        print(f"{'='*70}\n")
    
    # =========================================================================
    # MOMENTUM ANALYSIS
    # =========================================================================
    
    def analyze_momentum(self, symbol: str, prices: List[float], 
                         trade_direction: str) -> MomentumSignal:
        """
        Analyze price momentum to determine position sizing.
        
        Strong momentum aligned with trade = SCALE UP
        Weak momentum or misaligned = SCALE DOWN
        """
        if not prices or len(prices) < 5:
            return MomentumSignal(
                symbol=symbol, momentum_pct=0, momentum_strength="UNKNOWN",
                trend_alignment=True, volatility=0, recommended_sl_pips=20,
                confidence_boost=0
            )
        
        # Calculate momentum metrics
        short_mom = (prices[-1] - prices[-5]) / prices[-5] * 100  # 5-period momentum
        long_mom = (prices[-1] - prices[0]) / prices[0] * 100 if len(prices) >= 20 else short_mom
        
        # ATR-like volatility (average true range simplified)
        ranges = [abs(prices[i] - prices[i-1]) for i in range(1, len(prices))]
        avg_range = sum(ranges[-14:]) / min(14, len(ranges)) if ranges else 0.0001
        volatility = avg_range / prices[-1] * 100  # As percentage
        
        # Determine momentum strength
        abs_mom = abs(short_mom)
        if abs_mom < 0.05:
            strength = "WEAK"
            confidence_boost = -0.1
        elif abs_mom < 0.15:
            strength = "MODERATE"
            confidence_boost = 0.0
        elif abs_mom < 0.30:
            strength = "STRONG"
            confidence_boost = 0.15
        else:
            strength = "EXTREME"
            confidence_boost = 0.25
        
        # Check trend alignment
        is_long = trade_direction.upper() in ('BUY', 'LONG')
        is_bullish_mom = short_mom > 0
        trend_alignment = (is_long and is_bullish_mom) or (not is_long and not is_bullish_mom)
        
        # Calculate recommended SL based on volatility
        pip_val = 0.01 if 'JPY' in symbol else 0.0001
        atr_pips = avg_range / pip_val
        
        # Tight SL = 1.5x ATR (tighter than normal)
        # But enforce minimum of 5 pips, max of 25 pips for tight control
        recommended_sl = max(5, min(25, atr_pips * 1.5))
        
        return MomentumSignal(
            symbol=symbol,
            momentum_pct=short_mom,
            momentum_strength=strength,
            trend_alignment=trend_alignment,
            volatility=volatility,
            recommended_sl_pips=recommended_sl,
            confidence_boost=confidence_boost if trend_alignment else -0.15
        )
    
    # =========================================================================
    # DYNAMIC POSITION SIZING
    # =========================================================================
    
    def calculate_aggressive_size(self, base_size: float, momentum: MomentumSignal,
                                  signal_confidence: float) -> Tuple[float, str]:
        """
        Calculate position size based on momentum and goal progress.
        
        Returns: (adjusted_size, reasoning)
        """
        multiplier = 1.0
        reasons = []
        
        # 1. GOAL PROGRESS FACTOR
        progress = self.state.progress_pct
        
        if progress >= 100:
            # Goal reached - no new trades
            return 0, "🎯 Daily goal reached! Protecting profits."
        
        if progress >= 80:
            # Close to goal - be conservative
            multiplier *= 0.7
            reasons.append(f"80%+ to goal → conservative sizing")
        elif progress >= 50:
            # Halfway there - normal sizing
            reasons.append(f"{progress:.0f}% to goal → normal sizing")
        elif progress < 20:
            # Far from goal - be more aggressive on good setups
            if signal_confidence >= 0.65:
                multiplier *= 1.5
                reasons.append(f"<20% progress + high confidence → aggressive")
            else:
                reasons.append(f"<20% progress but low confidence → normal")
        
        # 2. MOMENTUM FACTOR
        if momentum.momentum_strength == "STRONG" and momentum.trend_alignment:
            multiplier *= 1.4
            reasons.append(f"Strong aligned momentum → +40% size")
        elif momentum.momentum_strength == "EXTREME" and momentum.trend_alignment:
            multiplier *= 1.8
            reasons.append(f"Extreme aligned momentum → +80% size")
        elif momentum.momentum_strength == "WEAK":
            multiplier *= 0.7
            reasons.append(f"Weak momentum → -30% size")
        elif not momentum.trend_alignment:
            multiplier *= 0.6
            reasons.append(f"Counter-trend → -40% size (risky)")
        
        # 3. WIN RATE FACTOR (today's performance)
        if self.state.trades_today >= 3:
            if self.state.win_rate >= 70:
                multiplier *= 1.2
                reasons.append(f"{self.state.win_rate:.0f}% win rate today → +20%")
            elif self.state.win_rate < 40:
                multiplier *= 0.7
                reasons.append(f"{self.state.win_rate:.0f}% win rate today → -30%")
        
        # 4. CONFIDENCE BOOST
        adjusted_conf = signal_confidence + momentum.confidence_boost
        if adjusted_conf >= 0.8:
            multiplier *= 1.15
            reasons.append(f"High confidence ({adjusted_conf:.0%}) → +15%")
        
        # Enforce bounds
        multiplier = max(MIN_AGGRESSION_MULTIPLIER, min(MAX_AGGRESSION_MULTIPLIER, multiplier))
        
        adjusted_size = base_size * multiplier
        reasoning = " | ".join(reasons) if reasons else "Standard sizing"
        
        return adjusted_size, reasoning
    
    # =========================================================================
    # TIGHT STOP LOSS CALCULATION  
    # =========================================================================
    
    def calculate_tight_sl(self, entry_price: float, side: str, 
                           momentum: MomentumSignal, symbol: str) -> Tuple[float, str]:
        """
        Calculate tight stop loss for quick profit capture.
        
        Uses ATR-based volatility to set tight but not too tight stops.
        """
        pip_val = 0.01 if 'JPY' in symbol else 0.0001
        sl_pips = momentum.recommended_sl_pips
        
        # Adjust based on momentum strength
        if momentum.momentum_strength == "STRONG":
            # Strong momentum = can use tighter SL, expect fast move
            sl_pips *= 0.8
            reason = f"Tight SL ({sl_pips:.1f} pips) - strong momentum expects fast capture"
        elif momentum.momentum_strength == "EXTREME":
            # Extreme momentum = very tight, quick scalp
            sl_pips *= 0.6
            reason = f"Very tight SL ({sl_pips:.1f} pips) - extreme momentum, quick capture"
        elif momentum.momentum_strength == "WEAK":
            # Weak momentum = need more room
            sl_pips *= 1.3
            reason = f"Wider SL ({sl_pips:.1f} pips) - weak momentum needs room"
        else:
            reason = f"Standard tight SL ({sl_pips:.1f} pips)"
        
        # Enforce minimum 5 pips
        sl_pips = max(5, sl_pips)
        
        sl_distance = sl_pips * pip_val
        
        if side.upper() in ('BUY', 'LONG'):
            sl_price = entry_price - sl_distance
        else:
            sl_price = entry_price + sl_distance
        
        return sl_price, reason
    
    # =========================================================================
    # QUANT HEDGING - LOSS RECAPTURE
    # =========================================================================
    
    def check_hedge_opportunity(self, trade_id: str, symbol: str, side: str,
                                units: float, entry_price: float, 
                                current_price: float) -> Optional[HedgeOpportunity]:
        """
        Check if a losing position should be hedged.
        
        QUANT HEDGING LOGIC:
        - When position is down X pips, place opposite direction trade
        - Hedge aims to capture the reversal and offset losses
        - Smaller hedge size (50%) to limit risk if original trade recovers
        """
        # Skip if already hedged
        if trade_id in self.active_hedges:
            return None
        
        pip_val = 0.01 if 'JPY' in symbol else 0.0001
        
        # Calculate current loss
        if side.upper() in ('BUY', 'LONG'):
            loss_pips = (entry_price - current_price) / pip_val
        else:
            loss_pips = (current_price - entry_price) / pip_val
        
        # Only hedge if loss exceeds threshold
        if loss_pips < HEDGE_TRIGGER_PIPS:
            return None
        
        # Hedge in opposite direction
        hedge_side = 'SELL' if side.upper() in ('BUY', 'LONG') else 'BUY'
        hedge_units = units * HEDGE_SIZE_RATIO
        
        # Hedge SL is tight (10 pips) - we're betting on continued reversal
        # Hedge TP is 1.5x the current loss - aim to recover most of it
        hedge_sl_pips = 10
        hedge_tp_pips = loss_pips * 1.5
        
        if hedge_side == 'BUY':
            hedge_sl = current_price - (hedge_sl_pips * pip_val)
            hedge_tp = current_price + (hedge_tp_pips * pip_val)
        else:
            hedge_sl = current_price + (hedge_sl_pips * pip_val)
            hedge_tp = current_price - (hedge_tp_pips * pip_val)
        
        return HedgeOpportunity(
            original_trade_id=trade_id,
            symbol=symbol,
            original_side=side,
            original_units=units,
            current_loss_pips=loss_pips,
            hedge_side=hedge_side,
            hedge_units=hedge_units,
            hedge_entry=current_price,
            hedge_sl=hedge_sl,
            hedge_tp=hedge_tp,
            reason=f"Original {side} down {loss_pips:.1f} pips → Hedge {hedge_side} to recapture"
        )
    
    def print_hedge_opportunity(self, hedge: HedgeOpportunity):
        """Print human-readable hedge opportunity."""
        print(f"\n{'🔄'*20}")
        print(f"⚠️  HEDGE OPPORTUNITY DETECTED!")
        print(f"{'🔄'*20}")
        print(f"\n📉 PROBLEM:")
        print(f"   Your {hedge.original_side} position on {hedge.symbol} is down {hedge.current_loss_pips:.1f} pips")
        print(f"\n💡 SOLUTION (Quant Hedge):")
        print(f"   Open a {hedge.hedge_side} position to capture the reversal")
        print(f"   • Size: {hedge.hedge_units:.0f} units (50% of original)")
        print(f"   • Entry: {hedge.hedge_entry:.5f}")
        print(f"   • Stop Loss: {hedge.hedge_sl:.5f} (10 pips risk)")
        print(f"   • Take Profit: {hedge.hedge_tp:.5f} (recover {hedge.current_loss_pips*1.5:.1f} pips)")
        print(f"\n📊 WHY THIS WORKS:")
        print(f"   If price keeps moving against original → hedge profits")
        print(f"   If price reverses back → original trade recovers")
        print(f"   Either way, we limit maximum loss!")
        print(f"{'='*60}\n")
    
    # =========================================================================
    # GOAL TRACKING & UPDATES
    # =========================================================================
    
    def update_realized_pnl(self, amount: float, is_win: bool):
        """Update state when a trade closes."""
        self.state.realized_pnl += amount
        self.state.trades_today += 1
        
        if is_win:
            self.state.wins_today += 1
        else:
            self.state.losses_today += 1
        
        if self.state.realized_pnl > self.state.peak_realized:
            self.state.peak_realized = self.state.realized_pnl
        
        # Check if goal reached
        if self.state.realized_pnl >= self.state.goal and not self.state.goal_reached:
            self.state.goal_reached = True
            self._print_goal_reached()
        
        self._print_progress_update(amount, is_win)
        self._save_state()
    
    def _print_goal_reached(self):
        """Celebrate goal achievement!"""
        print(f"\n{'🎉'*25}")
        print(f"\n   🏆 DAILY GOAL ACHIEVED! 🏆")
        print(f"\n{'🎉'*25}")
        print(f"\n📊 TODAY'S RESULTS:")
        print(f"   • Realized P&L: ${self.state.realized_pnl:.2f}")
        print(f"   • Goal: ${self.state.goal:.2f}")
        print(f"   • Trades: {self.state.trades_today}")
        print(f"   • Win Rate: {self.state.win_rate:.1f}%")
        print(f"   • Hedges Placed: {self.state.hedges_placed}")
        print(f"   • Loss Recovery: ${self.state.hedges_recovered:.2f}")
        print(f"\n🛑 TRADING STOPPED FOR TODAY")
        print(f"   Great job! Come back tomorrow for another $500!")
        print(f"{'='*60}\n")
    
    def _print_progress_update(self, pnl: float, is_win: bool):
        """Print progress after each trade."""
        status = "✅ WIN" if is_win else "❌ LOSS"
        progress = self.state.progress_pct
        remaining = self.state.remaining
        
        # Progress bar
        bar_len = 30
        filled = int(min(100, progress) / 100 * bar_len)
        bar = '█' * filled + '░' * (bar_len - filled)
        
        print(f"\n{'─'*60}")
        print(f"💰 TRADE CLOSED: {status} ${pnl:+.2f}")
        print(f"{'─'*60}")
        print(f"\n📊 DAILY GOAL PROGRESS:")
        print(f"   [{bar}] {progress:.1f}%")
        print(f"   Realized: ${self.state.realized_pnl:.2f} / ${self.state.goal:.2f}")
        print(f"   Remaining: ${remaining:.2f} to go")
        print(f"\n📈 TODAY'S STATS:")
        print(f"   • Trades: {self.state.trades_today}")
        print(f"   • Wins: {self.state.wins_today} | Losses: {self.state.losses_today}")
        print(f"   • Win Rate: {self.state.win_rate:.1f}%")
        
        if remaining > 0:
            # Suggest next trade size
            if progress < 50:
                print(f"\n💡 STRATEGY: Be aggressive on high-confidence setups")
            elif progress >= 80:
                print(f"\n💡 STRATEGY: Almost there! Be careful, protect gains")
        print(f"{'─'*60}\n")
    
    def should_trade(self) -> Tuple[bool, str]:
        """Check if we should place new trades."""
        if self.state.goal_reached:
            return False, "Daily goal reached - trading paused"
        
        # Check if we've had too many losses today (circuit breaker)
        if self.state.losses_today >= 5 and self.state.win_rate < 30:
            return False, "Circuit breaker: Too many losses today, taking a break"
        
        return True, "OK"
    
    def get_position_recommendation(self, base_size: float, momentum: MomentumSignal,
                                    signal_confidence: float, entry_price: float,
                                    side: str, symbol: str) -> Dict[str, Any]:
        """
        Get complete position recommendation including:
        - Adjusted size based on momentum and goal progress
        - Tight stop loss
        - Take profit target
        """
        # Check if we should trade
        should, reason = self.should_trade()
        if not should:
            return {'allowed': False, 'reason': reason}
        
        # Calculate aggressive size
        adj_size, size_reason = self.calculate_aggressive_size(
            base_size, momentum, signal_confidence
        )
        
        if adj_size <= 0:
            return {'allowed': False, 'reason': size_reason}
        
        # Calculate tight SL
        sl_price, sl_reason = self.calculate_tight_sl(entry_price, side, momentum, symbol)
        
        # Calculate TP (2:1 minimum R:R, higher if momentum is strong)
        pip_val = 0.01 if 'JPY' in symbol else 0.0001
        sl_pips = abs(entry_price - sl_price) / pip_val
        
        rr_ratio = 2.0
        if momentum.momentum_strength == "STRONG":
            rr_ratio = 2.5
        elif momentum.momentum_strength == "EXTREME":
            rr_ratio = 3.0
        
        tp_pips = sl_pips * rr_ratio
        
        if side.upper() in ('BUY', 'LONG'):
            tp_price = entry_price + (tp_pips * pip_val)
        else:
            tp_price = entry_price - (tp_pips * pip_val)
        
        return {
            'allowed': True,
            'size': adj_size,
            'size_multiplier': adj_size / base_size if base_size > 0 else 1.0,
            'size_reasoning': size_reason,
            'stop_loss': sl_price,
            'sl_pips': sl_pips,
            'sl_reasoning': sl_reason,
            'take_profit': tp_price,
            'tp_pips': tp_pips,
            'rr_ratio': rr_ratio,
            'momentum': {
                'strength': momentum.momentum_strength,
                'aligned': momentum.trend_alignment,
                'pct': momentum.momentum_pct
            },
            'goal_progress': self.state.progress_pct
        }
    
    def print_recommendation(self, rec: Dict[str, Any], symbol: str, side: str):
        """Print human-readable recommendation."""
        if not rec.get('allowed'):
            print(f"\n❌ TRADE NOT RECOMMENDED: {rec.get('reason')}")
            return
        
        print(f"\n{'='*60}")
        print(f"📊 GOAL PURSUIT ENGINE RECOMMENDATION")
        print(f"{'='*60}")
        
        print(f"\n🎯 POSITION SIZING:")
        print(f"   • Size: {rec['size']:.0f} units ({rec['size_multiplier']:.1f}x normal)")
        print(f"   • Reason: {rec['size_reasoning']}")
        
        print(f"\n🛡️ TIGHT STOP LOSS:")
        print(f"   • SL Price: {rec['stop_loss']:.5f} ({rec['sl_pips']:.1f} pips)")
        print(f"   • Reason: {rec['sl_reasoning']}")
        
        print(f"\n🎯 TAKE PROFIT:")
        print(f"   • TP Price: {rec['take_profit']:.5f} ({rec['tp_pips']:.1f} pips)")
        print(f"   • Risk/Reward: 1:{rec['rr_ratio']:.1f}")
        
        print(f"\n📈 MOMENTUM:")
        mom = rec['momentum']
        alignment = "✅ ALIGNED" if mom['aligned'] else "⚠️ AGAINST"
        print(f"   • Strength: {mom['strength']}")
        print(f"   • Direction: {alignment} with {side}")
        print(f"   • Change: {mom['pct']:+.2f}%")
        
        print(f"\n💰 GOAL STATUS:")
        print(f"   • Progress: {rec['goal_progress']:.1f}% toward ${self.state.goal:.2f}")
        print(f"   • Remaining: ${self.state.remaining:.2f}")
        print(f"{'='*60}\n")


# Global instance
_engine: Optional[GoalPursuitEngine] = None

def get_goal_engine() -> GoalPursuitEngine:
    """Get or create the goal pursuit engine."""
    global _engine
    if _engine is None:
        _engine = GoalPursuitEngine()
    return _engine


def enhance_trade_with_goal_pursuit(candidate, base_size: float, prices: List[float],
                                    signal_confidence: float) -> Dict[str, Any]:
    """
    Main entry point: Enhance a trade candidate with goal-pursuit logic.
    
    Returns enhanced parameters including:
    - Adjusted size based on momentum and goal progress
    - Tight stop loss
    - Take profit target
    """
    engine = get_goal_engine()
    
    symbol = getattr(candidate, 'symbol', 'UNKNOWN')
    side = getattr(candidate, 'side', 'BUY')
    entry_price = getattr(candidate, 'entry_price', 0)
    
    # Analyze momentum
    momentum = engine.analyze_momentum(symbol, prices, side)
    
    # Get recommendation
    rec = engine.get_position_recommendation(
        base_size, momentum, signal_confidence,
        entry_price, side, symbol
    )
    
    # Print human-readable recommendation
    engine.print_recommendation(rec, symbol, side)
    
    return rec


def update_goal_on_close(pnl: float):
    """Update goal tracking when a trade closes."""
    engine = get_goal_engine()
    is_win = pnl > 0
    engine.update_realized_pnl(pnl, is_win)


def check_for_hedge(trade_id: str, symbol: str, side: str, units: float,
                    entry_price: float, current_price: float) -> Optional[HedgeOpportunity]:
    """Check if a position should be hedged."""
    engine = get_goal_engine()
    hedge = engine.check_hedge_opportunity(
        trade_id, symbol, side, units, entry_price, current_price
    )
    
    if hedge:
        engine.print_hedge_opportunity(hedge)
    
    return hedge


def should_continue_trading() -> Tuple[bool, str]:
    """Check if trading should continue."""
    engine = get_goal_engine()
    return engine.should_trade()


# Test
if __name__ == '__main__':
    print("Testing Goal Pursuit Engine...")
    
    engine = GoalPursuitEngine()
    
    # Simulate some price data
    prices = [1.0850 + i * 0.0002 for i in range(30)]  # Uptrending prices
    
    # Analyze momentum
    momentum = engine.analyze_momentum('EUR_USD', prices, 'BUY')
    print(f"\nMomentum: {momentum}")
    
    # Get recommendation
    rec = engine.get_position_recommendation(
        base_size=1000,
        momentum=momentum,
        signal_confidence=0.72,
        entry_price=prices[-1],
        side='BUY',
        symbol='EUR_USD'
    )
    
    engine.print_recommendation(rec, 'EUR_USD', 'BUY')
    
    # Simulate a win
    engine.update_realized_pnl(45.00, is_win=True)
    
    # Simulate checking for hedge
    hedge = engine.check_hedge_opportunity(
        trade_id='12345',
        symbol='GBP_USD',
        side='BUY',
        units=1000,
        entry_price=1.2650,
        current_price=1.2625  # Down 25 pips
    )
    
    if hedge:
        engine.print_hedge_opportunity(hedge)
