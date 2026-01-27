#!/usr/bin/env bash
# RBOTzilla Environment Doctor - Detects drift, duplicates, missing keys
# Exit codes: 0=ok, 2=duplicates, 3=missing required, 4=both
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Load env first
# shellcheck disable=SC1091
source "${REPO_ROOT}/tools/env_load.sh"

TOGGLES_FILE="${REPO_ROOT}/config/toggles.env"
SECRETS_FILE=""
STATE_FILE="${REPO_ROOT}/ops/state/env_doctor_last.json"

# Find secrets file (same logic as env_load)
for candidate in \
    "${REPO_ROOT}/ops/secrets.env" \
    "${HOME}/.config/rbotzilla/secrets.env" \
    "/etc/rbotzilla/secrets.env"; do
    if [[ -f "$candidate" ]]; then
        SECRETS_FILE="$candidate"
        break
    fi
done

echo "========================================="
echo " RBOTzilla Environment Doctor"
echo "========================================="
echo ""

# Show what was found/loaded
echo "FOUND:"
echo "  toggles  = $TOGGLES_FILE"
if [[ -n "$SECRETS_FILE" ]]; then
    echo "  secrets  = $SECRETS_FILE"
else
    echo "  secrets  = NONE (using defaults/env)"
fi
echo ""

# Compute hashes (no content leak)
_hash_file() {
    local f="$1"
    if [[ -f "$f" ]]; then
        sha256sum "$f" 2>/dev/null | awk '{print $1}' || echo "HASH_FAILED"
    else
        echo "FILE_NOT_FOUND"
    fi
}

echo "HASHES:"
echo "  toggles  = $(_hash_file "$TOGGLES_FILE")"
echo "  secrets  = $(_hash_file "$SECRETS_FILE")"
echo ""

# Check for duplicates across both files
DUPLICATES=()
if [[ -f "$TOGGLES_FILE" ]] && [[ -n "$SECRETS_FILE" ]] && [[ -f "$SECRETS_FILE" ]]; then
    # Extract keys from both files (ignore comments and blank lines)
    TOGGLES_KEYS=$(grep -E '^[A-Z_]+=' "$TOGGLES_FILE" 2>/dev/null | cut -d= -f1 | sort || true)
    SECRETS_KEYS=$(grep -E '^[A-Z_]+=' "$SECRETS_FILE" 2>/dev/null | cut -d= -f1 | sort || true)
    
    # Find intersection (duplicates)
    for k in $TOGGLES_KEYS; do
        if echo "$SECRETS_KEYS" | grep -q "^${k}$"; then
            DUPLICATES+=("$k")
        fi
    done
fi

# Check required keys based on toggles
REQUIRED_KEYS=()
MISSING_KEYS=()

_key_present() {
    local key="$1"
    local val="${!key:-}"
    [[ -n "$val" ]]
}

# OANDA always required if ENABLE_OANDA=1
if [[ "${ENABLE_OANDA:-0}" == "1" ]]; then
    REQUIRED_KEYS+=("OANDA_API_TOKEN" "OANDA_ACCOUNT_ID")
fi

# AI seats required only if their REQUIRE_* flag is set
if [[ "${REQUIRE_XAI:-0}" == "1" ]] || [[ "${REQUIRE_XAI_MANDATORY:-0}" == "1" ]]; then
    REQUIRED_KEYS+=("XAI_API_KEY")
fi

if [[ "${REQUIRE_DEEPSEEK:-0}" == "1" ]] || [[ "${REQUIRE_DEEPSEEK_MANDATORY:-0}" == "1" ]]; then
    REQUIRED_KEYS+=("DEEPSEEK_API_KEY")
fi

if [[ "${REQUIRE_OPENAI:-0}" == "1" ]] || [[ "${REQUIRE_OPENAI_MANDATORY:-0}" == "1" ]]; then
    REQUIRED_KEYS+=("OPENAI_API_KEY")
fi

# Ollama required if REQUIRE_OLLAMA=1 (usually true)
if [[ "${REQUIRE_OLLAMA:-0}" == "1" ]] || [[ "${REQUIRE_OLLAMA:-}" == "true" ]]; then
    REQUIRED_KEYS+=("OLLAMA_URL")
fi

# Check presence (no values printed)
echo "REQUIRED KEYS (presence only):"
for k in "${REQUIRED_KEYS[@]}"; do
    if _key_present "$k"; then
        echo "  $k = [SET]"
    else
        echo "  $k = [EMPTY] ❌"
        MISSING_KEYS+=("$k")
    fi
done
echo ""

# Report duplicates
if [[ ${#DUPLICATES[@]} -gt 0 ]]; then
    echo "DUPLICATES DETECTED ⚠️"
    echo "  The following keys are defined in BOTH toggles and secrets:"
    for k in "${DUPLICATES[@]}"; do
        echo "    - $k"
    done
    echo "  (Secrets will override toggles, but duplicates cause confusion.)"
    echo ""
fi

# Summary
echo "========================================="
if [[ ${#MISSING_KEYS[@]} -eq 0 ]] && [[ ${#DUPLICATES[@]} -eq 0 ]]; then
    echo "✅ STATUS: OK"
    EXIT_CODE=0
elif [[ ${#MISSING_KEYS[@]} -gt 0 ]] && [[ ${#DUPLICATES[@]} -gt 0 ]]; then
    echo "❌ STATUS: DUPLICATES + MISSING KEYS"
    EXIT_CODE=4
elif [[ ${#DUPLICATES[@]} -gt 0 ]]; then
    echo "⚠️  STATUS: DUPLICATES FOUND"
    EXIT_CODE=2
else
    echo "❌ STATUS: MISSING REQUIRED KEYS"
    EXIT_CODE=3
fi
echo "========================================="

# Write state file (for observability)
mkdir -p "$(dirname "$STATE_FILE")"
cat > "$STATE_FILE" <<JSON
{
  "timestamp_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "toggles_path": "$TOGGLES_FILE",
  "secrets_path": "${SECRETS_FILE:-NONE}",
  "duplicates": [$(printf '"%s",' "${DUPLICATES[@]}" | sed 's/,$//')],
  "missing_keys": [$(printf '"%s",' "${MISSING_KEYS[@]}" | sed 's/,$//')],
  "exit_code": $EXIT_CODE
}
JSON

exit "$EXIT_CODE"
