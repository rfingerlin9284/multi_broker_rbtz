#!/usr/bin/env python3
"""Generate a versioned system snapshot and full audit report.
Runs `system_audit.sh`, captures output, collects config and strategy info,
and writes two files:
 - snapshots/SYSTEM_SNAPSHOT_YYYYMMDD_HHMMSS.md
 - docs/AUDIT_FULL_REPORT.md
"""
from __future__ import annotations
import subprocess
import shlex
import os
from datetime import datetime
import json

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SNAP_DIR = os.path.join(ROOT, 'snapshots')
DOCS_DIR = os.path.join(ROOT, 'docs')

os.makedirs(SNAP_DIR, exist_ok=True)
os.makedirs(DOCS_DIR, exist_ok=True)

# Run audit
audit_cmd = ['./system_audit.sh']
proc = subprocess.run(audit_cmd, cwd=ROOT, capture_output=True, text=True)
audit_stdout = proc.stdout
audit_stderr = proc.stderr
exit_code = proc.returncode

# Parse summary lines from audit stdout
passed = failed = warnings = None
for line in audit_stdout.splitlines():
    if '✅ Passed:' in line:
        parts = line.strip().split()
        try:
            passed = int(parts[-1])
        except Exception:
            pass
    if '❌ Failed:' in line:
        parts = line.strip().split()
        try:
            failed = int(parts[-1])
        except Exception:
            pass
    if 'Warnings:' in line:
        parts = line.strip().split()
        try:
            warnings = int(parts[-1])
        except Exception:
            pass

# Read .env (redact secrets)
env_path = os.path.join(ROOT, '.env')
env = {}
if os.path.exists(env_path):
    with open(env_path) as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                k, v = line.split('=', 1)
                v = v.strip().strip('"').strip("'")
                if 'KEY' in k or 'SECRET' in k or 'TOKEN' in k or 'PASS' in k:
                    env[k] = 'REDACTED'
                else:
                    env[k] = v

# Get strategy list
enabled_strategies = []
try:
    import sys
    sys.path.insert(0, os.path.join(ROOT, 'MULTI_BROKER_PHOENIX'))
    from multi_broker_phoenix.strategies.strategy_registry import get_enabled_strategies
    enabled_strategies = get_enabled_strategies()
except Exception as e:
    enabled_strategies = []

# Build snapshot
now = datetime.now()
stamp = now.strftime('%Y%m%d_%H%M%S')
snap_file = os.path.join(SNAP_DIR, f'SYSTEM_SNAPSHOT_{stamp}.md')
with open(snap_file, 'w') as fh:
    fh.write(f"# System Snapshot - {now.isoformat()}\n\n")
    fh.write("## Audit Summary\n\n")
    fh.write(f"- Exit code: {exit_code}\n")
    fh.write(f"- Passed: {passed or 'N/A'}\n")
    fh.write(f"- Failed: {failed or 'N/A'}\n")
    fh.write(f"- Warnings: {warnings or 'N/A'}\n\n")
    fh.write("## Enabled Strategies\n\n")
    for s in enabled_strategies:
        fh.write(f"- {s}\n")
    fh.write("\n## Key Environment Variables (redacted)\n\n")
    for k in ['DEFAULT_STRATEGY', 'TRADING_MODE', 'FEED_SYMBOLS', 'AI_HIVE_DAILY_BUDGET_USD', 'FABIO_RSI_THRESHOLD']:
        fh.write(f"- {k}: {env.get(k, 'MISSING')}\n")

# Build full report
report_file = os.path.join(DOCS_DIR, 'AUDIT_FULL_REPORT.md')
with open(report_file, 'w') as fh:
    fh.write(f"# Full Audit Report - {now.isoformat()}\n\n")
    fh.write("## Executive Summary\n\n")
    fh.write(f"System audit ran with exit code {exit_code}. Passed: {passed or 'N/A'}, Failed: {failed or 'N/A'}, Warnings: {warnings or 'N/A'}.\n\n")
    fh.write("## Protocols & Connectivity\n\n")
    fh.write("- OANDA: Configured if OANDA_API_TOKEN and OANDA_ACCOUNT_ID present. Connector will attempt pricing calls (practice mode by default).\n")
    fh.write("- IBKR: Paper connector available; will return stub telemetry if local gateway or ib_insync not installed. Port default 4002 for paper.\n")
    fh.write("- Coinbase: Connector supports Coinbase Advanced Trade API; real trading requires JWT/keys. Nano-lot safety limits enforced.\n\n")
    fh.write("## Agent Charters\n\n")
    fh.write("- AI Hive: Multi-agent consensus validation (OpenAI / XAI / DeepSeek). Strategy-first gating reduces calls and cost.\n")
    fh.write("- Hive Cost Control: Ensures daily budget, per-call gating and only triggers on strategy signals when configured.\n\n")
    fh.write("## Risk Logic & Protections\n\n")
    fh.write("- Per-strategy stop-loss percentages configurable via env (e.g., FABIO_STOP_MIN_PCT, EMA_SCALPER_STOP_PCT).\n")
    fh.write("- Trailing stops supported across brokers; position narrator writes JSON events for UI.\n")
    fh.write("- Safety tripwires: MAX_DRAWDOWN_PCT, DAILY_LOSS_LIMIT_USD, MAX_CONSECUTIVE_LOSSES.\n\n")
    fh.write("## Dynamic Leverage & Scaling\n\n")
    fh.write("- Coinbase connector implements auto-scaling tiers based on win-rate and profit thresholds.\n")
    fh.write("- Platform-level risk manager will gate position sizes and prevent scaling beyond configured per-day losses.\n\n")
    fh.write("## Launch Modes (RBOTZILLA)\n\n")
    fh.write("- Canary / Coinbase / OANDA / IBKR / Multi-Asset / Strategy Test / Hive-only / Audit. Each mode sets DEFAULT_STRATEGY and enables related subsystems.\n\n")
    fh.write("## Narration & Terminal Behavior\n\n")
    fh.write("- Position narration JSON file: /tmp/position_narration.jsonl (newline-separated JSON). Each entry includes 'human_summary' for easy reading.\n")
    fh.write("- Use tools/start_narration_tty.sh to open a persistent terminal that refreshes every 10s and shows recent human summaries.\n\n")
    fh.write("## Recommendations & Next Steps\n\n")
    fh.write("- (Optional) Run live connector tests to validate authentication and live API responses; requires network access and credentials.\n")
    fh.write("- Schedule weekly system_audit.sh runs and snapshot generation via cron or CI.\n")
    fh.write("\n---\n\n")
    fh.write("### Full raw audit output\n\n````\n")
    fh.write(audit_stdout)
    fh.write("\n````")

print(f"Snapshot written: {snap_file}")
print(f"Full report written: {report_file}")
