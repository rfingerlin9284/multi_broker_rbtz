#!/usr/bin/env python3
"""Phase 1 Live Trading with Autonomous Progression

REAL MONEY TRADING with Coinbase:
- Starts at $10 positions (Phase 1)
- Auto-graduates after 100+ winning trades at 55%+ win rate over 14 days
- Trailing stops: 2% initial, 1.5% activation, 1% trail
- Safety limits: $50 daily loss, 10 trades/day max
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

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global shutdown flag
shutdown_requested = False


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    global shutdown_requested
    logger.info("\n⚠️  Shutdown requested - closing positions...")
    shutdown_requested = True


signal.signal(signal.SIGINT, signal_handler)


class Phase1LiveTrader:
    """Live trading with progression tracking."""
    
    def __init__(self, symbols: list[str], poll_seconds: float = 10.0):
        self.symbols = symbols
        self.poll_seconds = poll_seconds
        
        # Initialize connector (LIVE MODE - paper_mode=False)
        logger.info("🔧 Initializing Coinbase connector (LIVE MODE)...")
        self.connector = CoinbaseSafeConnector(paper_mode=False)
        
        # Initialize progression manager
        logger.info("🎯 Initializing Progression Manager...")
        self.progression = ProgressionManager()
        
        # Status tracking
        self.last_status_time = time.time()
        self.status_interval = 60  # Log status every 60 seconds
        
    def log_startup_info(self):
        """Log configuration and current phase."""
        phase = self.progression.get_current_phase_config()
        
        logger.info("\n" + "="*80)
        logger.info("🚀 PHASE 1 LIVE TRADING STARTED")
        logger.info("="*80)
        logger.info(f"\n📊 Current Configuration:")
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
    
    def check_and_update_positions(self):
        """Monitor and update trailing stops for all open positions."""
        triggered_stops = self.connector.update_trailing_stops()
        
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
            logger.info(f"{result_emoji} {symbol} {side} closed: {pnl_pct:+.2f}% (${pnl_usd:+.2f})")
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
            
            # Close position in connector
            self.connector.close_position(symbol, exit_price, "trailing_stop")
    
    def log_status(self):
        """Log periodic status update."""
        summary = self.progression.get_summary()
        stats = summary['stats']
        
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
        logger.info(f"Open Positions: {len(self.connector.get_open_positions())}")
        logger.info("="*80 + "\n")
    
    def run(self):
        """Main trading loop."""
        self.log_startup_info()
        
        logger.info("🔄 Starting live trading loop...")
        logger.info("   Monitoring positions and trailing stops")
        logger.info("   Press Ctrl+C to stop gracefully\n")
        
        while not shutdown_requested:
            try:
                # Update trailing stops and close triggered positions
                self.check_and_update_positions()
                
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
        
        # Close any open positions
        open_positions = self.connector.get_open_positions()
        if open_positions:
            logger.info(f"Closing {len(open_positions)} open positions...")
            for symbol, pos in open_positions.items():
                try:
                    current_price = self.connector.fetch_live_price(symbol)
                    self.connector.close_position(symbol, current_price, "shutdown")
                    logger.info(f"   ✅ Closed {symbol}")
                except Exception as e:
                    logger.error(f"   ❌ Failed to close {symbol}: {e}")
        
        # Final summary
        summary = self.progression.get_summary()
        logger.info(f"\n📈 Final Stats:")
        logger.info(f"   Trades: {summary['stats']['total_trades']}")
        logger.info(f"   Win Rate: {summary['stats']['win_rate']:.1f}%")
        logger.info(f"   Final Capital: ${summary['stats']['current_capital']:.2f}")
        logger.info(f"   Net P&L: ${summary['stats']['net_profit']:.2f}")
        logger.info("\n✅ Shutdown complete\n")


def main():
    parser = argparse.ArgumentParser(description='Run Phase 1 live trading')
    parser.add_argument('--symbols', nargs='+', default=['BTC-USD', 'ETH-USD'],
                       help='Trading symbols (default: BTC-USD ETH-USD)')
    parser.add_argument('--poll-seconds', type=float, default=10.0,
                       help='Polling interval in seconds (default: 10.0)')
    
    args = parser.parse_args()
    
    trader = Phase1LiveTrader(symbols=args.symbols, poll_seconds=args.poll_seconds)
    trader.run()


if __name__ == '__main__':
    main()
