"""Entry Eligibility Gate

Evaluates candidate trades against a set of conservative, toggle-driven
filters to skip low-quality entries.

All behavior is config-driven via FEATURE_FLAGS['ENTRY_GATE'].
"""
from __future__ import annotations
import time
import logging
from typing import Dict, Any, List, Tuple, Optional

logger = logging.getLogger(__name__)

try:
    from global_config import FEATURE_FLAGS as _FF
except Exception:
    _FF = {}

# simple in-memory cooldown tracker (optionally persisted elsewhere)
_LAST_CLOSE: Dict[str, float] = {}


def _pip_size_for(instrument: str) -> float:
    inst = (instrument or '').upper()
    if 'JPY' in inst or inst.endswith('_JPY'):
        return 0.01
    return 0.0001


class EntryGate:
    @staticmethod
    def _log_skip(reason: str, details: Dict[str, Any]):
        logger.info('ENTRY_GATE_SKIP %s %s', reason, details)

    @staticmethod
    def evaluate(candidate: Any, market: Dict[str, Any], rm=None) -> Dict[str, Any]:
        """Evaluate candidate trade.

        candidate: object with .symbol and .side and optional entry_price
        market: dict with keys: 'bid','ask','spread_pips','prices' (list recent closes), 'ts' timestamp
        rm: RiskManager optional for exposure checks

        Returns: {'allow': bool, 'reasons': [..], 'metrics': {...}}
        """
        cfg = _FF.get('ENTRY_GATE', {})
        enabled = bool(cfg.get('enabled', True))
        if not enabled:
            return {'allow': True, 'reasons': [], 'metrics': {}}

        reasons: List[str] = []
        metrics: Dict[str, Any] = {}
        symbol = getattr(candidate, 'symbol', None) or market.get('symbol')

        # Spread check
        spread_pips = market.get('spread_pips')
        if spread_pips is None and market.get('bid') is not None and market.get('ask') is not None:
            pip = _pip_size_for(symbol)
            spread_pips = abs(market['ask'] - market['bid']) / pip
        metrics['spread_pips'] = spread_pips
        pair_type = 'MAJOR'
        if 'JPY' in (symbol or '').upper():
            pair_type = 'JPY'
        max_spread = float(cfg.get('max_spread_pips_by_pair', {}).get(pair_type, cfg.get('max_spread_pips_by_pair', {}).get('MAJOR', 1.6)))
        if spread_pips is not None and spread_pips > max_spread:
            reasons.append('SKIP_SPREAD')
            EntryGate._log_skip('SKIP_SPREAD', {'symbol': symbol, 'spread_pips': spread_pips, 'max_allowed': max_spread})

        # ATR-based volatility
        prices = market.get('prices') or []
        atr_period = int(cfg.get('atr_period', 14))
        atr = 0.0
        if len(prices) >= 2:
            # simple ATR proxy: mean of absolute diffs of consecutive closes over period
            diffs = [abs(prices[i] - prices[i-1]) for i in range(1, min(len(prices), atr_period))]
            atr = sum(diffs) / len(diffs) if diffs else 0.0
        metrics['atr'] = atr
        if atr > 0:
            if atr < float(cfg.get('atr_low_threshold', 0.0)):
                reasons.append('SKIP_LOW_VOL')
                EntryGate._log_skip('SKIP_LOW_VOL', {'symbol': symbol, 'atr': atr})
            if atr > float(cfg.get('atr_high_threshold', 999999.0)):
                reasons.append('SKIP_HIGH_VOL')
                EntryGate._log_skip('SKIP_HIGH_VOL', {'symbol': symbol, 'atr': atr})

        # Time-of-day
        ts = market.get('ts') or time.time()
        hour = time.gmtime(ts).tm_hour
        for window in cfg.get('time_of_day_disabled_windows', []):
            try:
                start_h, end_h = window
                if start_h <= hour < end_h:
                    reasons.append('SKIP_TIME_OF_DAY')
                    EntryGate._log_skip('SKIP_TIME_OF_DAY', {'symbol': symbol, 'hour': hour, 'window': window})
                    break
            except Exception:
                continue

        # Cooldown filter (per pair)
        cooldown = int(cfg.get('cooldown_seconds', 0))
        last = _LAST_CLOSE.get(symbol)
        now = time.time()
        if last and (now - last) < cooldown:
            reasons.append('SKIP_COOLDOWN')
            EntryGate._log_skip('SKIP_COOLDOWN', {'symbol': symbol, 'last_close': last, 'cooldown': cooldown})

        # Spike detector: check recent candle ranges
        spike_mult = float(cfg.get('spike_detector_multiplier', 3.0))
        recent_ranges = market.get('recent_ranges') or []
        if recent_ranges and atr > 0:
            last_range = recent_ranges[-1]
            if last_range > (spike_mult * atr):
                reasons.append('SKIP_EVENT_SPIKE')
                EntryGate._log_skip('SKIP_EVENT_SPIKE', {'symbol': symbol, 'last_range': last_range, 'atr': atr})

        # Exposure/correlation check
        max_exposure = float(cfg.get('max_exposure_per_pair_usd', 0.0))
        if rm and max_exposure > 0:
            # compute exposure for symbol in USD if risk manager has notional tracking
            try:
                exposures = rm.state.open_positions_by_symbol or {}
                units = sum(abs(int(u.get('units', u.get('currentUnits', 0)))) for u in exposures.get(symbol, [])) if isinstance(exposures.get(symbol, []), list) else 0
                # approximate notional using entry price
                entry_price = float(getattr(candidate, 'entry_price', market.get('bid') or market.get('ask') or 0.0))
                notional = units * entry_price
                metrics['current_notional_usd'] = notional
                if notional >= max_exposure:
                    reasons.append('SKIP_EXPOSURE')
                    EntryGate._log_skip('SKIP_EXPOSURE', {'symbol': symbol, 'notional': notional, 'max': max_exposure})
            except Exception:
                pass

        allow = len(reasons) == 0
        return {'allow': allow, 'reasons': reasons, 'metrics': metrics}

    @staticmethod
    def mark_close(symbol: str):
        _LAST_CLOSE[symbol] = time.time()
        logger.debug('ENTRY_GATE: mark_close %s', symbol)
