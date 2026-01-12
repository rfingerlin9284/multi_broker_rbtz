#!/usr/bin/env python3
"""
Compound Growth Simulator for RICK Growth Charter
Shows realistic path from $5k to $100k+ with monthly deposits

Assumptions based on GBP/USD strategy performance:
- Win rate: 38.1% (realistic from testing)
- Avg win: +2.0% (with 3:1 RR)
- Avg loss: -2.0% (2% risk per trade)
- Transaction costs: 0.6% per trade
- Monthly deposit: $1,000
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from multi_broker_phoenix.config.growth_charter import AdaptiveCharter


class CompoundingSimulator:
    def __init__(self, 
                 initial_capital: float = 5000,
                 monthly_deposit: float = 1000,
                 win_rate: float = 0.381,
                 risk_reward_ratio: float = 3.0,  # CRITICAL: Winners must be 3x bigger than losers
                 risk_per_trade_pct: float = 0.02,
                 transaction_cost_pct: float = 0.006,
                 trades_per_month: int = 8):
        
        self.capital = initial_capital
        self.monthly_deposit = monthly_deposit
        self.win_rate = win_rate
        self.risk_reward_ratio = risk_reward_ratio
        self.risk_per_trade_pct = risk_per_trade_pct
        self.transaction_cost_pct = transaction_cost_pct
        self.trades_per_month = trades_per_month
        
        # Calculate win/loss sizes
        self.avg_loss_pct = risk_per_trade_pct  # Lose 2% on losers
        self.avg_win_pct = risk_per_trade_pct * risk_reward_ratio  # Win 6% on winners (3:1 RR)
        
        self.charter = AdaptiveCharter(initial_capital)
        self.history = []
        self.month = 0
        
    def simulate_month(self) -> dict:
        """Simulate one month of trading"""
        self.month += 1
        month_start_capital = self.capital
        
        # Add monthly deposit (except month 1, already have initial capital)
        if self.month > 1:
            self.capital += self.monthly_deposit
        
        # Simulate trades
        wins = 0
        losses = 0
        total_profit = 0
        total_costs = 0
        
        # Calculate expected wins/losses for the month
        expected_wins = int(self.trades_per_month * self.win_rate)
        expected_losses = self.trades_per_month - expected_wins
        
        # Process winning trades
        for _ in range(expected_wins):
            # Winner: +2% on capital BEFORE this trade
            trade_capital = self.capital
            profit = trade_capital * self.avg_win_pct
            cost = trade_capital * self.transaction_cost_pct
            
            self.capital += profit - cost
            total_profit += profit
            total_costs += cost
            wins += 1
        
        # Process losing trades
        for _ in range(expected_losses):
            # Loser: -2% on capital BEFORE this trade
            trade_capital = self.capital
            profit = -trade_capital * self.avg_loss_pct
            cost = trade_capital * self.transaction_cost_pct
            
            self.capital += profit - cost
            total_profit += profit
            total_costs += cost
            losses += 1
        
        # Update charter
        graduation = self.charter.update_capital(self.capital)
        
        # Monthly stats
        month_stats = {
            'month': self.month,
            'start_capital': month_start_capital,
            'deposit': self.monthly_deposit if self.month > 1 else 0,
            'end_capital': self.capital,
            'wins': wins,
            'losses': losses,
            'win_rate': wins / (wins + losses) if (wins + losses) > 0 else 0,
            'gross_profit': total_profit,
            'costs': total_costs,
            'net_profit': total_profit - total_costs,
            'return_pct': ((self.capital - month_start_capital) / month_start_capital) * 100,
            'charter_phase': self.charter.get_active_charter()['phase'],
            'graduated': graduation.get('graduated', False)
        }
        
        self.history.append(month_stats)
        return month_stats
    
    def run_simulation(self, months: int = 60) -> list:
        """Run full simulation"""
        print("="*80)
        print("💰 COMPOUND GROWTH SIMULATION - $5k to $100k+ Journey")
        print("="*80)
        print(f"\nStarting Capital: ${self.capital:,.0f}")
        print(f"Monthly Deposit: ${self.monthly_deposit:,.0f}")
        print(f"Win Rate: {self.win_rate*100:.1f}%")
        print(f"Risk/Reward: {self.risk_reward_ratio:.1f}:1 (Win {self.avg_win_pct*100:.0f}% vs Lose {self.avg_loss_pct*100:.0f}%)")
        print(f"Transaction Cost: {self.transaction_cost_pct*100:.2f}% per trade")
        print(f"Trades/Month: {self.trades_per_month}")
        print(f"\n{'─'*80}\n")
        
        for m in range(months):
            stats = self.simulate_month()
            
            # Print milestone months
            if m == 0 or (m + 1) % 6 == 0 or stats['graduated']:
                self.print_month_summary(stats)
            
            # Stop if reached institutional phase
            if stats['charter_phase'] == 'INSTITUTIONAL':
                print("\n" + "="*80)
                print("🎓 GRADUATED TO INSTITUTIONAL CHARTER!")
                print("="*80)
                break
        
        print(f"\n{'='*80}\n")
        self.print_final_summary()
        return self.history
    
    def print_month_summary(self, stats: dict):
        """Print one month's summary"""
        grad_marker = " 🎓 GRADUATED!" if stats['graduated'] else ""
        
        print(f"Month {stats['month']:2d} [{stats['charter_phase']:>12s}]{grad_marker}")
        print(f"  Capital: ${stats['start_capital']:>8,.0f} → ${stats['end_capital']:>8,.0f} "
              f"({stats['return_pct']:+.1f}%)")
        print(f"  Deposit: ${stats['deposit']:>8,.0f} | "
              f"Trades: {stats['wins']}W/{stats['losses']}L ({stats['win_rate']*100:.0f}%)")
        print(f"  P&L: ${stats['gross_profit']:>+7,.0f} - ${stats['costs']:>5,.0f} costs = "
              f"${stats['net_profit']:>+7,.0f} net")
        print()
    
    def print_final_summary(self):
        """Print final results"""
        if not self.history:
            return
        
        total_deposits = sum(m['deposit'] for m in self.history)
        total_invested = self.history[0]['start_capital'] + total_deposits
        total_profit = self.capital - total_invested
        total_return_pct = (total_profit / total_invested) * 100
        
        wins = sum(m['wins'] for m in self.history)
        losses = sum(m['losses'] for m in self.history)
        overall_wr = wins / (wins + losses) if (wins + losses) > 0 else 0
        
        print("📊 FINAL RESULTS")
        print("="*80)
        print(f"Starting Capital:    ${self.history[0]['start_capital']:>10,.0f}")
        print(f"Total Deposits:      ${total_deposits:>10,.0f}")
        print(f"Total Invested:      ${total_invested:>10,.0f}")
        print()
        print(f"Ending Capital:      ${self.capital:>10,.0f}")
        print(f"Total Profit:        ${total_profit:>10,.0f} ({total_return_pct:+.1f}%)")
        print()
        print(f"Total Trades:        {wins + losses}")
        print(f"Win Rate:            {overall_wr*100:.1f}%")
        print(f"Months to $100k:     {self.month} months ({self.month/12:.1f} years)")
        print()
        
        # Graduation info
        if self.charter.get_active_charter()['phase'] == 'INSTITUTIONAL':
            print("✅ Graduated to INSTITUTIONAL charter")
            print("   • Can now trade $15k+ notional")
            print("   • Lower costs (0.4% vs 0.6%)")
            print("   • Conservative leverage (3x max)")
        else:
            remaining = 100000 - self.capital
            months_to_go = int(remaining / (total_profit / self.month)) if total_profit > 0 else 999
            print(f"📈 Still in GROWTH phase")
            print(f"   • ${remaining:,.0f} to institutional threshold")
            print(f"   • Estimated {months_to_go} months to $100k")
        
        print("\n" + "="*80)


def run_scenarios():
    """Run multiple scenarios to show range of outcomes"""
    print("\n" + "="*80)
    print("🎯 SCENARIO ANALYSIS: Conservative vs Optimistic")
    print("="*80 + "\n")
    
    scenarios = [
        {
            'name': 'CONSERVATIVE (30% WR)',
            'win_rate': 0.30,
            'trades_per_month': 6
        },
        {
            'name': 'REALISTIC (38% WR) ← GBP/USD Strategy',
            'win_rate': 0.381,
            'trades_per_month': 8
        },
        {
            'name': 'OPTIMISTIC (45% WR)',
            'win_rate': 0.45,
            'trades_per_month': 10
        }
    ]
    
    for scenario in scenarios:
        print(f"\n{'='*80}")
        print(f"📊 {scenario['name']}")
        print(f"{'='*80}\n")
        
        sim = CompoundingSimulator(
            initial_capital=5000,
            monthly_deposit=1000,
            win_rate=scenario['win_rate'],
            risk_reward_ratio=3.0,  # 3:1 RR minimum
            trades_per_month=scenario['trades_per_month']
        )
        
        sim.run_simulation(months=60)
        
        input("\nPress Enter to continue to next scenario...")


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--scenarios':
        run_scenarios()
    else:
        # Default: realistic scenario
        sim = CompoundingSimulator(
            initial_capital=5000,
            monthly_deposit=1000,
            win_rate=0.381,  # From GBP/USD testing
            risk_reward_ratio=3.0,  # CRITICAL: 3:1 minimum for profitability
            trades_per_month=8
        )
        sim.run_simulation(months=60)
