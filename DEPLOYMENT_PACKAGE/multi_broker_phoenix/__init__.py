"""Namespace shim to allow merged package layout across repo paths."""
from __future__ import annotations

from pathlib import Path

root = Path(__file__).resolve().parent
repo_root = root.parents[1]

candidates = [
	(repo_root / 'multi_broker_phoenix').resolve(),
	(repo_root / 'MULTI_BROKER_PHOENIX' / 'multi_broker_phoenix').resolve(),
]

for candidate in candidates:
	if candidate.exists() and str(candidate) not in __path__:
		__path__.append(str(candidate))

__all__ = []
