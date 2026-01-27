#!/usr/bin/env python3
"""
RICK BATTLESTATION - Unified Trading Command Center
Integrates: Dual-broker execution + Entry gates + Guardian safety + Progression + Voice + Adaptive AI

Architecture:
- Dual-broker trading: Coinbase (real $5-10 nano-lots) + IBKR (paper $1M)
- Crypto entry gates: 90% AI hive consensus, time windows, volatility sizing, 4/5 confluence
- Guardian gates: Margin <35%, max 3 positions, correlation checks
- 5-phase autonomous progression: NANO → SCALED → LOW_LEV → MID_LEV → HIGH_LEV
- Trailing stops: 2% initial, 1.5% activation, 1% trail distance
- Real-time dashboard: WebSocket stream to Node.js tmux_server
- Voice narration: Text-to-speech announcements for trades/phases
- Adaptive AI: ML learning system records outcomes, adapts parameters

PIN: 841921 | Charter Compliant | Battle-tested architecture
"""

import os
import sys
import json
import time
import signal
import logging
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

# Import RICK components
from rick_hive.crypto_entry_gate_system import CryptoEntryGateSystem, CryptoEntryGateResult
from rick_hive.guardian_gates import GuardianGates, GateResult
from rick_hive.adaptive_rick import AdaptiveRick, TradingDecision
from rick_hive.rick_hive_mind import RickHiveMind, HiveAnalysis

# Import trading components
from MULTI_BROKER_PHOENIX.multi_broker_phoenix.brokers.coinbase_safe_connector import CoinbaseSafeConnector
from MULTI_BROKER_PHOENIX.multi_broker_phoenix.foundation.progression_manager import ProgressionManager
from MULTI_BROKER_PHOENIX.multi_broker_phoenix.foundation.market_sessions import MarketSession
from MULTI_BROKER_PHOENIX.multi_broker_phoenix.foundation.position_narrator import LivePositionNarrator
from MULTI_BROKER_PHOENIX.multi_broker_phoenix.strategies.unified_hive_scanner import UnifiedScanner

# Add hive_real to path for AI Hive
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "hive_real"))
try:
    from api_ai_hive import APIAIHive
    HIVE_AVAILABLE = True
except ImportError:
    HIVE_AVAILABLE = False
    logger.warning("⚠️  AI Hive not available - will run strategies only")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler('logs/rick_battlestation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Ensure logs directory exists
Path("logs").mkdir(exist_ok=True)

@dataclass
class BattlestationStatus:
    """Complete system status for dashboard streaming"""
    timestamp: str
    phase: str
    capital: float
    total_pnl: float
    daily_pnl: float
    open_positions: List[Dict]
    win_rate: float
    profit_factor: float
    total_trades: int
    trailing_stops_active: int
    entry_gates_status: str
    guardian_gates_status: str
    adaptive_ai_learning: bool
    voice_enabled: bool
    session: str

class RickBattlestation:
    """
    Unified RICK Trading Battlestation
    Combines all systems into single coordinated command center
    """
    
    def __init__(self, pin: int = 841921):
        """Initialize all battlestation components with PIN verification"""
        if pin != 841921:
            raise PermissionError("Invalid PIN - Charter enforcement required")
        
        logger.info("="* 80)
        logger.info("🚀 RICK BATTLESTATION INITIALIZING")
        logger.info("="* 80)
        
        self.pin = pin
        self.running = False
        self.shutdown_requested = False
        
        # Initialize market session detector FIRST
        self.market_session = MarketSession()
        logger.info("✅ Market Session Detector: Active")
        
        # Display current market status
        session_status = self.market_session.get_session_status_display()
        print(session_status)
        
        # Initialize all components
        logger.info("📊 Initializing components...")
        
        # 1. Entry gates system (90% crypto consensus, time windows, volatility sizing)
        self.entry_gates = CryptoEntryGateSystem(pin=pin)
        logger.info("✅ Crypto Entry Gates: 90% consensus threshold")
        
        # 2. Guardian gates (margin, position limits, correlation)
        self.guardian_gates = GuardianGates(pin=pin)
        logger.info("✅ Guardian Gates: 35% max margin, 3 max positions")
        
        # 3. Adaptive AI learning system
        self.adaptive_ai = AdaptiveRick(pin=pin)
        logger.info("✅ Adaptive AI: ML learning enabled")
        
        # 4. Hive mind multi-AI system
        self.hive_mind = RickHiveMind(pin=pin)
        logger.info("✅ Hive Mind: Multi-AI delegation ready")
        
        # 5. Live position narrator (ticket numbers, SL tracking, trailing updates)
        self.narrator = LivePositionNarrator()
        logger.info("✅ Position Narrator: Real-time trade narration active")
        
        # 6. Coinbase safe connector (nano-lots, trailing stops)
        self.coinbase = CoinbaseSafeConnector(narrator=self.narrator)
        logger.info("✅ Coinbase Connector: Nano-lots ($5-10), trailing stops active")
        
        # 7. Progression manager (5-phase autonomous system)
        self.progression = ProgressionManager()
        phase_name = self.progression.PHASES[self.progression.current_phase].name
        logger.info(f"✅ Progression Manager: Phase {self.progression.current_phase} ({phase_name}), ${self.progression.stats.current_capital:.2f}")
        
        # 8. AI Hive connector (Oracle, Tactician, Analyst)
        self.hive_connector = None
        if HIVE_AVAILABLE:
            try:
                self.hive_connector = APIAIHive()
                logger.info("✅ AI Hive: 3 agents active (Oracle, Tactician, Analyst)")
                logger.info("   • Oracle: Fundamental & sentiment analysis")
                logger.info("   • Tactician: Technical analysis & chart patterns")
                logger.info("   • Analyst: Statistical & quantitative analysis")
            except Exception as e:
                logger.warning(f"⚠️  AI Hive initialization failed: {e}")
        else:
            logger.info("ℹ️  AI Hive: Disabled (strategies only mode)")
        
        # 9. Unified scanner (strategies + AI hive deep analysis)
        self.unified_scanner = UnifiedScanner(hive_connector=self.hive_connector)
        logger.info("✅ Unified Scanner: Multi-strategy + AI Hive collaboration")
        
        # 10. WebSocket server for dashboard (will be started separately)
        self.dashboard_ws = None
        self.dashboard_clients = []
        logger.info("📡 Dashboard WebSocket: Ready for connection")
        
        # 11. Voice narrator (browser-side, status only)
        self.voice_enabled = True
        logger.info("🎤 Voice Narrator: Enabled")
        
        # Autonomous scanning configuration
        self.scan_interval = 45  # seconds between scans
        self.last_scan_time = 0
        
        # Status tracking
        self.last_status_log = time.time()
        self.status_log_interval = 60  # seconds
        
        # Signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info("=" * 80)
        logger.info("✅ RICK BATTLESTATION READY FOR COMBAT")
        logger.info("=" * 80)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.warning(f"⚠️  Shutdown signal received: {signum}")
        self.shutdown_requested = True
    
    async def check_entry_gates(self, signal: Dict) -> Tuple[bool, Optional[CryptoEntryGateResult]]:
        """
        Validate signal through crypto entry gate system
        
        Args:
            signal: Trading signal with symbol, side, price, hive_consensus
            
        Returns:
            (approved: bool, gate_result: CryptoEntryGateResult)
        """
        symbol = signal.get('symbol', '')
        side = signal.get('side', '')
        hive_consensus = signal.get('hive_consensus', 0.85)
        
        # Run through entry gate system
        gate_result = self.entry_gates.evaluate_full_entry_gate(
            symbol=symbol,
            side=side,
            current_price=signal.get('price', 0),
            hive_consensus=hive_consensus,
            volatility_pct=signal.get('volatility', 1.5),
            current_time=datetime.now()
        )
        
        approved = gate_result.overall_result == "APPROVED"
        
        if approved:
            logger.info(f"✅ Entry Gates APPROVED: {symbol} {side}")
            logger.info(f"   Position size: ${gate_result.final_position_size:.2f}")
        else:
            logger.warning(f"❌ Entry Gates REJECTED: {symbol} {side}")
            for reason in gate_result.rejection_reasons:
                logger.warning(f"   - {reason}")
        
        return approved, gate_result
    
    def check_guardian_gates(self, signal: Dict) -> Tuple[bool, List[GateResult]]:
        """
        Pre-trade guardian gate validation
        
        Args:
            signal: Trading signal with symbol, side, units
            
        Returns:
            (all_passed: bool, results: List[GateResult])
        """
        # Get current account state
        account_info = self.coinbase.get_account_info()
        open_positions = self.coinbase.get_open_positions()
        
        account = {
            'nav': account_info.get('total_value', 0),
            'margin_used': sum(p.get('value', 0) for p in open_positions),
            'margin_available': account_info.get('available_balance', 0)
        }
        
        # Run guardian gates
        all_passed, results = self.guardian_gates.validate_all(
            signal=signal,
            account=account,
            positions=open_positions
        )
        
        if all_passed:
            logger.info("✅ Guardian Gates: All checks passed")
        else:
            logger.warning("⚠️  Guardian Gates: Some checks failed")
            for result in results:
                if not result.passed:
                    logger.warning(f"   ❌ {result.gate_name}: {result.reason}")
        
        return all_passed, results
    
    async def process_signal(self, signal: Dict) -> Optional[Dict]:
        """
        Process trading signal through full gate system
        
        Args:
            signal: Trading signal with symbol, side, price, confidence, etc.
            
        Returns:
            Trade result dict if executed, None if rejected
        """
        symbol = signal['symbol']
        side = signal['side']
        
        logger.info(f"📊 Processing signal: {symbol} {side}")
        
        # Step 1: Get hive mind consensus (multi-AI analysis)
        market_data = {
            'symbol': symbol,
            'price': signal.get('price', 0),
            'volatility': signal.get('volatility', 1.5)
        }
        hive_analysis = self.hive_mind.delegate_analysis(market_data)
        signal['hive_consensus'] = hive_analysis.consensus_confidence
        
        logger.info(f"🧠 Hive Mind: {hive_analysis.consensus_confidence:.1%} consensus")
        
        # Step 2: Entry gates validation
        entry_approved, entry_result = await self.check_entry_gates(signal)
        if not entry_approved:
            return None
        
        # Update position size from entry gates
        signal['position_size_usd'] = entry_result.final_position_size
        
        # Step 3: Guardian gates validation
        guardian_approved, guardian_results = self.check_guardian_gates(signal)
        if not guardian_approved:
            return None
        
        # Step 4: Execute trade through Coinbase
        logger.info(f"🎯 Executing {symbol} {side} with ${signal['position_size_usd']:.2f}")
        
        try:
            # Open position with trailing stop
            position = self.coinbase.open_position(
                symbol=symbol,
                side=side,
                size_usd=signal['position_size_usd'],
                current_price=signal['price']
            )
            
            if position:
                logger.info(f"✅ Position opened: {position['position_id']}")
                
                # ★ NARRATOR: Announce new position with ticket and initial SL
                self.narrator.narrate_new_position(
                    ticket=position['position_id'],
                    symbol=symbol,
                    side=side,
                    entry_price=signal['price'],
                    size=position.get('size', signal['position_size_usd']),
                    initial_sl=position.get('stop_loss', signal['price'] * 0.98 if side == 'BUY' else signal['price'] * 1.02)
                )
                
                # Record decision in adaptive AI
                decision = TradingDecision(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    symbol=symbol,
                    action=side,
                    confidence=signal['hive_consensus'],
                    reasoning=f"Hive consensus {signal['hive_consensus']:.1%}, gates passed",
                    ml_factors={
                        'hive_confidence': signal['hive_consensus'],
                        'entry_gate_score': len(entry_result.approvals) / 5.0,
                        'guardian_gate_score': sum(r.passed for r in guardian_results) / len(guardian_results)
                    }
                )
                self.adaptive_ai.record_decision(decision)
                
                # Broadcast to dashboard
                await self.broadcast_trade_event({
                    'type': 'trade_opened',
                    'symbol': symbol,
                    'side': side,
                    'size': signal['position_size_usd'],
                    'price': signal['price'],
                    'position_id': position['position_id'],
                    'voice_text': f"Entering {symbol}. Position locked and loaded."
                })
                
                return position
            
        except Exception as e:
            logger.error(f"❌ Trade execution failed: {e}")
            return None
    
    async def monitor_positions(self):
        """Monitor open positions and update trailing stops"""
        while self.running and not self.shutdown_requested:
            try:
                # Update trailing stops (method fetches prices internally)
                triggered_stops = self.coinbase.update_trailing_stops()
                
                # Handle triggered stops
                for stop in triggered_stops:
                    logger.info(f"🛑 Trailing stop triggered: {stop['symbol']} at ${stop['exit_price']:.2f}")
                    
                    # Close position
                    result = self.coinbase.close_position(
                        position_id=stop['position_id'],
                        exit_price=stop['exit_price'],
                        reason="Trailing stop"
                    )
                    
                    if result:
                        pnl = result['pnl']
                        
                        # ★ NARRATOR: Announce position close
                        self.narrator.narrate_position_close(
                            ticket=stop['position_id'],
                            exit_price=stop['exit_price'],
                            realized_pnl=pnl,
                            reason="Trailing stop triggered"
                        )
                        
                        # Record in progression manager
                        self.progression.record_trade(
                            symbol=stop['symbol'],
                            pnl=pnl,
                            win=pnl > 0
                        )
                        
                        # Check for phase graduation
                        if self.progression.stats.graduated:
                            phase_name = self.progression.PHASES[self.progression.current_phase].name
                            logger.info(f"🎓 GRADUATED TO PHASE {self.progression.current_phase} ({phase_name})!")
                            await self.broadcast_trade_event({
                                'type': 'phase_graduation',
                                'new_phase': self.progression.current_phase,
                                'voice_text': f"Phase graduation achieved. Welcome to phase {self.progression.current_phase}."
                            })
                        
                        # Broadcast to dashboard
                        await self.broadcast_trade_event({
                            'type': 'trade_closed',
                            'symbol': stop['symbol'],
                            'pnl': pnl,
                            'reason': 'Trailing stop',
                            'voice_text': f"{stop['symbol']} closed. P and L: {'profit' if pnl > 0 else 'loss'} {abs(pnl):.2f} dollars."
                        })
                
                # Log status periodically
                if time.time() - self.last_status_log > self.status_log_interval:
                    await self.log_status()
                    self.last_status_log = time.time()
                
                await asyncio.sleep(2)  # Check every 2 seconds
                
            except Exception as e:
                logger.error(f"Error in position monitoring: {e}")
                await asyncio.sleep(5)
    
    async def log_status(self):
        """Log current battlestation status"""
        stats = self.progression.stats
        positions = self.coinbase.get_open_positions()
        
        logger.info("=" * 80)
        logger.info("📊 RICK BATTLESTATION STATUS")
        logger.info("=" * 80)
        phase_name = self.progression.PHASES[self.progression.current_phase].name
        logger.info(f"Phase: {self.progression.current_phase} ({phase_name})")
        logger.info(f"Capital: ${stats.current_capital:.2f}")
        logger.info(f"Total P&L: ${stats.net_profit:.2f}")
        logger.info(f"Win Rate: {stats.win_rate:.1%}")
        logger.info(f"Profit Factor: {stats.profit_factor:.2f}")
        logger.info(f"Total Trades: {stats.total_trades}")
        logger.info(f"Open Positions: {len(positions)}")
        
        # Broadcast to dashboard
        phase_name = self.progression.PHASES[self.progression.current_phase].name
        status = BattlestationStatus(
            timestamp=datetime.now(timezone.utc).isoformat(),
            phase=f"{self.progression.current_phase}_{phase_name}",
            capital=stats.current_capital,
            total_pnl=stats.net_profit,
            daily_pnl=0.0,  # TODO: Calculate daily P&L
            open_positions=[
                {
                    'symbol': p['symbol'],
                    'side': p['side'],
                    'entry_price': p['entry_price'],
                    'size': p['size'],
                    'pnl': p.get('unrealized_pnl', 0)
                }
                for p in positions
            ],
            win_rate=stats.win_rate,
            profit_factor=stats.profit_factor,
            total_trades=stats.total_trades,
            trailing_stops_active=len(positions),
            entry_gates_status="ACTIVE",
            guardian_gates_status="ACTIVE",
            adaptive_ai_learning=True,
            voice_enabled=self.voice_enabled,
            session="CRYPTO_24/7"
        )
        
        await self.broadcast_status(status)
    
    async def autonomous_scan_and_execute(self):
        """
        Autonomous scan across all symbols using unified scanner
        Generates signals from strategies + AI Hive, executes approved trades
        """
        try:
            # Get active symbols from environment
            symbols_str = os.getenv('FEED_SYMBOLS', 'EUR_USD,GBP_USD,BTC-USD,ETH-USD')
            all_symbols = [s.strip() for s in symbols_str.split(',')]
            
            # Filter to only tradeable markets (session-aware)
            tradeable_symbols = self.market_session.filter_symbols_by_session(all_symbols)
            
            if not tradeable_symbols:
                logger.warning("⚠️  No markets currently open - skipping scan")
                return
            
            # Get market info for display
            market_info = self.market_session.get_tradeable_instruments_count(all_symbols)
            logger.info(f"🔎 Scanning {len(tradeable_symbols)}/{len(all_symbols)} symbols (only open markets)")
            logger.info(f"   📊 Forex: {market_info['forex']} | ₿ Crypto: {market_info['crypto']} | 📈 Futures: {market_info['futures']}")
            
            # Prepare market data (simplified for now)
            market_data = {
                'timestamp': datetime.now().isoformat(),
                'session': 'AUTO_DETECT',
                'volatility': 'NORMAL'
            }
            
            # Run unified scan (strategies + AI Hive)
            scan_response = await self.unified_scanner.unified_scan(tradeable_symbols, market_data)
            scan_results = scan_response.get('unified_recommendations', [])
            
            if not scan_results:
                logger.info("\u2139\ufe0f No high-quality signals found this scan")
                return
            
            logger.info(f"\ud83c\udfaf Found {len(scan_results)} potential signals")
            
            # Process top signals
            for i, result in enumerate(scan_results[:3], 1):  # Top 3 signals max per scan
                signal = {
                    'symbol': result.symbol,
                    'side': result.side,
                    'strategy': result.strategy_name,
                    'price': result.entry_price,
                    'confidence': result.confidence,
                    'quality_score': result.quality_score,
                    'hive_consensus': result.hive_scan.overall_quality if result.hive_scan else 0.85,
                    'volatility': 1.5,  # TODO: Get from market data
                    'tier': result.tier,
                    'target': result.take_profit,
                    'stop': result.stop_loss
                }
                
                logger.info(f"")
                logger.info(f"📨 Signal #{i}: {result.symbol} {result.side}")
                logger.info(f"   Strategy: {result.strategy_name}")
                logger.info(f"   Quality: {result.quality_score:.2f} | Tier: {result.tier}")
                logger.info(f"   Confidence: {result.confidence:.1%}")
                
                # Execute through battlestation gates
                trade_result = await self.execute_signal(signal)
                
                if trade_result:
                    logger.info(f"✅ Trade executed: {trade_result.get('order_id', 'N/A')}")
                else:
                    logger.info(f"❌ Trade rejected by gates")
                
                await asyncio.sleep(2)  # Brief pause between executions
                
        except Exception as e:
            logger.error(f"❌ Scan error: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _log_status(self):
        """Log current battlestation status"""
        stats = self.progression.stats
        phase = self.progression.current_phase
        phase_name = self.progression.PHASES[phase].name
        
        logger.info("="*60)
        logger.info(f"📊 BATTLESTATION STATUS | Phase {phase} ({phase_name})")
        logger.info(f"   Capital: ${stats.current_capital:.2f} | Trades: {stats.total_trades}")
        logger.info(f"   Win Rate: {stats.win_rate:.1f}% | PF: {stats.profit_factor:.2f}")
        logger.info(f"   ROI: {stats.roi_pct:.1f}% | Drawdown: {stats.max_drawdown_pct:.1f}%")
        logger.info("="*60)
    
    async def broadcast_status(self, status: BattlestationStatus):
        """Broadcast status to dashboard WebSocket clients"""
        if self.dashboard_clients:
            message = {
                'type': 'status_update',
                'data': asdict(status)
            }
            # TODO: Implement WebSocket broadcast
            # for client in self.dashboard_clients:
            #     await client.send(json.dumps(message))
    
    async def broadcast_trade_event(self, event: Dict):
        """Broadcast trade event to dashboard with voice trigger"""
        logger.info(f"📡 Broadcasting: {event['type']}")
        
        if self.dashboard_clients:
            # TODO: Implement WebSocket broadcast
            # for client in self.dashboard_clients:
            #     await client.send(json.dumps(event))
            pass
    
    async def run(self):
        """Main battlestation execution loop with autonomous scanning"""
        self.running = True
        logger.info("🚀 RICK BATTLESTATION STARTED - AUTONOMOUS MODE")
        logger.info(f"📡 Scanning every {self.scan_interval}s for OANDA forex + Coinbase crypto")
        
        # Start position monitoring
        monitor_task = asyncio.create_task(self.monitor_positions())
        
        try:
            # Main autonomous scanning loop
            while self.running and not self.shutdown_requested:
                current_time = time.time()
                
                # Check if it's time to scan
                if current_time - self.last_scan_time >= self.scan_interval:
                    logger.info("🔍 Starting unified scan...")
                    await self.autonomous_scan_and_execute()
                    self.last_scan_time = current_time
                
                # Status logging
                if current_time - self.last_status_log >= self.status_log_interval:
                    self._log_status()
                    self.last_status_log = current_time
                
                await asyncio.sleep(5)  # Check every 5 seconds
                
        except Exception as e:
            logger.error(f"❌ Fatal error: {e}")
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Graceful shutdown of all battlestation components"""
        logger.info("🛑 RICK BATTLESTATION SHUTTING DOWN...")
        self.running = False
        
        # Close all positions
        positions = self.coinbase.get_open_positions()
        if positions:
            logger.info(f"Closing {len(positions)} open positions...")
            for pos in positions:
                current_price = self.coinbase.fetch_live_price(pos['symbol'])
                self.coinbase.close_position(
                    position_id=pos['position_id'],
                    exit_price=current_price,
                    reason="System shutdown"
                )
        
        # Disconnect broker
        self.coinbase.disconnect()
        
        # Save final state
        self.progression.save_state()
        
        logger.info("✅ RICK BATTLESTATION SHUTDOWN COMPLETE")
        logger.info("=" * 80)


async def main():
    """Main entry point"""
    battlestation = RickBattlestation(pin=841921)
    await battlestation.run()


if __name__ == "__main__":
    asyncio.run(main())
