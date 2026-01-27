#!/usr/bin/env bash
python3 - <<PY
import yaml, json
p='tasks.yaml'
try:
    t=yaml.safe_load(open(p))
    print(t.get('DEFAULT_DASHBOARD_TASK',''))
except Exception as e:
    print('')
PY