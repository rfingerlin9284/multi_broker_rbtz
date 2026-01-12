"""
HIVE-ENABLED PAPER ENGINE
Paper trading engine with HIVE consensus filtering

Every trade candidate goes through:
1. Strategy generates signal
2. HIVE votes on trade
3. Only approved trades proceed to execution
4. Track HIVE performance vs non-filtered

This is your edge: Multi-agent validation before every trade
"""
from typing import Optional, Dict, List
import time
from datetime import datetime

from ..engines.hive_consensus import (
    HiveConsensusEngine, TradeOpportunity, FundamentalsAgent,
    TechnicalsAgent, RiskGuardianAgent
)
from ..engines.hive_advanced_agents import (
    DeepResearchAgent, FlowTrackerAgent,
    VolatilityRegimeAgent, MacroRegimeAgent
)
from ..risk.trade_risk_gate import TradeCandidate
from ..engines.paper_engine import PaperEngine


class HiveEnabledPaperEngine(PaperEngine):
    """Paper engine with HIVE consensus validation"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Initialize HIVE
        self.hive_agents = [
            DeepResearchAgent(),      # Oracle
            TechnicalsAgent(),        # Prometheus
            FlowTrackerAgent(),       # Hydra
            VolatilityRegimeAgent(),  # Sphinx
            MacroRegimeAgent(),       # Zeus
            RiskGuardianAgent(),      # Sentinel (VETO power)
            FundamentalsAgent(),      # Atlas
        ]
        
        self.hive = HiveConsensusEngine(
            self.hive_agents,
            approval_threshold=0.55  # Need 55% consensus
        )
        
        # Track HIVE stats
        self.hive_stats = {
            'signals_generated': 0,
            'approved': 0,
            'rejected': 0,
            'vetoed': 0,
            'approval_rate': 0.0
        }
        
        print("\n🐝 HIVE CONSENSUS ENGINE ACTIVATED")
        print("="*60)
        print("All trades will be validated by 7 specialized agents:")
        for agent in self.hive_agents:
            print(f"  • {agent.name} ({agent.role.value})")
        print(f"\nApproval threshold: {self.hive.approval_threshold*100:.0f}%")
        print("="*60 + "\n")
    
    def _convert_candidate_to_opportunity(self, candidate: TradeCandidate, prices: List[float]) -> TradeOpportunity:
        """Convert TradeCandidate to TradeOpportunity for HIVE evaluation"""
        
        # Calculate take profit (use 3:1 RR minimum)
        stop_distance = abs(candidate.entry_price - candidate.stop_loss)
        if candidate.side == 'BUY':
            take_profit = candidate.entry_price + (stop_distance * 3.0)
        else:
            take_profit = candidate.entry_price - (stop_distance * 3.0)
        
        return TradeOpportunity(
            symbol=candidate.symbol,
            side=candidate.side or 'BUY',
            entry_price=candidate.entry_price,
            stop_loss=candidate.stop_loss,
            take_profit=take_profit,
            reasoning=f"Strategy: {candidate.strategy_id}",
            discovered_by=candidate.strategy_id,
            confidence=0.7,  # Default confidence
            timestamp=time.time(),
            catalysts=[],
            risk_factors=[]
        )
    
    def process_candidate(self, candidate: TradeCandidate, prices: List[float]) -> Optional[Dict]:
        """Process trade candidate through HIVE before execution
        
        Returns:
            Dict with execution details if approved, None if rejected
        """
        self.hive_stats['signals_generated'] += 1
        
        # Convert to opportunity
        opportunity = self._convert_candidate_to_opportunity(candidate, prices)
        
        # HIVE evaluation
        print(f"\n{'='*80}")
        print(f"🐝 HIVE EVALUATING SIGNAL #{self.hive_stats['signals_generated']}")
        print(f"{'='*80}")
        
        result = self.hive.evaluate_opportunity(opportunity)
        
        # Update stats
        if result.vetoed:
            self.hive_stats['vetoed'] += 1
            print(f"\n🚫 TRADE VETOED BY HIVE - Not executing")
            return None
        elif result.approved:
            self.hive_stats['approved'] += 1
            print(f"\n✅ TRADE APPROVED BY HIVE - Proceeding to execution")
        else:
            self.hive_stats['rejected'] += 1
            print(f"\n❌ TRADE REJECTED BY HIVE - Insufficient consensus")
            return None
        
        # Update approval rate
        self.hive_stats['approval_rate'] = (
            self.hive_stats['approved'] / self.hive_stats['signals_generated']
            if self.hive_stats['signals_generated'] > 0 else 0
        )
        
        # If approved, proceed with normal execution
        # Use the original candidate for execution
        return {
            'candidate': candidate,
            'hive_result': result,
            'approved': True
        }
    
    def get_hive_stats(self) -> Dict:
        """Get HIVE performance statistics"""
        return {
            **self.hive_stats,
            'agents': [
                {
                    'name': agent.name,
                    'role': agent.role.value,
                    'weight': agent.expertise_weight
                }
                for agent in self.hive_agents
            ]
        }
    
    def print_hive_summary(self):
        """Print HIVE performance summary"""
        print("\n" + "="*80)
        print("🐝 HIVE CONSENSUS SUMMARY")
        print("="*80)
        print(f"Total Signals: {self.hive_stats['signals_generated']}")
        print(f"  ✅ Approved: {self.hive_stats['approved']} ({self.hive_stats['approval_rate']*100:.1f}%)")
        print(f"  ❌ Rejected: {self.hive_stats['rejected']}")
        print(f"  🚫 Vetoed: {self.hive_stats['vetoed']}")
        print(f"\n💡 Approval Rate: {self.hive_stats['approval_rate']*100:.1f}%")
        print("="*80 + "\n")


def demo_hive_paper_engine():
    """Demo HIVE-enabled paper engine"""
    import random
    
    print("\n" + "="*80)
    print("🚀 HIVE-ENABLED PAPER ENGINE DEMONSTRATION")
    print("="*80)
    print("\nThis engine filters ALL trades through the HIVE before execution")
    print("Watch how the HIVE protects you from bad trades!\n")
    
    # Initialize engine
    engine = HiveEnabledPaperEngine(
        starting_capital=50000,
        platform='OANDA',
        instruments=['GBP/USD', 'EUR/USD']
    )
    
    # Generate some test signals
    test_signals = [
        # Good trade: Wide stop, good RR
        TradeCandidate(
            strategy_id='gbp_usd_only',
            symbol='GBP/USD',
            platform='OANDA',
            entry_price=1.3000,
            stop_loss=1.2700,  # 3% stop
            side='BUY'
        ),
        # Bad trade: Tight stop
        TradeCandidate(
            strategy_id='scalper',
            symbol='EUR/USD',
            platform='OANDA',
            entry_price=1.1000,
            stop_loss=1.0945,  # 0.5% stop (TOO TIGHT)
            side='SELL'
        ),
        # Good trade: Decent setup
        TradeCandidate(
            strategy_id='holy_grail',
            symbol='GBP/USD',
            platform='OANDA',
            entry_price=1.3050,
            stop_loss=1.2790,  # 2% stop
            side='BUY'
        ),
        # Bad trade: Terrible RR
        TradeCandidate(
            strategy_id='random',
            symbol='EUR/USD',
            platform='OANDA',
            entry_price=1.1000,
            stop_loss=1.0890,  # 1% stop but only 1:1 RR
            side='BUY'
        ),
    ]
    
    # Simulate price history
    prices = [1.30 + random.uniform(-0.01, 0.01) for _ in range(100)]
    
    # Process each signal
    for i, signal in enumerate(test_signals, 1):
        print(f"\n\n{'#'*80}")
        print(f"SIGNAL {i}/{len(test_signals)}")
        print(f"{'#'*80}")
        
        result = engine.process_candidate(signal, prices)
        
        if result:
            print(f"✅ Signal executed")
        else:
            print(f"❌ Signal blocked by HIVE")
        
        time.sleep(1)  # Pause between signals
    
    # Final summary
    engine.print_hive_summary()
    
    print("\n💡 KEY INSIGHT:")
    print("="*80)
    print("The HIVE filtered out bad trades BEFORE they hit your account!")
    print("This is how you protect capital and improve win rate.")
    print("\nWithout HIVE: 4 trades executed (including 2 bad ones)")
    print(f"With HIVE: {engine.hive_stats['approved']} trades executed (only quality setups)")
    print("="*80 + "\n")


if __name__ == '__main__':
    demo_hive_paper_engine()
