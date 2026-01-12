#!/usr/bin/env python3
"""
CANONICAL HIVE OUTPUT SCHEMA
Single source of truth for all AI agent outputs
"""
import json
from typing import Dict, Any, List, Optional, Literal
from dataclasses import dataclass, asdict
from datetime import datetime

@dataclass
class KeyLevels:
    """Support/resistance/invalidation levels"""
    support: List[float]
    resistance: List[float]
    invalidation: float

@dataclass
class OCOBracket:
    """OCO (One-Cancels-Other) bracket - MANDATORY"""
    enabled: bool
    tp: List[float]  # Take profit levels
    sl: float        # Stop loss

@dataclass
class Setup:
    """Individual trade setup"""
    name: str
    scenario: Literal["base", "bull", "bear"]
    trigger: str
    entry: float
    stop_loss: float
    take_profit: List[float]
    oco: OCOBracket
    expected_R: float  # Risk/reward ratio
    notes: List[str]

@dataclass
class PositionSizing:
    """Position sizing parameters"""
    method: Literal["fixed_risk", "volatility_adjusted"]
    risk_per_trade_pct: float
    max_daily_loss_pct: float
    leverage_cap: float
    sizing_notes: List[str]

@dataclass
class CostModel:
    """Trading costs"""
    spread: Optional[float]
    fees_per_unit: Optional[float]
    notes: List[str]

@dataclass
class HiveOutput:
    """
    CANONICAL HIVE OUTPUT SCHEMA
    All agents must conform to this structure
    """
    status: Literal["ok", "need_input", "no_trade", "error"]
    instrument: str
    timeframe: str
    timestamp_utc: str
    session: Literal["NY", "London", "Asia", "overlap", "unknown"]
    regime: Literal["trend", "range", "transition", "high_volatility", "low_volatility"]
    bias: Literal["bullish", "bearish", "neutral"]
    confidence: float  # 0.0 to 1.0
    key_levels: Optional[KeyLevels]
    setups: List[Setup]
    position_sizing: PositionSizing
    cost_model: CostModel
    execution_notes: List[str]
    top_risks: List[str]
    
    # Optional fields for error states
    missing_fields: Optional[List[str]] = None
    reason: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    def validate(self) -> tuple[bool, List[str]]:
        """
        Validate output meets requirements
        Returns: (is_valid, list_of_errors)
        """
        errors = []
        
        # Check status-specific requirements
        if self.status == "ok":
            if not self.setups:
                errors.append("status=ok but no setups provided")
            
            # Validate each setup
            for i, setup in enumerate(self.setups):
                # OCO must be enabled
                if not setup.oco.enabled:
                    errors.append(f"Setup {i} ({setup.name}): OCO not enabled")
                
                # OCO must have valid TP and SL
                if not setup.oco.tp:
                    errors.append(f"Setup {i} ({setup.name}): OCO missing take_profit levels")
                if setup.oco.sl == 0:
                    errors.append(f"Setup {i} ({setup.name}): OCO missing stop_loss")
                
                # Expected R must be >= 1.5
                if setup.expected_R < 1.5:
                    errors.append(f"Setup {i} ({setup.name}): expected_R {setup.expected_R} < 1.5")
                
                # Entry/SL/TP must be valid numbers
                if setup.entry <= 0:
                    errors.append(f"Setup {i} ({setup.name}): invalid entry price")
                if setup.stop_loss <= 0:
                    errors.append(f"Setup {i} ({setup.name}): invalid stop_loss")
                if not all(tp > 0 for tp in setup.take_profit):
                    errors.append(f"Setup {i} ({setup.name}): invalid take_profit levels")
        
        elif self.status == "need_input":
            if not self.missing_fields:
                errors.append("status=need_input but missing_fields not specified")
            if not self.reason:
                errors.append("status=need_input but reason not provided")
        
        elif self.status == "no_trade":
            if not self.reason:
                errors.append("status=no_trade but reason not provided")
        
        # Confidence must be in range
        if not (0.0 <= self.confidence <= 1.0):
            errors.append(f"confidence {self.confidence} out of range [0.0, 1.0]")
        
        # OCO must be required in position sizing
        if not self.position_sizing:
            errors.append("position_sizing missing")
        
        return (len(errors) == 0, errors)


# Validation helpers
def validate_json_structure(data: Dict[str, Any]) -> tuple[bool, List[str]]:
    """
    Validate raw JSON matches schema structure
    Returns: (is_valid, list_of_errors)
    """
    errors = []
    required_fields = [
        "status", "instrument", "timeframe", "timestamp_utc", "session",
        "regime", "bias", "confidence", "position_sizing", "cost_model",
        "execution_notes", "top_risks"
    ]
    
    for field in required_fields:
        if field not in data:
            errors.append(f"Missing required field: {field}")
    
    # Validate status values
    if "status" in data and data["status"] not in ["ok", "need_input", "no_trade", "error"]:
        errors.append(f"Invalid status: {data['status']}")
    
    # If status=ok, setups must exist
    if data.get("status") == "ok":
        if "setups" not in data or not data["setups"]:
            errors.append("status=ok but setups missing or empty")
        else:
            # Validate each setup has OCO
            for i, setup in enumerate(data["setups"]):
                if "oco" not in setup:
                    errors.append(f"Setup {i}: missing oco field")
                elif not setup["oco"].get("enabled"):
                    errors.append(f"Setup {i}: oco.enabled is false")
    
    return (len(errors) == 0, errors)


def get_static_contract() -> str:
    """
    STATIC CONTRACT - sent once, defines role and output format
    This should rarely change
    """
    return """You are the Hive trading analyst. Use ONLY the information provided in the DYNAMIC JOB TICKET JSON below. Do not assume missing values. Do not use external market knowledge without provided context.

OUTPUT FORMAT: Return STRICT JSON ONLY (no markdown, no commentary, no code blocks). Your output must conform EXACTLY to this schema:

{
  "status": "ok|need_input|no_trade|error",
  "instrument": "string",
  "timeframe": "string", 
  "timestamp_utc": "string (ISO)",
  "session": "NY|London|Asia|overlap|unknown",
  "regime": "trend|range|transition|high_volatility|low_volatility",
  "bias": "bullish|bearish|neutral",
  "confidence": 0.0-1.0,
  "key_levels": {
    "support": [numbers],
    "resistance": [numbers],
    "invalidation": number
  },
  "setups": [
    {
      "name": "string",
      "scenario": "base|bull|bear",
      "trigger": "string",
      "entry": number,
      "stop_loss": number,
      "take_profit": [numbers],
      "oco": {
        "enabled": true,
        "tp": [numbers],
        "sl": number
      },
      "expected_R": number,
      "notes": [strings]
    }
  ],
  "position_sizing": {
    "method": "fixed_risk|volatility_adjusted",
    "risk_per_trade_pct": number,
    "max_daily_loss_pct": number,
    "leverage_cap": number,
    "sizing_notes": [strings]
  },
  "cost_model": {
    "spread": number|null,
    "fees_per_unit": number|null,
    "notes": [strings]
  },
  "execution_notes": [strings],
  "top_risks": [strings]
}

MANDATORY RULES:
1. OCO BRACKETS: Every setup MUST include an OCO bracket with oco.enabled=true, TP array, and SL. If you cannot determine valid levels, return status=no_trade.
2. RISK/REWARD: Expected_R must be >= 1.5. If less, return status=no_trade.
3. MISSING DATA: If required fields in the job ticket are missing, return status=need_input with missing_fields array.
4. UNCERTAINTY: If regime unclear or confidence < 0.5, return status=no_trade with reason.

ERROR STATES:
- If missing critical input: {"status":"need_input","missing_fields":[...],"reason":"..."}
- If no valid trade: {"status":"no_trade","reason":"...","top_risks":[...]}
- If error: {"status":"error","reason":"..."}"""


def get_dynamic_job_ticket(
    instrument: str,
    timeframe: str,
    price_context: Dict[str, Any],
    objective: Literal["scalp", "day", "swing", "hedge", "invest"],
    risk_rules: Dict[str, Any],
    cost_model: Optional[Dict[str, Any]] = None,
    session: Optional[str] = None,
    news_risk: Optional[str] = None
) -> str:
    """
    DYNAMIC JOB TICKET - changes every call with fresh market data
    This is the actual task + context
    """
    timestamp_utc = datetime.utcnow().isoformat() + "Z"
    
    # Determine session if not provided
    if not session:
        hour = datetime.utcnow().hour
        if 13 <= hour < 21:
            session = "NY"
        elif 7 <= hour < 16:
            session = "London"
        elif 0 <= hour < 8:
            session = "Asia"
        else:
            session = "overlap"
    
    # Build cost model
    if not cost_model:
        cost_model = {
            "estimated_spread": None,
            "estimated_fees_per_unit": None,
            "broker_fee_preset": ""
        }
    
    job_ticket = {
        "instrument": instrument,
        "timeframe": timeframe,
        "timestamp_utc": timestamp_utc,
        "session": session,
        "objective": objective,
        "price_context": price_context,
        "risk_rules": risk_rules,
        "cost_model": cost_model,
        "task": (
            "Determine regime, bias, key levels, and provide 2-3 setups with "
            "entry/SL/TP and OCO brackets. Include invalidation and risk notes. "
            "If unclear or R:R < 1.5, return status=no_trade."
        )
    }
    
    if news_risk:
        job_ticket["news_risk"] = news_risk
    
    return f"""DYNAMIC JOB TICKET:

{json.dumps(job_ticket, indent=2)}

ANALYZE THE ABOVE CONTEXT AND RETURN STRICT JSON MATCHING THE SCHEMA."""


# Export key functions
__all__ = [
    'HiveOutput', 'Setup', 'OCOBracket', 'KeyLevels', 'PositionSizing', 'CostModel',
    'validate_json_structure', 'get_static_contract', 'get_dynamic_job_ticket'
]
