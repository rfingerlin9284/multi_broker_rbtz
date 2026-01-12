#!/usr/bin/env bash
set -euo pipefail

IBKR_HOST=${IBKR_HOST:-}
IBKR_PORT=${IBKR_PORT:-}
IBKR_CLIENT_ID=${IBKR_CLIENT_ID:-}

if [[ -z "$IBKR_HOST" || -z "$IBKR_PORT" || -z "$IBKR_CLIENT_ID" ]]; then
  echo "ERROR: Please export IBKR_HOST, IBKR_PORT and IBKR_CLIENT_ID"
  exit 2
fi

python - <<PY
import os
from ibkr_gateway.ibkr_connector import IBKRConnector
c = IBKRConnector()
ok = c.connect()
print('connect_ok=', ok)
# Try a minimal place_order simulation (won't run if execution disabled)
import json
os.environ['EXECUTION_ENABLED'] = os.environ.get('EXECUTION_ENABLED', '0')
print('EXECUTION_ENABLED=', os.environ['EXECUTION_ENABLED'])
PY
