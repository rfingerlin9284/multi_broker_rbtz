"""Top-level import shim for repository layout.

This file makes importing `multi_broker_phoenix` work even when the
actual package is located under `MULTI_BROKER_PHOENIX/multi_broker_phoenix`.
It appends the real package path to `__path__` so Python can find it when
running from the repo root or installed in editable mode.
"""
from __future__ import annotations
import os
from pathlib import Path

# If alternate package directories exist, add them to __path__ (prefer canonical paths).
root = Path(__file__).resolve().parent
repo_root = root.parents[2]

candidates = [
    (repo_root / 'DEPLOYMENT_PACKAGE' / 'multi_broker_phoenix').resolve(),
    (repo_root / 'multi_broker_phoenix').resolve(),
]

for candidate in candidates:
    if candidate.exists() and str(candidate) not in __path__:
        __path__.insert(0, str(candidate))

# When installed via pyproject, the package will be findable normally.
__all__ = []
