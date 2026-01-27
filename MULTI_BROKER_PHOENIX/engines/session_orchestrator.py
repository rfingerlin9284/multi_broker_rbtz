#!/usr/bin/env python3
"""
SESSION ORCHESTRATOR
NYC/London session-aware trading with cross-broker hedging and loss recovery
"""
import os
import sys
from datetime import datetime, time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from multi_broker_phoenix.engines.extreme_compounding_engine import ExtremeCompoundingEngine, AccountState
from multi_broker_phoenix.engines.zombie_trade_killer import ZombieTradeKiller


class TradingSession(Enum):
    """Market sessions with optimal trading characteristics"""
    ASIA = "asia"           # 00:00-08:00 UTC - Low volume, range-bound
    LONDON = "london"       # 07:00-16:00 UTC - High volume, trend-heavy
    NY = "ny"              # 13:00-21:00 UTC - Highest volume, volatility
    OVERLAP = "overlap"     # 13:00-16:00 UTC - Maximum liquidity (London+NY)
    OFF_HOURS = "off"      # All other times - Avoid trading


@dataclass
class SessionConfig:
    """Session-specific trading configuration"""
    session: TradingSession
    max_positions: int
    preferred_strategies: List[str]
    preferred_instruments: List[str]
    risk_multiplier: float  # Multiply base risk by this
    hedging_enabled: bool
    
    # Broker allocation
    coinbase_allocation: float  # % of capital
    ibkr_allocation: float


class SessionOrchestrator:
    """
    Coordinates trading across NYC/London sessions with smart hedging
    
    Features:
    - Session-aware strategy selection
    - Cross-broker hedging for loss recovery
    - Overlap period maximum aggression
    - Automatic risk adjustment by session
    """
    
    # Session configurations
    SESSION_CONFIGS = {
        TradingSession.LONDON: SessionConfig(
            session=TradingSession.LONDON,
            max_positions=4,
            preferred_strategies=['institutional_sd', 'ema_scalper'],  # Trend-following
            preferred_instruments=['GBPUSD', 'EURUSD', 'GBPJPY', 'BTC-USD', 'ETH-USD'],
            risk_multiplier=1.2,  # 20% more risk in active session
            hedging_enabled=True,
            coinbase_allocation=0.4,  # 40% crypto
            ibkr_allocation=0.6       # 60% forex
        ),
        TradingSession.NY: SessionConfig(
            session=TradingSession.NY,
            max_positions=5,
            preferred_strategies=['institutional_sd', 'ema_scalper', 'trap_reversal'],
            preferred_instruments=['SPY', 'QQQ', 'EURUSD', 'BTC-USD', 'ETH-USD'],
            risk_multiplier=1.3,  # 30% more risk
            hedging_enabled=True,
            coinbase_allocation=0.5,  # 50/50 split
            ibkr_allocation=0.5
        ),
        TradingSession.OVERLAP: SessionConfig(
            session=TradingSession.OVERLAP,
            max_positions=7,  # MAXIMUM positions during peak liquidity
            preferred_strategies=['institutional_sd', 'ema_scalper', 'trap_reversal'],
            preferred_instruments=['GBPUSD', 'EURUSD', 'BTC-USD', 'ETH-USD', 'SPY'],
            risk_multiplier=1.5,  # 50% MORE RISK - peak opportunity
            hedging_enabled=True,
            coinbase_allocation=0.5,
            ibkr_allocation=0.5
        ),
        TradingSession.ASIA: SessionConfig(
            session=TradingSession.ASIA,
            max_positions=2,
            preferred_strategies=['trap_reversal'],  # Range-bound strategies
            preferred_instruments=['USDJPY', 'AUDUSD', 'NZDUSD'],
            risk_multiplier=0.7,  # Reduced risk in low liquidity
            hedging_enabled=False,  # No hedging in Asia
            coinbase_allocation=0.2,  # Minimal crypto overnight
            ibkr_allocation=0.8
        ),
        TradingSession.OFF_HOURS: SessionConfig(
            session=TradingSession.OFF_HOURS,
            max_positions=1,
            preferred_strategies=[],
            preferred_instruments=[],
            risk_multiplier=0.5,
            hedging_enabled=False,
            coinbase_allocation=0.0,
            ibkr_allocation=0.0
        )
    }
    
    def __init__(self,
                 compounding_engine: ExtremeCompoundingEngine,
                 zombie_killer: ZombieTradeKiller):
        self.compounding = compounding_engine
        self.zombie_killer = zombie_killer
        
        # Track losses for recovery
        self.session_losses = {
            'coinbase': [],  # List of loss amounts
            'ibkr': []
        }
        
        # Active hedge positions
        self.hedges = {}
    
    def get_current_session(self) -> TradingSession:
        """Determine current trading session based on UTC time"""
        now = datetime.utcnow()
        hour = now.hour
        
        # London/NY overlap (13:00-16:00 UTC) - HIGHEST PRIORITY
        if 13 <= hour < 16:
            return TradingSession.OVERLAP
        
        # London session (07:00-16:00 UTC)
        elif 7 <= hour < 16:
            return TradingSession.LONDON
        
        # NY session (13:00-21:00 UTC)
        elif 13 <= hour < 21:
            return TradingSession.NY
        
        # Asia session (00:00-08:00 UTC)
        elif 0 <= hour < 8:
            return TradingSession.ASIA
        
        # Off hours
        else:
            return TradingSession.OFF_HOURS
    
    def get_session_config(self) -> SessionConfig:
        """Get configuration for current session"""
        session = self.get_current_session()
        return self.SESSION_CONFIGS[session]
    
    def should_trade_now(self) -> bool:
        """Check if we should be trading in current session"""
        session = self.get_current_session()
        
        # Only trade during London, NY, and Overlap
        return session in [TradingSession.LONDON, TradingSession.NY, TradingSession.OVERLAP]
    
    def calculate_position_size(self,
                               broker: str,
                               account: AccountState,
                               signal_strength: float,
                               instrument: str) -> Dict[str, Any]:
        """
        Calculate position size with session-aware risk adjustment
        """
        config = self.get_session_config()
        
        # Check if instrument is preferred for this session
        instrument_match = any(pref in instrument.upper() for pref in config.preferred_instruments)
        
        # Adjust signal strength based on session optimality
        if instrument_match:
            adjusted_signal = min(1.0, signal_strength * 1.1)  # 10% boost
        else:
            adjusted_signal = signal_strength * 0.9  # 10% penalty
        
        # Get base sizing from compounding engine
        sizing = self.compounding.calculate_position_size(
            account=account,
            signal_strength=adjusted_signal,
            win_probability=account.win_rate_30d
        )
        
        # Apply session risk multiplier
        sizing['risk_pct'] *= config.risk_multiplier
        sizing['total_size'] *= config.risk_multiplier
        
        # Apply broker allocation
        if broker == 'coinbase':
            sizing['total_size'] *= config.coinbase_allocation
        elif broker == 'ibkr':
            sizing['total_size'] *= config.ibkr_allocation
        
        sizing['session'] = config.session.value
        sizing['session_adjusted'] = True
        
        return sizing
    
    def record_loss(self, broker: str, loss_amount: float, instrument: str):
        """Record a loss for potential hedging"""
        self.session_losses[broker].append({
            'amount': loss_amount,
            'instrument': instrument,
            'timestamp': datetime.utcnow(),
            'recovered': False
        })
    
    def should_hedge(self, broker: str, account: AccountState) -> Dict[str, Any]:
        """
        Determine if we should open a hedge position to recover losses
        
        Hedging Strategy:
        - After 2+ consecutive losses on one broker
        - Open counter-position on other broker
        - Use inverse correlation (BTC-USD vs SPY, EURUSD vs USDCHF, etc.)
        - Size hedge to recover recent losses + profit
        """
        config = self.get_session_config()
        
        if not config.hedging_enabled:
            return {'should_hedge': False, 'reason': 'Hedging disabled for this session'}
        
        # Check for consecutive losses
        recent_losses = [l for l in self.session_losses[broker] if not l['recovered']]
        
        if len(recent_losses) < 2:
            return {'should_hedge': False, 'reason': 'Not enough losses to hedge'}
        
        # Calculate total unrecovered losses
        total_loss = sum(l['amount'] for l in recent_losses)
        loss_pct = (total_loss / account.current_balance) * 100
        
        if loss_pct < 1.0:  # Less than 1% loss
            return {'should_hedge': False, 'reason': 'Losses too small to hedge'}
        
        # Determine hedge instrument and broker
        last_loss_instrument = recent_losses[-1]['instrument']
        hedge_broker = 'ibkr' if broker == 'coinbase' else 'coinbase'
        hedge_instrument = self._get_hedge_instrument(last_loss_instrument, hedge_broker)
        
        # Calculate hedge size: recover losses + 20% profit target
        target_recovery = total_loss * 1.2
        hedge_size = target_recovery / account.current_balance
        
        return {
            'should_hedge': True,
            'hedge_broker': hedge_broker,
            'hedge_instrument': hedge_instrument,
            'hedge_size_pct': hedge_size * 100,
            'target_recovery': target_recovery,
            'reason': f'Recovering ${total_loss:.2f} from {len(recent_losses)} losses'
        }
    
    def _get_hedge_instrument(self, original_instrument: str, hedge_broker: str) -> str:
        """
        Get inverse correlated instrument for hedging
        
        Hedging pairs:
        - BTC-USD (Coinbase) <-> SPY short (IBKR) - risk-off correlation
        - ETH-USD (Coinbase) <-> QQQ short (IBKR)
        - EURUSD long (IBKR) <-> USDCHF short (IBKR)
        - GBPUSD long (IBKR) <-> EURGBP short (IBKR)
        """
        orig_upper = original_instrument.upper()
        
        # Crypto -> Equities (inverse)
        if 'BTC' in orig_upper:
            return 'SPY' if hedge_broker == 'ibkr' else 'ETH-USD'
        elif 'ETH' in orig_upper:
            return 'QQQ' if hedge_broker == 'ibkr' else 'BTC-USD'
        
        # Forex inverse pairs
        elif 'EURUSD' in orig_upper:
            return 'USDCHF'
        elif 'GBPUSD' in orig_upper:
            return 'EURGBP'
        elif 'USDCHF' in orig_upper:
            return 'EURUSD'
        
        # Equities -> Crypto (inverse)
        elif 'SPY' in orig_upper or 'QQQ' in orig_upper:
            return 'BTC-USD' if hedge_broker == 'coinbase' else 'GBPUSD'
        
        # Default: use same instrument on opposite broker
        return original_instrument
    
    def mark_loss_recovered(self, broker: str, recovered_amount: float):
        """Mark losses as recovered after successful hedge"""
        unrecovered = [l for l in self.session_losses[broker] if not l['recovered']]
        
        remaining = recovered_amount
        for loss in unrecovered:
            if remaining >= loss['amount']:
                loss['recovered'] = True
                remaining -= loss['amount']
            else:
                break
    
    def get_trading_plan(self,
                        coinbase_account: AccountState,
                        ibkr_account: AccountState) -> Dict[str, Any]:
        """
        Generate comprehensive trading plan for current session
        
        Returns:
            {
                'session': str,
                'should_trade': bool,
                'max_positions': int,
                'strategies': [str],
                'instruments': [str],
                'coinbase': {
                    'allocation_pct': float,
                    'max_positions': int,
                    'needs_hedge': bool,
                    'hedge_details': {}
                },
                'ibkr': {
                    'allocation_pct': float,
                    'max_positions': int,
                    'needs_hedge': bool,
                    'hedge_details': {}
                },
                'risk_notes': [str]
            }
        """
        config = self.get_session_config()
        session = self.get_current_session()
        
        # Check hedge needs
        coinbase_hedge = self.should_hedge('coinbase', coinbase_account)
        ibkr_hedge = self.should_hedge('ibkr', ibkr_account)
        
        # Calculate position allocation
        coinbase_positions = int(config.max_positions * config.coinbase_allocation)
        ibkr_positions = int(config.max_positions * config.ibkr_allocation)
        
        plan = {
            'session': session.value,
            'session_description': self._get_session_description(session),
            'should_trade': self.should_trade_now(),
            'max_positions': config.max_positions,
            'strategies': config.preferred_strategies,
            'instruments': config.preferred_instruments,
            'risk_multiplier': config.risk_multiplier,
            
            'coinbase': {
                'allocation_pct': config.coinbase_allocation * 100,
                'max_positions': coinbase_positions,
                'needs_hedge': coinbase_hedge['should_hedge'],
                'hedge_details': coinbase_hedge if coinbase_hedge['should_hedge'] else None
            },
            
            'ibkr': {
                'allocation_pct': config.ibkr_allocation * 100,
                'max_positions': ibkr_positions,
                'needs_hedge': ibkr_hedge['should_hedge'],
                'hedge_details': ibkr_hedge if ibkr_hedge['should_hedge'] else None
            },
            
            'risk_notes': self._generate_risk_notes(config, coinbase_hedge, ibkr_hedge)
        }
        
        return plan
    
    def _get_session_description(self, session: TradingSession) -> str:
        """Get human-readable session description"""
        descriptions = {
            TradingSession.LONDON: "London Session (07:00-16:00 UTC) - High volume, trending markets, forex/crypto active",
            TradingSession.NY: "New York Session (13:00-21:00 UTC) - Highest volume, volatility peaks, all markets active",
            TradingSession.OVERLAP: "OVERLAP PERIOD (13:00-16:00 UTC) - MAXIMUM LIQUIDITY - London+NY combined, best execution, highest opportunity",
            TradingSession.ASIA: "Asia Session (00:00-08:00 UTC) - Low volume, range-bound, forex only",
            TradingSession.OFF_HOURS: "Off Hours - Minimal trading, high risk"
        }
        return descriptions.get(session, "Unknown session")
    
    def _generate_risk_notes(self,
                            config: SessionConfig,
                            coinbase_hedge: Dict,
                            ibkr_hedge: Dict) -> List[str]:
        """Generate risk management notes for the plan"""
        notes = []
        
        # Session risk
        if config.session == TradingSession.OVERLAP:
            notes.append("🔥 OVERLAP PERIOD: Maximum aggression, 50% higher risk, peak opportunity window")
        elif config.session in [TradingSession.LONDON, TradingSession.NY]:
            notes.append(f"✅ Active session: {config.risk_multiplier:.0%} risk multiplier applied")
        else:
            notes.append("⚠️ Low activity session: Reduced risk, minimal positions")
        
        # Hedging status
        if coinbase_hedge['should_hedge']:
            notes.append(f"🛡️ Coinbase hedge needed: {coinbase_hedge['reason']}")
        if ibkr_hedge['should_hedge']:
            notes.append(f"🛡️ IBKR hedge needed: {ibkr_hedge['reason']}")
        
        if not coinbase_hedge['should_hedge'] and not ibkr_hedge['should_hedge']:
            notes.append("✅ No hedging required - both brokers performing well")
        
        # Position allocation
        notes.append(f"📊 Coinbase: {config.coinbase_allocation:.0%} allocation, IBKR: {config.ibkr_allocation:.0%}")
        
        return notes


def get_session_orchestrator(compounding_engine: ExtremeCompoundingEngine,
                             zombie_killer: ZombieTradeKiller) -> SessionOrchestrator:
    """Factory function to create session orchestrator"""
    return SessionOrchestrator(compounding_engine, zombie_killer)
