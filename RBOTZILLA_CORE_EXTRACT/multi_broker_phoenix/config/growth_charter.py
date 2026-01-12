"""
RICK Growth Charter - For Small Account Compounding
Designed for: $5k-50k accounts that need leverage to grow
PIN: 841921 (Institutional rules archived until capital >= $100k)

Philosophy:
- Start small, compound aggressively
- Use leverage responsibly (2-5x)
- Monthly deposits fuel growth
- Graduate to institutional rules at $100k+
"""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class GrowthCharter:
    """Realistic constraints for small account growth"""
    
    # PHASE 1: GROWTH PHASE ($5k - $50k)
    # Goal: Build capital through compounding
    MIN_NOTIONAL_USD = 500           # Was $15k (achievable with $5k)
    MAX_NOTIONAL_USD = 5000          # Cap per trade until $50k capital
    MIN_RR_RATIO = 2.0               # Was 3.2 (still good but achievable)
    
    # Leverage (essential for growth)
    MIN_LEVERAGE = 2.0               # Minimum to make meaningful returns
    MAX_LEVERAGE = 5.0               # Conservative cap (not 10-50x retail)
    MAX_MARGIN_PCT = 60              # Was 35% (need room for multiple positions)
    
    # Risk Management
    RISK_PER_TRADE_PCT = 2.0         # 2% of capital per trade
    MAX_DAILY_RISK_PCT = 6.0         # 3 trades max per day
    MAX_CONCURRENT_POSITIONS = 3      # Same as institutional
    DAILY_LOSS_HALT_PCT = 5.0        # Stop trading at -5% day
    
    # Costs (realistic for retail)
    TRANSACTION_COST_PCT = 0.006     # 0.6% (spread + commission)
    SLIPPAGE_MIN_PCT = 0.001         # 0.1%
    SLIPPAGE_MAX_PCT = 0.003         # 0.3%
    
    # Compounding Strategy
    MONTHLY_DEPOSIT_USD = 1000       # User's plan
    REINVEST_PROFITS_PCT = 85        # 85% back to trading, 15% withdraw
    
    # Graduation Criteria
    INSTITUTIONAL_THRESHOLD_USD = 100000  # Move to institutional charter at $100k


@dataclass
class InstitutionalCharter:
    """Original strict rules - only for accounts >= $100k"""
    
    MIN_NOTIONAL_USD = 15000
    MIN_RR_RATIO = 3.2
    MAX_MARGIN_PCT = 35
    MAX_CONCURRENT_POSITIONS = 3
    RISK_PER_TRADE_PCT = 2.0         # Same as growth phase
    MAX_DAILY_RISK_PCT = 6.0
    DAILY_LOSS_HALT_PCT = 5.0
    TRANSACTION_COST_PCT = 0.004     # Better rates at institutional size
    SLIPPAGE_MIN_PCT = 0.0005
    SLIPPAGE_MAX_PCT = 0.0015


class AdaptiveCharter:
    """Automatically switches between Growth and Institutional based on capital"""
    
    def __init__(self, initial_capital: float):
        self.capital = initial_capital
        self.growth = GrowthCharter()
        self.institutional = InstitutionalCharter()
        self.pin = 841921
        
    def get_active_charter(self) -> Dict:
        """Return appropriate charter based on current capital"""
        if self.capital >= self.growth.INSTITUTIONAL_THRESHOLD_USD:
            return {
                'phase': 'INSTITUTIONAL',
                'charter': self.institutional,
                'min_notional': self.institutional.MIN_NOTIONAL_USD,
                'max_leverage': 3.0,  # Conservative at this level
                'reason': f'Capital ${self.capital:,.0f} >= $100k threshold'
            }
        else:
            return {
                'phase': 'GROWTH',
                'charter': self.growth,
                'min_notional': self.growth.MIN_NOTIONAL_USD,
                'max_leverage': self.growth.MAX_LEVERAGE,
                'reason': f'Capital ${self.capital:,.0f} in growth phase'
            }
    
    def update_capital(self, new_capital: float):
        """Update capital and potentially trigger charter change"""
        old_charter = self.get_active_charter()['phase']
        self.capital = new_capital
        new_charter = self.get_active_charter()['phase']
        
        if old_charter != new_charter:
            return {
                'graduated': True,
                'from': old_charter,
                'to': new_charter,
                'capital': new_capital
            }
        
        return {'graduated': False}
    
    def calculate_position_size(self, entry: float, stop: float) -> Dict:
        """Calculate position size based on active charter"""
        charter_info = self.get_active_charter()
        charter = charter_info['charter']
        
        # Risk amount (2% of capital)
        risk_amount = self.capital * (charter.RISK_PER_TRADE_PCT / 100)
        
        # Stop distance
        stop_distance = abs(entry - stop)
        if stop_distance == 0:
            return {'error': 'Zero stop distance'}
        
        # Units to risk 2% of capital
        units = risk_amount / stop_distance
        
        # Notional value
        notional = units * entry
        
        # Leverage required
        margin_required = notional / charter_info['max_leverage']
        margin_pct = (margin_required / self.capital) * 100
        
        # Check constraints
        if notional < charter.MIN_NOTIONAL_USD:
            return {
                'error': 'NOTIONAL_TOO_LOW',
                'notional': notional,
                'minimum': charter.MIN_NOTIONAL_USD,
                'capital': self.capital,
                'suggestion': f"Need ${charter.MIN_NOTIONAL_USD - notional:.0f} more capital or use {charter.MIN_NOTIONAL_USD/notional:.1f}x leverage"
            }
        
        if hasattr(charter, 'MAX_NOTIONAL_USD') and notional > charter.MAX_NOTIONAL_USD:
            # Scale down to max
            notional = charter.MAX_NOTIONAL_USD
            units = notional / entry
            risk_amount = units * stop_distance
            actual_risk_pct = (risk_amount / self.capital) * 100
        else:
            actual_risk_pct = charter.RISK_PER_TRADE_PCT
        
        if margin_pct > charter.MAX_MARGIN_PCT:
            return {
                'error': 'MARGIN_EXCEEDED',
                'margin_pct': margin_pct,
                'maximum': charter.MAX_MARGIN_PCT,
                'capital': self.capital,
                'suggestion': f"Reduce position size by {(margin_pct/charter.MAX_MARGIN_PCT - 1)*100:.0f}%"
            }
        
        return {
            'success': True,
            'units': units,
            'notional': notional,
            'margin_required': margin_required,
            'margin_pct': margin_pct,
            'leverage': notional / margin_required,
            'risk_amount': risk_amount,
            'risk_pct': actual_risk_pct,
            'charter_phase': charter_info['phase']
        }


def test_charter_scaling():
    """Demonstrate charter scaling from $5k to $200k"""
    print("\n" + "="*80)
    print("📊 ADAPTIVE CHARTER DEMONSTRATION")
    print("="*80)
    print("\nShowing how charter evolves from $5k to $200k\n")
    
    # Test at different capital levels
    test_capitals = [5000, 10000, 25000, 50000, 75000, 100000, 150000, 200000]
    entry_price = 1.30  # GBP/USD example
    stop_price = 1.27   # 3% stop
    
    for capital in test_capitals:
        charter = AdaptiveCharter(capital)
        info = charter.get_active_charter()
        sizing = charter.calculate_position_size(entry_price, stop_price)
        
        print(f"\n💰 Capital: ${capital:,}")
        print(f"   Phase: {info['phase']}")
        print(f"   Min Notional: ${info['min_notional']:,}")
        print(f"   Max Leverage: {info['max_leverage']}x")
        
        if sizing.get('success'):
            print(f"   ✅ Position: ${sizing['notional']:,.0f} notional")
            print(f"      Units: {sizing['units']:,.0f}")
            print(f"      Leverage: {sizing['leverage']:.1f}x")
            print(f"      Margin: {sizing['margin_pct']:.1f}%")
            print(f"      Risk: ${sizing['risk_amount']:.0f} ({sizing['risk_pct']:.1f}%)")
        else:
            print(f"   ❌ {sizing['error']}")
            if 'suggestion' in sizing:
                print(f"      {sizing['suggestion']}")
    
    print("\n" + "="*80)
    print("💡 KEY INSIGHTS:")
    print("="*80)
    print("• $5k-$99k: GROWTH phase (small trades, higher leverage)")
    print("• $100k+: INSTITUTIONAL phase (large trades, lower leverage)")
    print("• Both phases maintain 2% risk per trade")
    print("• Leverage scales DOWN as capital grows (safer)")
    print("\n")


if __name__ == '__main__':
    test_charter_scaling()
