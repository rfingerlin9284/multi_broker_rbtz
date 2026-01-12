#!/usr/bin/env python3
"""Fast Progression Demo - Simulates trades with synthetic price movements

Accelerated simulation that:
- Generates realistic price movements
- Opens/closes trades automatically
- Demonstrates progression tracking
- Shows auto-graduation when thresholds met
"""
import sys
import os
import time
import logging
import random
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from multi_broker_phoenix.brokers.coinbase_safe_connector import CoinbaseSafeConnector
from multi_broker_phoenix.foundation.progression_manager import ProgressionManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def simulate_trade_with_trailing_stop(
    connector: CoinbaseSafeConnector,
    progression: ProgressionManager,
    symbol: str,
    entry_price: float,
    side: str,
    trade_num: int
):
    """Simulate a single trade with realistic price movement and trailing stop."""
    
    phase = progression.get_current_phase_config()
    size = phase.position_size_usd / entry_price
    
    # Open position
    connector.open_position(symbol, side, entry_price, size, f"DEMO-{trade_num}")
    logger.info(f"📍 Trade #{trade_num}: {symbol} {side} @ ${entry_price:.2f}")
    
    # Simulate price movement
    current_price = entry_price
    max_price = entry_price
    min_price = entry_price
    ticks = 0
    max_ticks = 50
    
    # 60% chance this will be a winner
    is_winner = random.random() < 0.60
    
    while ticks < max_ticks:
        ticks += 1
        
        if is_winner:
            # Winning trade: gradually move in favor, then pullback to trailing stop
            if ticks < 30:
                # Move favorably
                if side in ('LONG', 'BUY'):
                    current_price *= (1 + random.uniform(0.001, 0.003))  # +0.1-0.3%
                else:
                    current_price *= (1 - random.uniform(0.001, 0.003))
            else:
                # Pullback to hit trailing stop
                if side in ('LONG', 'BUY'):
                    current_price *= (1 - random.uniform(0.002, 0.005))  # -0.2-0.5%
                else:
                    current_price *= (1 + random.uniform(0.002, 0.005))
        else:
            # Losing trade: move against position
            if side in ('LONG', 'BUY'):
                current_price *= (1 - random.uniform(0.001, 0.004))
            else:
                current_price *= (1 + random.uniform(0.001, 0.004))
        
        # Update connector price
        connector.update_price(symbol, current_price)
        
        # Check for triggered stops
        triggered_stops = connector.update_trailing_stops()
        
        if triggered_stops:
            # Stop hit - close position
            stop = triggered_stops[0]
            exit_price = current_price
            
            # Calculate P&L
            if side in ('BUY', 'LONG'):
                pnl_pct = ((exit_price - entry_price) / entry_price) * 100
            else:
                pnl_pct = ((entry_price - exit_price) / entry_price) * 100
            
            pnl_usd = (pnl_pct / 100) * phase.position_size_usd
            
            # Update capital and record trade
            new_capital = progression.stats.current_capital + pnl_usd
            progression.record_trade(pnl_usd, new_capital)
            
            connector.record_trade_result({
                'symbol': symbol,
                'pnl': pnl_usd,
                'notional_usd': phase.position_size_usd
            })
            
            connector.close_position(symbol, exit_price, "trailing_stop")
            
            logger.info(f"   Exit: ${exit_price:.2f} | P&L: {pnl_pct:+.2f}% (${pnl_usd:+.2f}) | Capital: ${new_capital:.2f}")
            return pnl_usd
        
        time.sleep(0.05)  # Small delay for realism
    
    # If we get here, manually close (shouldn't happen with proper stops)
    exit_price = current_price
    if side in ('BUY', 'LONG'):
        pnl_pct = ((exit_price - entry_price) / entry_price) * 100
    else:
        pnl_pct = ((entry_price - exit_price) / entry_price) * 100
    
    pnl_usd = (pnl_pct / 100) * phase.position_size_usd
    new_capital = progression.stats.current_capital + pnl_usd
    progression.record_trade(pnl_usd, new_capital)
    connector.close_position(symbol, exit_price, "manual")
    
    logger.info(f"   Exit: ${exit_price:.2f} | P&L: {pnl_pct:+.2f}% (${pnl_usd:+.2f}) | Capital: ${new_capital:.2f}")
    return pnl_usd


def run_fast_demo(num_trades: int = 30):
    """Run accelerated progression demonstration."""
    
    logger.info("=" * 80)
    logger.info("🚀 FAST PROGRESSION DEMO - SYNTHETIC PRICE MOVEMENTS")
    logger.info("=" * 80)
    
    # Initialize systems
    connector = CoinbaseSafeConnector(paper_mode=True)
    progression = ProgressionManager(starting_capital=10.0, starting_phase=1)
    
    # Starting prices
    btc_base = 87500.0
    eth_base = 2950.0
    
    logger.info(f"\n📊 Configuration:")
    phase = progression.get_current_phase_config()
    logger.info(f"   Phase: {phase.name}")
    logger.info(f"   Position Size: ${phase.position_size_usd}")
    logger.info(f"   Starting Capital: $10.00")
    logger.info(f"   Simulating {num_trades} trades...")
    logger.info("=" * 80)
    
    symbols = ['BTC-USD', 'ETH-USD']
    
    for trade_num in range(1, num_trades + 1):
        # Pick random symbol
        symbol = random.choice(symbols)
        
        # Generate entry price with some variance
        if symbol == 'BTC-USD':
            entry_price = btc_base * random.uniform(0.98, 1.02)
        else:
            entry_price = eth_base * random.uniform(0.98, 1.02)
        
        # Random side
        side = random.choice(['LONG', 'SHORT'])
        
        # Simulate trade
        try:
            pnl = simulate_trade_with_trailing_stop(
                connector, progression, symbol, entry_price, side, trade_num
            )
            
            # Show summary every 10 trades
            if trade_num % 10 == 0:
                summary = progression.get_summary()
                logger.info(f"\n{'='*80}")
                logger.info(f"📊 PROGRESS AFTER {trade_num} TRADES:")
                logger.info(f"   Phase: {summary['phase_name']} ({summary['leverage']}x)")
                logger.info(f"   Win Rate: {summary['stats']['win_rate']:.1f}%")
                logger.info(f"   Profit Factor: {summary['stats']['profit_factor']:.2f}")
                logger.info(f"   ROI: {summary['stats']['roi_pct']:.1f}%")
                logger.info(f"   Capital: ${summary['stats']['current_capital']:.2f}")
                logger.info(f"   Net P&L: ${summary['stats']['net_profit']:.2f}")
                logger.info(f"={'='*80}\n")
            
            # Small delay between trades
            time.sleep(0.2)
            
        except Exception as e:
            logger.error(f"Error in trade #{trade_num}: {e}")
            continue
    
    # Final summary
    logger.info("\n" + "=" * 80)
    logger.info("🏁 DEMO COMPLETE")
    logger.info("=" * 80)
    
    summary = progression.get_summary()
    logger.info(f"\n📈 FINAL RESULTS:")
    logger.info(f"   Phase: {summary['phase_name']} (Phase {summary['current_phase']})")
    logger.info(f"   Leverage: {summary['leverage']}x")
    logger.info(f"   Total Trades: {summary['stats']['total_trades']}")
    logger.info(f"   Win Rate: {summary['stats']['win_rate']:.1f}%")
    logger.info(f"   Profit Factor: {summary['stats']['profit_factor']:.2f}")
    logger.info(f"   ROI: {summary['stats']['roi_pct']:.1f}%")
    logger.info(f"   Starting Capital: $10.00")
    logger.info(f"   Final Capital: ${summary['stats']['current_capital']:.2f}")
    logger.info(f"   Net P&L: ${summary['stats']['net_profit']:.2f}")
    logger.info(f"   Max Drawdown: {summary['stats']['max_drawdown_pct']:.1f}%")
    
    if summary['current_phase'] > 1:
        logger.info(f"\n🎓 GRADUATED! Now in Phase {summary['current_phase']}")
        logger.info(f"   ✅ Ready for {summary['leverage']}x leverage")
        logger.info(f"   ✅ Position size increased to ${summary['position_size']}")
        if summary['use_futures']:
            logger.info(f"   🚀 FUTURES TRADING UNLOCKED")
    else:
        logger.info(f"\n⏳ Still in Phase 1 - Progress:")
        progress = summary['progress']
        logger.info(f"   Trades: {progress['trades_complete']}")
        logger.info(f"   Win Rate: {'✅' if progress['win_rate_met'] else '❌'}")
        logger.info(f"   Profit Factor: {'✅' if progress['profit_factor_met'] else '❌'}")
        logger.info(f"   ROI: {'✅' if progress['roi_met'] else '❌'}")
        logger.info(f"   Drawdown: {'✅' if progress['drawdown_ok'] else '❌'}")
        logger.info(f"   Days: {'✅' if progress['days_met'] else '❌'}")
    
    logger.info("=" * 80)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Run fast progression demo')
    parser.add_argument('--trades', type=int, default=30,
                       help='Number of trades to simulate (default: 30)')
    
    args = parser.parse_args()
    
    run_fast_demo(num_trades=args.trades)
