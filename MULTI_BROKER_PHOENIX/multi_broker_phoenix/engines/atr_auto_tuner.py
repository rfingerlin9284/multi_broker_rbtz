"""
ATR AUTO-TUNER - Learns optimal multipliers automatically.

This system tracks performance for each (symbol, multiplier) combination
and automatically adjusts multipliers based on actual win/loss outcomes.

No manual tuning needed - system learns what works best!
"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, Tuple, Optional

class ATRAutoTuner:
    """Automatically learns and adjusts ATR multipliers based on trading results."""
    
    def __init__(self, tuning_file: str = "atr_tuning_metrics.json"):
        self.logger = logging.getLogger(__name__)
        self.tuning_file = tuning_file
        self.metrics = self._load_metrics()
        self.logger.info("🤖 ATR AUTO-TUNER INITIALIZED")
    
    def _load_metrics(self) -> Dict:
        """Load tuning metrics from disk."""
        if os.path.exists(self.tuning_file):
            try:
                with open(self.tuning_file, 'r') as f:
                    data = json.load(f)
                    self.logger.info(f"✅ Loaded tuning metrics for {len(data)} symbols")
                    return data
            except Exception as e:
                self.logger.warning(f"Failed to load tuning file: {e}")
        
        return {}
    
    def _save_metrics(self):
        """Persist tuning metrics to disk."""
        try:
            with open(self.tuning_file, 'w') as f:
                json.dump(self.metrics, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save tuning metrics: {e}")
    
    def record_trade_outcome(self, symbol: str, multiplier: float, 
                            pnl_pct: float, bars_held: int, 
                            exit_reason: str = "unknown"):
        """Record trade outcome and learn from it."""
        
        symbol_key = symbol.replace('-', '_').upper()
        
        # Initialize symbol metrics if needed
        if symbol_key not in self.metrics:
            self.metrics[symbol_key] = {
                'trades': [],
                'current_multiplier': 2.5,
                'optimal_multiplier': 2.5,
                'adjustment_count': 0,
                'win_count': 0,
                'loss_count': 0
            }
        
        metrics = self.metrics[symbol_key]
        
        # Record trade
        trade_record = {
            'timestamp': datetime.now().isoformat(),
            'multiplier': multiplier,
            'pnl_pct': pnl_pct,
            'bars_held': bars_held,
            'exit_reason': exit_reason,
            'profitable': pnl_pct > 0.1  # >0.1% = win
        }
        metrics['trades'].append(trade_record)
        
        # Update win/loss counters
        if pnl_pct > 0.1:
            metrics['win_count'] += 1
        else:
            metrics['loss_count'] += 1
        
        # Keep only last 100 trades per symbol (for efficiency)
        if len(metrics['trades']) > 100:
            metrics['trades'] = metrics['trades'][-100:]
        
        self._save_metrics()
        
        # Analyze and adjust (every 5 trades)
        if (metrics['win_count'] + metrics['loss_count']) % 5 == 0:
            self._analyze_and_adjust(symbol_key)
    
    def _analyze_and_adjust(self, symbol_key: str):
        """Analyze recent trades and adjust multiplier if needed."""
        metrics = self.metrics[symbol_key]
        trades = metrics['trades'][-20:]  # Look at last 20 trades
        
        if len(trades) < 5:
            return  # Need at least 5 trades to analyze
        
        # Calculate statistics per multiplier
        multiplier_stats = {}
        
        for trade in trades:
            mult = trade['multiplier']
            if mult not in multiplier_stats:
                multiplier_stats[mult] = {
                    'wins': 0,
                    'losses': 0,
                    'avg_pnl': 0,
                    'total_pnl': 0,
                    'count': 0
                }
            
            stats = multiplier_stats[mult]
            if trade['profitable']:
                stats['wins'] += 1
            else:
                stats['losses'] += 1
            
            stats['total_pnl'] += trade['pnl_pct']
            stats['count'] += 1
        
        # Calculate win rate and average profit for each multiplier
        best_multiplier = metrics['current_multiplier']
        best_score = -999
        
        for mult, stats in multiplier_stats.items():
            stats['win_rate'] = stats['wins'] / stats['count'] if stats['count'] > 0 else 0
            stats['avg_pnl'] = stats['total_pnl'] / stats['count']
            
            # Score: balance win rate and avg profit
            # Win rate worth more for consistency, but avg profit matters for returns
            score = (stats['win_rate'] * 100) + (stats['avg_pnl'] * 10)
            
            if score > best_score:
                best_score = score
                best_multiplier = mult
        
        # Decide if we should adjust
        current_stats = multiplier_stats.get(metrics['current_multiplier'], {})
        best_stats = multiplier_stats.get(best_multiplier, {})
        
        if best_multiplier != metrics['current_multiplier']:
            # New best multiplier found
            improvement = ((best_stats.get('win_rate', 0) - current_stats.get('win_rate', 0)) * 100)
            
            self.logger.info(
                f"🔧 AUTO-TUNE: {symbol_key}\n"
                f"   Current: {metrics['current_multiplier']:.2f}x "
                f"({current_stats.get('win_rate', 0)*100:.0f}% wins, "
                f"{current_stats.get('avg_pnl', 0):+.2f}% avg)\n"
                f"   Better: {best_multiplier:.2f}x "
                f"({best_stats.get('win_rate', 0)*100:.0f}% wins, "
                f"{best_stats.get('avg_pnl', 0):+.2f}% avg)\n"
                f"   Improvement: {improvement:+.1f}% win rate"
            )
            
            metrics['current_multiplier'] = best_multiplier
            metrics['optimal_multiplier'] = best_multiplier
            metrics['adjustment_count'] += 1
    
    def get_multiplier(self, symbol: str) -> float:
        """Get auto-tuned multiplier for symbol (or default)."""
        symbol_key = symbol.replace('-', '_').upper()
        
        if symbol_key in self.metrics:
            mult = self.metrics[symbol_key]['current_multiplier']
            return mult
        
        # First time seeing this symbol - start with 2.5
        return 2.5
    
    def get_stats(self, symbol: str = None) -> Dict:
        """Get tuning statistics."""
        if symbol:
            symbol_key = symbol.replace('-', '_').upper()
            return self.metrics.get(symbol_key, {})
        return self.metrics
    
    def print_tuning_summary(self):
        """Print summary of all auto-tuned multipliers."""
        self.logger.info("\n" + "="*80)
        self.logger.info("🤖 ATR AUTO-TUNER SUMMARY")
        self.logger.info("="*80)
        
        for symbol, metrics in sorted(self.metrics.items()):
            trades = len(metrics['trades'])
            if trades > 0:
                win_rate = metrics['win_count'] / (metrics['win_count'] + metrics['loss_count']) * 100
                self.logger.info(
                    f"   {symbol}:\n"
                    f"      Current Multiplier: {metrics['current_multiplier']:.2f}x\n"
                    f"      Wins: {metrics['win_count']} | Losses: {metrics['loss_count']} | "
                    f"Win Rate: {win_rate:.1f}%\n"
                    f"      Adjustments: {metrics['adjustment_count']} | Trades Analyzed: {trades}"
                )
        
        self.logger.info("="*80 + "\n")
