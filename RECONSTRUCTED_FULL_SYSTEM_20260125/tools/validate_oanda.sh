#!/usr/bin/env bash
set -euo pipefail

# Simple OANDA validation script. Reads env vars OANDA_API_TOKEN and OANDA_ACCOUNT_ID
# By default performs info checks. Use --place-order --confirm to submit a tiny practice order.

OANDA_API_URL=${OANDA_API_URL:-https://api-fxpractice.oanda.com}
TOKEN=${OANDA_API_TOKEN:-}
ACCOUNT=${OANDA_ACCOUNT_ID:-}

if [ -z "$TOKEN" ] || [ -z "$ACCOUNT" ]; then
  echo "ERROR: OANDA_API_TOKEN and OANDA_ACCOUNT_ID must be exported in your shell or .env"
  exit 1
fi

show_usage() {
  cat <<EOF
Usage: $0 [--info] [--place-order SYMBOL UNITS] [--confirm]

--info               : Show account info and pricing example
--place-order SYMBOL UNITS : Place a small market order on practice account (requires --confirm)
--confirm            : Must be present to actually place the order
EOF
}

if [ "$#" -eq 0 ]; then
  set -- --info
fi

MODE=info
PLACE_SYMBOL=""
PLACE_UNITS=0
CONFIRM=0

while [ $# -gt 0 ]; do
  case "$1" in
    --info) MODE=info; shift;;
    --place-order) MODE=place; PLACE_SYMBOL="$2"; PLACE_UNITS="$3"; shift 3;;
    --confirm) CONFIRM=1; shift;;
    -h|--help) show_usage; exit 0;;
    *) echo "Unknown: $1"; show_usage; exit 1;;
  esac
done

echo "Using OANDA API URL: $OANDA_API_URL"

# Check account
echo "Checking account..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $TOKEN" "$OANDA_API_URL/v3/accounts/$ACCOUNT")
if [ "$HTTP_CODE" -ne 200 ]; then
  echo "Failed to access account: HTTP $HTTP_CODE"
  exit 1
fi

echo "Account is reachable. Fetching details..."
curl -s -H "Authorization: Bearer $TOKEN" "$OANDA_API_URL/v3/accounts/$ACCOUNT" | jq '.'

# price example for a common instrument
INSTRUMENT=EUR_USD
echo "Fetching pricing for $INSTRUMENT..."
curl -s -H "Authorization: Bearer $TOKEN" "$OANDA_API_URL/v3/accounts/$ACCOUNT/pricing?instruments=$INSTRUMENT" | jq '.'

if [ "$MODE" = "place" ]; then
  echo "Preparing to place market order: $PLACE_SYMBOL $PLACE_UNITS units"
  if [ "$CONFIRM" -ne 1 ]; then
    echo "RUN WITH --confirm to actually place the practice order (this will use your practice account)."
    echo "Example curl POST payload:" 
    cat <<JSON
{
  "order": {
    "units": "$PLACE_UNITS",
    "instrument": "$PLACE_SYMBOL",
    "timeInForce": "FOK",
    "type": "MARKET",
    "positionFill": "DEFAULT"
  }
}
JSON
    exit 0
  fi

  echo "Placing practice market order..."
  RESP=$(curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"order": {"units": "'" -d '"instrument": "'" -d '"timeInForce": "FOK"' -d '"type": "MARKET"' -d '"positionFill": "DEFAULT"' ) || true
echo "$RESP" | jq '.' || echo "$RESP"
