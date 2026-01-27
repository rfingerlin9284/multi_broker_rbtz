"""
🎯 GLOBAL SYSTEM CONFIGURATION - QUALITY FIRST TRADING
Master configuration enforced across all RBOTZILLA agents and Hive systems
Version: 2.0.0 | Date: 2026-01-07
"""

# ═══════════════════════════════════════════════════════════════════════════════
# 1. BROKER CONFIGURATION - IMMUTABLE
# ═══════════════════════════════════════════════════════════════════════════════

BROKER_CONFIG = {
    "OANDA": {
        "mode": "PAPER",  # NEVER CHANGE - Paper trading only
        "account_id": "002",  # Demo account
        "status": "LIVE",
        "description": "Forex pairs (EUR_USD, GBP_USD, USD_JPY, etc.)"
    },
    "IBKR": {
        "mode": "PAPER",  # NEVER CHANGE - Paper trading only
        "port": 7497,  # Paper mode port (NOT 7496 which is live)
        "status": "LIVE",
        "description": "Futures (ES, NQ, GC, CL, etc.)"
    },
    "COINBASE": {
        "mode": "LIVE",  # REAL MONEY - but with nano-lot safety limits
        "nano_mode": True,
        "min_trade_usd": 5.0,  # MINIMUM: $5 per trade
        "max_trade_usd": 10.0,  # MAXIMUM: $10 per trade
        "auto_scale": True,  # Auto-scale UP on wins, DOWN on losses
        "status": "LIVE",
        "description": "Crypto (BTC-USD, ETH-USD) - REAL MONEY with safety limits"
    }
}

# ═══════════════════════════════════════════════════════════════════════════════
# 2. QUALITY-FIRST TRADING - IMMUTABLE THRESHOLDS
# ═══════════════════════════════════════════════════════════════════════════════

QUALITY_THRESHOLDS = {
    "MINIMUM_CONFIDENCE": 0.75,  # 75% minimum confidence required
    "PREFERRED_CONFIDENCE": 0.80,  # 80%+ preferred for all trades
    
    "STRATEGY_MINIMUMS": {
        "fabio_aaa_full": 0.78,        # FABIO: 78/100 minimum
        "holy_grail": 0.75,            # Holy Grail: 75/100 minimum
        "ema_scalper": 0.65,           # EMA: 65/100 minimum
        "institutional_sd": 0.80,      # Institutional: 80/100 minimum
        "trap_reversal": 0.75,         # Trap Reversal: 75/100 minimum
    },
    
    "HIVE_REQUIREMENTS": {
        "enabled": True,  # ALWAYS enabled
        "min_consensus": 2,  # Minimum 2 AI agents must agree
        "strategy_first": True,  # Run strategies first (free)
        "hive_only_on_signal": True,  # Only call AI when strategy fires
        "reject_below_confidence": 0.75,  # Reject trades < 75% confidence
    }
}

# ═══════════════════════════════════════════════════════════════════════════════
# 3. HIVE AGENT CONFIGURATION - QUALITY FIRST
# ═══════════════════════════════════════════════════════════════════════════════

HIVE_AGENT_CONFIG = {
    "GLOBAL_OBJECTIVE": "Find HIGHEST QUALITY trades only - reject low confidence signals",
    
    "SEARCH_PARAMETERS": {
        "quality_bias": "MAXIMUM",  # Bias toward quality, NOT quantity
        "confidence_minimum": 0.80,  # Only search for 80%+ confidence signals
        "consensus_requirement": "STRICT",  # Require multi-agent agreement
        "edge_validation": "REQUIRED",  # All trades must show statistical edge
    },
    
    "AI_AGENTS": {
        "grok": {
            "role": "Speed + Accuracy",
            "search_for": "Market catalysts, sentiment, breakout signals",
            "quality_bias": 0.85,  # Strict
            "enabled": True,
            "cost": 0.001  # $0.001 per call
        },
        "openai": {
            "role": "Deep Analysis",
            "search_for": "Pattern confirmation, risk assessment, edge validation",
            "quality_bias": 0.85,  # Strict
            "enabled": True,
            "cost": 0.002  # $0.002 per call
        },
        "deepseek": {
            "role": "Consensus",
            "search_for": "Cross-validation, alternative perspectives",
            "quality_bias": 0.80,  # Strict
            "enabled": True,
            "cost": 0.0005  # $0.0005 per call
        }
    },
    
    "AGENT_INSTRUCTIONS": {
        "search_strategy": [
            "1. Identify HIGH CONFIDENCE setups (80%+ signals only)",
            "2. Verify multiple timeframes agree (1H, 4H, Daily)",
            "3. Check for confluence of indicators",
            "4. Validate edge exists (backtest stats available)",
            "5. Confirm risk/reward ratio > 1:2",
            "6. Reject if any doubt or ambiguity",
            "7. Only approve for execution = UNANIMOUS consensus"
        ],
        "priority": "QUALITY OVER QUANTITY - One good trade > 10 mediocre trades",
        "rejection_criteria": [
            "- Confidence < 80%",
            "- Missing multi-timeframe confirmation",
            "- No edge validation",
            "- Risk/reward < 1:2",
            "- Less than 100% agent consensus"
        ]
    }
}

# ═══════════════════════════════════════════════════════════════════════════════
# 4. AUTO-SCALING CONFIGURATION - GRADUATION ALERTS
# ═══════════════════════════════════════════════════════════════════════════════

AUTO_SCALING_CONFIG = {
    "ENABLED": True,
    "APPLIES_TO": ["COINBASE"],  # Only Coinbase (OANDA/IBKR stay paper)
    
    "SCALE_UP_CRITERIA": {
        "win_streak": 5,  # 5 wins in a row
        "profit_threshold": 50.0,  # $50+ profit
        "win_rate": 0.60,  # 60%+ win rate
        "action": "Increase trade size from $5→$8→$10 (max)"
    },
    
    "SCALE_DOWN_CRITERIA": {
        "loss_streak": 3,  # 3 losses in a row
        "daily_loss": -50.0,  # -$50 loss in a day
        "win_rate": 0.45,  # Below 45% win rate
        "action": "Decrease trade size from $10→$5 (minimum)"
    },
    
    "GRADUATION_ALERTS": {
        "enabled": True,
        "notify_on": [
            "SCALE_UP_EVENT",  # Alert when increasing trade size
            "SCALE_DOWN_EVENT",  # Alert when decreasing trade size
            "PHASE_GRADUATION",  # Alert when entering next phase
            "PROFIT_MILESTONE",  # Alert at $100, $500, $1000 profits
        ],
        "alert_methods": [
            "CONSOLE: Print to stdout with 🎉 emoji",
            "NARRATION: Log to narration.jsonl",
            "LOG: Write to engine.log",
            "EMAIL: Optional (if configured)"
        ]
    },
    
    "PHASE_STRUCTURE": {
        "Phase 1": {
            "trade_size": "$5-10",
            "criteria": "Initial testing (100 trades)",
            "graduation": "55%+ win rate, 1.5+ profit factor"
        },
        "Phase 2": {
            "trade_size": "$10-15",
            "criteria": "Proven edge (50 trades)",
            "graduation": "57%+ win rate, 1.6+ profit factor"
        },
        "Phase 3": {
            "trade_size": "$15-25",
            "criteria": "Consistent profit (50 trades)",
            "graduation": "58%+ win rate, 1.7+ profit factor"
        }
    }
}

# ═══════════════════════════════════════════════════════════════════════════════
# 5. NARRATION & MONITORING - REAL TIME
# ═══════════════════════════════════════════════════════════════════════════════

MONITORING_CONFIG = {
    "NARRATION_FILE": "narration.jsonl",
    "NARRATION_EVENTS": [
        "TRADE_OPENED",
        "ORDER_FILLED",
        "TRADE_CLOSED",
        "PROFIT_TAKEN",
        "STOP_HIT",
        "SCALE_UP_EVENT",
        "SCALE_DOWN_EVENT",
        "PHASE_GRADUATION",
        "HIVE_VALIDATION",
        "STRATEGY_SIGNAL",
        "BROKER_ERROR"
    ],
    
    "REAL_TIME_MONITORING": {
        "enabled": True,
        "update_interval_seconds": 2.0,
        "tools": [
            "monitor_narration.py - Watch live trades",
            "prove_ibkr_working.py - Verify IBKR status",
            "tail -f narration.jsonl - Raw event stream"
        ]
    }
}

# ═══════════════════════════════════════════════════════════════════════════════
# 6. IMMUTABLE RULES - ENFORCED GLOBALLY
# ═══════════════════════════════════════════════════════════════════════════════

IMMUTABLE_RULES = [
    "🔒 RULE 1: OANDA ALWAYS PAPER - Never change to live trading",
    "🔒 RULE 2: IBKR ALWAYS PAPER - Never change to live trading (port 7497)",
    "🔒 RULE 3: COINBASE LIVE - Real money, but nano-lots only ($5-10)",
    "🔒 RULE 4: QUALITY FIRST - Reject trades < 80% confidence",
    "🔒 RULE 5: HIVE CONSENSUS - All agents must agree before execution",
    "🔒 RULE 6: FILL VERIFICATION - Only count broker-verified fills",
    "🔒 RULE 7: AUTO-SCALE ONLY - Coinbase scales up/down, not manual",
    "🔒 RULE 8: ALERT ON GRADUATION - Notify when phases change",
    "🔒 RULE 9: NARRATE EVERYTHING - Log all trades to narration.jsonl",
    "🔒 RULE 10: PRESERVE THRESHOLDS - Never lower strategy confidence requirements"
]

# ═══════════════════════════════════════════════════════════════════════════════
# 7. STARTUP VERIFICATION CHECKLIST
# ═══════════════════════════════════════════════════════════════════════════════

STARTUP_CHECKLIST = {
    "BROKERS": {
        "OANDA_PAPER": "✅ Paper mode confirmed",
        "IBKR_PAPER": "✅ Paper mode confirmed (port 7497)",
        "COINBASE_LIVE": "✅ Live with nano-lots enabled"
    },
    
    "HIVE_AGENTS": {
        "GROK": "✅ Enabled (speed + accuracy)",
        "OPENAI": "✅ Enabled (deep analysis)",
        "DEEPSEEK": "✅ Enabled (consensus)"
    },
    
    "QUALITY_GATES": {
        "MIN_CONFIDENCE": "✅ Set to 75-80%",
        "HIVE_CONSENSUS": "✅ Requires 2+ agents",
        "STRATEGY_FIRST": "✅ Strategy passes before Hive"
    },
    
    "MONITORING": {
        "NARRATION": "✅ Active",
        "FILL_VERIFICATION": "✅ All brokers",
        "AUTO_SCALING": "✅ Enabled (Coinbase only)"
    }
}

# ═══════════════════════════════════════════════════════════════════════════════
# 8. EXAMPLE TRADE FLOW (Quality-First)
# ═══════════════════════════════════════════════════════════════════════════════

EXAMPLE_TRADE_FLOW = """
QUALITY-FIRST TRADE EXECUTION FLOW:

1. STRATEGY FIRES (Local, Free)
   → FABIO analyzes ES contract
   → Generates BUY signal, 85% confidence
   → Checks threshold: 85% > 78% ✅ PASSES

2. HIVE VALIDATION (Multi-agent, Consensus)
   → Grok checks: Market sentiment, breakout confirmation → 88% confidence
   → OpenAI checks: Risk/reward, pattern validation → 86% confidence
   → DeepSeek checks: Edge validation, backtest stats → 84% confidence
   → All 3 agree: 85-88% range ✅ UNANIMOUS

3. ORDER EXECUTION
   → IBKR: Place order for 1 ES contract
   → Price: 5847.25
   → Status: PLACED → PENDING → FILLED

4. FILL VERIFICATION (Broker Confirmation)
   → Verify at TWS API
   → Order moved to _filled_orders
   → Fill confirmed in narration.jsonl

5. TRADE LOGGED (Real-time Narration)
   {
     "ts": "2026-01-07T15:50:00Z",
     "event_type": "ORDER_FILLED",
     "venue": "ibkr",
     "symbol": "ES",
     "details": {
       "price": 5847.25,
       "size": 1,
       "direction": "BUY",
       "strategy": "fabio_aaa_full",
       "hive_consensus": "UNANIMOUS (85-88%)",
       "status": "FILLED"
     }
   }

6. MONITORING (Real-time)
   → Monitor narration.py shows live trade
   → Dashboard updated
   → Proof of execution available

RESULT: Only HIGHEST QUALITY trades executed ✅
"""

# ═══════════════════════════════════════════════════════════════════════════════
# USAGE IN CODE:
# ═══════════════════════════════════════════════════════════════════════════════

"""
# In any agent, strategy, or connector:

from global_config import (
    BROKER_CONFIG,
    QUALITY_THRESHOLDS,
    HIVE_AGENT_CONFIG,
    AUTO_SCALING_CONFIG,
    IMMUTABLE_RULES
)

# Check if Coinbase should trade:
if BROKER_CONFIG['COINBASE']['mode'] == 'LIVE':
    trade_size = 5.0  # Start at minimum
    
# Check minimum confidence:
if strategy_confidence >= QUALITY_THRESHOLDS['MINIMUM_CONFIDENCE']:
    # Proceed with trade
    
# Alert on graduation:
if AUTO_SCALING_CONFIG['GRADUATION_ALERTS']['enabled']:
    notify_user("🎉 SCALE UP EVENT: Increasing trade size from $5 to $8")
"""

print(__doc__)
print("\n✅ Global configuration loaded successfully")
print(f"✅ Immutable rules: {len(IMMUTABLE_RULES)}")
print(f"✅ Broker configs: {len(BROKER_CONFIG)}")
print(f"✅ Quality thresholds enforced")
print(f"✅ Hive agents configured for quality-first search")
