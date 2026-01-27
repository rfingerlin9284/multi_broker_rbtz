#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-$(pwd)}"
cd "$ROOT"

echo "=============================================="
echo "RBOT LIVE/PAPER EXECUTION AUDIT"
echo "Repo: $ROOT"
echo "Time: $(date -Is)"
echo "=============================================="
echo

have_rg=1
command -v rg >/dev/null 2>&1 || have_rg=0
if [[ "$have_rg" -eq 0 ]]; then
  echo "NOTE: ripgrep (rg) not found. Using grep (slower)."
  echo
fi

scan() {
  local label="$1"; shift
  local pattern="$1"; shift
  echo "---- $label ----"
  if [[ "$have_rg" -eq 1 ]]; then
    rg -n --no-heading -S "$pattern" . || true
  else
    grep -RIn --exclude-dir=.git --line-number -E "$pattern" . || true
  fi
  echo
}

scan "1) MODE FLAGS (LIVE/DRY_RUN/SIM/MOCK/PAPER/SANDBOX/PRACTICE)" \
     "(LIVE[[:space:]]*=|DRY_RUN|SIMULAT|MOCK|PAPER|SANDBOX|PRACTICE|ENVIRON|BASE_URL|FXPRACTICE|FXTRADE)"

scan "2) DUMMY DATA / NO-EXEC STUBS" \
     "(load_dummy|dummy_data|synthetic|simulate|paper_only|no_exec|TODO: Plug into broker|TODO.*broker|return None[[:space:]]*#.*no trade)"

scan "3) ORDER PLACEMENT CALLS (DO WE EVER SEND AN ORDER?)" \
     "(submit_order|place_order|create_order|OrdersCreate|MarketOrder|stopLossOnFill|takeProfitOnFill|order_class|bracket|ib\\.placeOrder|placeOrder\\(|/orders)"

scan "4) BROKER IDENTIFIERS (OANDA/IBKR/COINBASE) + PORTS" \
     "(OANDA|fxpractice|fxtrade|IBKR|TWS|IBGATEWAY|7496|7497|4001|4002|COINBASE|ADVANCED|EXCHANGE|api-public\\.sandbox\\.exchange\\.coinbase\\.com)"

echo "---- 5) .env presence (REDACTED) ----"
if [[ -f ".env" ]]; then
  grep -E "^(OANDA|IBKR|COINBASE)_" .env | sed "s/=.*$/=<redacted>/" || true
else
  echo "No .env found in repo root."
fi
echo

echo "---- 6) ENV presence (REDACTED + length only) ----"
keys=(
  OANDA_API_KEY OANDA_TOKEN OANDA_ACCOUNT_ID OANDA_ENV
  IBKR_HOST IBKR_PORT IBKR_CLIENT_ID
  COINBASE_API_KEY COINBASE_API_SECRET COINBASE_API_PASSPHRASE
  COINBASE_ADVANCED_KEY COINBASE_ADVANCED_SECRET COINBASE_JWT_KEY COINBASE_JWT_SECRET
)
for k in "${keys[@]}"; do
  v="${!k-}"
  if [[ -n "$v" ]]; then
    echo "SET  $k (len=${#v})"
  else
    echo "MISS $k"
  fi
done
echo

echo "=============================================="
echo "READ THIS:"
echo " - If section (3) is basically empty, your bot cannot place trades (it is data-only)."
echo " - If section (2) shows dummy_data/simulate/TODO broker, you are in mock mode by design."
echo " - If section (1) shows LIVE=False/DRY_RUN=True, flip the switch AND ensure execution code exists."
echo "=============================================="
