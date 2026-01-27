#!/usr/bin/env bash
# OANDA Daily Operations Helper
# Prints what each task does + terminal equivalents

cat <<'EOF'
╔════════════════════════════════════════════════════════════════════╗
║              OANDA DAILY OPERATIONS - QUICK REFERENCE              ║
╔════════════════════════════════════════════════════════════════════╝
║
║  VS Code Tasks (Terminal → Run Task):
║  ═══════════════════════════════════════════════════════════════
║
║  1) "OANDA DAILY: 1) Start + Preflight + Arm"
║     └─ Starts orchestrator + OANDA runner
║     └─ OANDA-only mode (AI Hive REQUIRED)
║     └─ Runs preflight validation
║     └─ Terminal: ./tools/start_preflight_arm_oanda.sh
║
║  2) "OANDA DAILY: 2) Status (Heartbeat + Gates)"
║     └─ Check broker health + heartbeat updates
║     └─ Verify gates (should show ALL PASS)
║     └─ Terminal: ./tools/status_full_system.sh
║
║  3) "OANDA DAILY: 3) Tail Logs (engine.log)"
║     └─ Watch real-time engine activity
║     └─ Verify protect_loop running (errors=0)
║     └─ Terminal: tail -f /home/ing/RICK/logs/oanda/engine.log
║
║  4) "OANDA DAILY: 4) Preflight Check"
║     └─ Verify system health before trading
║     └─ Terminal: ./tools/preflight_oanda.sh
║
║  5) "OANDA DAILY: 5) Stop OANDA (Clean)"
║     └─ Graceful shutdown
║     └─ Waits for positions to close
║     └─ Terminal: ./tools/stop_broker.sh oanda
║
╠════════════════════════════════════════════════════════════════════
║  Key Files to Monitor:
╠════════════════════════════════════════════════════════════════════
║
║  Heartbeat:  /home/ing/RICK/ops/state/brokers/oanda.json
║  Logs:       /home/ing/RICK/logs/oanda/engine.log
║  Orch:       /home/ing/RICK/logs/orchestrator/orchestrator.log
║
╠════════════════════════════════════════════════════════════════════
║  Daily Workflow:
╠════════════════════════════════════════════════════════════════════
║
║  Morning:
║    ✓ Run Task #1 (Start + Preflight + Arm)
║    ✓ Run Task #2 (Status) - verify gates PASS
║    ✓ Run Task #3 (Tail Logs) - confirm clean startup
║
║  Monitoring:
║    ✓ Run Task #2 every 30-60 minutes
║    ✓ Keep Task #3 open in a terminal
║
║  Evening:
║    ✓ Run Task #5 (Stop OANDA)
║
╠════════════════════════════════════════════════════════════════════
║  Full Documentation:
╠════════════════════════════════════════════════════════════════════
║
║  See: OPS_VSCODE_TASK_PROTOCOL_OANDA.md (repo root)
║
╚════════════════════════════════════════════════════════════════════
EOF
