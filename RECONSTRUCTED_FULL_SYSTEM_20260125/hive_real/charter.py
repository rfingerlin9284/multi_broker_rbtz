"""Hive Charter enforcement helpers.

Provides:
 - the canonical system prompt (strict charter)
 - a simple JSON schema validator for seat outputs
 - helper to record charter violations to ops/state/hive_violations.json
"""
from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Tuple, List, Dict, Any

ROOT = Path(__file__).resolve().parent.parent
OPS = ROOT / 'ops' / 'state'
OPS.mkdir(parents=True, exist_ok=True)
VIOLATIONS = OPS / 'hive_violations.jsonl'

CHARter_TEXT = """
RBOTzilla HIVE CHARTER - SYSTEM PROMPT

PRIME DIRECTIVE: Survive first. Profit second. Ego never.

You are a strict, disciplined trading advisor. You MUST produce a single JSON object matching the seat output contract.
If you cannot justify a trade in JSON, return {"decision":"HOLD"}.

Follow the Hive Charter rules (safety, OCO, invalidation, JSON-only, fail-closed in LIVE, etc.)
"""

# Required fields for seat outputs and basic types
REQUIRED_FIELDS = {
    'seat': str,
    'decision': str,  # BUY|SELL|HOLD|VETO
    'confidence': (int, float),
    'pair': str,
    'timeframe': str,
    'entry': dict,
    'stop_loss': dict,
    'take_profit': dict,
    'r_multiple_est': (int, float),
    'key_reasons': list,
    'invalidation': list,
    'self_heal_actions': list,
}

ALLOWED_DECISIONS = {'BUY', 'SELL', 'HOLD', 'VETO'}


def get_system_prompt() -> str:
    """Return the canonical charter that MUST be used as the system prompt."""
    # Keep the system prompt concise but authoritative
    return CHARter_TEXT.strip()


def validate_seat_output(obj: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate a seat output dict against required fields and constraints.
    Returns (ok, errors)
    """
    errors: List[str] = []
    if not isinstance(obj, dict):
        return False, ['not_a_json_object']
    for k, t in REQUIRED_FIELDS.items():
        if k not in obj:
            errors.append(f'missing:{k}')
            continue
        v = obj[k]
        expected = t
        if isinstance(t, tuple):
            if not isinstance(v, t):
                errors.append(f'bad_type:{k}')
        else:
            if not isinstance(v, t):
                errors.append(f'bad_type:{k}')
    # decision constraints
    dec = obj.get('decision')
    if dec and dec.upper() not in ALLOWED_DECISIONS:
        errors.append('invalid_decision')
    # confidence range
    conf = obj.get('confidence')
    try:
        if conf is None or not (0.0 <= float(conf) <= 1.0):
            errors.append('invalid_confidence')
    except Exception:
        errors.append('invalid_confidence')
    # entry/stop/tp sanity: price numbers
    for name in ('entry', 'stop_loss', 'take_profit'):
        val = obj.get(name)
        if isinstance(val, dict):
            price = val.get('price')
            if price is None:
                errors.append(f'missing_price:{name}')
            else:
                try:
                    float(price)
                except Exception:
                    errors.append(f'invalid_price:{name}')
    return (len(errors) == 0), errors


def record_violation(source: str, content: Any, errors: List[str]):
    rec = {'ts': time.time(), 'source': source, 'errors': errors, 'content': content}
    try:
        with open(VIOLATIONS, 'a') as f:
            f.write(json.dumps(rec) + '\n')
    except Exception:
        pass


# Small helper used by seats/tests to assert schema
def assert_valid_or_raise(obj: Dict[str, Any]):
    ok, errs = validate_seat_output(obj)
    if not ok:
        record_violation(obj.get('seat', 'unknown'), obj, errs)
        raise ValueError('Seat output invalid: ' + ','.join(errs))
