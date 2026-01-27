#!/usr/bin/env python3
"""Dual-Broker Live Trading: Coinbase (Real) + IBKR (Paper)

Trades simultaneously on:
- Coinbase Advanced: REAL MONEY with nano-lots ($10 positions)
- IBKR Paper: FAKE MONEY ($1M paper account)

Both feed into single progression manager for unified tracking.
"""
import sys
import os
import time
import logging
import argparse
import signal
from datetime import datetime
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from multi_broker_phoenix.brokers.coinbase_safe_connector import CoinbaseSafeConnector
from multi_broker_phoenix.foundation.progression_manager import ProgressionManager

# Try to import IBKR (may fail if ib_insync not installed)
try:
    from multi_broker_phoenix.ibkr_gateway.ibkr_connector import IBKRLiveConnector
    IBKR_AVAILABLE = True
except ImportError:
    IBKR_AVAILABLE = False
    IBKRLiveConnector = None

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global shutdown flag
shutdown_requested = False


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    global shutdown_requested
    logger.info("\n⚠️  Shutdown requested - closing all positions...")
    shutdown_requested = True


signal.signal(signal.SIGINT, signal_handler)


class DualBrokerTrader:
    """Dual-broker live trading with unified progression."""
    
    def __init__(self, symbols: list[str], poll_seconds: float = 10.0, ibkr_enabled: bool = True):
        self.symbols = symbols
        self.poll_seconds = poll_seconds
        self.ibkr_enabled = ibkr_enabled and IBKR_AVAILABLE
        
        # Initialize Coinbase (LIVE)
        logger.info("🔧 Initializing Coinbase connector (LIVE MODE - REAL MONEY)...")
        self.coinbase = CoinbaseSafeConnector(paper_mode=False)
        
        # Initialize IBKR (PAPER) if available
        self.ibkr = None
        if self.ibkr_enabled:
            try:
                logger.info("🔧 Initializing IBKR connector (PAPER MODE - FAKE MONEY)...")
                self.ibkr = IBKRLiveConnector()
                logger.info("✅ IBKR connected (Paper Account)")
            except Exception as e:
                logger.warning(f"⚠️  IBKR connection failed: {e}")
                logger.info("   Continuing with Coinbase only...")
                self.ibkr = None
        else:
            logger.info("ℹ️  IBKR disabled or not available")
        
        # Initialize progression manager (unified for both brokers)
        logger.info("🎯 Initializing Progression Manager...")
        self.progression = ProgressionManager()
        
        # Status tracking
        self.last_status_time = time.time()
        self.status_interval = 60  # Log status every 60 seconds
        
    def log_startup_info(self):
        """Log configuration and current phase."""
        phase = self.progression.get_current_phase_config()
        
        logger.info("\n" + "="*80)
        logger.info("🚀 DUAL-BROKER LIVE TRADING STARTED")
        logger.info("="*80)
        logger.info(f"\n📊 Broker Configuration:")
        logger.info(f"   Coinbase: LIVE (REAL MONEY)")
        logger.info(f"   IBKR: {'PAPER (FAKE MONEY)' if self.ibkr else 'DISABLED'}")
        logger.info(f"\n📈 Phase Configuration:")
        logger.info(f"   Phase: {phase.name} (Phase {self.progression.current_phase})")
        logger.info(f"   Position Size: ${phase.position_size_usd}")
        logger.info(f"   Leverage: {phase.leverage}x")
        logger.info(f"   Capital: ${self.progression.stats.current_capital:.2f}")
        logger.info(f"\n🎯 Graduation Requirements:")
        logger.info(f"   Min Trades: {phase.min_trades}")
        logger.info(f"   Win Rate: {phase.min_win_rate_pct}%+")
        logger.info(f"   Profit Factor: {phase.min_profit_factor}+")
        logger.info(f"   ROI: {phase.min_roi_pct}%+")
        logger.info(f"   Max Drawdown: <{phase.max_drawdown_pct}%")
        logger.info(f"   Days Active: {phase.min_days_active}+")
        logger.info(f"\n🛡️ Safety Limits:")
        logger.info(f"   Daily Loss: $50 max")
        logger.info(f"   Daily Trades: 10 max")
        logger.info(f"   Stop Loss: 2% initial")
        logger.info(f"   Trailing: 1.5% activation, 1% trail")
        logger.info(f"   Consecutive Losses: 5 max")
        logger.info(f"\n📈 Watching: {', '.join(self.symbols)}")
        logger.info(f"   Poll Interval: {self.poll_seconds}s")
        logger.info("="*80 + "\n")
    
    def check_and_update_coinbase(self):
        """Monitor and update Coinbase positions."""
        triggered_stops = self.coinbase.update_trailing_stops()
        
        for stop in triggered_stops:
            symbol = stop['symbol']
            side = stop['side']
            entry = stop['entry_price']
            exit_price = stop.get('current_price', entry)
            
            # Calculate P&L
            if side in ('BUY', 'LONG'):
                pnl_pct = ((exit_price - entry) / entry) * 100
            else:
                pnl_pct = ((entry - exit_price) / entry) * 100
            
            phase = self.progression.get_current_phase_config()
            pnl_usd = (pnl_pct / 100) * phase.position_size_usd
            
            # Update capital and record trade
            new_capital = self.progression.stats.current_capital + pnl_usd
            progression_result = self.progression.record_trade(pnl_usd, new_capital)
            
            # Log result
            result_emoji = "📈" if pnl_usd > 0 else "📉"
            logger.info(f"{result_emoji} [COINBASE] {symbol} {side} closed: {pnl_pct:+.2f}% (${pnl_usd:+.2f})")
            logger.info(f"   Capital: ${new_capital:.2f}")
            
            # Check for graduation
            if progression_result.get('graduated'):
                new_phase = self.progression.get_current_phase_config()
                logger.info("\n" + "="*80)
                logger.info(f"🎓 GRADUATED TO PHASE {self.progression.current_phase}!")
                logger.info(f"   New Position Size: ${new_phase.position_size_usd}")
                logger.info(f"   New Leverage: {new_phase.leverage}x")
                if new_phase.leverage > 1:
                    logger.info(f"   🚀 FUTURES TRADING UNLOCKED")
                logger.info("="*80 + "\n")
            
            # Close position
            self.coinbase.close_position(symbol, exit_price, "trailing_stop")
    
    def check_and_update_ibkr(self):
        """Monitor and update IBKR positions (if enabled)."""
        if not self.ibkr:
            return
        
        # TODO: Implement IBKR position monitoring
        # For now, just placeholder
        pass
    
    def log_status(self):
        """Log periodic status update."""
        summary = self.progression.get_summary()
        stats = summary['stats']
        
        coinbase_positions = len(self.coinbase.get_open_positions())
        ibkr_positions = 0  # TODO: Get from IBKR
        
        logger.info("\n" + "="*80)
        logger.info("📊 STATUS UPDATE")
        logger.info("="*80)
        logger.info(f"Phase: {summary['phase_name']} ({summary['leverage']}x)")
        logger.info(f"Capital: ${stats['current_capital']:.2f}")
        logger.info(f"Trades: {stats['total_trades']} (W: {stats['winning_trades']}, L: {stats['losing_trades']})")
        logger.info(f"Win Rate: {stats['win_rate']:.1f}%")
        logger.info(f"Profit Factor: {stats['profit_factor']:.2f}")
        logger.info(f"ROI: {stats['roi_pct']:.1f}%")
        logger.info(f"Max Drawdown: {stats['max_drawdown_pct']:.1f}%")
        logger.info(f"Open Positions:")
        logger.info(f"   Coinbase: {coinbase_positions}")
        logger.info(f"   IBKR: {ibkr_positions}")
        logger.info("="*80 + "\n")
    
    def run(self):
        """Main trading loop."""
        self.log_startup_info()
        
        logger.info("🔄 Starting dual-broker trading loop...")
        logger.info("   Monitoring positions and trailing stops")
        logger.info("   Press Ctrl+C to stop gracefully\n")
        
        while not shutdown_requested:
            try:
                # Update Coinbase positions
                self.check_and_update_coinbase()
                
                # Update IBKR positions
                self.check_and_update_ibkr()
                
                # Log status periodically
                if time.time() - self.last_status_time >= self.status_interval:
                    self.log_status()
                    self.last_status_time = time.time()
                
                # Sleep
                time.sleep(self.poll_seconds)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error in trading loop: {e}", exc_info=True)
                time.sleep(self.poll_seconds)
        
        # Shutdown
        logger.info("\n" + "="*80)
        logger.info("🛑 SHUTTING DOWN")
        logger.info("="*80)
        
        # Close Coinbase positions
        coinbase_positions = self.coinbase.get_open_positions()
        if coinbase_positions:
            logger.info(f"Closing {len(coinbase_positions)} Coinbase positions...")
            for symbol, pos in coinbase_positions.items():
                try:
                    current_price = self.coinbase.fetch_live_price(symbol)
                    self.coinbase.close_position(symbol, current_price, "shutdown")
                    logger.info(f"   ✅ Closed {symbol} (Coinbase)")
                except Exception as e:
                    logger.error(f"   ❌ Failed to close {symbol}: {e}")
        
        # Close IBKR positions
        if self.ibkr:
            logger.info("Closing IBKR positions...")
            # TODO: Close IBKR positions
        
        # Disconnect IBKR
        if self.ibkr:
            try:
                self.ibkr.disconnect()
                logger.info("✅ IBKR disconnected")
            except:
                pass
        
        # Final summary
        summary = self.progression.get_summary()
        logger.info(f"\n📈 Final Stats:")
        logger.info(f"   Trades: {summary['stats']['total_trades']}")
        logger.info(f"   Win Rate: {summary['stats']['win_rate']:.1f}%")
        logger.info(f"   Final Capital: ${summary['stats']['current_capital']:.2f}")
        logger.info(f"   Net P&L: ${summary['stats']['net_profit']:.2f}")
        logger.info("\n✅ Shutdown complete\n")


def main():
    parser = argparse.ArgumentParser(description='Run dual-broker live trading')
    parser.add_argument('--symbols', nargs='+', default=['BTC-USD', 'ETH-USD'],
                       help='Trading symbols (default: BTC-USD ETH-USD)')
    parser.add_argument('--poll-seconds', type=float, default=10.0,
                       help='Polling interval in seconds (default: 10.0)')
    parser.add_argument('--ibkr-enabled', type=lambda x: x.lower() == 'true', default=True,
                       help='Enable IBKR trading (default: true)')
    
    args = parser.parse_args()
    
    trader = DualBrokerTrader(
        symbols=args.symbols,
        poll_seconds=args.poll_seconds,
        ibkr_enabled=args.ibkr_enabled
    )
    trader.run()


if __name__ == '__main__':
    main()
