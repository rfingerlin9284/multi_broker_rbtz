"""
RICK STRATEGY REGISTRY
Central configuration for all trading strategies with their specific parameters
"""

STRATEGY_CONFIGS = {
    # === FABIO AAA SUITE (Advanced Multi-Engine) ===
    "FABIO_AAA_FULL": {
        "name": "Fabio AAA Full Suite",
        "description": "Complete AAA setup: Profile + OrderFlow + Liquidity + VWAP + 3-tranche OCO",
        "enabled": False,  # Under development
        "requires_engines": ["profile", "orderflow", "liquidity", "vwap", "range_bar"],
        "params": {
            "top_n_candidates": 5,
            "min_aaa_score": 75,
            "require_all_engines": True,
            "profile_weight": 0.25,
            "orderflow_weight": 0.25,
            "liquidity_weight": 0.25,
            "vwap_weight": 0.25,
            "tranche_sizes": [0.30, 0.40, 0.30],  # Entry distribution
            "tranche_targets": [1.0, 2.0, 3.0],   # R multiples
        }
    },
    
    # === HOLY GRAIL (Price Action) ===
    "HOLY_GRAIL": {
        "name": "Price Action Holy Grail",
        "description": "Support/resistance retests, wick rejections, structure breaks",
        "enabled": True,
        "params": {
            "timeframes": ["15m", "1h", "4h"],
            "min_confidence": 0.65,
            "target_rr": 2.0,
            "level_buffer": 0.0005,  # Price distance to consider "at level"
            "require_higher_tf_confirmation": True,
        }
    },
    
    # === LIQUIDITY SWEEP ===
    "LIQUIDITY_SWEEP": {
        "name": "Liquidity Sweep Reversal",
        "description": "Equal highs/lows sweep + structure shift reversal",
        "enabled": True,
        "params": {
            "timeframes": ["5m", "15m", "1h"],
            "min_confidence": 0.75,
            "target_rr": 2.5,
            "sweep_tolerance": 0.0003,  # Price tolerance for sweep detection
            "require_structure_shift": True,
            "min_equal_touches": 2,  # Minimum touches to form equal highs/lows
        }
    },
    
    # === FVG (Fair Value Gap) ===
    "FVG_WOLF": {
        "name": "Fair Value Gap Wolf",
        "description": "Trades FVG fill + structure confirmation",
        "enabled": False,
        "params": {
            "timeframes": ["5m", "15m", "1h"],
            "min_confidence": 0.70,
            "target_rr": 2.0,
            "min_fvg_size": 0.0005,  # Minimum gap size
            "fvg_fill_ratio": 0.50,  # How much of gap to fill before entry
            "require_trend_alignment": True,
        }
    },

    # === SIMPLE STRATEGIES (Backtested winners before AAA) ===
    "EMA_SCALPER": {
        "name": "EMA Scalper",
        "description": "Fast EMA crossover scalper for high-probability moves",
        "enabled": True,
        "params": {
            "timeframes": ["1m", "5m", "15m"],
            "fast_period": 8,
            "slow_period": 21,
            "min_confidence": 0.68,
            "target_rr": 1.5,
            "stop_pct": 0.005,  # 0.5% default
        }
    },

    "INSTITUTIONAL_SD": {
        "name": "Institutional SD",
        "description": "Volatility breakout and institutional flow detection",
        "enabled": True,
        "params": {
            "timeframes": ["5m", "15m", "1h"],
            "min_confidence": 0.70,
            "target_rr": 2.0,
            "sd_window": 20,
            "breakout_multiplier": 2.0,
            "require_flow_confirmation": True,
        }
    },
    
    # === FIBONACCI CONFLUENCE ===
    "FIB_CONFLUENCE": {
        "name": "Fibonacci Confluence Breakout",
        "description": "Multi-timeframe Fib level confluence + breakout",
        "enabled": False,
        "params": {
            "timeframes": ["15m", "1h", "4h"],
            "min_confidence": 0.68,
            "target_rr": 2.5,
            "fib_levels": [0.382, 0.50, 0.618, 0.786],  # Key Fib ratios
            "confluence_threshold": 2,  # Min levels within range
            "confluence_range": 0.0005,  # Price range for confluence
        }
    },
    
    # === CRYPTO BREAKOUT ===
    "CRYPTO_BREAKOUT": {
        "name": "Crypto Momentum Breakout",
        "description": "Volume-confirmed breakouts for crypto pairs",
        "enabled": False,
        "params": {
            "timeframes": ["15m", "1h"],
            "min_confidence": 0.65,
            "target_rr": 2.0,
            "volume_multiplier": 1.5,  # Breakout volume vs avg volume
            "consolidation_periods": 10,  # Min bars in consolidation
            "breakout_strength": 0.0008,  # Min price move for breakout
        }
    },
    
    # === TRAP REVERSAL ===
    "TRAP_REVERSAL": {
        "name": "Trap Reversal Scalper",
        "description": "False breakout trap + quick reversal scalp",
        "enabled": True,
        "params": {
            "timeframes": ["5m", "15m"],
            "min_confidence": 0.72,
            "target_rr": 1.5,  # Tighter for scalps
            "trap_duration": 5,  # Max bars for trap to develop
            "reversal_speed": 3,  # Max bars for reversal
            "min_volume_spike": 1.3,
        }
    },
    
    # === WOLF PACK (Trend Following) ===
    "BULLISH_WOLF": {
        "name": "Bullish Wolf Trend",
        "description": "Multi-timeframe bullish trend alignment",
        "enabled": False,
        "params": {
            "timeframes": ["15m", "1h", "4h"],
            "min_confidence": 0.70,
            "target_rr": 2.5,
            "ma_periods": [20, 50, 200],
            "require_all_tf_bullish": True,
            "min_trend_strength": 0.65,
        }
    },
    
    "BEARISH_WOLF": {
        "name": "Bearish Wolf Trend",
        "description": "Multi-timeframe bearish trend alignment",
        "enabled": False,
        "params": {
            "timeframes": ["15m", "1h", "4h"],
            "min_confidence": 0.70,
            "target_rr": 2.5,
            "ma_periods": [20, 50, 200],
            "require_all_tf_bearish": True,
            "min_trend_strength": 0.65,
        }
    },
    
    "SIDEWAYS_WOLF": {
        "name": "Sideways Wolf Range",
        "description": "Range-bound mean reversion",
        "enabled": False,
        "params": {
            "timeframes": ["15m", "1h"],
            "min_confidence": 0.68,
            "target_rr": 1.5,  # Tighter for range trading
            "range_threshold": 0.0015,  # Max range size
            "min_touches": 3,  # Min touches of support/resistance
            "entry_at_extreme": 0.85,  # Enter at 85% of range extreme
        }
    },
    
    "CORRELATION_WOLF": {
        "name": "Correlation Wolf",
        "description": "Multi-instrument correlation divergence",
        "enabled": False,
        "params": {
            "timeframes": ["1h", "4h"],
            "min_confidence": 0.72,
            "target_rr": 2.0,
            "correlation_pairs": ["EURUSD", "GBPUSD", "USDCHF", "USDJPY"],
            "min_correlation": 0.70,
            "divergence_threshold": 0.0015,
        }
    },
    
    # === FIBONACCI WOLF ===
    "FIBONACCI_WOLF": {
        "name": "Fibonacci Wolf",
        "description": "Trend + Fibonacci retracement entries",
        "enabled": False,
        "params": {
            "timeframes": ["15m", "1h", "4h"],
            "min_confidence": 0.68,
            "target_rr": 2.5,
            "entry_fibs": [0.382, 0.50, 0.618],  # Preferred entry levels
            "require_trend": True,
            "min_swing_size": 0.0015,  # Min swing to draw Fibs
        }
    },
    
    # === EVENT STRADDLE ===
    "EVENT_STRADDLE": {
        "name": "Event Straddle",
        "description": "News/event volatility expansion plays",
        "enabled": False,  # Requires event calendar integration
        "params": {
            "min_confidence": 0.60,
            "target_rr": 2.0,
            "event_types": ["NFP", "CPI", "FOMC", "GDP"],
            "pre_event_minutes": 30,
            "breakout_threshold": 0.0010,
        }
    },
    
    # === HIGH PROBABILITY CORE ===
    "HIGH_PROB_CORE": {
        "name": "High Probability Core",
        "description": "Best setups only - highest conviction trades",
        "enabled": False,
        "params": {
            "timeframes": ["1h", "4h"],
            "min_confidence": 0.80,  # Only take very high confidence
            "target_rr": 3.0,  # Higher targets
            "require_multi_tf_confluence": True,
            "require_volume_confirmation": True,
            "require_trend_alignment": True,
            "max_trades_per_day": 3,  # Quality over quantity
        }
    },
}


def get_strategy_config(strategy_code: str) -> dict:
    """Get configuration for a strategy."""
    return STRATEGY_CONFIGS.get(strategy_code, {})


def get_enabled_strategies() -> list:
    """Get list of enabled strategy codes."""
    return [code for code, cfg in STRATEGY_CONFIGS.items() if cfg.get("enabled", False)]


def list_all_strategies() -> dict:
    """Get all strategy configs."""
    return STRATEGY_CONFIGS
