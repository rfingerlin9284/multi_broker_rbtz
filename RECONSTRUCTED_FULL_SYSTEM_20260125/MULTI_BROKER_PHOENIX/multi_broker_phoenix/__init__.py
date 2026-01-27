"""Top-level import shim for repository layout.

This file makes importing `multi_broker_phoenix` work even when the
actual package is located under `MULTI_BROKER_PHOENIX/multi_broker_phoenix`.
It appends the real package path to `__path__` so Python can find it when
running from the repo root or installed in editable mode.
"""
from __future__ import annotations
import os
from pathlib import Path

# If the real package directory exists in the conventional place, add it to __path__
root = Path(__file__).resolve().parent
candidate = (root / '..' / 'MULTI_BROKER_PHOENIX' / 'multi_broker_phoenix').resolve()
if candidate.exists():
    __path__.append(str(candidate))

# When installed via pyproject, the package will be findable normally.
__all__ = []
