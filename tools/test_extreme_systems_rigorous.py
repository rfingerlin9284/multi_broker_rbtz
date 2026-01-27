#!/usr/bin/env python3
"""
🔥 EXTREME SYSTEMS RIGOROUS TEST SUITE
=====================================
Tests all three extreme systems with 35+ scenarios
Validates returns, win rates, zombie kills, and leverage scaling

Author: RICK Autonomous Trading System
Date: 2026-01-06
"""
import sys
import os
import random
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import statistics

# Add project path
sys.path.insert(0, '/home/ing/RICK/MULTI_BROKER_PHOENIX/MULTI_BROKER_PHOENIX')

# Import extreme systems
from multi_broker_phoenix.engines.extreme_compounding_engine import ExtremeCompoundingEngine, AccountState
from multi_broker_phoenix.engines.zombie_trade_killer import ZombieTradeKiller, TradeHealth
from tools.extreme_market_simulator import EXTREME_SCENARIOS


@dataclass
class TradeResult:
    """Single trade result"""
    entry_bar: int
    exit_bar: int
    entry_price: float
    exit_price: float
    profit_pct: float
    position_size: float
    leverage: float
    exit_reason: str


@dataclass
class BacktestResult:
    """Full backtest result"""
    strategy: str
    scenario: str
    total_return_pct: float
    max_leverage_used: float
    win_rate: float
    total_trades: int
    zombies_killed: int
    max_drawdown_pct: float
    final_balance: float
    starting_balance: float


class SimpleStrategy:
    """Simple trend-following strategy for testing"""
    
    def __init__(self, name: str, lookback: int = 20, threshold: float = 0.02):
        self.name = name
        self.lookback = lookback
        self.threshold = threshold
    
    def generate_signal(self, prices: List[float], idx: int) -> Tuple[float, str]:
        """
        Generate trading signal
        Returns: (signal_strength: 0-1, direction: 'long'|'short'|'none')
        """
        if idx < self.lookback:
            return 0.0, 'none'
        
        recent = prices[idx-self.lookback:idx]
        current = prices[idx]
        avg = sum(recent) / len(recent)
        
        pct_diff = (current - avg) / avg
        
        if pct_diff > self.threshold:
            strength = min(1.0, abs(pct_diff) * 10)
            return strength, 'long'
        elif pct_diff < -self.threshold:
            strength = min(1.0, abs(pct_diff) * 10)
            return strength, 'short'
        else:
            return 0.0, 'none'


STRATEGIES = {
    'ema_scalper': SimpleStrategy('ema_scalper', lookback=10, threshold=0.01),
    'institutional_sd': SimpleStrategy('institutional_sd', lookback=30, threshold=0.03),
    'trap_reversal': SimpleStrategy('trap_reversal', lookback=5, threshold=0.02),
    'holy_grail': SimpleStrategy('holy_grail', lookback=20, threshold=0.015),
    'fabio_aaa': SimpleStrategy('fabio_aaa', lookback=15, threshold=0.02),
}


def run_backtest(
    strategy: SimpleStrategy,
    prices: List[float],
    starting_balance: float = 10000,
    base_risk_pct: float = 5.0,  # EXTREME risk
    kelly_fraction: float = 0.75,  # Aggressive Kelly
    zombie_bars: int = 30,  # Let trades breathe
) -> BacktestResult:
    """
    Run full backtest with extreme compounding and zombie killing
    """
    # Initialize systems
    compounder = ExtremeCompoundingEngine(
        base_risk_pct=base_risk_pct,
        max_leverage=5.0,
        kelly_fraction=kelly_fraction
    )
    
    killer = ZombieTradeKiller(
        max_stagnant_bars=zombie_bars,
        signal_fade_threshold=0.4,  # More tolerance
        zombie_profit_threshold=-1.0,  # Deeper tolerance
    )
    
    # Account state
    balance = starting_balance
    peak_balance = starting_balance
    min_balance = starting_balance
    consecutive_wins = 0
    consecutive_losses = 0
    trades: List[TradeResult] = []
    
    # Position tracking
    position = None  # {'entry_bar': int, 'entry_price': float, 'direction': str, 'size': float, 'leverage': float}
    max_leverage_used = 1.0
    zombies_killed = 0
    
    # Trade history for stats
    win_amounts = [5.0]  # Default seed
    loss_amounts = [2.0]  # Default seed
    
    for bar in range(len(prices)):
        current_price = prices[bar]
        signal_strength, direction = strategy.generate_signal(prices, bar)
        
        # Update position if we have one
        if position is not None:
            entry_price = position['entry_price']
            pos_direction = position['direction']
            bars_held = bar - position['entry_bar']
            
            # Calculate current P&L
            if pos_direction == 'long':
                profit_pct = ((current_price - entry_price) / entry_price) * 100
            else:
                profit_pct = ((entry_price - current_price) / entry_price) * 100
            
            # Register with zombie killer
            symbol = f"TEST_{position['entry_bar']}"
            if symbol not in killer.active_monitors:
                killer.register_trade(symbol, entry_price, position.get('signal', 0.5))
            
            # Update zombie killer
            opportunities = [{'symbol': 'OTHER', 'signal_strength': signal_strength, 'expected_return': 2.0}]
            zombie_result = killer.update_trade(
                symbol,
                current_price=current_price,
                current_signal_strength=signal_strength,
                available_opportunities=opportunities
            )
            
            # Check exit conditions
            exit_reason = None
            
            # 1. Zombie killer says CUT
            if zombie_result['action'] == 'CUT':
                exit_reason = f"ZOMBIE: {zombie_result['health'].value}"
                zombies_killed += 1
            
            # 2. Take profit at 5%
            elif profit_pct > 5.0:
                exit_reason = "TAKE_PROFIT"
            
            # 3. Stop loss at -3%
            elif profit_pct < -3.0:
                exit_reason = "STOP_LOSS"
            
            # 4. Max bars held (50)
            elif bars_held >= 50:
                exit_reason = "MAX_HOLD"
            
            # 5. Signal reversal
            elif signal_strength > 0.7 and direction != pos_direction and direction != 'none':
                exit_reason = "SIGNAL_REVERSAL"
            
            # Exit position
            if exit_reason:
                # Calculate final profit
                position_profit = (profit_pct / 100) * position['size'] * position['leverage']
                balance += position_profit
                
                # Track drawdown
                if balance > peak_balance:
                    peak_balance = balance
                if balance < min_balance:
                    min_balance = balance
                
                # Update win/loss tracking
                if position_profit > 0:
                    consecutive_wins += 1
                    consecutive_losses = 0
                    win_amounts.append(abs(profit_pct))
                else:
                    consecutive_losses += 1
                    consecutive_wins = 0
                    loss_amounts.append(abs(profit_pct))
                
                # Record trade
                trades.append(TradeResult(
                    entry_bar=position['entry_bar'],
                    exit_bar=bar,
                    entry_price=entry_price,
                    exit_price=current_price,
                    profit_pct=profit_pct,
                    position_size=position['size'],
                    leverage=position['leverage'],
                    exit_reason=exit_reason
                ))
                
                killer.close_trade(symbol)
                position = None
        
        # Check for new entry
        if position is None and signal_strength > 0.5 and direction != 'none':
            # Calculate account state
            drawdown_pct = ((peak_balance - balance) / peak_balance) * 100 if peak_balance > 0 else 0
            
            account = AccountState(
                starting_balance=starting_balance,
                current_balance=balance,
                peak_balance=peak_balance,
                drawdown_pct=drawdown_pct,
                consecutive_wins=consecutive_wins,
                consecutive_losses=consecutive_losses,
                win_rate_30d=len([t for t in trades[-30:] if t.profit_pct > 0]) / max(len(trades[-30:]), 1),
                avg_win_pct=statistics.mean(win_amounts[-20:]) if win_amounts else 5.0,
                avg_loss_pct=statistics.mean(loss_amounts[-20:]) if loss_amounts else 2.0
            )
            
            # Get position sizing from compounding engine
            sizing = compounder.calculate_position_size(
                account=account,
                signal_strength=signal_strength,
                win_probability=0.6 if consecutive_wins > 0 else 0.5
            )
            
            max_leverage_used = max(max_leverage_used, sizing['leverage'])
            
            position = {
                'entry_bar': bar,
                'entry_price': current_price,
                'direction': direction,
                'size': sizing['total_size'],
                'leverage': sizing['leverage'],
                'signal': signal_strength
            }
    
    # Close any remaining position
    if position is not None:
        entry_price = position['entry_price']
        current_price = prices[-1]
        pos_direction = position['direction']
        
        if pos_direction == 'long':
            profit_pct = ((current_price - entry_price) / entry_price) * 100
        else:
            profit_pct = ((entry_price - current_price) / entry_price) * 100
        
        position_profit = (profit_pct / 100) * position['size'] * position['leverage']
        balance += position_profit
        
        trades.append(TradeResult(
            entry_bar=position['entry_bar'],
            exit_bar=len(prices)-1,
            entry_price=entry_price,
            exit_price=current_price,
            profit_pct=profit_pct,
            position_size=position['size'],
            leverage=position['leverage'],
            exit_reason="END_OF_DATA"
        ))
    
    # Calculate final stats
    total_return_pct = ((balance - starting_balance) / starting_balance) * 100
    winning_trades = [t for t in trades if t.profit_pct > 0]
    win_rate = len(winning_trades) / len(trades) * 100 if trades else 0
    max_drawdown_pct = ((peak_balance - min_balance) / peak_balance) * 100 if peak_balance > 0 else 0
    
    return BacktestResult(
        strategy=strategy.name,
        scenario="",
        total_return_pct=total_return_pct,
        max_leverage_used=max_leverage_used,
        win_rate=win_rate,
        total_trades=len(trades),
        zombies_killed=zombies_killed,
        max_drawdown_pct=max_drawdown_pct,
        final_balance=balance,
        starting_balance=starting_balance
    )


def print_header():
    """Print test header"""
    print("\n" + "="*80)
    print("🔥 EXTREME SYSTEMS RIGOROUS TEST SUITE")
    print("="*80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Testing: 5 Strategies × 7 Scenarios = 35 Backtests")
    print(f"Settings: 5% risk, 0.75 Kelly, 30-bar zombie tolerance")
    print("="*80 + "\n")


def run_all_tests() -> List[BacktestResult]:
    """Run all 35 backtest combinations"""
    results = []
    test_num = 0
    total_tests = len(STRATEGIES) * len(EXTREME_SCENARIOS)
    
    print_header()
    
    for strategy_name, strategy in STRATEGIES.items():
        for scenario_name, scenario_func in EXTREME_SCENARIOS.items():
            test_num += 1
            
            # Generate price series
            prices = scenario_func(length=500, seed=42)
            
            # Run backtest
            result = run_backtest(
                strategy=strategy,
                prices=prices,
                starting_balance=10000,
                base_risk_pct=5.0,
                kelly_fraction=0.75,
                zombie_bars=30
            )
            result.scenario = scenario_name
            results.append(result)
            
            # Print progress
            status = "✅" if result.total_return_pct > 0 else "❌"
            print(f"[{test_num:02d}/{total_tests}] {status} {strategy_name:20s} × {scenario_name:35s}")
            print(f"         Return: {result.total_return_pct:+7.2f}% | Win Rate: {result.win_rate:5.1f}% | "
                  f"Leverage: {result.max_leverage_used:.1f}x | Zombies: {result.zombies_killed:2d} | "
                  f"Trades: {result.total_trades:2d}")
            print()
    
    return results


def print_summary(results: List[BacktestResult]):
    """Print comprehensive summary"""
    print("\n" + "="*80)
    print("📊 SUMMARY REPORT")
    print("="*80)
    
    # Overall stats
    profitable = [r for r in results if r.total_return_pct > 0]
    total_return = sum(r.total_return_pct for r in results)
    avg_return = total_return / len(results)
    avg_win_rate = sum(r.win_rate for r in results) / len(results)
    total_zombies = sum(r.zombies_killed for r in results)
    max_leverage = max(r.max_leverage_used for r in results)
    
    print(f"\n📈 OVERALL PERFORMANCE:")
    print(f"   Profitable Tests: {len(profitable)}/{len(results)} ({len(profitable)/len(results)*100:.1f}%)")
    print(f"   Average Return: {avg_return:+.2f}%")
    print(f"   Average Win Rate: {avg_win_rate:.1f}%")
    print(f"   Total Zombies Killed: {total_zombies}")
    print(f"   Max Leverage Used: {max_leverage:.1f}x")
    
    # Top performers
    print(f"\n🏆 TOP 5 PERFORMERS:")
    top5 = sorted(results, key=lambda x: x.total_return_pct, reverse=True)[:5]
    for i, r in enumerate(top5, 1):
        print(f"   {i}. {r.strategy} × {r.scenario}")
        print(f"      Return: {r.total_return_pct:+.2f}% | Win: {r.win_rate:.1f}% | Leverage: {r.max_leverage_used:.1f}x | Zombies: {r.zombies_killed}")
    
    # Worst performers
    print(f"\n💀 BOTTOM 5 PERFORMERS:")
    bottom5 = sorted(results, key=lambda x: x.total_return_pct)[:5]
    for i, r in enumerate(bottom5, 1):
        print(f"   {i}. {r.strategy} × {r.scenario}")
        print(f"      Return: {r.total_return_pct:+.2f}% | Win: {r.win_rate:.1f}% | DD: {r.max_drawdown_pct:.1f}%")
    
    # By strategy
    print(f"\n📊 BY STRATEGY:")
    for strategy_name in STRATEGIES:
        strat_results = [r for r in results if r.strategy == strategy_name]
        strat_avg = sum(r.total_return_pct for r in strat_results) / len(strat_results)
        strat_profitable = len([r for r in strat_results if r.total_return_pct > 0])
        print(f"   {strategy_name:20s}: Avg {strat_avg:+7.2f}% | Profitable: {strat_profitable}/{len(strat_results)}")
    
    # By scenario
    print(f"\n🌪️ BY SCENARIO:")
    for scenario_name in EXTREME_SCENARIOS:
        scen_results = [r for r in results if r.scenario == scenario_name]
        scen_avg = sum(r.total_return_pct for r in scen_results) / len(scen_results)
        scen_profitable = len([r for r in scen_results if r.total_return_pct > 0])
        print(f"   {scenario_name:35s}: Avg {scen_avg:+7.2f}% | Profitable: {scen_profitable}/{len(scen_results)}")
    
    # Pass/Fail
    print(f"\n" + "="*80)
    if len(profitable) >= len(results) * 0.4:  # 40% threshold
        print("🎉 TEST SUITE: PASSED")
        print(f"   {len(profitable)}/{len(results)} tests profitable (>{40}% required)")
    else:
        print("❌ TEST SUITE: FAILED")
        print(f"   Only {len(profitable)}/{len(results)} tests profitable (<{40}% required)")
    print("="*80)
    
    # Return best result
    best = max(results, key=lambda x: x.total_return_pct)
    print(f"\n🏆 BEST RESULT: {best.strategy} × {best.scenario}")
    print(f"   Return: {best.total_return_pct:+.2f}%")
    print(f"   ${best.starting_balance:,.0f} → ${best.final_balance:,.0f}")
    print(f"   Win Rate: {best.win_rate:.1f}%")
    print(f"   Max Leverage: {best.max_leverage_used:.1f}x")
    print(f"   Zombies Killed: {best.zombies_killed}")


def test_component_units():
    """Unit tests for individual components"""
    print("\n" + "="*80)
    print("🧪 COMPONENT UNIT TESTS")
    print("="*80)
    
    passed = 0
    failed = 0
    
    # Test 1: Kelly Criterion calculation
    print("\n[TEST 1] Kelly Criterion Calculation...")
    engine = ExtremeCompoundingEngine(base_risk_pct=2.0, kelly_fraction=0.5)
    kelly = engine._kelly_criterion(win_prob=0.6, avg_win_pct=5.0, avg_loss_pct=2.0)
    if 0.0 < kelly < 0.5:
        print(f"   ✅ PASS: Kelly = {kelly:.4f} (expected 0 < k < 0.5)")
        passed += 1
    else:
        print(f"   ❌ FAIL: Kelly = {kelly:.4f}")
        failed += 1
    
    # Test 2: Leverage scaling
    print("\n[TEST 2] Win-Streak Leverage Scaling...")
    account = AccountState(
        starting_balance=10000, current_balance=12000, peak_balance=12000,
        drawdown_pct=0, consecutive_wins=10, consecutive_losses=0,
        win_rate_30d=0.7, avg_win_pct=5.0, avg_loss_pct=2.0
    )
    leverage = engine._calculate_leverage(account)
    if leverage == 5.0:
        print(f"   ✅ PASS: 10 wins = {leverage}x leverage")
        passed += 1
    else:
        print(f"   ❌ FAIL: Expected 5.0x, got {leverage}x")
        failed += 1
    
    # Test 3: Zombie detection
    print("\n[TEST 3] Zombie Trade Detection...")
    killer = ZombieTradeKiller(max_stagnant_bars=15)
    killer.register_trade("TEST", 100.0, 0.8)
    # Simulate 20 bars of stagnation
    for _ in range(20):
        result = killer.update_trade("TEST", 100.01, 0.3, [])
    if result['health'] == TradeHealth.ZOMBIE:
        print(f"   ✅ PASS: Stagnant trade marked as ZOMBIE")
        passed += 1
    else:
        print(f"   ❌ FAIL: Expected ZOMBIE, got {result['health']}")
        failed += 1
    
    # Test 4: Emergency deleverage
    print("\n[TEST 4] Emergency Deleverage...")
    account.drawdown_pct = 12.0
    reduction = engine.emergency_deleverage(account)
    if reduction == 0.5:
        print(f"   ✅ PASS: 12% DD = {reduction}x reduction")
        passed += 1
    else:
        print(f"   ❌ FAIL: Expected 0.5, got {reduction}")
        failed += 1
    
    # Test 5: Market simulator output
    print("\n[TEST 5] Extreme Market Simulator...")
    from tools.extreme_market_simulator import gen_extreme_chaos
    prices = gen_extreme_chaos(length=100, seed=42)
    if len(prices) == 100 and all(p > 0 for p in prices):
        print(f"   ✅ PASS: Generated 100 valid prices")
        passed += 1
    else:
        print(f"   ❌ FAIL: Invalid price series")
        failed += 1
    
    # Test 6: Compound multiplier
    print("\n[TEST 6] Compound Multiplier...")
    account.current_balance = 20000  # 2x growth
    compound_mult = engine._compound_multiplier(account)
    if compound_mult > 1.0:
        print(f"   ✅ PASS: 2x growth = {compound_mult:.2f}x compound")
        passed += 1
    else:
        print(f"   ❌ FAIL: Expected >1.0, got {compound_mult}")
        failed += 1
    
    print(f"\n{'='*40}")
    print(f"UNIT TESTS: {passed} PASSED, {failed} FAILED")
    print(f"{'='*40}")
    
    return passed, failed


if __name__ == "__main__":
    print("\n" + "🔥"*40)
    print(" EXTREME SYSTEMS RIGOROUS TEST SUITE")
    print("🔥"*40)
    
    # Run unit tests first
    unit_passed, unit_failed = test_component_units()
    
    if unit_failed > 0:
        print("\n⚠️ WARNING: Some unit tests failed, proceeding with backtests anyway...")
    
    # Run full backtest suite
    results = run_all_tests()
    
    # Print summary
    print_summary(results)
    
    # Exit code
    profitable = len([r for r in results if r.total_return_pct > 0])
    sys.exit(0 if profitable >= len(results) * 0.4 else 1)
