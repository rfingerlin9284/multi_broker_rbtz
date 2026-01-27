"""Runtime configuration helpers for trading modes and execution types.

Env vars:
- TRADING_MODE: 'SIMULATED'|'PAPER'|'LIVE' (default 'PAPER')
- PAPER_VIA_PLATFORM: '1'|'0' (default '0')
- ALLOW_LIVE_REAL: '1'|'0' (default '0')
- TEST_ORDER_MAX_USD: number (default 10)
- TEST_ORDER_MAX_PER_DAY: int (default 2)
"""
from __future__ import annotations
import os
from typing import Literal

TradingMode = Literal['SIMULATED', 'PAPER', 'LIVE']


def _get_env_bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip() not in ('0', 'false', 'False', '')


def get_trading_mode() -> TradingMode:
    v = os.getenv('TRADING_MODE', 'PAPER').upper()
    if v not in ('SIMULATED', 'PAPER', 'LIVE'):
        return 'PAPER'
    return v  # type: ignore


def paper_via_platform() -> bool:
    # Default to True to favor platform paper where available (safer ops than LIVE)
    return _get_env_bool('PAPER_VIA_PLATFORM', True)


def allow_live_real() -> bool:
    return _get_env_bool('ALLOW_LIVE_REAL', False)


def test_order_max_usd() -> float:
    try:
        return float(os.getenv('TEST_ORDER_MAX_USD', '10'))
    except Exception:
        return 10.0


def test_order_max_per_day() -> int:
    try:
        return int(os.getenv('TEST_ORDER_MAX_PER_DAY', '2'))
    except Exception:
        return 2


def resolve_execution_type(platform_name: str, supports_platform_paper: bool = False) -> str:
    """Return one of 'SIMULATED', 'PLATFORM_PAPER', 'LIVE_REAL' based on env config
    and platform capability.
    """
    mode = get_trading_mode()
    if mode == 'SIMULATED':
        return 'SIMULATED'
    if mode == 'PAPER':
        if paper_via_platform() and supports_platform_paper:
            return 'PLATFORM_PAPER'
        return 'SIMULATED'
    # mode == LIVE
    if allow_live_real():
        return 'LIVE_REAL'
    # fallback to safety
    return 'SIMULATED'
