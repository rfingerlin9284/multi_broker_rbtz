#!/usr/bin/env python3
"""
TEST ALL STRATEGIES ON REAL OANDA DATA PATTERNS
See which one actually has edge in real conditions
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from multi_broker_phoenix.tools.backtest import Backtester
from multi_broker_phoenix.strategies.base import list_strategies
import numpy as np

def test_all_strategies():
    """Test each strategy on realistic data"""
    
    # Generate realistic trending and choppy data
    scenarios = {
        'Clean Uptrend': [100 + i*0.8 + np.random.normal(0, 0.5) for i in range(100)],
        'Clean Downtrend': [100 - i*0.8 + np.random.normal(0, 0.5) for i in range(100)],
        'Noisy Uptrend': [100 + i*0.5 + np.random.normal(0, 2) for i in range(100)],
        'Noisy Downtrend': [100 - i*0.5 + np.random.normal(0, 2) for i in range(100)],
        'Choppy Sideways': [100 + np.random.normal(0, 3) for _ in range(100)],
    }
    
    strategies = list_strategies()
    
    print("\n" + "="*80)
    print("🎯 STRATEGY COMPARISON - Which One Actually Works?")
    print("="*80)
    print("\nTesting on realistic price patterns...\n")
    
    results = {}
    
    for strat_id in strategies.keys():
        try:
            backtester = Backtester(strat_id)
            results[strat_id] = {}
            
            print(f"\n📊 {strat_id.upper()}:")
            print("-" * 60)
            
            total_return = 0
            total_wr = 0
            total_trades = 0
            scenario_count = 0
            
            for scenario_name, prices in scenarios.items():
                try:
                    stats = backtester.run(prices, symbol='TEST', platform='TEST')
                    
                    ret = stats['total_return'] * 100
                    wr = stats['win_rate'] * 100
                    trades = stats['trades']
                    
                    total_return += ret
                    total_wr += wr
                    total_trades += trades
                    scenario_count += 1
                    
                    status = "✅" if ret > 5 and wr > 50 else "❌" if ret < 0 else "⚠️"
                    
                    print(f"   {status} {scenario_name:20s}: {ret:+6.1f}% return, {wr:4.0f}% WR, {trades:3d} trades")
                    
                except Exception as e:
                    print(f"   ❌ {scenario_name:20s}: ERROR - {str(e)[:40]}")
            
            # Calculate averages
            avg_return = total_return / scenario_count if scenario_count > 0 else 0
            avg_wr = total_wr / scenario_count if scenario_count > 0 else 0
            avg_trades = total_trades / scenario_count if scenario_count > 0 else 0
            
            results[strat_id] = {
                'avg_return': avg_return,
                'avg_wr': avg_wr,
                'avg_trades': avg_trades,
                'score': avg_return * (avg_wr / 100) if avg_wr > 0 else avg_return
            }
            
            print(f"\n   AVERAGE: {avg_return:+.1f}% return, {avg_wr:.0f}% WR, {avg_trades:.1f} trades/scenario")
            
        except Exception as e:
            print(f"\n❌ {strat_id}: Failed to initialize - {e}")
    
    # Rank strategies
    print("\n\n" + "="*80)
    print("🏆 STRATEGY RANKINGS (Best to Worst)")
    print("="*80)
    
    ranked = sorted(results.items(), key=lambda x: x[1]['score'], reverse=True)
    
    for rank, (strat_id, stats) in enumerate(ranked, 1):
        score = stats['score']
        ret = stats['avg_return']
        wr = stats['avg_wr']
        
        if score > 5:
            emoji = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉"
            verdict = "WINNER - Use this one"
        elif score > 0:
            emoji = "⚠️"
            verdict = "Marginal - needs improvement"
        else:
            emoji = "❌"
            verdict = "LOSER - avoid"
        
        print(f"\n{emoji} #{rank}. {strat_id.upper()}")
        print(f"   Score: {score:.2f}")
        print(f"   Avg Return: {ret:+.1f}%")
        print(f"   Avg Win Rate: {wr:.0f}%")
        print(f"   Verdict: {verdict}")
    
    # Recommendation
    if ranked:
        best = ranked[0]
        print("\n\n" + "="*80)
        print("💡 RECOMMENDATION:")
        print("="*80)
        print(f"\nUse '{best[0]}' as your primary strategy.")
        print(f"   • Average Return: {best[1]['avg_return']:+.1f}%")
        print(f"   • Average Win Rate: {best[1]['avg_wr']:.0f}%")
        print(f"   • Score: {best[1]['score']:.2f}")
        
        if best[1]['score'] < 5:
            print("\n⚠️  WARNING: Even the best strategy has marginal edge.")
            print("   Consider:")
            print("   • Using tighter risk management")
            print("   • Only trading during optimal market sessions")
            print("   • Combining with additional filters")
        
        print("\n")

if __name__ == '__main__':
    test_all_strategies()
