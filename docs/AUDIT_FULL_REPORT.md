# Full Audit Report - 2026-01-04T04:10:03.053789

## Executive Summary

System audit ran with exit code 0. Passed: N/A, Failed: N/A, Warnings: N/A.

## Protocols & Connectivity

- OANDA: Configured if OANDA_API_TOKEN and OANDA_ACCOUNT_ID present. Connector will attempt pricing calls (practice mode by default).
- IBKR: Paper connector available; will return stub telemetry if local gateway or ib_insync not installed. Port default 4002 for paper.
- Coinbase: Connector supports Coinbase Advanced Trade API; real trading requires JWT/keys. Nano-lot safety limits enforced.

## Agent Charters

- AI Hive: Multi-agent consensus validation (OpenAI / XAI / DeepSeek). Strategy-first gating reduces calls and cost.
- Hive Cost Control: Ensures daily budget, per-call gating and only triggers on strategy signals when configured.

## Risk Logic & Protections

- Per-strategy stop-loss percentages configurable via env (e.g., FABIO_STOP_MIN_PCT, EMA_SCALPER_STOP_PCT).
- Trailing stops supported across brokers; position narrator writes JSON events for UI.
- Safety tripwires: MAX_DRAWDOWN_PCT, DAILY_LOSS_LIMIT_USD, MAX_CONSECUTIVE_LOSSES.

## Dynamic Leverage & Scaling

- Coinbase connector implements auto-scaling tiers based on win-rate and profit thresholds.
- Platform-level risk manager will gate position sizes and prevent scaling beyond configured per-day losses.

## Launch Modes (RBOTZILLA)

- Canary / Coinbase / OANDA / IBKR / Multi-Asset / Strategy Test / Hive-only / Audit. Each mode sets DEFAULT_STRATEGY and enables related subsystems.

## Narration & Terminal Behavior

- Position narration JSON file: /tmp/position_narration.jsonl (newline-separated JSON). Each entry includes 'human_summary' for easy reading.
- Use tools/start_narration_tty.sh to open a persistent terminal that refreshes every 10s and shows recent human summaries.

## Recommendations & Next Steps

- (Optional) Run live connector tests to validate authentication and live API responses; requires network access and credentials.
- Schedule weekly system_audit.sh runs and snapshot generation via cron or CI.

---

### Full raw audit output

````
════════════════════════════════════════════════════════════════
🔍 RBOTZILLA FULL SYSTEM AUDIT
════════════════════════════════════════════════════════════════

1️⃣  CRITICAL FILES & STRUCTURE
────────────────────────────────────────────────────────────────
  [0;32m✅ .env configuration file exists[0m
  [0;32m✅ Strategies directory exists[0m
  [0;32m✅ Backup system active[0m

2️⃣  API KEYS & CONNECTIVITY
────────────────────────────────────────────────────────────────
  [0;32m✅ OANDA API token configured[0m
  [0;32m✅ OANDA account ID configured[0m
  [0;32m✅ Coinbase credentials configured[0m
  [0;32m✅ IBKR Gateway enabled[0m
  [0;32m✅ IBKR configured for paper account (port 4002)[0m
  [0;32m✅ IBKR futures symbols configured[0m
  [0;32m✅ OpenAI API key configured[0m
  [0;32m✅ XAI (Grok) API key configured[0m
  [0;32m✅ DeepSeek API key configured[0m

3️⃣  STRATEGY CONFIGURATION
────────────────────────────────────────────────────────────────
  [0;32m✅ FABIO_RSI_THRESHOLD=40 (optimized, 167 trades)[0m
  [0;32m✅ Strategy file: fabio_aaa_full.py[0m
  [0;32m✅ Strategy file: base.py[0m
  [0;32m✅ Strategy file: unified_hive_scanner.py[0m
  [0;32m✅ Strategy file: hive_cost_control.py[0m

4️⃣  STOP LOSS & RISK MANAGEMENT
────────────────────────────────────────────────────────────────
  [0;32m✅ FABIO stop loss configured: 0.01-0.08%[0m
  [0;32m✅ Holy Grail stop loss: 0.03%[0m
  [0;32m✅ EMA Scalper stop loss: 0.005%[0m
  [0;32m✅ Max drawdown limit: 10.0%[0m
  [0;32m✅ Daily loss limit: $100.0[0m
  [0;32m✅ Max consecutive losses: 5[0m
  [0;32m✅ OANDA trailing stops ENABLED[0m
  [0;32m✅ IBKR trailing stops ENABLED[0m
  [0;32m✅ Coinbase trailing stops ENABLED[0m

5️⃣  AI HIVE INTEGRATION
────────────────────────────────────────────────────────────────
  [0;32m✅ AI Hive validation ENABLED[0m
  [0;32m✅ AI budget control: $10.0/day[0m
  [0;32m✅ Strategy-first mode ENABLED (cost efficient)[0m
  [0;32m✅ AI only on signals ENABLED (cost efficient)[0m
  [0;32m✅ AI consensus requirement: 2 agents[0m

6️⃣  TRADING MODE & SYMBOLS
────────────────────────────────────────────────────────────────
  [0;32m✅ Trading mode: PAPER (safe)[0m
  [0;32m✅ Using platform paper accounts[0m
  [0;32m✅ Trading symbols configured: 18 symbols[0m
     Symbols: EUR_USD,GBP_USD,USD_JPY,AUD_USD,USD_CAD,NZD_USD,USD_CHF,ES,NQ,YM,RTY,GC,SI,HG,CL,NG,BTC-USD,ETH-USD
  [0;32m✅ Default strategy: institutional_sd[0m

7️⃣  POSITION & RISK LIMITS
────────────────────────────────────────────────────────────────
  [0;32m✅ OANDA max positions: 1 per instrument[0m
  [0;32m✅ Coinbase daily trade limit: 10[0m
  [0;32m✅ Coinbase daily loss limit: $50.0[0m
  [0;32m✅ Max concurrent trades: 5[0m

8️⃣  CANARY MODE SAFETY
────────────────────────────────────────────────────────────────
  [0;32m✅ Canary max risk: $10.0[0m
  [0;32m✅ Canary poll interval: 30.0s[0m

9️⃣  PYTHON DEPENDENCIES
────────────────────────────────────────────────────────────────
  [0;32m✅ Python available: Python 3.12.3[0m
  [0;32m✅ Python module: requests[0m
  [0;32m✅ Python module: pandas[0m
  [0;32m✅ Python module: numpy[0m

🔟  AUTOMATED TESTS
────────────────────────────────────────────────────────────────
  [0;32m✅ FABIO uses configurable RSI threshold[0m
  [0;32m✅ FABIO threshold properly implemented[0m
  [0;32m✅ Restore script executable[0m

════════════════════════════════════════════════════════════════
📊 AUDIT SUMMARY
════════════════════════════════════════════════════════════════

  [0;32m✅ Passed:   48[0m
  [0;31m❌ Failed:   0[0m
  [1;33m⚠️  Warnings: 0[0m

[0;32m🎉 SYSTEM READY FOR LIVE PAPER TRADING[0m

````