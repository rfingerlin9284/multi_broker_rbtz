#!/bin/bash
# 🎯 RBOTZILLA QUICK REFERENCE - Always Available
# Copy this to your clipboard or print it

cat << 'EOF'

╔════════════════════════════════════════════════════════════════════════════╗
║                   🎯 RBOTZILLA QUICK REFERENCE v2.0                       ║
║              Quality-First Trading with AI Hive Consensus                  ║
╚════════════════════════════════════════════════════════════════════════════╝

┌─ SYSTEM CHECK ──────────────────────────────────────────────────────────────┐
│                                                                             │
│  Is engine running?                                                         │
│  $ pgrep -f run_headless.py && echo "✅ YES" || echo "❌ NO"              │
│                                                                             │
│  System status dashboard:                                                   │
│  $ python3 system_status_dashboard.py                                      │
│                                                                             │
│  View global config:                                                        │
│  $ python3 global_config.py                                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─ BROKER STATUS ─────────────────────────────────────────────────────────────┐
│                                                                             │
│  Check all brokers:                                                         │
│  $ python3 prove_ibkr_working.py                                           │
│                                                                             │
│  OANDA (Forex):                                                             │
│    Mode: PAPER (Demo account 002)                                          │
│    Status: ✅ LIVE                                                         │
│                                                                             │
│  IBKR (Futures):                                                            │
│    Mode: PAPER (Port 7497)                                                 │
│    Status: ✅ LIVE                                                         │
│                                                                             │
│  Coinbase (Crypto):                                                         │
│    Mode: LIVE (Real money)                                                 │
│    Size: $5-10 nano-lots                                                   │
│    Auto-scale: Enabled                                                      │
│    Status: ✅ LIVE                                                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─ MONITOR TRADES ────────────────────────────────────────────────────────────┐
│                                                                             │
│  Live narration monitor:                                                    │
│  $ python3 monitor_narration.py                                            │
│                                                                             │
│  Tail raw events:                                                           │
│  $ tail -f narration.jsonl | python3 -m json.tool                          │
│                                                                             │
│  Count filled orders:                                                       │
│  $ grep ORDER_FILLED narration.jsonl | wc -l                               │
│                                                                             │
│  View latest trade:                                                         │
│  $ tail -1 narration.jsonl | python3 -m json.tool                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─ QUALITY GATES ─────────────────────────────────────────────────────────────┐
│                                                                             │
│  Minimum confidence: 75%                                                    │
│  Preferred confidence: 80%+                                                 │
│  Hive consensus: 100% (all 3 agents must agree)                            │
│  Edge validation: REQUIRED                                                  │
│                                                                             │
│  🎯 RULE: Reject ANY trade < 75% confidence                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─ HIVE AGENTS ───────────────────────────────────────────────────────────────┐
│                                                                             │
│  GROK (Speed + Accuracy)                                                    │
│    Status: ✅ ENABLED                                                     │
│    Quality bias: 0.85 (Strict)                                             │
│    Cost: $0.001/call                                                        │
│                                                                             │
│  OpenAI (Deep Analysis)                                                     │
│    Status: ✅ ENABLED                                                     │
│    Quality bias: 0.85 (Strict)                                             │
│    Cost: $0.002/call                                                        │
│                                                                             │
│  DeepSeek (Consensus)                                                       │
│    Status: ✅ ENABLED                                                     │
│    Quality bias: 0.80 (Strict)                                             │
│    Cost: $0.0005/call                                                       │
│                                                                             │
│  Search Objective:                                                          │
│    ➜ Find HIGHEST QUALITY trades only                                     │
│    ➜ Reject signals < 80% confidence                                       │
│    ➜ Require unanimous consensus                                           │
│    ➜ Validate statistical edge                                             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─ AUTO-SCALING ──────────────────────────────────────────────────────────────┐
│                                                                             │
│  Scale UP when:                                                             │
│    • 5 wins in a row, OR                                                   │
│    • +$50 profit, OR                                                       │
│    • 60%+ win rate achieved                                                │
│    Action: Increase size $5 → $8 → $10                                     │
│                                                                             │
│  Scale DOWN when:                                                           │
│    • 3 losses in a row, OR                                                 │
│    • -$50 loss, OR                                                         │
│    • Win rate < 45%                                                        │
│    Action: Decrease size $10 → $5                                          │
│                                                                             │
│  Alerts ON:                                                                 │
│    🎉 Scale-up event                                                      │
│    📉 Scale-down event                                                     │
│    🎓 Phase graduation                                                     │
│    💰 Profit milestones ($100, $500, $1000)                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─ IMMUTABLE RULES ───────────────────────────────────────────────────────────┐
│                                                                             │
│  🔒 OANDA = ALWAYS PAPER                                                  │
│  🔒 IBKR = ALWAYS PAPER (port 7497)                                       │
│  🔒 Coinbase = LIVE with nano-lots ($5-10)                                │
│  🔒 Quality FIRST (reject < 75%)                                           │
│  🔒 Hive consensus = UNANIMOUS                                             │
│  🔒 Fill verification = Broker-confirmed only                              │
│  🔒 Narrate everything = All trades logged                                 │
│  🔒 Preserve thresholds = Never lower quality                              │
│                                                                             │
│  ⚠️  These rules CANNOT be overridden                                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─ START / STOP ──────────────────────────────────────────────────────────────┐
│                                                                             │
│  Start trading engine:                                                      │
│  $ bash RBOTZILLA_LAUNCH.sh                                                │
│    → Select option 4 (Multi-Asset - All Brokers)                           │
│                                                                             │
│  Stop all trading:                                                          │
│  $ pkill -f run_headless.py                                                │
│                                                                             │
│  Check status:                                                              │
│  $ python3 system_status_dashboard.py                                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─ FILES TO KNOW ─────────────────────────────────────────────────────────────┐
│                                                                             │
│  Configuration:                                                             │
│    /home/ing/RICK/MULTI_BROKER_PHOENIX/global_config.py                   │
│    /home/ing/RICK/MULTI_BROKER_PHOENIX/GLOBAL_AGENT_PROTOCOL.md           │
│                                                                             │
│  Monitoring:                                                                │
│    /home/ing/RICK/MULTI_BROKER_PHOENIX/narration.jsonl                    │
│    /home/ing/RICK/MULTI_BROKER_PHOENIX/monitor_narration.py               │
│                                                                             │
│  Status:                                                                    │
│    /home/ing/RICK/MULTI_BROKER_PHOENIX/system_status_dashboard.py         │
│    /home/ing/RICK/MULTI_BROKER_PHOENIX/prove_ibkr_working.py              │
│                                                                             │
│  Documentation:                                                             │
│    /home/ing/RICK/MULTI_BROKER_PHOENIX/NARRATION_GUIDE.md                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─ EXAMPLE WORKFLOW ──────────────────────────────────────────────────────────┐
│                                                                             │
│  1. Start system:                                                           │
│     $ bash RBOTZILLA_LAUNCH.sh                                             │
│                                                                             │
│  2. Verify operational:                                                     │
│     $ python3 system_status_dashboard.py                                   │
│                                                                             │
│  3. Monitor trades in real-time:                                            │
│     $ python3 monitor_narration.py                                         │
│                                                                             │
│  4. System is waiting for high-quality signals from strategies              │
│     + Hive agents searching for 80%+ confidence trades                      │
│                                                                             │
│  5. When trade executes:                                                    │
│     - Order placed at broker                                                │
│     - Fill verified                                                         │
│     - Event logged to narration.jsonl                                       │
│     - Dashboard updated                                                     │
│                                                                             │
│  6. Watch for graduation alerts:                                            │
│     - Scale-up/down events                                                  │
│     - Phase changes                                                         │
│     - Profit milestones                                                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

╔════════════════════════════════════════════════════════════════════════════╗
║  ✅ SYSTEM FULLY OPERATIONAL - Quality-First Trading Active                ║
║  📊 Monitoring: narration.jsonl | 🎯 Hive: Searching for 80%+ trades     ║
║  💰 Alerts: ON (graduation + scale events) | 🚀 Auto-scaling: ENABLED     ║
╚════════════════════════════════════════════════════════════════════════════╝

EOF
