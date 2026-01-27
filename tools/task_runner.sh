#!/usr/bin/env bash
set -euo pipefail

# Determine repo root
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.."; pwd)"

# Load environment deterministically
source "${ROOT}/tools/env_load.sh"

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

# Defensive: if task name is passed twice, drop the duplicate
if [[ "${1:-}" == "$task_name" ]]; then
  shift
fi

if [[ $# -lt 1 ]]; then
  echo "Usage: task_runner.sh <task_name> <command...>"
  exit 2
fi

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

# Baseline drift check (commit + toggles_hash + script_hash)
baseline_dir="$ROOT/ops/state/task_baselines"
baseline_file="$baseline_dir/${task_name}.json"
mkdir -p "$baseline_dir"

auto_baseline="${TASK_BASELINE_AUTO:-0}"
force_baseline="${TASK_BASELINE_RESET:-0}"

if [[ -f "$baseline_file" && "$force_baseline" != "1" ]]; then
  base_commit="$(python3 - <<PY
import json
try:
  print(json.load(open('$baseline_file')).get('commit',''))
except Exception:
  print('')
PY
)"
  base_toggles="$(python3 - <<PY
import json
try:
  print(json.load(open('$baseline_file')).get('toggles_hash',''))
except Exception:
  print('')
PY
)"
  base_script="$(python3 - <<PY
import json
try:
  print(json.load(open('$baseline_file')).get('script_hash',''))
except Exception:
  print('')
PY
)"

  drift=0
  if [[ -n "$base_commit" && -n "$commit" && "$base_commit" != "$commit" ]]; then
    drift=1
  fi
  if [[ -n "$base_toggles" && -n "$toggles_hash" && "$base_toggles" != "$toggles_hash" ]]; then
    drift=1
  fi
  if [[ -n "$base_script" && -n "$script_hash" && "$base_script" != "$script_hash" ]]; then
    drift=1
  fi

  if [[ $drift -eq 1 ]]; then
    echo "❌ DRIFT DETECTED: baseline mismatch for task '$task_name'"
    if [[ "$auto_baseline" == "1" ]]; then
      python3 - <<PY
import json
out = {
  'task_name': '$task_name',
  'commit': '$commit',
  'toggles_hash': '$toggles_hash',
  'script_hash': '$script_hash'
}
with open('$baseline_file','w') as f:
  json.dump(out, f, indent=2)
PY
      echo "✅ BASELINE UPDATED (auto)"
    else
      echo "   Suggestion: re-baseline after verifying changes are intended"
      exit 3
    fi
  else
    echo "✅ BASELINE OK"
  fi
else
  if [[ $exit_code -eq 0 ]]; then
    python3 - <<PY
import json
out = {
  'task_name': '$task_name',
  'commit': '$commit',
  'toggles_hash': '$toggles_hash',
  'script_hash': '$script_hash'
}
with open('$baseline_file','w') as f:
  json.dump(out, f, indent=2)
PY
    echo "✅ BASELINE STORED"
  else
    echo "⚠️ BASELINE NOT STORED (command failed)"
  fi
fi

if [[ "$force_baseline" == "1" && -f "$baseline_file" ]]; then
  python3 - <<PY
import json
out = {
  'task_name': '$task_name',
  'commit': '$commit',
  'toggles_hash': '$toggles_hash',
  'script_hash': '$script_hash'
}
with open('$baseline_file','w') as f:
  json.dump(out, f, indent=2)
PY
  echo "✅ BASELINE RESET"
fi

exit $exit_code
