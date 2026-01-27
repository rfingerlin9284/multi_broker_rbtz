"""Connectivity test for the practice OANDA execution client."""
from __future__ import annotations

import os
from pathlib import Path

from execution.oanda_practice_client import OandaPracticeClient


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
            # strip inline comments (only after '=')
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
            parsed[k] = v  # last-wins within file

    for k, v in parsed.items():
        if k not in os.environ:
            os.environ[k] = v


_load_env()


def main() -> None:
    client = OandaPracticeClient()
    summary = client.get_account_summary()
    account = summary.get('account', {})
    print("OANDA Practice connectivity test")
    print("--------------------------------")
    print(f"Account ID: {account.get('accountID')}")
    print(f"Currency: {account.get('currency')}")
    print(f"Balance: {account.get('balance')}")
    print("Raw payload:", summary)


if __name__ == '__main__':
    main()
