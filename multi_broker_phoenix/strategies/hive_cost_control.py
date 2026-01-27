"""
API COST CONTROL & HIVE-STRATEGY COORDINATION
Prevents duplicate scanning and manages AI API costs
"""
import os
import logging 
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from collections import defaultdict
import json

logger = logging.getLogger(__name__)


class APIBudgetManager:
    """Manages AI API usage and costs to prevent overruns."""
    
    def __init__(self):
        # Load budget limits from environment
        self.daily_budget_usd = float(os.getenv('AI_HIVE_DAILY_BUDGET_USD', '10.0'))
        self.cost_per_call = {
            'openai': float(os.getenv('OPENAI_COST_PER_CALL', '0.01')),
            'xai': float(os.getenv('XAI_COST_PER_CALL', '0.005')),
            'deepseek': float(os.getenv('DEEPSEEK_COST_PER_CALL', '0.002'))
        }
        
        # Tracking
        self.daily_spend = 0.0
        self.call_count = defaultdict(int)
        self.last_reset = datetime.now()
        
        # Limits
        self.max_calls_per_symbol = int(os.getenv('AI_MAX_CALLS_PER_SYMBOL', '3'))
        self.max_total_calls_per_scan = int(os.getenv('AI_MAX_CALLS_PER_SCAN', '50'))
        self.symbol_call_tracker = defaultdict(int)
        
        logger.info(f"💰 API Budget Manager initialized")
        logger.info(f"   Daily budget: ${self.daily_budget_usd:.2f}")
        logger.info(f"   Max calls per symbol: {self.max_calls_per_symbol}")
        logger.info(f"   Max calls per scan: {self.max_total_calls_per_scan}")
    
    def reset_daily_if_needed(self):
        """Reset counters at midnight."""
        now = datetime.now()
        if now.date() > self.last_reset.date():
            logger.info(f"🔄 Daily budget reset - Previous spend: ${self.daily_spend:.2f}")
            self.daily_spend = 0.0
            self.call_count.clear()
            self.symbol_call_tracker.clear()
            self.last_reset = now
    
    def can_make_call(self, provider: str, symbol: str = None) -> bool:
        """Check if we can afford another AI call."""
        self.reset_daily_if_needed()
        
        # Check daily budget
        estimated_cost = self.cost_per_call.get(provider, 0.01)
        if self.daily_spend + estimated_cost > self.daily_budget_usd:
            logger.warning(f"❌ Budget limit reached: ${self.daily_spend:.2f}/${self.daily_budget_usd:.2f}")
            return False
        
        # Check per-symbol limit
        if symbol and self.symbol_call_tracker[symbol] >= self.max_calls_per_symbol:
            logger.debug(f"⚠️  Symbol {symbol} call limit reached: {self.symbol_call_tracker[symbol]}")
            return False
        
        # Check total calls per scan
        total_calls = sum(self.call_count.values())
        if total_calls >= self.max_total_calls_per_scan:
            logger.warning(f"⚠️  Scan call limit reached: {total_calls}/{self.max_total_calls_per_scan}")
            return False
        
        return True
    
    def record_call(self, provider: str, symbol: str = None, cost: float = None):
        """Record an API call."""
        if cost is None:
            cost = self.cost_per_call.get(provider, 0.01)
        
        self.daily_spend += cost
        self.call_count[provider] += 1
        if symbol:
            self.symbol_call_tracker[symbol] += 1
        
        logger.debug(f"💸 API call: {provider} ${cost:.4f} (total: ${self.daily_spend:.2f})")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current budget stats."""
        return {
            'daily_spend': self.daily_spend,
            'daily_budget': self.daily_budget_usd,
            'remaining_budget': self.daily_budget_usd - self.daily_spend,
            'utilization_pct': (self.daily_spend / self.daily_budget_usd * 100) if self.daily_budget_usd > 0 else 0,
            'total_calls': sum(self.call_count.values()),
            'calls_by_provider': dict(self.call_count),
            'symbols_scanned': len(self.symbol_call_tracker)
        }


class HiveStrategyCoordinator:
    """Coordinates between strategy scanning and AI Hive to prevent redundancy."""
    
    def __init__(self, budget_manager: APIBudgetManager):
        self.budget = budget_manager
        
        # Configuration
        self.strategy_must_pass_first = os.getenv('HIVE_STRATEGY_FIRST', 'true').lower() == 'true'
        self.hive_only_on_strategy_signal = os.getenv('HIVE_ONLY_ON_SIGNAL', 'true').lower() == 'true'
        self.min_strategy_confidence = float(os.getenv('HIVE_MIN_STRATEGY_CONF', '0.60'))
        
        # Critical: Ensure strategy threshold changes are permanent
        self.preserve_fabio_rsi_threshold = int(os.getenv('FABIO_RSI_THRESHOLD', '40'))
        
        logger.info(f"🤝 Hive-Strategy Coordinator initialized")
        logger.info(f"   Strategy must pass first: {self.strategy_must_pass_first}")
        logger.info(f"   Hive only on signal: {self.hive_only_on_strategy_signal}")
        logger.info(f"   Min strategy confidence: {self.min_strategy_confidence}")
        logger.info(f"   ✅ FABIO RSI Threshold locked at: {self.preserve_fabio_rsi_threshold}")
    
    def should_invoke_hive(self, symbol: str, strategy_signal: Optional[Dict] = None) -> bool:
        """Decide if we should invoke AI Hive for this symbol.
        
        This prevents expensive AI calls when not needed.
        """
        # Check budget first
        if not self.budget.can_make_call('openai', symbol):
            return False
        
        # If configured for strategy-first mode
        if self.strategy_must_pass_first:
            if not strategy_signal:
                logger.debug(f"⏭️  Skipping Hive for {symbol} - no strategy signal (strategy-first mode)")
                return False
            
            if strategy_signal.get('confidence', 0) < self.min_strategy_confidence:
                logger.debug(f"⏭️  Skipping Hive for {symbol} - confidence {strategy_signal.get('confidence', 0):.2f} < {self.min_strategy_confidence}")
                return False
        
        # If configured for hive-only-on-signal
        if self.hive_only_on_strategy_signal and not strategy_signal:
            return False
        
        return True
    
    def build_efficient_scan_plan(self, universe: List[str], 
                                  strategy_results: Dict[str, Any]) -> Dict[str, Any]:
        """Create efficient scan plan that minimizes AI API calls.
        
        Strategy:
        1. Strategy scans run first (cheap, fast)
        2. Only invoke Hive for symbols with strategy signals
        3. Prioritize high-confidence signals for Hive validation
        4. Skip Hive entirely if budget exhausted
        
        Returns plan with symbols_to_scan and estimated_cost
        """
        plan = {
            'strategy_phase': {
                'symbols': universe,
                'cost': 0.0,  # Strategy scanning is local/free
                'expected_signals': len(universe) * 0.05  # 5% signal rate
            },
            'hive_phase': {
                'symbols': [],
                'cost': 0.0,
                'max_calls': 0
            },
            'total_estimated_cost': 0.0
        }
        
        # Get strategy signals that passed
        signals_by_symbol = {}
        for sig in strategy_results.get('signals', []):
            symbol = sig.get('symbol')
            if symbol and sig.get('confidence', 0) >= self.min_strategy_confidence:
                signals_by_symbol[symbol] = sig
        
        # Plan Hive phase only for symbols with strong signals
        hive_candidates = []
        for symbol, signal in signals_by_symbol.items():
            if self.should_invoke_hive(symbol, signal):
                hive_candidates.append({
                    'symbol': symbol,
                    'priority': signal.get('confidence', 0) * signal.get('quality_score', 0.5)
                })
        
        # Sort by priority
        hive_candidates.sort(key=lambda x: x['priority'], reverse=True)
        
        # Limit by budget
        max_hive_calls = min(len(hive_candidates), self.budget.max_total_calls_per_scan)
        hive_symbols = [c['symbol'] for c in hive_candidates[:max_hive_calls]]
        
        plan['hive_phase']['symbols'] = hive_symbols
        plan['hive_phase']['max_calls'] = len(hive_symbols) * 3  # 3 agents per symbol
        plan['hive_phase']['cost'] = len(hive_symbols) * 3 * 0.01  # Estimate
        plan['total_estimated_cost'] = plan['hive_phase']['cost']
        
        logger.info(f"📋 Efficient Scan Plan:")
        logger.info(f"   Strategy phase: {len(universe)} symbols (free)")
        logger.info(f"   Hive phase: {len(hive_symbols)} symbols ({plan['hive_phase']['max_calls']} calls)")
        logger.info(f"   Estimated cost: ${plan['total_estimated_cost']:.2f}")
        logger.info(f"   Budget remaining: ${self.budget.get_stats()['remaining_budget']:.2f}")
        
        return plan


# Global instances
_budget_manager = None
_coordinator = None

def get_budget_manager() -> APIBudgetManager:
    """Get global budget manager."""
    global _budget_manager
    if _budget_manager is None:
        _budget_manager = APIBudgetManager()
    return _budget_manager

def get_coordinator() -> HiveStrategyCoordinator:
    """Get global coordinator."""
    global _coordinator
    if _coordinator is None:
        budget = get_budget_manager()
        _coordinator = HiveStrategyCoordinator(budget)
    return _coordinator
