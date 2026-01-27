"""IBKR practice connectivity test.

Attempts to use the IBKR live connector (paper, port 4002) if ib_insync is
installed and IBKR env vars are present. Falls back to the simple simulated
IBKRConnector if the live connector is not available.
"""
from __future__ import annotations

# pyright: reportMissingImports=false

import os
import sys
from pathlib import Path


# Allow running this script directly from the repo without PYTHONPATH exports.
_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / 'MULTI_BROKER_PHOENIX'))


def _load_env() -> None:
    """Load repo-root .env without overriding existing process environment."""
    repo_root = Path(__file__).resolve().parents[1]
    env_path = repo_root / '.env'
    if not env_path.exists():
        return

    parsed: dict[str, str] = {}
    with env_path.open('r', encoding='utf-8', errors='ignore') as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            if '#' in line:
                eq = line.find('=')
                hp = line.find('#', eq)
                if hp > 0:
                    line = line[:hp].strip()
            if '=' not in line:
                continue
            k, v = line.split('=', 1)
            k = k.strip()
            v = v.strip()
            if not k:
                continue
            parsed[k] = v

    for k, v in parsed.items():
        if k not in os.environ:
            os.environ[k] = v


_load_env()

try:
    from multi_broker_phoenix.brokers.ibkr_connector_live import get_ibkr_connector
    IBKR_LIVE_AVAILABLE = True
except Exception:
    get_ibkr_connector = None  # type: ignore[assignment]
    IBKR_LIVE_AVAILABLE = False

try:
    from multi_broker_phoenix.brokers.ibkr_connector import IBKRConnector
except Exception:
    IBKRConnector = None


def main() -> None:
    print("IBKR Practice connectivity test")
    print("---------------------------------")

    if IBKR_LIVE_AVAILABLE and get_ibkr_connector is not None:
        conn = get_ibkr_connector(paper_mode=True)
        ok = conn.connect()
        print(f"IBKRLiveConnector available. Connected: {ok}")
        if ok:
            summary = conn.get_account_summary()
            print("Account summary:", summary)
        else:
            print("Could not connect to IBKR Gateway. Ensure TWS/Gateway is running on port 4002 and IBKR_HOST/IBKR_PORT/IBKR_CLIENT_ID env vars are set.")
        return

    if IBKRConnector is not None:
        print("IBKR live connector not available; falling back to simulated IBKRConnector")
        conn = IBKRConnector()
        print("Simulated connector initialized. Use engine to simulate orders or seed price using conn.update_price(symbol, price).")
        return

    print("No IBKR connector found in the codebase. Please install or check repository layout.")


if __name__ == '__main__':
    main()
