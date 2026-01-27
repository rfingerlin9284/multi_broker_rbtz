"""Unified Signal Brain – Full Indicator Scanning + Confluence

Provides a self-contained, defensive implementation suitable for import in
strategies. Includes lightweight fallbacks (no hard dependency on pandas).
"""
from __future__ import annotations

import logging
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime

import numpy as np

logger = logging.getLogger("signal_brain")
logger.setLevel(logging.INFO)

# Try to optionally use pandas for EMA convenience; provide fallback if absent
try:
    import pandas as pd
except Exception:  # pragma: no cover - pandas optional
    pd = None


def _ema_array(values: List[float], span: int) -> float:
    """Return final EMA value for `values` and `span`.
    Uses pandas if available, otherwise a simple numpy-based EMA.
    """
    if pd is not None:
        return pd.Series(values).ewm(span=span, adjust=False).mean().iloc[-1]

    # Numpy fallback (standard EMA calculation)
    vals = np.asarray(values, dtype=float)
    alpha = 2.0 / (span + 1.0)
    ema = vals[0]
    for v in vals[1:]:
        ema = alpha * v + (1 - alpha) * ema
    return float(ema)


class Layer1_CharterGuard:
    def evaluate(self, symbol: str, context: Dict[str, Any]) -> Dict[str, Any]:
        return {"decision": "PASS", "confidence": 1.0, "veto": False, "meta": {}}


class Layer2_MarketStructure:
    def evaluate(self, symbol: str, context: Dict[str, Any]) -> Dict[str, Any]:
        return {"decision": "PASS", "confidence": 1.0, "veto": False, "meta": {}}


class Layer3_FullIndicatorScan:
    """Scans indicators and builds a confluence vote for BUY/SELL.

    Defensive: returns empty indicators dict if not enough data.
    """

    def __init__(self):
        # Minimum agreeing indicators for a signal; tunable
        self.required_confluence = 6

    def _calculate_indicators(
        self, closes: List[float], highs: List[float], lows: List[float], volumes: List[float]
    ) -> Dict[str, float]:
        # Require a reasonable minimum amount of data
        if len(closes) < 50:
            return {}

        c = np.asarray(closes, dtype=float)
        h = np.asarray(highs, dtype=float)
        l = np.asarray(lows, dtype=float)
        v = np.asarray(volumes, dtype=float)

        ind: Dict[str, float] = {}

        # SMA various periods (only if available)
        for p in [5, 10, 20, 50, 100, 200]:
            if len(c) >= p:
                ind[f"SMA_{p}"] = float(np.mean(c[-p:]))

        # EMA various periods
        for p in [9, 21, 50, 100]:
            if len(c) >= p:
                ind[f"EMA_{p}"] = float(_ema_array(list(c[-(p * 3) :] if len(c) >= p * 3 else list(c)), p))

        # RSI 14
        if len(c) >= 15:
            delta = np.diff(c)
            gain = np.where(delta > 0, delta, 0.0)
            loss = np.where(delta < 0, -delta, 0.0)
            avg_gain = np.mean(gain[-14:]) if len(gain) >= 14 else np.mean(gain) if len(gain) > 0 else 0.0
            avg_loss = np.mean(loss[-14:]) if len(loss) >= 14 else np.mean(loss) if len(loss) > 0 else 1e-9
            ind["RSI_14"] = float(100.0 - (100.0 / (1.0 + (avg_gain / (avg_loss or 1e-9)))))

        # MACD (12,26,9)
        if len(c) >= 26:
            ema12 = _ema_array(list(c), 12)
            ema26 = _ema_array(list(c), 26)
            ind["MACD_LINE"] = float(ema12 - ema26)
            # Approximate signal using last values
            # For robustness, compute MACD series and then its EMA if possible
            try:
                macd_series = np.array([_ema_array(list(c[:i + 1]), 12) - _ema_array(list(c[:i + 1]), 26) for i in range(len(c))])
                ind["MACD_SIGNAL"] = float(_ema_array(list(macd_series), 9))
            except Exception:
                ind["MACD_SIGNAL"] = 0.0

        # Bollinger Bands (20,2)
        if len(c) >= 20:
            mid = float(np.mean(c[-20:]))
            std = float(np.std(c[-20:]))
            ind["BB_UPPER"] = mid + 2.0 * std
            ind["BB_LOWER"] = mid - 2.0 * std

        # ATR 14
        if len(c) >= 15:
            prev_close = np.roll(c, 1)
            tr = np.maximum(h - l, np.maximum(np.abs(h - prev_close), np.abs(l - prev_close)))[1:]
            ind["ATR_14"] = float(np.mean(tr[-14:]))

        # Stochastic (14,3,3)
        if len(c) >= 14:
            low14 = float(np.min(l[-14:]))
            high14 = float(np.max(h[-14:]))
            ind["STOCH_K"] = float(100.0 * (c[-1] - low14) / (high14 - low14 + 1e-9))

        # ADX 14 (simplified proxy)
        try:
            if len(c) >= 26:
                prev_h = np.roll(h, 1)
                prev_l = np.roll(l, 1)
                plus = (h - prev_h)[1:]
                minus = (prev_l - l)[1:]
                tr = np.maximum(h - l, np.maximum(np.abs(h - prev_close), np.abs(l - prev_close)))[1:]
                plus_di = 100.0 * np.mean(plus[-14:] / (tr[-14:] + 1e-9))
                minus_di = 100.0 * np.mean(minus[-14:] / (tr[-14:] + 1e-9))
                ind["ADX_14"] = float(100.0 * abs(plus_di - minus_di) / (plus_di + minus_di + 1e-9))
        except Exception:
            ind["ADX_14"] = 0.0

        # CCI 20
        if len(c) >= 20:
            tp = (h + l + c) / 3.0
            sma_tp = float(np.mean(tp[-20:]))
            mad = float(np.mean(np.abs(tp[-20:] - sma_tp)))
            ind["CCI_20"] = float((tp[-1] - sma_tp) / (0.015 * mad + 1e-9))

        # Ichimoku (simplified)
        if len(c) >= 26:
            ind["ICH_TENKAN"] = float((np.max(h[-9:]) + np.min(l[-9:])) / 2.0)
            ind["ICH_KIJUN"] = float((np.max(h[-26:]) + np.min(l[-26:])) / 2.0)

        # Fibonacci (last swing proxy)
        if len(c) >= 50:
            swing_high = float(np.max(h[-50:]))
            swing_low = float(np.min(l[-50:]))
            ind["FIB_618"] = swing_low + 0.618 * (swing_high - swing_low)

        # Pivot Points (classic single period pivot)
        ind["PIVOT"] = float((h[-1] + l[-1] + c[-1]) / 3.0)

        # Volume MA
        if len(v) >= 20:
            ind["VOL_MA_20"] = float(np.mean(v[-20:]))

        return ind

    def _confluence_vote(self, indicators: Dict[str, float], last_price: float) -> Tuple[Optional[str], float, int, int]:
        bull_votes = 0
        bear_votes = 0

        # RSI
        rsi = indicators.get("RSI_14")
        if rsi is not None:
            if rsi < 30:
                bull_votes += 1
            if rsi > 70:
                bear_votes += 1

        # MACD
        macd = indicators.get("MACD_LINE")
        macd_sig = indicators.get("MACD_SIGNAL")
        if macd is not None and macd_sig is not None:
            if macd > macd_sig:
                bull_votes += 1
            elif macd < macd_sig:
                bear_votes += 1

        # Bollinger
        upper = indicators.get("BB_UPPER")
        lower = indicators.get("BB_LOWER")
        if upper is not None and lower is not None:
            if last_price > upper:
                bear_votes += 1
            if last_price < lower:
                bull_votes += 1

        # ADX: strong trend (if >25) strengthens the larger side
        adx = indicators.get("ADX_14")
        if adx is not None and adx > 25:
            if bull_votes > bear_votes:
                bull_votes += 1
            elif bear_votes > bull_votes:
                bear_votes += 1

        # CCI extremes
        cci = indicators.get("CCI_20")
        if cci is not None:
            if cci < -100:
                bull_votes += 1
            if cci > 100:
                bear_votes += 1

        # Volume confirmation
        vol_ma = indicators.get("VOL_MA_20")
        if vol_ma is not None:
            # If last volume above MA, slightly favor current moves (not computed here)
            pass

        total_votes = bull_votes + bear_votes
        if total_votes < self.required_confluence:
            return None, 0.0, bull_votes, bear_votes

        if bull_votes > bear_votes:
            return "BUY", bull_votes / total_votes, bull_votes, bear_votes
        elif bear_votes > bull_votes:
            return "SELL", bear_votes / total_votes, bull_votes, bear_votes
        return None, 0.0, bull_votes, bear_votes

    def evaluate(self, symbol: str, context: Dict[str, Any]) -> Dict[str, Any]:
        candles = context.get("candles", [])
        if not candles:
            return {"decision": None, "confidence": 0.0, "veto": False, "meta": {}}

        # Build arrays
        closes = [float(c["mid"]["c"]) for c in candles if "mid" in c]
        highs = [float(c["mid"]["h"]) for c in candles if "mid" in c]
        lows = [float(c["mid"]["l"]) for c in candles if "mid" in c]
        volumes = [int(c.get("volume", 0)) for c in candles]

        indicators = self._calculate_indicators(closes, highs, lows, volumes)
        if not indicators:
            return {"decision": None, "confidence": 0.0, "veto": False, "meta": {"indicators": indicators}}

        last_price = float(closes[-1])
        decision, conf, bull_votes, bear_votes = self._confluence_vote(indicators, last_price)

        meta = {"indicators": indicators, "confluence_votes": {"bull": bull_votes, "bear": bear_votes}}
        logger.info(f"[FullScan] {symbol} scanned {len(indicators)} indicators → {decision} (conf {conf:.2f})")
        return {"decision": decision, "confidence": conf, "veto": False, "meta": meta}


class SignalBrain:
    def __init__(self):
        self.layers = [
            Layer1_CharterGuard(),
            Layer2_MarketStructure(),
            Layer3_FullIndicatorScan(),
        ]

    def process(self, symbol: str, candles: List[Dict]) -> Tuple[Optional[str], float, Dict]:
        context = {"candles": candles, "layers": {}}
        final_signal: Optional[str] = None
        final_conf = 0.0
        meta: Dict[str, Any] = {"layers": {}}

        for layer in self.layers:
            result = layer.evaluate(symbol, context)
            context["layers"][layer.__class__.__name__] = result.get("meta", {})
            meta["layers"][layer.__class__.__name__] = result.get("meta", {})

            if result.get("veto"):
                final_signal = None
                final_conf = 0.0
                break

            if result.get("decision") in ("BUY", "SELL"):
                if result.get("confidence", 0.0) > final_conf:
                    final_signal = result.get("decision")
                    final_conf = result.get("confidence", 0.0)

        return final_signal, final_conf, meta


brain = SignalBrain()


def unified_signal(symbol: str, candles: List[Dict]) -> Tuple[Optional[str], float, Dict]:
    return brain.process(symbol, candles)
