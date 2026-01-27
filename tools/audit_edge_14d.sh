#!/usr/bin/env bash
set -euo pipefail

REPO="${REPO:-/home/ing/RICK/MULTI_BROKER_PHOENIX}"
DAYS="${DAYS:-14}"
TS="${TS:-$(date -u +%Y%m%dT%H%M%SZ)}"
OUT="${OUT:-$REPO/audit_runs/$TS}"
mkdir -p "$OUT"

REPORT="$OUT/REPORT.md"
: >"$REPORT"

md(){ printf "%s\n" "$*" | tee -a "$REPORT" >/dev/null; }

slug(){
  # dash at end avoids locale range weirdness; LC_ALL=C makes behavior deterministic
  LC_ALL=C echo "${1:-untitled}" | tr " /" "__" | tr -cd "[:alnum:]_.-"
}

run(){
  local title="$1"; shift
  local cmd="$1"
  local out="$OUT/$(slug "$title").out"
  md ""; md "## $title"; md ""
  md '```bash'; md "$cmd"; md '```'; md ""
  ( cd "$REPO" && bash -lc "$cmd" ) >"$out" 2>&1 || true
  md "**Output (saved):** \`$out\`"; md ""
}

[[ -d "$REPO/.git" ]] || { echo "ERROR: not a git repo: $REPO" >&2; exit 1; }

md "# RBOTZILLA 14-Day Edge Audit"
md ""
md "- Repo: \`$REPO\`"
md "- Window: last \`$DAYS\` days"
md "- Timestamp (UTC): \`$TS\`"
md ""

run "Locate Logs" \
'ls -lah ./logs 2>/dev/null || true; echo; ls -lah ./logs/oanda 2>/dev/null || true; echo; ls -lah ./ops/state 2>/dev/null || true'

run "Search: Big Profit / PnL / Close events" \
'LOGS=(./logs/oanda/engine.log ./logs/engine_headless.log ./narration.jsonl ./narration_old*.jsonl);
for f in "${LOGS[@]}"; do
  [[ -f "$f" ]] || continue
  echo "--- $f ---"
  grep -nEi "realized|unrealized|pnl|profit|closed|close_position|take profit|stop loss|tp=|sl=" "$f" | tail -n 200 || true
  echo
done'

run "Search: Reject reasons (FIFO/Margin/OCO)" \
'LOGS=(./logs/oanda/engine.log ./logs/engine_headless.log ./narration.jsonl ./narration_old*.jsonl);
for f in "${LOGS[@]}"; do
  [[ -f "$f" ]] || continue
  echo "--- $f ---"
  grep -nEi "FIFO_VIOLATION|INSUFFICIENT_MARGIN|orderCancelTransaction|ORDER_CANCEL|orderReject|REJECT|CANCEL|stopLossOnFill.*null|takeProfitOnFill.*null|OCO.*(missing|fail|invalid|incomplete)" "$f" | tail -n 300 || true
  echo
done'

run "USD_CAD timeline (fills + FIFO cancels)" \
'F=./logs/engine_headless.log
[[ -f "$F" ]] || { echo "MISSING: $F"; exit 0; }
grep -nE "USD_CAD|FIFO_VIOLATION_SAFEGUARD_VIOLATION|orderFillTransaction|tradeOpened" "$F" | tail -n 400'

md ""
md "# Notes"
md "- If FIFO cancels appear after recent USD_CAD fills, treat as per-symbol gating failure (entry spam)."
md "- Next action is to enforce: one-position-per-symbol + one-pending-per-symbol + cooldown after any cancel."
echo "OK: wrote $REPORT"
