# OANDA Practice (Platform-Paper) Setup — Rick Phoenix

This guide shows how to configure and validate the OANDA practice (paper) account so the headless Rick Phoenix runner can use **platform paper trading** where available. Follow the steps below carefully — **do not** share API tokens in the repo.

## 1) Obtain OANDA practice credentials
1. Sign in at https://www.oanda.com/ (create a practice/demo account if you don't have one)
2. Go to "Manage API Access" and create an API token for the **Practice** environment
3. Record the **Account ID** for the practice account (visible in your account dashboard)

## 2) Local environment variables
Create a local `.env` file (DO NOT COMMIT) or set env vars in your shell:

```
TRADING_MODE=PAPER
PAPER_VIA_PLATFORM=1
ALLOW_LIVE_REAL=0
OANDA_API_TOKEN=<your_practice_token>
OANDA_ACCOUNT_ID=<your_account_id>
OANDA_API_URL=https://api-fxpractice.oanda.com
```

- `TRADING_MODE=PAPER`: default safe mode (paper trading enabled)
- `PAPER_VIA_PLATFORM=1`: prefer platform paper accounts when supported
- `ALLOW_LIVE_REAL=0`: real-money trading disabled by default

## 3) Validate connectivity (quick)
Install dependencies and activate your venv (see README), then run the validator:

```bash
# From repo root
chmod +x tools/validate_oanda.sh
. .venv/bin/activate
export OANDA_API_TOKEN=...
export OANDA_ACCOUNT_ID=...
./tools/validate_oanda.sh --info
```

The script performs a token/account check and optionally will show a safe, non-executing sample order curl command. To actually place a practice (paper) order from the CLI you must pass `--place-order --confirm` and ensure the `OANDA_API_TOKEN` is the practice token.

## 4) Starting the headless runner
Use the provided start script (systemd unit example is in `tools/systemd/`):

```bash
# Quick start (manual)
. .venv/bin/activate
./tools/start_headless.sh

# As a systemd service (example)
sudo cp tools/systemd/rick_phoenix.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now rick_phoenix.service
sudo journalctl -u rick_phoenix -f
```

By default the runner will use platform paper for OANDA and IBKR (where configured) and simulated client-side fills for Coinbase.

## 5) Safety checklist before placing orders
- Verify `ALLOW_LIVE_REAL=0` (forbid real-money live orders by default)
- Confirm `OANDA_API_TOKEN` is a practice token (not a live token)
- Confirm your intended symbol and size are within `TEST_ORDER_MAX_USD` limits

## 6) Troubleshooting
- If account info returns 401/403: double-check token or network connectivity
- If streaming/polling latency is too high: check network & adjust polling intervals in config
- If headless does not start: check logs via the start script or `journalctl`


---

If you want, I can also configure a scheduled health check and add a Slack alert integration to notify on connectivity failures.