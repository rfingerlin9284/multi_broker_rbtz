"""
MULTI-STRATEGY SCANNER
Scans ALL enabled strategies simultaneously and ranks best setups
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from .strategy_registry import get_enabled_strategies, get_strategy_config

logger = logging.getLogger(__name__)


class StrategySignal:
    """Signal from a strategy."""
    def __init__(self, strategy_code: str, symbol: str, direction: str, 
                 confidence: float, entry_price: float, stop_loss: float,
                 take_profit: float, reasoning: str, metadata: Dict = None):
        self.strategy_code = strategy_code
        self.symbol = symbol
        self.direction = direction  # BUY or SELL
        self.confidence = confidence
        self.entry_price = entry_price
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.reasoning = reasoning
        self.metadata = metadata or {}
        self.timestamp = datetime.now()
        self.quality_score = self._calculate_quality_score()
    
    def _calculate_quality_score(self) -> float:
        """Calculate overall quality score for ranking."""
        rr_ratio = abs(self.take_profit - self.entry_price) / abs(self.entry_price - self.stop_loss)
        
        # Quality = Confidence * R:R factor * Strategy weight
        strategy_cfg = get_strategy_config(self.strategy_code)
        base_confidence = strategy_cfg.get('params', {}).get('min_confidence', 0.65)
        
        # Bonus for exceeding minimum confidence
        confidence_bonus = (self.confidence - base_confidence) / base_confidence
        
        # R:R scoring (2.0 = 1.0, 3.0 = 1.2, 1.5 = 0.8)
        rr_score = min(rr_ratio / 2.0, 1.5)
        
        return self.confidence * rr_score * (1.0 + confidence_bonus)
    
    def __repr__(self):
        return f"<Signal {self.strategy_code} {self.symbol} {self.direction} conf={self.confidence:.2f} quality={self.quality_score:.2f}>"


class ConflictDetector:
    """Detects and resolves strategy conflicts."""
    
    @staticmethod
    def detect_conflicts(signals: List[StrategySignal]) -> Dict[str, List[StrategySignal]]:
        """Group signals by symbol to detect conflicts."""
        by_symbol = {}
        for sig in signals:
            if sig.symbol not in by_symbol:
                by_symbol[sig.symbol] = []
            by_symbol[sig.symbol].append(sig)
        return by_symbol
    
    @staticmethod
    def resolve_conflicts(signals: List[StrategySignal]) -> Optional[StrategySignal]:
        """Resolve conflicts for a single symbol.
        
        Returns:
            Best signal if consensus exists, None if conflicting
        """
        if len(signals) == 1:
            return signals[0]
        
        # Check for directional conflicts
        buy_signals = [s for s in signals if s.direction == 'BUY']
        sell_signals = [s for s in signals if s.direction == 'SELL']
        
        # If conflicting directions, check strength
        if buy_signals and sell_signals:
            buy_quality = sum(s.quality_score for s in buy_signals) / len(buy_signals)
            sell_quality = sum(s.quality_score for s in sell_signals) / len(sell_signals)
            
            # Need clear winner (20% difference)
            if abs(buy_quality - sell_quality) / max(buy_quality, sell_quality) < 0.20:
                logger.warning(f"⚠️  CONFLICT on {signals[0].symbol}: BUY vs SELL signals too close - BLOCKING")
                return None
            
            # Return strongest direction's best signal
            if buy_quality > sell_quality:
                return max(buy_signals, key=lambda s: s.quality_score)
            else:
                return max(sell_signals, key=lambda s: s.quality_score)
        
        # Same direction - return highest quality
        return max(signals, key=lambda s: s.quality_score)


class MultiStrategyScanner:
    """Scans all enabled strategies and ranks best opportunities."""
    
    def __init__(self, max_concurrent_trades: int = 5):
        self.max_concurrent_trades = max_concurrent_trades
        self.enabled_strategies = get_enabled_strategies()
        self.conflict_detector = ConflictDetector()
        
        logger.info(f"📊 Multi-Strategy Scanner initialized")
        logger.info(f"   Enabled strategies: {len(self.enabled_strategies)}")
        logger.info(f"   Max concurrent: {self.max_concurrent_trades}")
    
    def scan_all_strategies(self, symbols: List[str], market_data: Dict[str, Any]) -> List[StrategySignal]:
        """Scan ALL enabled strategies across universe.
        
        Args:
            symbols: List of symbols to scan
            market_data: Dict of {symbol: {candles, indicators, etc}}
        
        Returns:
            List of StrategySignal objects from all strategies
        """
        all_signals = []
        
        logger.info(f"🔍 Scanning {len(symbols)} symbols with {len(self.enabled_strategies)} strategies...")
        
        for strategy_code in self.enabled_strategies:
            strategy_cfg = get_strategy_config(strategy_code)
            logger.info(f"   Scanning: {strategy_cfg.get('name', strategy_code)}")
            
            # Get signals from this strategy
            signals = self._scan_strategy(strategy_code, symbols, market_data)
            all_signals.extend(signals)
            
            if signals:
                logger.info(f"      ✅ Found {len(signals)} signals")
        
        logger.info(f"📈 Total signals: {len(all_signals)}")
        return all_signals
    
    def _scan_strategy(self, strategy_code: str, symbols: List[str], 
                      market_data: Dict[str, Any]) -> List[StrategySignal]:
        """Scan a single strategy across all symbols."""
        signals = []
        
        # Import and instantiate strategy
        try:
            strategy_instance = self._get_strategy_instance(strategy_code)
            if not strategy_instance:
                return []
            
            # Scan each symbol
            for symbol in symbols:
                if symbol not in market_data:
                    continue
                
                signal = self._check_strategy_signal(
                    strategy_instance, 
                    strategy_code,
                    symbol, 
                    market_data[symbol]
                )
                
                if signal:
                    signals.append(signal)
        
        except Exception as e:
            logger.error(f"Error scanning {strategy_code}: {e}")
        
        return signals
    
    def _get_strategy_instance(self, strategy_code: str):
        """Get strategy instance (placeholder - implement actual strategy loading)."""
        # TODO: Implement actual strategy class loading
        # For now, return None to indicate strategy needs implementation
        return None
    
    def _check_strategy_signal(self, strategy, strategy_code: str, 
                               symbol: str, data: Dict) -> Optional[StrategySignal]:
        """Check if strategy has a signal for this symbol."""
        try:
            # Call strategy's signal generation method
            # This is a placeholder - actual implementation depends on strategy interface
            result = strategy.generate_signal(symbol, data)
            
            if result:
                return StrategySignal(
                    strategy_code=strategy_code,
                    symbol=symbol,
                    direction=result.get('direction'),
                    confidence=result.get('confidence'),
                    entry_price=result.get('entry_price'),
                    stop_loss=result.get('stop_loss'),
                    take_profit=result.get('take_profit'),
                    reasoning=result.get('reasoning', ''),
                    metadata=result.get('metadata', {})
                )
        except Exception as e:
            logger.debug(f"No signal from {strategy_code} for {symbol}: {e}")
        
        return None
    
    def rank_and_filter(self, signals: List[StrategySignal], 
                       active_positions: List[Dict] = None) -> List[StrategySignal]:
        """Rank signals by quality and filter conflicts.
        
        Args:
            signals: All signals from strategies
            active_positions: Currently open positions to avoid conflicts
        
        Returns:
            Top N filtered signals ready for execution
        """
        if not signals:
            return []
        
        active_positions = active_positions or []
        
        # 1. Remove symbols we already have positions in
        active_symbols = set(pos.get('symbol') for pos in active_positions)
        signals = [s for s in signals if s.symbol not in active_symbols]
        
        logger.info(f"📊 Ranking {len(signals)} signals (after filtering active positions)")
        
        # 2. Detect and resolve conflicts per symbol
        by_symbol = self.conflict_detector.detect_conflicts(signals)
        resolved_signals = []
        
        for symbol, symbol_signals in by_symbol.items():
            if len(symbol_signals) > 1:
                logger.info(f"   {symbol}: {len(symbol_signals)} signals - checking conflicts")
            
            resolved = self.conflict_detector.resolve_conflicts(symbol_signals)
            if resolved:
                resolved_signals.append(resolved)
            else:
                logger.warning(f"   ⚠️  {symbol}: Conflicting signals - BLOCKED")
        
        # 3. Sort by quality score
        resolved_signals.sort(key=lambda s: s.quality_score, reverse=True)
        
        # 4. Ensure diversity - limit signals per strategy
        diverse_signals = self._ensure_diversity(resolved_signals)
        
        # 5. Take top N based on concurrent trade limit
        available_slots = self.max_concurrent_trades - len(active_positions)
        top_signals = diverse_signals[:available_slots]
        
        logger.info(f"✅ Top {len(top_signals)} signals selected:")
        for i, sig in enumerate(top_signals, 1):
            logger.info(f"   {i}. {sig.strategy_code}: {sig.symbol} {sig.direction} "
                       f"(conf={sig.confidence:.2%}, quality={sig.quality_score:.2f})")
        
        return top_signals
    
    def _ensure_diversity(self, signals: List[StrategySignal], 
                         max_per_strategy: int = 2) -> List[StrategySignal]:
        """Ensure diverse strategy representation."""
        strategy_counts = {}
        diverse = []
        
        for sig in signals:
            count = strategy_counts.get(sig.strategy_code, 0)
            if count < max_per_strategy:
                diverse.append(sig)
                strategy_counts[sig.strategy_code] = count + 1
        
        return diverse


# Global scanner instance
_scanner = None

def get_scanner(max_concurrent: int = 5) -> MultiStrategyScanner:
    """Get or create global scanner instance."""
    global _scanner
    if _scanner is None:
        _scanner = MultiStrategyScanner(max_concurrent_trades=max_concurrent)
    return _scanner
