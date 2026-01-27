"""Simple deterministic scorecard for signal quality.
"""
from __future__ import annotations
from typing import Dict, Any, List
import logging
try:
    from global_config import FEATURE_FLAGS as _FF
except Exception:
    _FF = {}

logger = logging.getLogger(__name__)


def score_signal(features: Dict[str, float], cfg: Dict[str, Any] = None) -> Dict[str, Any]:
    cfg = cfg or _FF.get('SCORECARD', {})
    weights = cfg.get('weights', {})
    # normalize weights sum to 1.0
    total = sum(weights.values()) or 1.0
    normalized = {k: v / total for k, v in weights.items()}

    score = 0.0
    reasons: List[str] = []
    # feature keys: htf_alignment, structure, momentum, volatility_sanity, spread_sanity, risk_feasibility
    for k, w in normalized.items():
        val = float(features.get(k, 0.0))
        score += val * 100.0 * w
        if val < 0.5:
            reasons.append(f'LOW_{k.upper()}')

    score = max(0.0, min(100.0, score))
    min_thresh = float(cfg.get('min_score_threshold', 70))
    passed = score >= min_thresh
    if not passed:
        logger.info('SCORECARD_SKIP score=%s min=%s reasons=%s', score, min_thresh, reasons)
    return {'score': score, 'passed': passed, 'reasons': reasons}
