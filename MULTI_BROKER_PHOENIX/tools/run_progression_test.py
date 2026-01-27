#!/usr/bin/env python3
"""Progression Test Runner - Simulate Phase 1 with Autonomous Graduation

Runs Coinbase in SIMULATION (paper mode) to test:
- Trailing stops working
- Safety limits enforced
- Progression tracking
- Auto-graduation when thresholds met

Safe to run - NO REAL MONEY, just testing the system.
"""
import sys
import os
import time
import logging
from datetime import datetime

# Setup path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from multi_broker_phoenix.brokers.coinbase_safe_connector import CoinbaseSafeConnector
from multi_broker_phoenix.foundation.progression_manager import ProgressionManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_simulation_loop(max_trades: int = 20, poll_seconds: float = 2.0):
    """Run simulation loop with progression tracking.
    
    Args:
        max_trades: Maximum number of trades to simulate
        poll_seconds: Seconds between price checks
    """
    logger.info("=" * 80)
    logger.info("🚀 STARTING PROGRESSION SIMULATION - COINBASE PAPER MODE")
    logger.info("=" * 80)
    
    # Initialize connector in PAPER MODE
    connector = CoinbaseSafeConnector(paper_mode=True)
    
    # Initialize progression manager
    starting_capital = float(os.getenv('PROGRESSION_STARTING_CAPITAL', '10.0'))
    progression = ProgressionManager(
        starting_capital=starting_capital,
        starting_phase=1
    )
    
    # Get current phase config
    phase = progression.get_current_phase_config()
    logger.info(f"\n📊 STARTING CONFIGURATION:")
    logger.info(f"   Phase: {phase.name}")
    logger.info(f"   Position Size: ${phase.position_size_usd}")
    logger.info(f"   Leverage: {phase.leverage}x")
    logger.info(f"   Starting Capital: ${starting_capital:.2f}")
    logger.info(f"   Max Trades: {max_trades}")
    
    symbols = ['BTC-USD', 'ETH-USD']
    trades_executed = 0
    open_positions = {}
    
    logger.info(f"\n🔄 Starting price monitoring loop (Ctrl+C to stop)...")
    logger.info("=" * 80)
    
    try:
        while trades_executed < max_trades:
            # Fetch current prices
            for symbol in symbols:
                price = connector.fetch_live_price(symbol)
                if price:
                    connector.update_price(symbol, price)
                    
                    # Check for trailing stop triggers
                    triggered_stops = connector.update_trailing_stops()
                    for stop in triggered_stops:
                        # Close position
                        pos = stop['position']
                        exit_price = stop['price']
                        entry_price = pos['entry_price']
                        
                        # Calculate P&L
                        if pos['side'] in ('BUY', 'LONG'):
                            pnl_pct = ((exit_price - entry_price) / entry_price) * 100
                        else:
                            pnl_pct = ((entry_price - exit_price) / entry_price) * 100
                        
                        pnl_usd = (pnl_pct / 100) * phase.position_size_usd
                        
                        # Update capital and record trade
                        progression.record_trade(pnl_usd, progression.stats.current_capital + pnl_usd)
                        connector.record_trade_result({
                            'symbol': symbol,
                            'pnl': pnl_usd,
                            'notional_usd': phase.position_size_usd
                        })
                        
                        trades_executed += 1
                        
                        # Remove from open positions tracking
                        if symbol in open_positions:
                            del open_positions[symbol]
                        
                        # Check if phase changed
                        new_phase = progression.get_current_phase_config()
                        if new_phase.name != phase.name:
                            phase = new_phase
                            logger.warning("🎓 PHASE UPGRADED! New settings active.")
                    
                    # Check for new signals (if no position open)
                    if symbol not in open_positions and symbol not in connector.get_open_positions():
                        # Simple signal generation (you'd use real strategy here)
                        # For demo: generate random signals with 60% win bias
                        import random
                        if random.random() < 0.15:  # 15% chance of signal each check
                            side = 'LONG' if random.random() < 0.6 else 'SHORT'
                            
                            # Calculate position size
                            size = phase.position_size_usd / price
                            
                            logger.info(f"\n📍 SIGNAL: {symbol} {side} @ ${price:.2f}")
                            
                            # Open position with trailing stops
                            connector.open_position(symbol, side, price, size, f"SIM-{trades_executed}")
                            open_positions[symbol] = {
                                'side': side,
                                'entry': price,
                                'size': size
                            }
            
            # Log status every 10 iterations
            if int(time.time()) % 20 == 0:
                summary = progression.get_summary()
                stats_daily = connector.get_daily_stats()
                logger.info(f"\n📊 STATUS UPDATE:")
                logger.info(f"   Phase: {summary['phase_name']} ({summary['leverage']}x)")
                logger.info(f"   Trades: {summary['stats']['total_trades']}/{phase.min_trades}")
                logger.info(f"   Win Rate: {summary['stats']['win_rate']:.1f}% (need {phase.min_win_rate_pct}%)")
                logger.info(f"   Capital: ${summary['stats']['current_capital']:.2f}")
                logger.info(f"   Open Positions: {len(connector.get_open_positions())}")
                logger.info(f"   Daily Trades: {stats_daily['trades_today']}/{stats_daily['remaining_trades'] + stats_daily['trades_today']}")
            
            # Check if we should stop
            stats_daily = connector.get_daily_stats()
            if stats_daily['stopped']:
                logger.error("⛔ Daily safety limits triggered - stopping")
                break
            
            time.sleep(poll_seconds)
            
    except KeyboardInterrupt:
        logger.info("\n⚠️  Interrupted by user")
    
    # Final summary
    logger.info("\n" + "=" * 80)
    logger.info("📈 SIMULATION COMPLETE")
    logger.info("=" * 80)
    
    summary = progression.get_summary()
    logger.info(f"Final Phase: {summary['phase_name']} (Phase {summary['current_phase']})")
    logger.info(f"Total Trades: {summary['stats']['total_trades']}")
    logger.info(f"Win Rate: {summary['stats']['win_rate']:.1f}%")
    logger.info(f"Profit Factor: {summary['stats']['profit_factor']:.2f}")
    logger.info(f"ROI: {summary['stats']['roi_pct']:.1f}%")
    logger.info(f"Final Capital: ${summary['stats']['current_capital']:.2f}")
    logger.info(f"Net P&L: ${summary['stats']['net_profit']:.2f}")
    
    if summary['current_phase'] > 1:
        logger.info(f"\n🎓 GRADUATED! Ready for {summary['leverage']}x leverage")
    else:
        logger.info(f"\n⏳ Still in Phase 1. Progress:")
        for key, value in summary['progress'].items():
            logger.info(f"   {key}: {value}")
    
    logger.info("=" * 80)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Run progression simulation test')
    parser.add_argument('--max-trades', type=int, default=20,
                       help='Maximum trades to execute (default: 20)')
    parser.add_argument('--poll-seconds', type=float, default=2.0,
                       help='Seconds between price checks (default: 2.0)')
    
    args = parser.parse_args()
    
    run_simulation_loop(max_trades=args.max_trades, poll_seconds=args.poll_seconds)
