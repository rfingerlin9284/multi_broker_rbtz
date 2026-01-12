#!/usr/bin/env python3
"""
Test all strategies on REALISTIC choppy/noisy data
Since backtests showed holy_grail with 90% WR but real trading had 4.9% WR,
we need to test on more realistic conditions with noise, whipsaws, gaps
"""

# This file is a *manual* analysis script, not a pytest suite.
# Without this, pytest will try to collect it (because of the filename/function
# prefixes) and fail due to missing fixtures.
__test__ = False
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from multi_broker_phoenix.tools.backtest import Backtester
import numpy as np

def generate_realistic_data(base: float = 100.0, bars: int | float = 100, trend: float = 0.5, noise: float = 2.0, whipsaw_freq: float = 0.15) -> list[float]:
    """Generate realistic price data with noise, gaps, whipsaws"""
    prices: list[float] = [float(base)]
    
    for i in range(int(bars)):
        # Base trend
        trend_component = trend
        
        # Add noise
        noise_component = np.random.normal(0, noise)
        
        # Random whipsaws (sudden reversals that trigger stops)
        if np.random.random() < whipsaw_freq:
            noise_component *= 3  # 3x noise = whipsaw
        
        # Occasional gaps (like weekends, news)
        if np.random.random() < 0.05:
            noise_component *= 2
        
        new_price = float(prices[-1] + trend_component + noise_component)
        prices.append(max(1.0, new_price))  # prevent negative
    
    return prices


def test_strategy_realistic(strategy_id):
    """Test a strategy on 10 realistic scenarios"""
    print(f"\n{'='*70}")
    print(f"Testing: {strategy_id.upper()}")
    print('='*70)
    
    scenarios = [
        ('Clean Uptrend', 100, 100, 0.8, 0.5, 0.05),
        ('Noisy Uptrend', 100, 100, 0.5, 2.0, 0.15),
        ('Very Noisy Uptrend', 100, 100, 0.4, 3.0, 0.25),
        ('Clean Downtrend', 100, 100, -0.8, 0.5, 0.05),
        ('Noisy Downtrend', 100, 100, -0.5, 2.0, 0.15),
        ('Very Noisy Downtrend', 100, 100, -0.4, 3.0, 0.25),
        ('Tight Sideways', 100, 100, 0.0, 1.0, 0.10),
        ('Choppy Sideways', 100, 100, 0.0, 2.5, 0.20),
        ('Whipsaw Hell', 100, 100, 0.0, 3.0, 0.35),
        ('Weak Trend + Noise', 100, 100, 0.2, 2.5, 0.20),
    ]
    
    backtester = Backtester(strategy_id)
    
    total_return = 0
    total_wr = 0
    win_count = 0
    scenario_count = 0
    
    for name, *params in scenarios:
        prices = generate_realistic_data(*params)
        
        try:
            stats = backtester.run(prices, symbol='TEST', platform='TEST')
            
            ret = stats['total_return'] * 100
            wr = stats['win_rate'] * 100
            trades = stats['trades']
            
            total_return += ret
            total_wr += wr
            scenario_count += 1
            
            # Count "winning" scenarios (positive return + decent WR)
            if ret > 5 and wr > 50:
                win_count += 1
                status = "✅"
            elif ret > 0:
                status = "⚠️"
            else:
                status = "❌"
            
            print(f"{status} {name:22s}: {ret:+7.1f}% return, {wr:5.1f}% WR, {trades:3d} trades")
            
        except Exception as e:
            print(f"❌ {name:22s}: ERROR - {str(e)[:50]}")
    
    # Summary
    avg_return = total_return / scenario_count if scenario_count > 0 else 0
    avg_wr = total_wr / scenario_count if scenario_count > 0 else 0
    success_rate = (win_count / scenario_count * 100) if scenario_count > 0 else 0
    
    print(f"\n📊 SUMMARY:")
    print(f"   Average Return: {avg_return:+.1f}%")
    print(f"   Average Win Rate: {avg_wr:.1f}%")
    print(f"   Winning Scenarios: {win_count}/{scenario_count} ({success_rate:.0f}%)")
    
    # Verdict
    if avg_return > 10 and avg_wr > 55 and success_rate > 60:
        verdict = "🥇 EXCELLENT - Use this strategy"
        score = 3
    elif avg_return > 5 and avg_wr > 50 and success_rate > 40:
        verdict = "🥈 GOOD - Workable with tight risk management"
        score = 2
    elif avg_return > 0:
        verdict = "🥉 MARGINAL - Needs heavy filtering/optimization"
        score = 1
    else:
        verdict = "❌ LOSER - Avoid or completely redesign"
        score = 0
    
    print(f"   Verdict: {verdict}")
    
    return {
        'strategy': strategy_id,
        'avg_return': avg_return,
        'avg_wr': avg_wr,
        'success_rate': success_rate,
        'score': score,
        'verdict': verdict
    }


def main():
    print("\n" + "="*70)
    print("🔬 REALISTIC STRATEGY TESTING")
    print("="*70)
    print("\nTesting on noisy/choppy data that mirrors REAL market conditions")
    print("(Not clean synthetic uptrends that make everything look good)\n")
    
    strategies = ['ema_scalper', 'institutional_sd', 'trap_reversal', 'holy_grail']
    results = []
    
    for strat_id in strategies:
        try:
            result = test_strategy_realistic(strat_id)
            results.append(result)
        except Exception as e:
            print(f"\n❌ {strat_id} FAILED TO TEST: {e}\n")
    
    # Final ranking
    print("\n\n" + "="*70)
    print("🏆 FINAL RANKINGS (on realistic data)")
    print("="*70)
    
    ranked = sorted(results, key=lambda x: (x['score'], x['avg_return']), reverse=True)
    
    for rank, r in enumerate(ranked, 1):
        print(f"\n#{rank}. {r['strategy'].upper()}")
        print(f"   Score: {r['score']}/3")
        print(f"   Avg Return: {r['avg_return']:+.1f}%")
        print(f"   Avg Win Rate: {r['avg_wr']:.1f}%")
        print(f"   Success Rate: {r['success_rate']:.0f}%")
        print(f"   {r['verdict']}")
    
    if ranked:
        best = ranked[0]
        print("\n\n" + "="*70)
        print("💡 RECOMMENDATION:")
        print("="*70)
        
        if best['score'] >= 2:
            print(f"\n✅ Use '{best['strategy']}' as your primary strategy")
            print(f"   It performs well on realistic noisy/choppy data")
        elif best['score'] == 1:
            print(f"\n⚠️  '{best['strategy']}' is marginal - use with EXTREME caution")
            print(f"   Requires tight risk management and additional filters")
        else:
            print(f"\n❌ ALL STRATEGIES FAILED on realistic data")
            print(f"\n   This explains why holy_grail had 90% WR in backtests")
            print(f"   but 4.9% WR in real trading!")
            print(f"\n   RECOMMENDATIONS:")
            print(f"   1. Build strategy from scratch using real OANDA patterns")
            print(f"   2. Train ML model on crypto_fvg_enhanced_training_data.csv")
            print(f"   3. Focus on GBP/USD only (your only profitable pair)")
            print(f"   4. Use much wider stops (3-5%) to survive whipsaws")
    
    print("\n")


if __name__ == '__main__':
    main()
