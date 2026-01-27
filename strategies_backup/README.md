# Strategy Files - Reference Copy

**Date**: December 28, 2025  
**Source**: `MULTI_BROKER_PHOENIX/multi_broker_phoenix/strategies/`

## Contents

This folder contains backup copies of all trading strategy implementations for the RBOTzilla system.

### Strategy Files

1. **`base.py`** (8,796 bytes)
   - Core strategy implementations
   - Strategy registry and base class
   - Contains: `holy_grail`, `ema_scalper`, `institutional_sd`, `trap_reversal`

2. **`bullish_regime.py`** (1,604 bytes)
   - Bullish market strategy (delegates to `holy_grail`)
   - Trend-following with RSI confirmation

3. **`bearish_regime.py`** (644 bytes)
   - Bearish market strategy (delegates to `trap_reversal`)
   - Mean-reversion on spike reversals

4. **`sideways_regime.py`** (579 bytes)
   - Sideways market strategy (delegates to `institutional_sd`)
   - Volatility-based scalping

5. **`triage_regime.py`** (570 bytes)
   - Conservative strategy (delegates to `institutional_sd`)
   - Volatility-based entry

6. **`__init__.py`** (empty)
   - Module initialization file

## All Registered Strategies

| Strategy ID | Implementation | Type |
|-------------|----------------|------|
| `bearish_regime` | BearishRegime | Mean-reversion |
| `bullish_regime` | BullishRegime | Trend-following |
| `ema_scalper` | EMAScalper | EMA crossover |
| `holy_grail` | HolyGrail | RSI + Trend ⭐ |
| `institutional_sd` | InstitutionalSD | Volatility-based |
| `sideways_regime` | SidewaysRegime | Range-bound |
| `trap_reversal` | TrapReversal | Spike reversal |
| `triage_regime` | TriageRegime | Conservative |

⭐ = Currently active strategy

## Usage

These files are reference copies. To modify active strategies, edit the originals in:
```
MULTI_BROKER_PHOENIX/multi_broker_phoenix/strategies/
```

To switch strategies, edit `.env`:
```bash
DEFAULT_STRATEGY=holy_grail  # Change to any strategy ID above
```

## Notes

- All strategies inherit from `Strategy` base class
- Regime strategies are aliases that delegate to core implementations
- Strategies are auto-registered via `@register_strategy` decorator
- Current active: `holy_grail` (trend + RSI)
