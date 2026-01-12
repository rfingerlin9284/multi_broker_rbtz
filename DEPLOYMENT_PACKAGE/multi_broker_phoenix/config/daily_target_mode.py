"""$400/DAY TARGET MODE - Maximum Aggression

GOAL: Average $400+ profit per trading day
STARTING CAPITAL: $5,000

MATHEMATICAL REALITY:
- $400/day = 8% daily return
- At 38% win rate, 3:1 R:R:
  * Each trade risks 3.5% ($175)
  * Each win = $525, each loss = $175
  * Need 6-8 quality trades/day
  * 3 wins, 5 losses = $1,575 - $875 = $700/day ✅

REQUIREMENTS:
1. HIGH FREQUENCY: 8-12 trades/day (vs 2-3 normal)
2. AGGRESSIVE SIZING: 3.5% risk/trade (vs 2%)
3. LOWER HIVE THRESHOLD: 30% (vs 45%)
4. ALL EDGE FEATURES: Hedging, sniping, pyramiding maxed
5. EXTENDED HOURS: Trade 12+ hours/day
"""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class DailyTargetConfig:
    """Configuration for $400/day target mode"""
    
    # DAILY TARGET
    target_daily_profit: float = 400.0  # $400/day goal
    min_acceptable_profit: float = 250.0  # Minimum to consider success
    max_daily_loss_halt: float = -200.0  # Stop if down $200
    
    # POSITION SIZING (AGGRESSIVE)
    risk_per_trade_pct: float = 3.5  # 3.5% per trade ($175 on $5k)
    max_position_pct: float = 15.0  # Up to 15% in one position
    max_concurrent_positions: int = 8  # Up to 8 positions
    
    # HIVE CONSENSUS (VERY LOW THRESHOLD)
    hive_approval_threshold: float = 0.30  # 30% approval (was 45%)
    allow_sentinel_override: bool = False  # Disable Sentinel veto for speed
    require_oracle_vote: bool = False  # Don't wait for news research
    
    # RISK PARAMETERS (AGGRESSIVE)
    max_daily_risk_pct: float = 12.0  # Can risk up to 12% capital/day
    max_portfolio_correlation: float = 0.85  # Allow high correlation
    leverage_multiplier: float = 1.5  # 1.5x standard leverage
    
    # TRADE EXECUTION (FAST)
    min_rr_ratio: float = 2.0  # Lower from 3.0 for more trades
    max_stop_distance_pct: float = 6.0  # Wider stops allowed
    slippage_tolerance_pct: float = 0.8  # Accept more slippage
    
    # SMART AGGRESSION (ALL FEATURES MAXED)
    hedging_enabled: bool = True
    auto_hedge_threshold_pct: float = 1.0  # Hedge at -1% (was -1.5%)
    hedge_ratio: float = 0.60  # 60% hedge (was 40%)
    
    sniping_enabled: bool = True
    snipe_min_spike_pct: float = 0.3  # Snipe 0.3% spikes (was 0.5%)
    snipe_quick_target_pct: float = 1.5  # 1.5% quick target (was 2%)
    snipe_max_hold_seconds: int = 300  # 5 min max (was 10 min)
    
    pyramiding_enabled: bool = True
    pyramid_after_profit_pct: float = 1.5  # Add at +1.5% (was +2%)
    pyramid_max_entries: int = 4  # Up to 4 entries (was 3)
    pyramid_size_multiplier: float = 0.7  # 70% size (was 50%)
    
    # BREAKEVEN & TRAILING (AGGRESSIVE)
    trail_to_be_after_r: float = 1.0  # BE after +1R (was +1.5R)
    lock_profit_at_r: float = 1.5  # Lock at +1.5R (was +2R)
    trail_tight_after_r: float = 2.0  # Trail tight at +2R (was +3R)
    trail_increment_pct: float = 0.3  # Trail every 0.3% (was 0.5%)
    
    # TRADING HOURS (24/7 AUTONOMOUS)
    start_hour_utc: int = 0  # 24/7 operation
    end_hour_utc: int = 23  # Never stops
    trade_major_news: bool = True  # Trade through news
    weekend_trading: bool = True  # YES - trade crypto 24/7


# Preset configurations for different capital levels
DAILY_TARGET_CONFIGS = {
    "5K_TO_400": DailyTargetConfig(
        # $5k capital → $400/day target
        risk_per_trade_pct=3.5,
        target_daily_profit=400.0,
        hive_approval_threshold=0.30,
    ),
    
    "10K_TO_400": DailyTargetConfig(
        # $10k capital → $400/day target (easier)
        risk_per_trade_pct=2.5,
        target_daily_profit=400.0,
        hive_approval_threshold=0.35,
        max_concurrent_positions=6,
    ),
    
    "20K_TO_800": DailyTargetConfig(
        # $20k capital → $800/day target (scaled)
        risk_per_trade_pct=2.5,
        target_daily_profit=800.0,
        hive_approval_threshold=0.35,
        max_concurrent_positions=6,
    ),
}


def get_config_for_capital(capital: float) -> DailyTargetConfig:
    """Get optimal config based on current capital"""
    if capital < 7500:
        return DAILY_TARGET_CONFIGS["5K_TO_400"]
    elif capital < 15000:
        return DAILY_TARGET_CONFIGS["10K_TO_400"]
    else:
        return DAILY_TARGET_CONFIGS["20K_TO_800"]


class DailyTargetTracker:
    """Track progress toward daily $400 target"""
    
    def __init__(self, config: DailyTargetConfig):
        self.config = config
        self.daily_pnl: float = 0.0
        self.trades_today: int = 0
        self.wins_today: int = 0
        self.losses_today: int = 0
        self.start_equity: float = 0.0
        
    def reset_day(self, starting_equity: float):
        """Reset counters for new trading day"""
        self.daily_pnl = 0.0
        self.trades_today = 0
        self.wins_today = 0
        self.losses_today = 0
        self.start_equity = starting_equity
        
    def record_trade(self, pnl: float):
        """Record trade result"""
        self.daily_pnl += pnl
        self.trades_today += 1
        if pnl > 0:
            self.wins_today += 1
        else:
            self.losses_today += 1
            
    def should_halt_trading(self) -> bool:
        """Check if should stop trading for day"""
        # Hit daily loss limit
        if self.daily_pnl <= self.config.max_daily_loss_halt:
            return True
        
        # Hit daily profit target (optional stop)
        if self.daily_pnl >= self.config.target_daily_profit * 1.5:
            # Made 1.5x target, can stop
            return False  # Keep going for max profit
        
        return False
        
    def need_more_trades(self) -> bool:
        """Check if need more trades to hit target"""
        # If already hit target, optional to continue
        if self.daily_pnl >= self.config.target_daily_profit:
            return False
        
        # If getting close to loss limit, need wins
        if self.daily_pnl < -100:
            return True
        
        # Always need more trades if below target
        return True
        
    def get_status(self) -> Dict[str, Any]:
        """Get current status"""
        pct_of_target = (self.daily_pnl / self.config.target_daily_profit) * 100
        win_rate = (self.wins_today / self.trades_today * 100) if self.trades_today > 0 else 0
        
        return {
            'daily_pnl': self.daily_pnl,
            'target': self.config.target_daily_profit,
            'pct_of_target': pct_of_target,
            'trades': self.trades_today,
            'wins': self.wins_today,
            'losses': self.losses_today,
            'win_rate': win_rate,
            'should_halt': self.should_halt_trading(),
            'need_more': self.need_more_trades(),
        }
        
    def get_recommendation(self) -> str:
        """Get trading recommendation"""
        status = self.get_status()
        
        if status['should_halt']:
            return f"🛑 HALT TRADING - Daily loss limit hit (${self.daily_pnl:.2f})"
        
        if status['pct_of_target'] >= 100:
            return f"✅ TARGET HIT - ${self.daily_pnl:.2f} ({status['pct_of_target']:.0f}%)"
        
        remaining = self.config.target_daily_profit - self.daily_pnl
        trades_needed = max(1, int(remaining / (self.start_equity * 0.035 * 2.0)))
        
        if status['pct_of_target'] >= 50:
            return f"⚡ HALFWAY THERE - ${remaining:.2f} to go (~{trades_needed} trades needed)"
        
        return f"🎯 HUNTING - ${remaining:.2f} to target (~{trades_needed} trades needed)"


# Quick trade requirement calculator
def calculate_daily_requirements(capital: float, daily_target: float,
                                  win_rate: float = 0.38, rr_ratio: float = 3.0) -> Dict[str, Any]:
    """Calculate how many trades needed per day to hit target"""
    
    # Calculate risk per trade needed
    risk_per_trade = capital * 0.035  # 3.5%
    
    # Calculate expected value per trade
    win_amount = risk_per_trade * rr_ratio
    loss_amount = risk_per_trade
    ev_per_trade = (win_rate * win_amount) - ((1 - win_rate) * loss_amount)
    
    # Trades needed to hit target
    trades_needed = daily_target / ev_per_trade if ev_per_trade > 0 else 999
    
    # Wins and losses
    expected_wins = trades_needed * win_rate
    expected_losses = trades_needed * (1 - win_rate)
    
    return {
        'capital': capital,
        'daily_target': daily_target,
        'risk_per_trade': risk_per_trade,
        'win_amount': win_amount,
        'loss_amount': loss_amount,
        'ev_per_trade': ev_per_trade,
        'trades_needed': int(trades_needed) + 1,
        'expected_wins': expected_wins,
        'expected_losses': expected_losses,
        'target_win_rate': win_rate * 100,
        'rr_ratio': rr_ratio,
    }


if __name__ == "__main__":
    print("=" * 60)
    print("💰 $400/DAY TARGET MODE - REQUIREMENTS")
    print("=" * 60)
    
    # Calculate for $5k capital
    reqs = calculate_daily_requirements(5000, 400)
    
    print(f"\n📊 STARTING CAPITAL: ${reqs['capital']:,.0f}")
    print(f"🎯 DAILY TARGET: ${reqs['daily_target']:.0f}")
    print(f"⚡ RISK PER TRADE: ${reqs['risk_per_trade']:.2f} (3.5%)")
    print(f"💚 WIN AMOUNT: ${reqs['win_amount']:.2f} ({reqs['rr_ratio']}:1 R:R)")
    print(f"❌ LOSS AMOUNT: ${reqs['loss_amount']:.2f}")
    print(f"📈 EV PER TRADE: ${reqs['ev_per_trade']:.2f}")
    print(f"\n🔢 TRADES NEEDED PER DAY: {reqs['trades_needed']}")
    print(f"   └─ Expected wins: {reqs['expected_wins']:.1f}")
    print(f"   └─ Expected losses: {reqs['expected_losses']:.1f}")
    print(f"   └─ Win rate needed: {reqs['target_win_rate']:.1f}%")
    
    print(f"\n⏰ TRADING SCHEDULE:")
    print(f"   └─ Hours/day: 24 HOURS (AUTONOMOUS 24/7)")
    print(f"   └─ Trades/hour: ~{reqs['trades_needed']/24:.1f}")
    print(f"   └─ Frequency: Every ~{60*24/reqs['trades_needed']:.0f} minutes")
    
    print(f"\n🎰 EXAMPLE DAY:")
    wins = int(reqs['expected_wins'])
    losses = int(reqs['expected_losses'])
    profit = wins * reqs['win_amount'] - losses * reqs['loss_amount']
    print(f"   {wins} wins × ${reqs['win_amount']:.0f} = ${wins * reqs['win_amount']:.0f}")
    print(f"   {losses} losses × ${reqs['loss_amount']:.0f} = ${losses * reqs['loss_amount']:.0f}")
    print(f"   Net: ${profit:.0f} 🎯")
    
    print(f"\n⚠️  REALITY CHECK:")
    print(f"   • This is AGGRESSIVE (8% daily return)")
    print(f"   • Need {reqs['trades_needed']} quality trades/day")
    print(f"   • Lower HIVE threshold → more trades, more risk")
    print(f"   • Bad days WILL happen (max loss: -$200/day)")
    print(f"   • Requires 12+ hour trading days")
    
    print(f"\n📈 GROWTH PROJECTION:")
    days_to_10k = 0
    capital = 5000
    while capital < 10000 and days_to_10k < 100:
        capital += 400
        days_to_10k += 1
    print(f"   $5k → $10k in {days_to_10k} days")
    
    days_to_20k = days_to_10k
    while capital < 20000 and days_to_20k < 200:
        capital += 400
        days_to_20k += 1
    print(f"   $5k → $20k in {days_to_20k} days")
    
    print("\n" + "=" * 60)
    print("✅ Configuration saved to DAILY_TARGET_CONFIGS")
    print("=" * 60)
