from __future__ import annotations
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

DEFAULT_PATH = Path('multi_broker_phoenix/config/platform_breakers.json')

@dataclass
class BreakerState:
    enabled: bool = True
    reason: str = ''
    updated_utc: str = ''

def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

def load_breakers(path: Path = DEFAULT_PATH) -> Dict[str, BreakerState]:
    if not path.exists():
        return {k: BreakerState(True) for k in ('oanda','coinbase','ibkr')}
    try:
        data = json.loads(path.read_text(encoding='utf-8')) or {}
    except Exception:
        data = {}
    out: Dict[str, BreakerState] = {}
    for k in ('oanda','coinbase','ibkr'):
        v = data.get(k, {}) if isinstance(data, dict) else {}
        out[k] = BreakerState(
            enabled=bool(v.get('enabled', True)),
            reason=str(v.get('reason', '') or ''),
            updated_utc=str(v.get('updated_utc', '') or ''),
        )
    return out

def is_platform_enabled(platform: str, path: Path = DEFAULT_PATH) -> bool:
    platform = (platform or '').lower().strip()
    st = load_breakers(path).get(platform)
    if st is None:
        return True
    return bool(st.enabled)

def set_platform_enabled(platform: str, enabled: bool, reason: str = '', path: Path = DEFAULT_PATH) -> Dict[str, Any]:
    platform = (platform or '').lower().strip()
    if platform not in ('oanda','coinbase','ibkr'):
        raise ValueError(f'Unknown platform: {platform}')
    breakers = load_breakers(path)
    breakers[platform] = BreakerState(bool(enabled), str(reason or ''), _utc_now_iso())
    data = {
        k: {'enabled': bool(v.enabled), 'reason': v.reason, 'updated_utc': v.updated_utc}
        for k,v in breakers.items()
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return data
