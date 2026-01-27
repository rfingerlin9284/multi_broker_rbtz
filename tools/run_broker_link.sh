#!/usr/bin/env bash
# Wrapper to run broker_link as a foreground process (used by systemd unit)
set -euo pipefail
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"
# Use repo python packages in case not installed
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"
exec python3 -m multi_broker_phoenix.services.broker_link
