# Package initializer for tools
# Avoid importing submodules at package import time to prevent import-time
# dependency cycles during test collection. Import submodules explicitly in
# consumers where needed.
try:
    from .backtest import Backtester  # optional
except Exception:
    Backtester = None

__all__ = ["Backtester"] if Backtester is not None else []
