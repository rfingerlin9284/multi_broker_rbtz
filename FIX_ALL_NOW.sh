#!/usr/bin/env bash
set -euo pipefail

ts() { date +"%Y-%m-%d %H:%M:%S"; }
say() { printf "[%s] %s\n" "$(ts)" "$*"; }
die() { say "❌ $*"; exit 1; }

ROOT="${1:-$(pwd)}"

# Locate the actual project root that contains tools/resume_paper_now.sh
find_base() {
  local start="$1"
  if [[ -f "$start/tools/resume_paper_now.sh" && -d "$start/multi_broker_phoenix" ]]; then
    echo "$start"; return 0
  fi
  if [[ -d "$start/MULTI_BROKER_PHOENIX" && -f "$start/MULTI_BROKER_PHOENIX/tools/resume_paper_now.sh" ]]; then
    echo "$start/MULTI_BROKER_PHOENIX"; return 0
  fi
  local hit
  hit="$(find "$start" -maxdepth 4 -type f -path "*/tools/resume_paper_now.sh" -print -quit 2>/dev/null || true)"
  if [[ -n "${hit:-}" ]]; then
    echo "$(cd "$(dirname "$hit")/.." && pwd)"; return 0
  fi
  return 1
}

BASE="$(find_base "$ROOT" || true)"
[[ -n "${BASE:-}" ]] || die "Couldn't find tools/resume_paper_now.sh under: $ROOT"
cd "$BASE"
say "✅ Base detected: $BASE"

# --- 1) Ensure required dirs/files exist (prevents PNL kill logging FileNotFoundError) ---
mklogs() {
  local p="$1"
  mkdir -p "$p/logs/runs"
  mkdir -p "$p/ops/state" || true
  # Common log files various modules expect
  touch "$p/logs/audit.log" || true
  touch "$p/logs/pnl_kill_events.jsonl" || true
  touch "$p/logs/runs/engine.jsonl" || true
}
# Root package logs
[[ -d "multi_broker_phoenix" ]] && mklogs "multi_broker_phoenix"

# Nested package logs (known issue in backup notes)
if [[ -d "MULTI_BROKER_PHOENIX/multi_broker_phoenix" ]]; then
  mklogs "MULTI_BROKER_PHOENIX/multi_broker_phoenix"
fi
if [[ -d "MULTI_BROKER_PHOENIX/MULTI_BROKER_PHOENIX/multi_broker_phoenix" ]]; then
  mklogs "MULTI_BROKER_PHOENIX/MULTI_BROKER_PHOENIX/multi_broker_phoenix"
fi
say "✅ Log directories/files ensured"

# --- 2) Kill dual-package drift: replace nested multi_broker_phoenix with a symlink to the canonical one ---
link_nested() {
  local nested="$1"
  local canonical="$2"

  [[ -d "$canonical" ]] || return 0
  [[ -e "$nested" ]] || return 0

  if [[ -L "$nested" ]]; then
    say "ℹ️ Nested already symlinked: $nested"
    return 0
  fi

  local bak="${nested}.bak.$(date +%Y%m%d_%H%M%S)"
  mv "$nested" "$bak"
  ln -s "../$(basename "$canonical")" "$nested"
  say "✅ Nested package symlinked: $nested -> $canonical (backup: $bak)"
}

CANON="multi_broker_phoenix"
if [[ -d "$CANON" ]]; then
  # Case A: BASE/MULTI_BROKER_PHOENIX/multi_broker_phoenix exists
  if [[ -d "MULTI_BROKER_PHOENIX" ]]; then
    link_nested "MULTI_BROKER_PHOENIX/multi_broker_phoenix" "$CANON" || true
    # Case B: double-nested
    if [[ -d "MULTI_BROKER_PHOENIX/MULTI_BROKER_PHOENIX" ]]; then
      # create a symlinked canonical inside the inner dir as well
      if [[ -e "MULTI_BROKER_PHOENIX/MULTI_BROKER_PHOENIX/multi_broker_phoenix" ]]; then
        # from inner dir, canonical is ../../multi_broker_phoenix
        local_inner="MULTI_BROKER_PHOENIX/MULTI_BROKER_PHOENIX/multi_broker_phoenix"
        if [[ -L "$local_inner" ]]; then
          say "ℹ️ Double-nested already symlinked: $local_inner"
        else
          bak="${local_inner}.bak.$(date +%Y%m%d_%H%M%S)"
          mv "$local_inner" "$bak"
          ln -s "../../multi_broker_phoenix" "$local_inner"
          say "✅ Double-nested symlinked: $local_inner -> ../../multi_broker_phoenix (backup: $bak)"
        fi
      fi
    fi
  fi
else
  say "⚠️ No canonical ./multi_broker_phoenix found here. Skipping symlink fix."
fi

# --- 3) Ensure resume scripts export PYTHONPATH correctly + always load env (prevents import failures) ---
ensure_line_once() {
  local file="$1" line="$2"
  [[ -f "$file" ]] || return 0
  grep -Fqx "$line" "$file" 2>/dev/null && return 0
  # Insert after shebang if present, else prepend
  if head -n1 "$file" | grep -q "^#\!"; then
    awk -v l="$line" 'NR==1{print;print l;next}1' "$file" > "${file}.tmp" && mv "${file}.tmp" "$file"
  else
    printf "%s\n%s\n" "$line" "$(cat "$file")" > "${file}.tmp" && mv "${file}.tmp" "$file"
  fi
}

patch_resume() {
  local f="$1"
  [[ -f "$f" ]] || return 0

  cp -a "$f" "${f}.bak.$(date +%Y%m%d_%H%M%S)"

  ensure_line_once "$f" 'set -euo pipefail'
  # Canonical + nested on PYTHONPATH (matches the backup fix but also includes canonical)
  ensure_line_once "$f" 'export PYTHONPATH="${PWD}:${PWD}/MULTI_BROKER_PHOENIX:${PYTHONPATH:-}"'
  # Always load env if present
  ensure_line_once "$f" '[[ -f tools/env_load.sh ]] && source tools/env_load.sh || true'
  chmod +x "$f" || true
  say "✅ Patched: $f"
}

patch_resume "tools/resume_paper_now.sh"
patch_resume "tools/resume_live_now.sh"

# --- 4) Quiet the DeepSeek auth fail by disabling it when the key is missing/placeholder (DeepSeek is optional) ---
set_kv() {
  local file="$1" key="$2" val="$3"
  [[ -f "$file" ]] || return 0

  # If not writable, don't brick anything—just report.
  if [[ ! -w "$file" ]]; then
    say "⚠️ Not writable (skipping edit): $file"
    return 0
  fi

  cp -a "$file" "${file}.bak.$(date +%Y%m%d_%H%M%S)"
  if grep -qE "^${key}=" "$file"; then
    sed -i -E "s|^${key}=.*|${key}=${val}|g" "$file"
  else
    printf "\n%s=%s\n" "$key" "$val" >> "$file"
  fi
}

get_env_val() {
  local file="$1" key="$2"
  [[ -f "$file" ]] || return 1
  grep -E "^${key}=" "$file" | tail -n1 | cut -d'=' -f2- || true
}

DEEPKEY=""
[[ -f ".env" ]] && DEEPKEY="$(get_env_val ".env" "DEEPSEEK_API_KEY" || true)"
# treat empty / placeholder as invalid
if [[ -z "${DEEPKEY// }" || "$DEEPKEY" == "CHANGEME" || "$DEEPKEY" == "YOUR_KEY_HERE" ]]; then
  say "ℹ️ DeepSeek key missing/placeholder -> disabling DeepSeek to stop auth-fail spam"
  set_kv "config/toggles.env" "ENABLE_DEEPSEEK" "0"
  set_kv ".env" "ENABLE_DEEPSEEK" "0"
  set_kv ".env" "DEEPSEEK_ENABLED" "0"
  set_kv "ops/secrets.env" "ENABLE_DEEPSEEK" "0"
  set_kv "ops/secrets.env" "DEEPSEEK_ENABLED" "0"
else
  say "✅ DeepSeek key present (not touching ENABLE_DEEPSEEK)"
fi

# --- 5) Quick sanity checks (env + imports), matching the backup verification steps ---
if [[ -f "tools/env_load.sh" ]]; then
  # shellcheck disable=SC1091
  source tools/env_load.sh || true
fi

# Require OANDA creds in runtime env to avoid "connector missing" behavior
: "${OANDA_API_TOKEN:=}"
: "${OANDA_TOKEN:=}"
: "${OANDA_ACCOUNT_ID:=}"
OANDA_TOKEN_EFFECTIVE="${OANDA_TOKEN:-${OANDA_API_TOKEN:-}}"
if [[ -z "${OANDA_TOKEN_EFFECTIVE// }" || -z "${OANDA_ACCOUNT_ID// }" ]]; then
  say "❌ Missing OANDA env vars at runtime."
  say "   Expected at least: OANDA_API_TOKEN (or OANDA_TOKEN) and OANDA_ACCOUNT_ID"
  say "   Fix: put them in ops/secrets.env (preferred) and re-run: source tools/env_load.sh ; echo \$OANDA_API_TOKEN ; echo \$OANDA_ACCOUNT_ID"
  exit 2
fi
say "✅ OANDA env present (token/account id)"

python3 - <<'PY'
import sys
try:
  from multi_broker_phoenix.risk.exit_manager import ExitManager
  print("✅ Python imports OK (ExitManager)")
except Exception as e:
  print("❌ Import test failed:", repr(e))
  sys.exit(3)
PY

say "✅ All fixes applied."
say "Next: restart clean -> bash tools/STOP_ENGINE.sh (if running) ; bash tools/resume_paper_now.sh"