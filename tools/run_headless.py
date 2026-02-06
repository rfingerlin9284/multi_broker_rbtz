#!/usr/bin/env python3
"""
RBOTZILLA AUTONOMOUS TRADING ENGINE v2.1
=========================================
FIXED: Uses place_oco with OCOOrder for OANDA execution.

Approval ID: 841921 | Date: 2026-02-02
"""
import sys, os, time, json, logging, requests
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

# ===== AI HIVE INTEGRATION =====
AI_HIVE_AVAILABLE = False
get_api_ai_vote = None
try:
    hive_path = str(REPO_ROOT / 'hive_real')
    if hive_path not in sys.path:
        sys.path.insert(0, hive_path)
    from api_ai_hive import get_api_ai_vote
    AI_HIVE_AVAILABLE = True
except Exception as e:
    logger.warning(f"⚠️  AI Hive not available: {e}")
# ===== END AI HIVE =====

os.makedirs(REPO_ROOT / 'logs', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler(REPO_ROOT / 'logs' / 'engine_aggressive_default.log')]
)
logger = logging.getLogger(__name__)

# RBZ tight trailing / tp guard (optional) - ensure module path includes 'New folder'
try:
    _rbz_candidate = REPO_ROOT / 'New folder'
    if _rbz_candidate.exists() and str(_rbz_candidate) not in sys.path:
        sys.path.insert(0, str(_rbz_candidate))
    from rbz_tight_trailing import apply_rbz_overrides, CharterConfig, tp_guard
    _RBZ_TIGHT_AVAILABLE = True
except Exception as e:
    _RBZ_TIGHT_AVAILABLE = False
    logger.info(f"   ⚠️ RBZ tight trailing module not available: {e}")

def load_secrets():
    secrets_path = REPO_ROOT / 'ops' / 'secrets.env'
    config = {}
    if secrets_path.exists():
        with open(secrets_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip().strip('"').strip("'")
                    os.environ[key.strip()] = value.strip().strip('"').strip("'")
    return config

CONFIG = load_secrets()
FOREX_PAIRS = ["EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD", "USD_CAD", "NZD_USD", "USD_CHF", "EUR_GBP", "EUR_JPY", "GBP_JPY"]


class OandaCandleFetcher:
    def __init__(self):
        self.token = CONFIG.get('OANDA_API_TOKEN', os.getenv('OANDA_API_TOKEN', ''))
        self.account_id = CONFIG.get('OANDA_ACCOUNT_ID', os.getenv('OANDA_ACCOUNT_ID', ''))
        self.base_url = "https://api-fxpractice.oanda.com"
        self.headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        logger.info(f"   OANDA CandleFetcher ready (account={self.account_id[:20]}...)")
    
    def get_candles(self, pair: str, count: int = 100, granularity: str = "M5") -> List[Dict]:
        try:
            url = f"{self.base_url}/v3/instruments/{pair}/candles"
            params = {"count": count, "granularity": granularity, "price": "M"}
            resp = requests.get(url, headers=self.headers, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return [{'open': float(c.get('mid', {}).get('o', 0)), 'high': float(c.get('mid', {}).get('h', 0)),
                         'low': float(c.get('mid', {}).get('l', 0)), 'close': float(c.get('mid', {}).get('c', 0)),
                         'volume': int(c.get('volume', 0))} for c in data.get('candles', [])]
        except Exception as e:
            logger.debug(f"Candle fetch error for {pair}: {e}")
        return []
    
    def get_price(self, pair: str) -> Dict:
        try:
            url = f"{self.base_url}/v3/accounts/{self.account_id}/pricing"
            params = {"instruments": pair}
            resp = requests.get(url, headers=self.headers, params=params, timeout=10)
            if resp.status_code == 200:
                prices = resp.json().get('prices', [])
                if prices:
                    p = prices[0]
                    return {'bid': float(p.get('bids', [{}])[0].get('price', 0)), 'ask': float(p.get('asks', [{}])[0].get('price', 0))}
        except Exception as e:
            logger.debug(f"Price fetch error: {e}")
        return {'bid': 0, 'ask': 0}


class TradingStrategyScanner:
    def __init__(self, catalog: dict = None):
        self.catalog = catalog or {}
        self.enabled_strategies = CONFIG.get('ENABLED_STRATEGIES', '').split(',')
        self.enabled_strategies = [s.strip() for s in self.enabled_strategies if s.strip()]
        if not self.enabled_strategies:
            self.enabled_strategies = ['fabio_aaa_full', 'ema_scalper', 'holy_grail', 'trap_reversal', 'institutional_sd']
        logger.info(f"   Strategies: {self.enabled_strategies} | Catalog entries: {len(self.catalog)}")
        
    def generate_signals(self, pair: str, candles: List[Dict]) -> List[Dict]:
        signals = []
        if not candles or len(candles) < 50:
            return signals
        
        closes = [c['close'] for c in candles]
        highs = [c['high'] for c in candles]
        lows = [c['low'] for c in candles]
        
        sma_20, sma_50 = sum(closes[-20:]) / 20, sum(closes[-50:]) / 50
        gains = [max(0, closes[i] - closes[i-1]) for i in range(1, len(closes))]
        losses = [max(0, closes[i-1] - closes[i]) for i in range(1, len(closes))]
        avg_gain = sum(gains[-14:]) / 14 if len(gains) >= 14 else 0.01
        avg_loss = sum(losses[-14:]) / 14 if len(losses) >= 14 else 0.01
        rsi = 100 - (100 / (1 + avg_gain / (avg_loss + 0.0001)))
        current = closes[-1]
        
        if 'fabio_aaa_full' in self.enabled_strategies:
            if rsi < 35 and current > sma_50:
                signals.append({'strategy': 'fabio_aaa_full', 'pair': pair, 'side': 'BUY', 'confidence': 0.72, 'reason': f'RSI oversold ({rsi:.1f}) in uptrend'})
            elif rsi > 65 and current < sma_50:
                signals.append({'strategy': 'fabio_aaa_full', 'pair': pair, 'side': 'SELL', 'confidence': 0.70, 'reason': f'RSI overbought ({rsi:.1f}) in downtrend'})
        
        if 'ema_scalper' in self.enabled_strategies:
            ema_8, ema_21 = self._ema(closes, 8), self._ema(closes, 21)
            if ema_8[-1] > ema_21[-1] and ema_8[-2] <= ema_21[-2]:
                signals.append({'strategy': 'ema_scalper', 'pair': pair, 'side': 'BUY', 'confidence': 0.68, 'reason': 'EMA 8/21 bullish cross'})
            elif ema_8[-1] < ema_21[-1] and ema_8[-2] >= ema_21[-2]:
                signals.append({'strategy': 'ema_scalper', 'pair': pair, 'side': 'SELL', 'confidence': 0.68, 'reason': 'EMA 8/21 bearish cross'})
        
        if 'trap_reversal' in self.enabled_strategies:
            recent_high, recent_low = max(highs[-10:]), min(lows[-10:])
            if highs[-1] > recent_high and closes[-1] < highs[-1] * 0.999:
                signals.append({'strategy': 'trap_reversal', 'pair': pair, 'side': 'SELL', 'confidence': 0.73, 'reason': 'Liquidity trap failed high'})
            elif lows[-1] < recent_low and closes[-1] > lows[-1] * 1.001:
                signals.append({'strategy': 'trap_reversal', 'pair': pair, 'side': 'BUY', 'confidence': 0.73, 'reason': 'Liquidity trap failed low'})
        
        if 'holy_grail' in self.enabled_strategies:
            if current > sma_50 and closes[-2] < sma_20 <= closes[-1]:
                signals.append({'strategy': 'holy_grail', 'pair': pair, 'side': 'BUY', 'confidence': 0.75, 'reason': 'Pullback to SMA20 in uptrend'})
            elif current < sma_50 and closes[-2] > sma_20 >= closes[-1]:
                signals.append({'strategy': 'holy_grail', 'pair': pair, 'side': 'SELL', 'confidence': 0.75, 'reason': 'Pullback to SMA20 in downtrend'})
        
        if 'institutional_sd' in self.enabled_strategies:
            price_range = max(highs[-20:]) - min(lows[-20:])
            if current < min(lows[-20:]) + price_range * 0.15:
                signals.append({'strategy': 'institutional_sd', 'pair': pair, 'side': 'BUY', 'confidence': 0.70, 'reason': 'Price at demand zone'})
            elif current > max(highs[-20:]) - price_range * 0.15:
                signals.append({'strategy': 'institutional_sd', 'pair': pair, 'side': 'SELL', 'confidence': 0.70, 'reason': 'Price at supply zone'})
        
        # Enrich signals with catalog metadata when available (allow_stop_only, tags, win_rate)
        for sig in signals:
            try:
                key = sig.get('strategy', '').strip().lower()
                catalog_entry = self.catalog.get(key)
                if not catalog_entry:
                    # Try partial matches against catalog names and tags
                    for k, v in self.catalog.items():
                        name_lower = v.get('name','').lower()
                        tags_lower = ' '.join(v.get('tags', [])).lower()
                        if key in k or key in name_lower or key in tags_lower:
                            catalog_entry = v
                            break
                if catalog_entry:
                    sig['catalog'] = catalog_entry
                    sig['allow_stop_only'] = bool(catalog_entry.get('allow_stop_only', False))
                    sig['tags'] = catalog_entry.get('tags', [])
                    sig['win_rate_pct'] = catalog_entry.get('win_rate_pct')
                else:
                    sig.setdefault('allow_stop_only', False)
                    sig.setdefault('tags', [])
            except Exception:
                sig.setdefault('allow_stop_only', False)
                sig.setdefault('tags', [])
        
        return signals
    
    def _ema(self, data: List[float], period: int) -> List[float]:
        if len(data) < period: return data
        k = 2 / (period + 1)
        ema = [sum(data[:period]) / period]
        for price in data[period:]:
            ema.append(price * k + ema[-1] * (1 - k))
        return ema


class AutonomousTradingEngine:
    def __init__(self, mode: str = "paper"):
        self.mode = mode
        self.start_time = datetime.now(timezone.utc)
        
        logger.info("=" * 70)
        logger.info("🚀 RBOTZILLA AUTONOMOUS TRADING ENGINE v2.1 (OCO FIX)")
        logger.info("=" * 70)
        logger.info(f"   Mode: {mode.upper()} | Started: {self.start_time}")
        
        self.position_size = int(CONFIG.get('POSITION_SIZE_UNITS', '10000'))  # Default/fallback
        # Quality-based sizing config
        self.enable_quality_sizing = CONFIG.get('ENABLE_QUALITY_BASED_SIZING', 'false').lower() == 'true'
        self.quality_scale_min = int(CONFIG.get('QUALITY_SIZE_SCALE_MIN', 40))
        self.quality_scale_low = int(CONFIG.get('QUALITY_SIZE_SCALE_LOW', 60))
        self.quality_scale_mid = int(CONFIG.get('QUALITY_SIZE_SCALE_MID', 75))
        self.quality_scale_high = int(CONFIG.get('QUALITY_SIZE_SCALE_HIGH', 85))
        self.max_units = int(CONFIG.get('POSITION_SIZE_UNITS', '10000'))
        self.min_notional = int(CONFIG.get('MIN_NOTIONAL_USD', 5000))
        self.max_notional = int(CONFIG.get('MAX_NOTIONAL_USD', 8000))
        self.sl_pips = int(CONFIG.get('OANDA_INITIAL_STOP_PIPS', '15'))
        self.confidence_threshold = float(CONFIG.get('OANDA_SIGNAL_CONFIDENCE_THRESHOLD', '0.45'))
        self.max_concurrent = int(CONFIG.get('MAX_CONCURRENT_POSITIONS', '15'))
        
        logger.info(f"   Position: {self.position_size} units | SL: {self.sl_pips} pips | Confidence: {self.confidence_threshold}")
        
        # AI Hive Status
        ai_hive_enabled = os.getenv('ENABLE_AI_HIVE', 'false').lower() == 'true'
        if AI_HIVE_AVAILABLE and ai_hive_enabled:
            logger.info("   ✅ AI HIVE ENABLED - All trades will be validated by Grok/OpenAI")
        elif ai_hive_enabled and not AI_HIVE_AVAILABLE:
            logger.warning("   ⚠️  AI HIVE CONFIGURED but MODULE MISSING - trades may not be validated!")
        else:
            logger.warning("   ⚠️  AI HIVE DISABLED - NO QUALITY GATING (expect losses)")
        
        self.candle_fetcher = OandaCandleFetcher()
        
        # Import OCOOrder and OandaAdapter
        try:
            from multi_broker_phoenix.core.interfaces import OCOOrder
            from multi_broker_phoenix.adapters.oanda_adapter import OandaAdapter
            self.OCOOrder = OCOOrder
            self.order_executor = OandaAdapter()
            logger.info("   ✅ OANDA Order Executor ready (OCO mode)")
            # Apply RBZ tight trailing overrides if available
            if _RBZ_TIGHT_AVAILABLE and self.order_executor:
                try:
                    apply_rbz_overrides(connector=self.order_executor, engine=self, charter_cfg=CharterConfig(min_notional_usd=self.min_notional))
                    logger.info("   ✅ RBZ tight trailing & charter overrides applied")
                except Exception as e:
                    logger.warning(f"   ⚠️ apply_rbz_overrides failed: {e}")
        except Exception as e:
            self.order_executor = None
            logger.warning(f"   ⚠️ OANDA not available: {e}")
        
        # Load ops/strategies.json as a catalog for per-strategy tuning
        try:
            import json
            catalog_path = REPO_ROOT / 'ops' / 'strategies.json'
            if catalog_path.exists():
                with open(catalog_path, 'r') as f:
                    self.strategy_catalog = {s.get('name','').strip().lower(): s for s in json.load(f)}
                    logger.info(f"   ✅ Loaded {len(self.strategy_catalog)} strategy configs from ops/strategies.json")
            else:
                self.strategy_catalog = {}
        except Exception as e:
            self.strategy_catalog = {}
            logger.warning(f"   ⚠️ Failed to load strategy catalog: {e}")

        # Instantiate the scanner and pass the catalog for per-strategy enrichment
        self.scanner = TradingStrategyScanner(catalog=self.strategy_catalog)

        self.active_positions, self.signals_generated, self.trades_executed, self.iteration = [], 0, 0, 0
    
    def get_open_positions_count(self) -> int:
        """Get REAL position count from OANDA, not local tracking"""
        try:
            if self.order_executor:
                positions = self.order_executor.get_positions()
                return len(positions) if positions else 0
        except Exception as e:
            logger.warning(f"   ⚠️ Could not get positions from OANDA: {e}")
        return len(self.active_positions)  # Fallback to local tracking

    def _manage_trade(self, trade: dict) -> None:
        """Legacy hook required by RBZ Tight SL wrapper - no-op default."""
        # RBZ wrapper will replace this function to enforce tight SL/trailing
        return None

        logger.info("=" * 70)
        logger.info("🎬 Starting autonomous trading loop...")
    
    def scan_all_pairs(self) -> List[Dict]:
        all_signals = []
        for pair in FOREX_PAIRS:
            try:
                candles = self.candle_fetcher.get_candles(pair, count=100)
                if not candles: continue
                signals = self.scanner.generate_signals(pair, candles)
                for sig in signals:
                    self.signals_generated += 1
                    if sig['confidence'] >= self.confidence_threshold:
                        all_signals.append(sig)
                        logger.info(f"   🎯 SIGNAL: {sig['pair']} {sig['side']} via {sig['strategy']} ({sig['confidence']:.0%})")
                        logger.info(f"      Reason: {sig['reason']}")
            except Exception as e:
                logger.debug(f"   Scan error {pair}: {e}")
        return all_signals
    
    def _calculate_position_size(self, signal: Dict) -> int:
        """Calculate position size based on quality/confidence if enabled."""
        if not self.enable_quality_sizing:
            return self.max_units
        # Use confidence as quality proxy (0-1 float or 0-100 int)
        quality = signal.get('confidence', 0)
        if quality <= 1.0:
            quality = int(quality * 100)
        if quality < self.quality_scale_low:
            scale = 0.25
        elif quality < self.quality_scale_mid:
            scale = 0.5
        elif quality < self.quality_scale_high:
            scale = 0.75
        else:
            scale = 1.0
        units = int(self.max_units * scale)
        # Clamp to min/max notional if needed
        units = max(int(self.min_notional * scale), units)
        units = min(units, self.max_units)
        return units

    def execute_trade(self, signal: Dict) -> Optional[Dict]:
        if not self.order_executor:
            logger.warning("   No order executor available")
            return None
        
        try:
            pair, side = signal['pair'], signal['side']
            price = self.candle_fetcher.get_price(pair)
            entry_price = price['ask'] if side == 'BUY' else price['bid']
            if entry_price == 0:
                logger.warning(f"   Price not available for {pair}")
                return None

            # ===== AI HIVE QUALITY GATE =====
            if AI_HIVE_AVAILABLE and os.getenv('ENABLE_AI_HIVE', 'false').lower() == 'true':
                if os.getenv('HIVE_EMERGENCY_BYPASS', 'false').lower() != 'true':
                    try:
                        logger.info(f"   🤖 AI Hive validating {pair} {side}...")
                        recent_candles = self.candle_fetcher.get_candles(pair, count=30)
                        recent_prices = [c['close'] for c in recent_candles] if recent_candles else [entry_price] * 10
                        market_data = {'prices': recent_prices}
                        strategy = signal.get('strategy', 'unknown')
                        hive_result = get_api_ai_vote(pair, side.upper(), entry_price, market_data, strategy=strategy)
                        ai_source = hive_result.get('ai_used', 'Unknown')
                        logger.info(f"   🧠 AI Source: {ai_source.upper()}")
                        if hive_result['vote'] not in ['approve', 'execute']:
                            logger.warning(f"   🚫 AI Hive REJECTED: {hive_result.get('reasoning', 'Low quality setup')}")
                            logger.warning(f"      Consensus: {hive_result.get('consensus', 0):.0%}")
                            return None
                        logger.info(f"   ✅ AI Hive APPROVED (consensus: {hive_result.get('consensus', 0):.0%})")
                    except Exception as hive_err:
                        logger.error(f"   🚨 AI Hive ERROR: {hive_err} - BLOCKING for safety")
                        return None
            # ===== END AI HIVE GATE =====

            # --- QUALITY-BASED POSITION SIZING ---
            position_size = self._calculate_position_size(signal)
            pip_value = 0.0001 if 'JPY' not in pair else 0.01
            sl_distance = self.sl_pips * pip_value
            if side == 'BUY':
                sl_price = entry_price - sl_distance
                tp_price = entry_price + (sl_distance * 2)
            else:
                sl_price = entry_price + sl_distance
                tp_price = entry_price - (sl_distance * 2)

            # RBZ TP guard: strip TP if strategy/policy disallows it
            allow_sl_only = False
            try:
                if _RBZ_TIGHT_AVAILABLE:
                    strategy_name = signal.get('strategy')
                    tags = set([t.strip().lower() for t in (signal.get('tags') or [])])
                    tp_price = tp_guard(strategy_name, tags, tp_price)
                    if tp_price is None:
                        logger.info(f"   ⚠️ TP removed by tp_guard for {pair} {strategy_name} (policy)")
                        # Prefer enrichment from signal, fall back to catalog lookup
                        strat_allows_stop_only = bool(signal.get('allow_stop_only', False))
                        if not strat_allows_stop_only:
                            strat_key = (strategy_name or '').strip().lower()
                            strat_cfg = getattr(self, 'strategy_catalog', {}).get(strat_key, {})
                            strat_allows_stop_only = bool(strat_cfg.get('allow_stop_only'))

                        enable_stop_only = CONFIG.get('ENABLE_STOP_ONLY_FOR_SCALPS', 'false').lower() == 'true'
                        stop_only_mult = float(CONFIG.get('STOP_ONLY_SIZE_MULT', 0.5))

                        if strat_allows_stop_only or (enable_stop_only and ('scalp' in tags or 'micro' in tags or 'hf' in tags)):
                            allow_sl_only = True
                            position_size = int(position_size * stop_only_mult)
                            logger.info(f"   ⚠️ Allowing SL-only (scaled size x{stop_only_mult}) for {strategy_name} (strat_allow={strat_allows_stop_only})")
                        else:
                            logger.warning(f"   ⚠️ OCO requires both SL and TP - trade blocked (TP removed by policy) for {strategy_name}")
                            return None
            except Exception as e:
                logger.debug(f"   TP guard error: {e}")

            # mark client_tag if this will be SL-only
            client_tag = None
            if allow_sl_only:
                client_tag = f"sl_only_{int(time.time())}"

            oco = self.OCOOrder(
                symbol=pair,
                entry_side=side,
                entry_quantity=float(position_size),
                take_profit_price=tp_price,
                stop_loss_price=sl_price,
                client_tag=client_tag
            )
            result = self.order_executor.place_oco(oco)
            if result:
                self.trades_executed += 1
                # Log SL/TP safely when TP may be None
                logger.info(f"   ✅ TRADE: {side} {position_size} {pair} @ {entry_price:.5f}")
                if tp_price is not None:
                    logger.info(f"      SL: {sl_price:.5f} | TP: {tp_price:.5f} | Strategy: {signal['strategy']} | Quality: {signal.get('confidence', 0):.2f}")
                else:
                    logger.info(f"      SL: {sl_price:.5f} | TP: None (SL-only) | Strategy: {signal['strategy']} | Quality: {signal.get('confidence', 0):.2f}")
                self.active_positions.append({
                    'pair': pair, 'side': side, 'units': position_size,
                    'entry_price': entry_price, 'strategy': signal['strategy'],
                    'open_time': datetime.now(timezone.utc).isoformat()
                })
                return result
        except Exception as e:
            logger.error(f"   ❌ Trade failed: {e}")
        return None
    
    def run_iteration(self):
        self.iteration += 1
        
        if self.iteration % 60 == 0:
            elapsed = (datetime.now(timezone.utc) - self.start_time).total_seconds()
            logger.info(f"📊 Status: {elapsed:.0f}s uptime | Signals: {self.signals_generated} | Trades: {self.trades_executed}")
        
        if self.iteration % 30 == 0:
            logger.info(f"\n🔍 Scanning {len(FOREX_PAIRS)} pairs...")
            signals = self.scan_all_pairs()
            
            if signals:
                logger.info(f"   Found {len(signals)} signals above threshold")
                
                # Get REAL position count from OANDA
                real_position_count = self.get_open_positions_count()
                logger.info(f"   📊 Open positions: {real_position_count}/{self.max_concurrent}")
                
                if real_position_count >= self.max_concurrent:
                    logger.info(f"   ⚠️ Max positions ({self.max_concurrent}) reached")
                    return
                
                for sig in signals[:2]:
                    self.execute_trade(sig)
                    time.sleep(2)
    
    def run(self):
        try:
            while True:
                self.run_iteration()
                time.sleep(1)
                if Path('/tmp/engine_stop').exists():
                    Path('/tmp/engine_stop').unlink()
                    break
        except KeyboardInterrupt:
            logger.info("\n⏹️ Shutdown signal received")
        except Exception as e:
            logger.error(f"❌ Fatal error: {e}", exc_info=True)
        finally:
            elapsed = (datetime.now(timezone.utc) - self.start_time).total_seconds()
            logger.info(f"✅ Engine stopped | Uptime: {elapsed:.0f}s | Signals: {self.signals_generated} | Trades: {self.trades_executed}")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['paper', 'live'], default='paper')
    args = parser.parse_args()
    AutonomousTradingEngine(mode=args.mode).run()

if __name__ == '__main__':
    main()
