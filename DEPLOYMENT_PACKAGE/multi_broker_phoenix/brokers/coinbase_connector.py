"""Compatibility wrapper for the Coinbase connector.

RBOTzilla code/tests historically imported:

    from multi_broker_phoenix.brokers.coinbase_connector import CoinbaseConnector

The project now implements a safety-first Coinbase connector in
`coinbase_safe_connector.py`. To avoid breaking the rest of the bot (and to keep
AAA strategy work isolated), we provide this thin shim that preserves the
original import path and class name.
"""

from __future__ import annotations

from .coinbase_safe_connector import CoinbaseSafeConnector


class CoinbaseConnector(CoinbaseSafeConnector):
    """Backwards-compatible alias of :class:`CoinbaseSafeConnector`."""


__all__ = ["CoinbaseConnector"]
