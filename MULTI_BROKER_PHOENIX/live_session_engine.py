#!/usr/bin/env python3
"""
LIVE SESSION ENGINE
NYC/London session-aware trading with cross-broker hedging and loss recovery

FEATURES:
✅ Session-aware trading (London/NY/Overlap prioritization)
✅ Cross-broker hedging (Coinbase ↔ IBKR)
✅ Automatic loss recovery with inverse positions
✅ Peak aggression during overlap period (13:00-16:00 UTC)
✅ Smart capital allocation by session
✅ Extreme compounding with Kelly Criterion
✅ Zombie trade killing

SCHEDULE:
- London: 07:00-16:00 UTC (4 positions, 60% IBKR/40% Coinbase)
- NY: 13:00-21:00 UTC (5 positions, 50/50 split)
- OVERLAP: 13:00-16:00 UTC (7 positions, MAXIMUM AGGRESSION, 50% risk boost)
- Asia/Off: Minimal/no trading
"""
import os
import sys
import time
import logging
from datetime import datetime
from typing import Dict, List, Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from multi_broker_phoenix.strategies.base import get_strategy
from multi_broker_phoenix.engines.extreme_compounding_engine import ExtremeCompoundingEngine, AccountState
from multi_broker_phoenix.engines.zombie_trade_killer import ZombieTradeKiller
from multi_broker_phoenix.engines.session_orchestrator import SessionOrchestrator, TradingSession
from multi_broker_phoenix.brokers.coinbase_advanced_connector import CoinbaseAdvancedTradeConnector
from multi_broker_phoenix.brokers.ibkr_connector import IBKRConnector

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('live_session_engine.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class LiveSessionEngine:
    """
    Production trading engine with session awareness and cross-broker hedging
    """
    
    def __init__(self):
        # Initialize extreme systems
        self.compounding = ExtremeCompoundingEngine(
            base_risk_pct=4.0,  # 4% base (EXTREME)
            max_leverage=5.0,
            kelly_fraction=0.75
        )
        
        self.zombie_killer = ZombieTradeKiller(
            max_stagnant_bars=25,
            signal_fade_threshold=0.4,
            zombie_profit_threshold=-1.0
        )
        
        # Session orchestrator
        self.orchestrator = SessionOrchestrator(self.compounding, self.zombie_killer)
        
        # Broker connections
        self.connectors = {
            'coinbase': CoinbaseAdvancedTradeConnector(),
            'ibkr': IBKRConnector()
        }
        
        # Account states
        self.accounts = {}
        
        # Active positions by broker
        self.positions = {
            'coinbase': {},
            'ibkr': {}
        }
        
        logger.info("🚀 LiveSessionEngine initialized")
        logger.info("   ✅ Session-aware trading (London/NY/Overlap)")
        logger.info("   ✅ Cross-broker hedging enabled")
        logger.info("   ✅ Extreme compounding active (4% base, 0.75 Kelly)")
    
    def initialize_accounts(self):
        """Fetch account balances"""
        for broker_name, connector in self.connectors.items():
            try:
                balance = connector.get_account_balance()
                self.accounts[broker_name] = AccountState(
                    starting_balance=balance,
                    current_balance=balance,
                    peak_balance=balance,
                    drawdown_pct=0.0,
                    consecutive_wins=0,
                    consecutive_losses=0,
                    win_rate_30d=0.50,
                    avg_win_pct=2.0,
                    avg_loss_pct=1.0
                )
                logger.info(f"✅ {broker_name}: ${balance:,.2f}")
            except Exception as e:
                logger.error(f"❌ {broker_name} failed: {e}")
    
    def display_session_status(self):
        """Display current session and trading plan"""
        plan = self.orchestrator.get_trading_plan(
            self.accounts.get('coinbase'),
            self.accounts.get('ibkr')
        )
        
        logger.info(f"\n{'='*80}")
        logger.info(f"📅 {plan['session_description']}")
        logger.info(f"{'='*80}")
        logger.info(f"Trading Active: {plan['should_trade']}")
        logger.info(f"Max Positions: {plan['max_positions']}")
        logger.info(f"Risk Multiplier: {plan['risk_multiplier']:.1f}x")
        logger.info(f"Strategies: {', '.join(plan['strategies'])}")
        logger.info(f"Instruments: {', '.join(plan['instruments'][:5])}...")
        
        logger.info(f"\n📊 Coinbase: {plan['coinbase']['allocation_pct']:.0f}% allocation, {plan['coinbase']['max_positions']} max positions")
        if plan['coinbase']['needs_hedge']:
            logger.info(f"   🛡️ HEDGE NEEDED: {plan['coinbase']['hedge_details']['reason']}")
        
        logger.info(f"📊 IBKR: {plan['ibkr']['allocation_pct']:.0f}% allocation, {plan['ibkr']['max_positions']} max positions")
        if plan['ibkr']['needs_hedge']:
            logger.info(f"   🛡️ HEDGE NEEDED: {plan['ibkr']['hedge_details']['reason']}")
        
        logger.info(f"\n📝 Risk Notes:")
        for note in plan['risk_notes']:
            logger.info(f"   {note}")
        
        logger.info(f"{'='*80}\n")
    
    def execute_hedge(self, broker: str, hedge_details: Dict[str, Any]):
        """Execute hedge position to recover losses"""
        hedge_broker = hedge_details['hedge_broker']
        hedge_instrument = hedge_details['hedge_instrument']
        hedge_size_pct = hedge_details['hedge_size_pct']
        
        account = self.accounts[hedge_broker]
        connector = self.connectors[hedge_broker]
        
        # Calculate hedge position size
        hedge_value = account.current_balance * (hedge_size_pct / 100.0)
        
        try:
            # Get current price
            current_price = connector.get_current_price(hedge_instrument)
            quantity = hedge_value / current_price
            
            # Place hedge order (SELL for inverse correlation)
            order = connector.place_order(
                symbol=hedge_instrument,
                side='SELL',  # Inverse position
                quantity=quantity,
                order_type='MARKET'
            )
            
            # Track hedge position
            position_key = f"HEDGE_{hedge_instrument}"
            self.positions[hedge_broker][position_key] = {
                'broker': hedge_broker,
                'symbol': hedge_instrument,
                'entry_price': current_price,
                'quantity': quantity,
                'side': 'SELL',
                'is_hedge': True,
                'recovering_for': broker,
                'target_recovery': hedge_details['target_recovery'],
                'entry_time': time.time()
            }
            
            logger.info(f"🛡️ HEDGE EXECUTED: {hedge_broker} {hedge_instrument} SELL {quantity:.4f} @ {current_price:.2f}")
            logger.info(f"   Recovering ${hedge_details['target_recovery']:.2f} for {broker}")
            
        except Exception as e:
            logger.error(f"❌ Hedge execution failed: {e}")
    
    def scan_opportunities(self, broker: str, plan: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Scan for opportunities based on session plan"""
        opportunities = []
        
        broker_plan = plan[broker]
        if not plan['should_trade']:
            return opportunities
        
        connector = self.connectors[broker]
        account = self.accounts[broker]
        
        # Get instruments for this broker/session
        instruments = plan['instruments'][:10]
        
        for instrument in instruments:
            try:
                # Get price data
                prices = connector.get_historical_prices(instrument, bars=100)
                
                # Test each strategy
                for strategy_name in plan['strategies']:
                    strategy = get_strategy(strategy_name)
                    if not strategy:
                        continue
                    
                    candidate = strategy.generate_candidate({
                        'symbol': instrument,
                        'platform': broker.upper(),
                        'prices': prices
                    })
                    
                    if candidate:
                        # Calculate session-aware position size
                        sizing = self.orchestrator.calculate_position_size(
                            broker=broker,
                            account=account,
                            signal_strength=0.75,
                            instrument=instrument
                        )
                        
                        opportunities.append({
                            'broker': broker,
                            'symbol': instrument,
                            'strategy': strategy_name,
                            'candidate': candidate,
                            'sizing': sizing,
                            'expected_value': sizing['risk_pct'] * 0.75,
                            'session_priority': 1.0 if plan['session'] == 'overlap' else 0.8
                        })
            
            except Exception as e:
                logger.warning(f"Scan failed: {broker} {instrument} - {e}")
        
        # Sort by EV * session priority
        opportunities.sort(key=lambda x: x['expected_value'] * x['session_priority'], reverse=True)
        return opportunities
    
    def execute_opportunity(self, opp: Dict[str, Any]):
        """Execute a trade opportunity"""
        broker = opp['broker']
        connector = self.connectors[broker]
        account = self.accounts[broker]
        
        position_value = account.current_balance * (opp['sizing']['risk_pct'] / 100.0)
        
        try:
            order = connector.place_order(
                symbol=opp['symbol'],
                side=opp['candidate'].side,
                quantity=position_value / opp['candidate'].entry_price,
                order_type='MARKET'
            )
            
            self.zombie_killer.register_trade(
                f"{broker}:{opp['symbol']}",
                opp['candidate'].entry_price,
                0.75
            )
            
            position_key = f"{broker}:{opp['symbol']}"
            self.positions[broker][position_key] = {
                'broker': broker,
                'symbol': opp['symbol'],
                'strategy': opp['strategy'],
                'entry_price': opp['candidate'].entry_price,
                'stop_loss': opp['candidate'].stop_loss,
                'side': opp['candidate'].side,
                'quantity': position_value / opp['candidate'].entry_price,
                'sizing': opp['sizing'],
                'entry_time': time.time(),
                'bars_held': 0,
                'is_hedge': False
            }
            
            logger.info(f"✅ EXECUTED: {position_key} {opp['candidate'].side} @ {opp['candidate'].entry_price:.4f}")
            logger.info(f"   Risk: {opp['sizing']['risk_pct']:.2f}% | Leverage: {opp['sizing']['leverage']:.1f}x | Session: {opp['sizing']['session']}")
            
        except Exception as e:
            logger.error(f"❌ Execution failed: {broker} {opp['symbol']} - {e}")
    
    def monitor_positions(self, plan: Dict[str, Any]):
        """Monitor and manage active positions"""
        for broker, positions in self.positions.items():
            account = self.accounts[broker]
            connector = self.connectors[broker]
            
            for pos_key, position in list(positions.items()):
                try:
                    current_price = connector.get_current_price(position['symbol'])
                    
                    # Calculate P&L
                    if position['side'] == 'BUY':
                        pnl_pct = ((current_price - position['entry_price']) / position['entry_price']) * 100
                    else:
                        pnl_pct = ((position['entry_price'] - current_price) / position['entry_price']) * 100
                    
                    # Apply leverage if present
                    if 'sizing' in position and 'leverage' in position['sizing']:
                        pnl_pct *= position['sizing']['leverage']
                    
                    # Check zombie status
                    opportunities = []
                    action = self.zombie_killer.update_trade(
                        pos_key,
                        current_price,
                        0.70,
                        opportunities
                    )
                    
                    # Exit conditions
                    should_exit = False
                    exit_reason = ""
                    
                    if action['action'] in ['CUT', 'REALLOCATE']:
                        should_exit = True
                        exit_reason = f"ZOMBIE: {action['reason']}"
                    elif position['side'] == 'BUY' and current_price <= position.get('stop_loss', 0):
                        should_exit = True
                        exit_reason = "STOP LOSS"
                    elif position['side'] == 'SELL' and current_price >= position.get('stop_loss', float('inf')):
                        should_exit = True
                        exit_reason = "STOP LOSS"
                    elif position['bars_held'] > 50:
                        should_exit = True
                        exit_reason = "MAX HOLD"
                    
                    # Exit if needed
                    if should_exit:
                        close_side = 'SELL' if position['side'] == 'BUY' else 'BUY'
                        connector.place_order(
                            symbol=position['symbol'],
                            side=close_side,
                            quantity=position['quantity'],
                            order_type='MARKET'
                        )
                        
                        # Update account
                        position_value = account.current_balance * (position.get('sizing', {}).get('risk_pct', 1.0) / 100.0)
                        pnl_dollars = position_value * (pnl_pct / 100.0)
                        account.current_balance += pnl_dollars
                        
                        # Track loss for hedging
                        if pnl_dollars < 0:
                            self.orchestrator.record_loss(broker, abs(pnl_dollars), position['symbol'])
                        
                        # Update streaks
                        if pnl_pct > 0:
                            account.consecutive_wins += 1
                            account.consecutive_losses = 0
                            
                            # Mark losses recovered if hedge
                            if position.get('is_hedge'):
                                recovering_for = position.get('recovering_for')
                                self.orchestrator.mark_loss_recovered(recovering_for, abs(pnl_dollars))
                        else:
                            account.consecutive_wins = 0
                            account.consecutive_losses += 1
                        
                        account.peak_balance = max(account.peak_balance, account.current_balance)
                        account.drawdown_pct = ((account.peak_balance - account.current_balance) / account.peak_balance) * 100
                        
                        logger.info(f"🔴 CLOSED: {pos_key} | P/L: {pnl_pct:+.2f}% (${pnl_dollars:+.2f}) | {exit_reason}")
                        
                        del self.positions[broker][pos_key]
                    else:
                        position['bars_held'] += 1
                
                except Exception as e:
                    logger.error(f"❌ Monitor failed: {pos_key} - {e}")
    
    def run(self, scan_interval: int = 60):
        """Main trading loop"""
        logger.info(f"\n{'='*80}")
        logger.info(f"🔥 LIVE SESSION ENGINE - STARTING")
        logger.info(f"{'='*80}\n")
        
        self.initialize_accounts()
        
        iteration = 0
        last_session = None
        
        while True:
            iteration += 1
            current_session = self.orchestrator.get_current_session()
            
            # Display session info if changed
            if current_session != last_session:
                self.display_session_status()
                last_session = current_session
            
            logger.info(f"\n--- ITERATION {iteration} ({current_session.value.upper()}) ---")
            
            try:
                # Get trading plan
                plan = self.orchestrator.get_trading_plan(
                    self.accounts.get('coinbase'),
                    self.accounts.get('ibkr')
                )
                
                # Monitor existing positions
                self.monitor_positions(plan)
                
                # Execute hedges if needed
                if plan['coinbase']['needs_hedge']:
                    self.execute_hedge('coinbase', plan['coinbase']['hedge_details'])
                if plan['ibkr']['needs_hedge']:
                    self.execute_hedge('ibkr', plan['ibkr']['hedge_details'])
                
                # Scan for new opportunities if room and session is active
                if plan['should_trade']:
                    for broker in ['coinbase', 'ibkr']:
                        current_positions = len(self.positions[broker])
                        max_positions = plan[broker]['max_positions']
                        
                        if current_positions < max_positions:
                            opportunities = self.scan_opportunities(broker, plan)
                            slots = max_positions - current_positions
                            
                            for opp in opportunities[:slots]:
                                self.execute_opportunity(opp)
                
                # Display status
                logger.info(f"Positions: Coinbase {len(self.positions['coinbase'])}, IBKR {len(self.positions['ibkr'])}")
                for broker, account in self.accounts.items():
                    logger.info(f"  {broker}: ${account.current_balance:,.2f} "
                              f"(Streak: {account.consecutive_wins}W/{account.consecutive_losses}L, "
                              f"DD: {account.drawdown_pct:.2f}%)")
                
                time.sleep(scan_interval)
                
            except KeyboardInterrupt:
                logger.info("\n🛑 Shutting down...")
                break
            except Exception as e:
                logger.error(f"❌ Loop error: {e}")
                time.sleep(scan_interval)


if __name__ == "__main__":
    engine = LiveSessionEngine()
    engine.run(scan_interval=60)
