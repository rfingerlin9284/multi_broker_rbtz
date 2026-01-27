#!/usr/bin/env bash
# Smoke tests for package importability.
set -euo pipefail
python3 -c "import multi_broker_phoenix; print('OK: import multi_broker_phoenix')"
python3 -c "from multi_broker_phoenix.engines.real_trading_engine import RealTradingEngine; print('OK: import RealTradingEngine')"
echo "Smoke import tests passed"