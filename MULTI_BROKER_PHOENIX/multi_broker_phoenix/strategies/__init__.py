"""Strategies package.

Important: Many strategies register themselves via the @register_strategy decorator.
To ensure the registry contains the full RBOTzilla strategy set, we import all
strategy modules here for their registration side-effects.

FABIO_AAA_FULL is intentionally self-contained and *does not* change the
behavior of other strategies; it is only used when explicitly selected.
"""

# Canonical strategies
from . import base

# Optional / specialty strategies
from . import gbp_usd_only

# Regime/meta strategies
from . import bullish_regime
from . import bearish_regime
from . import sideways_regime
from . import triage_regime

# AAA strategy (self-contained; opt-in by DEFAULT_STRATEGY / explicit selection)
from . import fabio_aaa_full

__all__ = [
	'base',
	'gbp_usd_only',
	'bullish_regime',
	'bearish_regime',
	'sideways_regime',
	'triage_regime',
	'fabio_aaa_full',
]
