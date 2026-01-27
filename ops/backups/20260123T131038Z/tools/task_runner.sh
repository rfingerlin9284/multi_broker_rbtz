#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: task_runner.sh <task_name> <command...>"
  exit 2
fi

task_name="$1"
shift

ROOT="/home/ing/RICK/MULTI_BROKER_PHOENIX"
LOG_ROOT="$ROOT/ops/task_runs/$task_name"
mkdir -p "$LOG_ROOT"

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
log_file="$LOG_ROOT/${stamp}.log"
summary_file="$LOG_ROOT/${stamp}.summary.txt"
json_file="$LOG_ROOT/${stamp}.json"

cmd_display="$*"

# Capture called script hash (best-effort)
script_path="${1:-}"
script_hash=""
if [[ -n "$script_path" && -f "$script_path" ]]; then
  script_hash="$(python3 - "$script_path" <<'PY'
import hashlib
import sys
path = sys.argv[1]
try:
    data = open(path, 'rb').read()
    print(hashlib.sha256(data).hexdigest())
except Exception:
    print('')
PY
)"
fi

# Capture git commit if available
commit=""
if command -v git >/dev/null 2>&1 && git -C "$ROOT" rev-parse --git-dir >/dev/null 2>&1; then
  commit="$(git -C "$ROOT" rev-parse HEAD 2>/dev/null || true)"
fi

# Capture toggles snapshot hash (no secrets)
toggles_hash=""
if [[ -f "$ROOT/config/toggles.env" ]]; then
  toggles_hash="$(python3 - <<'PY'
import hashlib
p = '/home/ing/RICK/MULTI_BROKER_PHOENIX/config/toggles.env'
try:
    data = open(p, 'rb').read()
    print(hashlib.sha256(data).hexdigest())
except Exception:
    print('')
PY
)"
fi

# Run command and capture output
set +e
{
  echo "=== TASK RUNNER START ==="
  echo "task_name=${task_name}"
  echo "timestamp=${stamp}"
  echo "command=${cmd_display}"
  echo "script_path=${script_path}"
  echo "script_hash=${script_hash}"
  echo "commit=${commit}"
  echo "toggles_hash=${toggles_hash}"
  echo "=========================="
  "$@"
} 2>&1 | tee "$log_file"
exit_code=${PIPESTATUS[0]}
set -e

# Summary: last 200 lines
if [[ -f "$log_file" ]]; then
  tail -n 200 "$log_file" > "$summary_file" || true
fi

summary_hash="$(python3 - "$task_name" "$stamp" <<'PY'
import hashlib
import sys
task = sys.argv[1]
stamp = sys.argv[2]
p = f'/home/ing/RICK/MULTI_BROKER_PHOENIX/ops/task_runs/{task}/{stamp}.summary.txt'
try:
  data = open(p, 'rb').read()
  print(hashlib.sha256(data).hexdigest())
except Exception:
  print('')
PY
)"

# Find last successful run
prev_summary=""
prev_hash=""
python3 - "$task_name" <<'PY'
import json, glob, os
import sys
root = f"/home/ing/RICK/MULTI_BROKER_PHOENIX/ops/task_runs/{sys.argv[1]}"
paths = sorted(glob.glob(os.path.join(root, '*.json')))
last = None
for p in paths[::-1]:
    try:
        with open(p) as f:
            d = json.load(f)
        if d.get('exit_code') == 0:
            last = d
            break
    except Exception:
        continue
if last:
  print(last.get('summary_file',''))
  print(last.get('summary_hash',''))
PY
> "$LOG_ROOT/.prev_summary.tmp" || true

if [[ -f "$LOG_ROOT/.prev_summary.tmp" ]]; then
  prev_summary="$(sed -n '1p' "$LOG_ROOT/.prev_summary.tmp")"
  prev_hash="$(sed -n '2p' "$LOG_ROOT/.prev_summary.tmp")"
  rm -f "$LOG_ROOT/.prev_summary.tmp"
fi

# Write JSON metadata
python3 - <<PY
import json
out = {
  'task_name': '$task_name',
  'timestamp': '$stamp',
  'command': '$cmd_display',
  'script_path': '$script_path',
  'script_hash': '$script_hash',
  'exit_code': $exit_code,
  'commit': '$commit',
  'toggles_hash': '$toggles_hash',
  'log_file': '$log_file',
  'summary_file': '$summary_file',
  'summary_hash': '$summary_hash'
}
with open('$json_file','w') as f:
  json.dump(out, f, indent=2)
PY

# Compare to baseline
if [[ -n "$prev_hash" && -n "$summary_hash" ]]; then
  if [[ "$prev_hash" == "$summary_hash" ]]; then
    echo "✅ SAME AS BASELINE"
  else
    echo "⚠️ DIFFERENT FROM BASELINE (summary diff below)"
    if [[ -f "$prev_summary" && -f "$summary_file" ]]; then
      diff -u "$prev_summary" "$summary_file" || true
    fi
  fi
else
  echo "⚠️ BASELINE NOT FOUND (first successful run establishes baseline)"
fi

exit $exit_code
