#!/usr/bin/env python3
"""
DATA COMPLETENESS GATE
Validates required fields before calling AI agents
Blocks calls when inputs missing and shows what's needed
"""
from typing import Dict, Any, List, Tuple, Optional, Literal
from datetime import datetime

class DataCompletenessGate:
    """
    Validates market data completeness before AI agent calls
    Prevents "need_input" loops by catching missing data early
    """
    
    # Minimum required fields (Tier A)
    REQUIRED_FIELDS = {
        "instrument": str,
        "timeframe": str,
        "price_context.current_price": (int, float),
        "price_context.recent_high": (int, float),
        "price_context.recent_low": (int, float),
        "objective": str,
        "risk_rules.max_risk_per_trade_pct": (int, float),
        "risk_rules.max_daily_loss_pct": (int, float),
        "risk_rules.leverage_cap": (int, float),
        "risk_rules.oco_required": bool,
    }
    
    # Optional but recommended fields
    RECOMMENDED_FIELDS = {
        "price_context.last_10_closes": list,
        "price_context.last_10_candles": list,
        "session": str,
        "cost_model.estimated_spread": (int, float, type(None)),
        "news_risk": str,
    }
    
    @staticmethod
    def _get_nested_value(data: Dict, path: str) -> Any:
        """Get value from nested dict using dot notation"""
        keys = path.split('.')
        value = data
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        return value
    
    @staticmethod
    def _check_type(value: Any, expected_type) -> bool:
        """Check if value matches expected type(s)"""
        if isinstance(expected_type, tuple):
            return isinstance(value, expected_type)
        return isinstance(value, expected_type)
    
    def validate(self, data: Dict[str, Any]) -> Tuple[bool, List[str], List[str], str]:
        """
        Validate data completeness
        
        Returns:
            (is_valid, missing_fields, warnings, tier)
            - is_valid: True if all required fields present
            - missing_fields: List of missing required fields
            - warnings: List of missing recommended fields
            - tier: Data quality tier (A/B/C)
        """
        missing = []
        warnings = []
        
        # Check required fields
        for field, expected_type in self.REQUIRED_FIELDS.items():
            value = self._get_nested_value(data, field)
            if value is None:
                missing.append(field)
            elif not self._check_type(value, expected_type):
                missing.append(f"{field} (wrong type: {type(value).__name__})")
        
        # Check recommended fields
        for field, expected_type in self.RECOMMENDED_FIELDS.items():
            value = self._get_nested_value(data, field)
            if value is None:
                warnings.append(field)
        
        # Determine data tier
        tier = self._determine_tier(data)
        
        is_valid = len(missing) == 0
        return (is_valid, missing, warnings, tier)
    
    def _determine_tier(self, data: Dict[str, Any]) -> str:
        """
        Determine data quality tier
        Tier A: Minimum viable (current + high + low)
        Tier B: Better (+ last 10 candles)
        Tier C: Best (+ last 50 candles + volatility indicators)
        """
        price_context = data.get("price_context", {})
        
        # Check for Tier C (best)
        if price_context.get("last_50_candles") and len(price_context.get("last_50_candles", [])) >= 50:
            if "ATR" in price_context or "volatility" in price_context:
                return "C"
        
        # Check for Tier B (better)
        last_10 = price_context.get("last_10_candles") or price_context.get("last_10_closes")
        if last_10 and len(last_10) >= 10:
            return "B"
        
        # Tier A (minimum)
        if all(k in price_context for k in ["current_price", "recent_high", "recent_low"]):
            return "A"
        
        return "INSUFFICIENT"
    
    def format_error_message(self, missing: List[str], warnings: List[str], tier: str) -> str:
        """Format user-friendly error message"""
        lines = ["❌ DATA INCOMPLETE - Cannot call AI agent"]
        lines.append("")
        
        if missing:
            lines.append("MISSING REQUIRED FIELDS:")
            for field in missing:
                lines.append(f"  - {field}")
            lines.append("")
        
        if warnings:
            lines.append("MISSING RECOMMENDED FIELDS (optional but improves analysis):")
            for field in warnings:
                lines.append(f"  - {field}")
            lines.append("")
        
        lines.append(f"DATA QUALITY TIER: {tier}")
        lines.append("")
        lines.append("ACTIONS:")
        lines.append("  1. Fill in missing required fields")
        lines.append("  2. Click 'Autofill from chart' if available")
        lines.append("  3. Check settings for risk_rules defaults")
        
        return "\n".join(lines)
    
    def autofill_defaults(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Attempt to autofill missing fields with sensible defaults
        WARNING: Only use for non-critical fields
        """
        data = data.copy()
        
        # Autofill session if missing
        if "session" not in data:
            hour = datetime.utcnow().hour
            if 13 <= hour < 21:
                data["session"] = "NY"
            elif 7 <= hour < 16:
                data["session"] = "London"
            elif 0 <= hour < 8:
                data["session"] = "Asia"
            else:
                data["session"] = "overlap"
        
        # Autofill timestamp if missing
        if "timestamp_utc" not in data:
            data["timestamp_utc"] = datetime.utcnow().isoformat() + "Z"
        
        # Autofill objective if missing (default to day trading)
        if "objective" not in data:
            data["objective"] = "day"
        
        # Autofill OCO requirement if missing (default to True)
        if "risk_rules" in data and "oco_required" not in data["risk_rules"]:
            data["risk_rules"]["oco_required"] = True
        
        return data
    
    def suggest_autofill_actions(self, missing: List[str]) -> List[Dict[str, str]]:
        """
        Suggest concrete autofill actions for missing fields
        Returns list of {field, action, source}
        """
        suggestions = []
        
        for field in missing:
            if field.startswith("price_context."):
                suggestions.append({
                    "field": field,
                    "action": "Fetch from chart/price feed",
                    "source": "market_data_source"
                })
            elif field.startswith("risk_rules."):
                suggestions.append({
                    "field": field,
                    "action": "Load from risk settings",
                    "source": "risk_config"
                })
            elif field == "instrument":
                suggestions.append({
                    "field": field,
                    "action": "Select from dropdown or enter symbol",
                    "source": "ui_input"
                })
            elif field == "timeframe":
                suggestions.append({
                    "field": field,
                    "action": "Select from dropdown (5m/15m/1h/4h/1D)",
                    "source": "ui_input"
                })
            elif field == "objective":
                suggestions.append({
                    "field": field,
                    "action": "Select trading style (scalp/day/swing)",
                    "source": "ui_input"
                })
        
        return suggestions


# Validation presets for different use cases
class ValidationPresets:
    """Common validation configurations"""
    
    @staticmethod
    def scalping() -> Dict[str, Any]:
        """Strict requirements for scalping (needs high-quality data)"""
        return {
            "min_tier": "B",
            "required_spread": True,
            "required_fees": True,
            "min_candles": 20,
            "max_age_seconds": 60  # Data must be fresh
        }
    
    @staticmethod
    def day_trading() -> Dict[str, Any]:
        """Standard requirements for day trading"""
        return {
            "min_tier": "A",
            "required_spread": False,
            "required_fees": False,
            "min_candles": 10,
            "max_age_seconds": 300
        }
    
    @staticmethod
    def swing_trading() -> Dict[str, Any]:
        """Relaxed requirements for swing trading"""
        return {
            "min_tier": "A",
            "required_spread": False,
            "required_fees": False,
            "min_candles": 5,
            "max_age_seconds": 3600
        }


# Quick validation function
def validate_before_ai_call(data: Dict[str, Any], 
                           objective: Optional[str] = None) -> Tuple[bool, str]:
    """
    Quick validation check before AI call
    
    Returns:
        (can_proceed, error_message)
    """
    gate = DataCompletenessGate()
    is_valid, missing, warnings, tier = gate.validate(data)
    
    if not is_valid:
        error_msg = gate.format_error_message(missing, warnings, tier)
        return (False, error_msg)
    
    # Check tier requirements based on objective
    if objective == "scalp" and tier == "A":
        return (False, "⚠️ SCALPING requires Tier B or C data (need at least 10-20 candles)")
    
    return (True, "")


# Export
__all__ = [
    'DataCompletenessGate',
    'ValidationPresets',
    'validate_before_ai_call'
]
