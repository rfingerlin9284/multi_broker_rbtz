"""
RICK SMART AGGRESSION MODE
Maximum edge extraction with intelligent risk management

Features:
- Hedging: Protect positions with inverse exposure
- Sniping: Quick opportunistic trades on anomalies
- Pyramiding: Scale into winning positions
- Mean Reversion: Counter-trend plays at extremes
- Breakout Hunting: Capture explosive moves

This is NOT simulation - this is REAL MONEY
"""
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class SmartAggressionConfig:
    """Configuration for aggressive edge-seeking trading"""
    
    # AGGRESSION LEVEL
    mode: str = "SMART_AGGRESSIVE"  # CONSERVATIVE / BALANCED / SMART_AGGRESSIVE / FULL_BEAST
    
    # HIVE CONSENSUS (lowered for more trades)
    hive_approval_threshold: float = 0.45  # 45% vs 55% conservative
    allow_split_decisions: bool = True  # Execute on 3-4 agent split if RR good
    
    # POSITION MANAGEMENT
    max_concurrent_positions: int = 5  # Up from 3
    allow_correlated_pairs: bool = True  # Trade EUR/USD + GBP/USD simultaneously
    position_overlap_max: float = 0.70  # Max correlation between positions
    
    # HEDGING
    hedging_enabled: bool = True
    hedge_threshold_loss_pct: float = 1.5  # Hedge if down 1.5% on position
    hedge_ratio: float = 0.5  # Hedge 50% of exposure
    hedge_symbols: Dict[str, str] = None  # Auto-populated
    
    # SNIPING (quick opportunistic trades)
    sniping_enabled: bool = True
    snipe_volatility_spike_threshold: float = 2.0  # 2x normal vol
    snipe_quick_rr_min: float = 2.0  # Lower RR for quick trades
    snipe_max_hold_minutes: int = 60  # Exit after 1 hour max
    
    # PYRAMIDING (scale into winners)
    pyramiding_enabled: bool = True
    pyramid_profit_threshold_pct: float = 2.0  # Add after +2% profit
    pyramid_max_adds: int = 2  # Max 2 additional entries
    pyramid_size_reduction: float = 0.5  # Each add = 50% of original
    
    # MEAN REVERSION
    mean_reversion_enabled: bool = True
    mean_reversion_oversold_rsi: float = 25  # RSI < 25
    mean_reversion_overbought_rsi: float = 75  # RSI > 75
    mean_reversion_size_multiplier: float = 1.5  # 1.5x normal size
    
    # BREAKOUT HUNTING
    breakout_enabled: bool = True
    breakout_volume_threshold: float = 2.5  # 2.5x average volume
    breakout_momentum_min: float = 0.02  # 2% move minimum
    breakout_quick_entry: bool = True  # Enter on confirmation
    
    # RISK PARAMETERS (adjusted for aggression)
    risk_per_trade_pct: float = 2.5  # 2.5% vs 2% conservative
    max_daily_risk_pct: float = 8.0  # 8% vs 6% conservative
    stop_loss_min_pct: float = 1.5  # Tighter stops allowed (1.5% vs 2%)
    stop_loss_max_pct: float = 5.0  # Wider stops allowed
    
    # LEVERAGE
    max_leverage: float = 8.0  # Up to 8x (from 5x growth phase)
    target_leverage: float = 5.0  # Target 5x utilization
    
    # EXECUTION
    slippage_tolerance_pct: float = 0.5  # Accept 0.5% slippage
    fill_timeout_seconds: int = 3  # Fast execution required
    retry_failed_orders: bool = True
    max_retries: int = 2
    
    # PROFIT TARGETS (aggressive)
    default_rr_ratio: float = 2.5  # 2.5:1 vs 3:1 conservative
    trailing_stop_activation_pct: float = 3.0  # Trail after +3%
    trailing_stop_distance_pct: float = 1.5  # 1.5% trail
    
    # MARKET CONDITIONS
    trade_during_news: bool = True  # Don't avoid news (smart aggression)
    trade_overnight: bool = True  # Hold overnight positions
    trade_weekends: bool = False  # Still avoid weekend gaps
    
    def __post_init__(self):
        """Initialize derived configurations"""
        if self.hedge_symbols is None:
            # Define hedge pairs
            self.hedge_symbols = {
                'EUR/USD': 'USD/CHF',  # Inverse correlation
                'GBP/USD': 'USD/JPY',
                'AUD/USD': 'USD/CAD',
                'NZD/USD': 'USD/CAD',
                'EUR/GBP': 'GBP/CHF',
            }
    
    def get_mode_description(self) -> str:
        """Describe current aggression mode"""
        descriptions = {
            'CONSERVATIVE': '🐌 Conservative: Safety first, low risk, high quality only',
            'BALANCED': '⚖️  Balanced: Moderate risk, good opportunities',
            'SMART_AGGRESSIVE': '🦅 Smart Aggressive: Max edge with intelligent risk',
            'FULL_BEAST': '🔥 Full Beast: Maximum aggression, all systems go'
        }
        return descriptions.get(self.mode, 'Unknown mode')


# Default configuration
DEFAULT_SMART_AGGRESSION = SmartAggressionConfig()


# Full beast mode for when you want maximum aggression
FULL_BEAST_MODE = SmartAggressionConfig(
    mode="FULL_BEAST",
    hive_approval_threshold=0.35,  # 35% - very aggressive
    max_concurrent_positions=8,
    risk_per_trade_pct=3.0,  # 3% risk per trade
    max_daily_risk_pct=12.0,  # 12% daily risk
    max_leverage=10.0,
    default_rr_ratio=2.0,  # Accept 2:1
    sniping_enabled=True,
    pyramiding_enabled=True,
    mean_reversion_enabled=True,
    breakout_enabled=True,
    hedging_enabled=True,
)


def print_config_summary(config: SmartAggressionConfig):
    """Print configuration summary"""
    print("\n" + "="*80)
    print("⚡ RICK SMART AGGRESSION CONFIGURATION")
    print("="*80)
    print(f"\n{config.get_mode_description()}\n")
    
    print("🎯 AGGRESSION SETTINGS:")
    print(f"   HIVE Threshold: {config.hive_approval_threshold*100:.0f}% (lower = more trades)")
    print(f"   Max Positions: {config.max_concurrent_positions}")
    print(f"   Risk per Trade: {config.risk_per_trade_pct}%")
    print(f"   Max Daily Risk: {config.max_daily_risk_pct}%")
    print(f"   Leverage: {config.target_leverage}x target, {config.max_leverage}x max")
    
    print(f"\n🔧 ADVANCED FEATURES:")
    print(f"   {'✅' if config.hedging_enabled else '❌'} Hedging (protect positions)")
    print(f"   {'✅' if config.sniping_enabled else '❌'} Sniping (quick opportunistic trades)")
    print(f"   {'✅' if config.pyramiding_enabled else '❌'} Pyramiding (scale into winners)")
    print(f"   {'✅' if config.mean_reversion_enabled else '❌'} Mean Reversion (counter-trend)")
    print(f"   {'✅' if config.breakout_enabled else '❌'} Breakout Hunting (explosive moves)")
    
    print(f"\n💰 PROFIT OPTIMIZATION:")
    print(f"   Default R:R: {config.default_rr_ratio}:1")
    print(f"   Trailing Stop: Activate at +{config.trailing_stop_activation_pct}%, trail {config.trailing_stop_distance_pct}%")
    
    print(f"\n⚠️  RISK CONTROLS:")
    print(f"   Stop Range: {config.stop_loss_min_pct}% - {config.stop_loss_max_pct}%")
    print(f"   Daily Loss Halt: {config.max_daily_risk_pct}%")
    print(f"   Correlation Limit: {config.position_overlap_max*100:.0f}%")
    
    print("\n" + "="*80)
    print("⚠️  WARNING: THIS IS REAL MONEY TRADING")
    print("="*80)
    print("All features are LIVE and will execute REAL trades")
    print("HIVE consensus still protects you from terrible setups")
    print("Smart aggression = calculated risks, not reckless gambling")
    print("="*80 + "\n")


if __name__ == '__main__':
    print("\n🔥 RICK SMART AGGRESSION MODES\n")
    
    # Show conservative for comparison
    conservative = SmartAggressionConfig(
        mode="CONSERVATIVE",
        hive_approval_threshold=0.60,
        max_concurrent_positions=3,
        risk_per_trade_pct=2.0,
        max_leverage=3.0,
        hedging_enabled=False,
        sniping_enabled=False,
        pyramiding_enabled=False,
    )
    print_config_summary(conservative)
    
    input("Press Enter to see SMART AGGRESSIVE mode...")
    
    # Show smart aggressive (default)
    print_config_summary(DEFAULT_SMART_AGGRESSION)
    
    input("Press Enter to see FULL BEAST mode...")
    
    # Show full beast
    print_config_summary(FULL_BEAST_MODE)
    
    print("\n💡 Recommendation: Start with SMART_AGGRESSIVE mode")
    print("   Graduate to FULL_BEAST once you've proven consistent profitability\n")
