#!/usr/bin/env bash
# RBOTzilla Single Source of Truth Environment Loader
# This script MUST be sourced at the top of every runtime script.
# It loads env vars in deterministic order: toggles → secrets (secrets override toggles).
# NEVER prints secret values.

set -euo pipefail

# Determine repo root reliably
if [[ -n "${BASH_SOURCE[0]:-}" ]]; then
    SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
    REPO_ROOT="$(cd "$(dirname "$SCRIPT_PATH")/.." && pwd)"
else
    REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
fi

TOGGLES_FILE="${REPO_ROOT}/config/toggles.env"
SECRETS_FILE=""
STATE_FILE="${REPO_ROOT}/ops/state/env_state.json"

# Find secrets file from priority list
for candidate in \
    "${REPO_ROOT}/ops/secrets.env" \
    "${HOME}/.config/rbotzilla/secrets.env" \
    "/etc/rbotzilla/secrets.env"; do
    if [[ -f "$candidate" ]]; then
        SECRETS_FILE="$candidate"
        break
    fi
done

# Helper: compute SHA256 hash of file (no content leak)
_hash_file() {
    local f="$1"
    if [[ -f "$f" ]]; then
        sha256sum "$f" 2>/dev/null | awk '{print $1}' || echo "HASH_FAILED"
    else
        echo "FILE_NOT_FOUND"
    fi
}

# Helper: check if key is set and non-empty (returns true/false, no value)
_key_present() {
    local key="$1"
    local val="${!key:-}"
    if [[ -n "$val" ]]; then
        echo "true"
    else
        echo "false"
    fi
}

# Load toggles first (committed, non-secret)
if [[ -f "$TOGGLES_FILE" ]]; then
    set -a  # auto-export
    # shellcheck disable=SC1090
    source "$TOGGLES_FILE"
    set +a
fi

# Load secrets second (overrides toggles)
if [[ -n "$SECRETS_FILE" ]] && [[ -f "$SECRETS_FILE" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$SECRETS_FILE"
    set +a
fi

# Compute presence-only status for required keys (NO VALUES)
REQUIRED_KEYS=(
    "OANDA_API_TOKEN"
    "OANDA_ACCOUNT_ID"
    "OANDA_API_URL"
    "XAI_API_KEY"
    "DEEPSEEK_API_KEY"
    "OPENAI_API_KEY"
    "OLLAMA_URL"
    "OLLAMA_MODEL"
)

# Build JSON presence map
PRESENCE_JSON="{"
first=true
for k in "${REQUIRED_KEYS[@]}"; do
    present=$(_key_present "$k")
    if [[ "$first" == "true" ]]; then
        PRESENCE_JSON="${PRESENCE_JSON}\"${k}\": ${present}"
        first=false
    else
        PRESENCE_JSON="${PRESENCE_JSON}, \"${k}\": ${present}"
    fi
done
PRESENCE_JSON="${PRESENCE_JSON}}"

# Write state file (for observability, NO SECRET VALUES)
mkdir -p "$(dirname "$STATE_FILE")"
cat > "$STATE_FILE" <<JSON
{
  "last_loaded_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "toggles_path": "$TOGGLES_FILE",
  "secrets_path_used": "${SECRETS_FILE:-NONE}",
  "sha256_toggles": "$(_hash_file "$TOGGLES_FILE")",
  "sha256_secrets": "$(_hash_file "$SECRETS_FILE")",
  "required_keys_presence": $PRESENCE_JSON,
  "duplicates_detected": []
}
JSON

# Export marker that env was loaded
export RBOTZILLA_ENV_LOADED="true"
export RBOTZILLA_ENV_LOADED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
