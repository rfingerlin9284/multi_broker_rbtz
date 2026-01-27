# IBKR TWS / Gateway — Setup & Validation

This document describes how to configure and validate IBKR TWS/Gateway for use with the headless Phoenix runner in **paper** mode.

1) Ensure TWS / IB Gateway is installed and updated to the version required by your OS.

2) Configure the Gateway to accept API connections (TWS/Gateway settings):
   - Enable API connections
   - Set trusted IPs if required
   - Note the host (usually `127.0.0.1`) and port (TWS default 7496/7497, gateway commonly 4001/4002)
   - Create a paper account if using LIVE otherwise set gateway to `paper` mode

3) Export environment variables (example):

```bash
export IBKR_HOST=127.0.0.1
export IBKR_PORT=4001
export IBKR_CLIENT_ID=1
export IBKR_ACCOUNT_ID=DU1234567  # optional
export IBKR_PLACE_TEST_ORDER=1     # required to enable guarded integration test
```

4) Validate connectivity (quick check):

```bash
tools/validate_ibkr.sh --info
```

5) Place a small practice order (manual):

```bash
# Enable execution for safety checks
export EXECUTION_ENABLED=1
python -c "from ibkr_gateway.ibkr_connector import IBKRConnector; print(IBKRConnector().place_order('TEST','BUY',1,entry_price=1.0,stop_loss=0.99,take_profit=1.1))"
```

6) If you are automating integration tests in CI ensure the job is gated and secrets are injected securely. Do not commit API keys into the repo.

---

If anything fails, inspect the Gateway logs and verify the port/host and client id match the config.
