#!/usr/bin/env python3
"""
UI RENDERER
Converts strict JSON outputs to human-readable format
Provides clean summaries for users without exposing raw JSON
"""
from typing import Dict, Any, List, Optional
from datetime import datetime

class HiveUIRenderer:
    """Renders AI Hive outputs in human-readable format"""
    
    @staticmethod
    def render_summary(output: Dict[str, Any], include_json: bool = False) -> str:
        """
        Render complete analysis summary
        
        Args:
            output: HiveOutput dict (validated JSON from AI)
            include_json: If True, append raw JSON at bottom
        
        Returns:
            Formatted string ready for display
        """
        status = output.get("status", "unknown")
        
        if status == "need_input":
            return HiveUIRenderer._render_need_input(output)
        elif status == "no_trade":
            return HiveUIRenderer._render_no_trade(output)
        elif status == "error":
            return HiveUIRenderer._render_error(output)
        elif status == "ok":
            result = HiveUIRenderer._render_ok(output)
            if include_json:
                import json
                result += "\n\n" + "="*70
                result += "\nRAW JSON OUTPUT:\n"
                result += "="*70 + "\n"
                result += json.dumps(output, indent=2)
            return result
        else:
            return f"⚠️  Unknown status: {status}"
    
    @staticmethod
    def _render_need_input(output: Dict[str, Any]) -> str:
        """Render need_input status"""
        lines = [
            "❌ INCOMPLETE DATA - Cannot Analyze",
            "=" * 70,
            ""
        ]
        
        missing = output.get("missing_fields", [])
        if missing:
            lines.append("MISSING REQUIRED FIELDS:")
            for field in missing:
                lines.append(f"  • {field}")
            lines.append("")
        
        reason = output.get("reason", "")
        if reason:
            lines.append(f"REASON: {reason}")
            lines.append("")
        
        lines.append("ACTIONS:")
        lines.append("  1. Fill in missing fields")
        lines.append("  2. Click 'Autofill from chart' if available")
        lines.append("  3. Check settings for default values")
        
        return "\n".join(lines)
    
    @staticmethod
    def _render_no_trade(output: Dict[str, Any]) -> str:
        """Render no_trade status"""
        lines = [
            "🚫 NO TRADE RECOMMENDED",
            "=" * 70,
            ""
        ]
        
        reason = output.get("reason", "Conditions not favorable")
        lines.append(f"REASON: {reason}")
        lines.append("")
        
        risks = output.get("top_risks", [])
        if risks:
            lines.append("TOP RISKS:")
            for risk in risks:
                lines.append(f"  ⚠️  {risk}")
            lines.append("")
        
        # Still show market context if available
        instrument = output.get("instrument")
        timeframe = output.get("timeframe")
        regime = output.get("regime")
        bias = output.get("bias")
        
        if instrument and timeframe:
            lines.append(f"MARKET: {instrument} {timeframe}")
            if regime:
                lines.append(f"REGIME: {regime}")
            if bias:
                lines.append(f"BIAS: {bias}")
        
        return "\n".join(lines)
    
    @staticmethod
    def _render_error(output: Dict[str, Any]) -> str:
        """Render error status"""
        lines = [
            "❌ ERROR",
            "=" * 70,
            ""
        ]
        
        reason = output.get("reason", "Unknown error occurred")
        lines.append(f"ERROR: {reason}")
        lines.append("")
        lines.append("Please check logs or contact support")
        
        return "\n".join(lines)
    
    @staticmethod
    def _render_ok(output: Dict[str, Any]) -> str:
        """Render successful analysis"""
        lines = [
            "✅ HIVE ANALYSIS COMPLETE",
            "=" * 70,
            ""
        ]
        
        # Header info
        instrument = output.get("instrument", "N/A")
        timeframe = output.get("timeframe", "N/A")
        session = output.get("session", "N/A")
        timestamp = output.get("timestamp_utc", "")
        
        lines.append(f"📊 {instrument} | {timeframe} | {session} session")
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                lines.append(f"⏰ {dt.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            except:
                lines.append(f"⏰ {timestamp}")
        lines.append("")
        
        # Market assessment
        regime = output.get("regime", "unknown")
        bias = output.get("bias", "neutral")
        confidence = output.get("confidence", 0.0)
        
        # Color-code bias
        bias_emoji = "📈" if bias == "bullish" else "📉" if bias == "bearish" else "➡️"
        confidence_bar = HiveUIRenderer._confidence_bar(confidence)
        
        lines.append("MARKET ASSESSMENT:")
        lines.append(f"  Regime: {regime.upper()}")
        lines.append(f"  Bias: {bias_emoji} {bias.upper()}")
        lines.append(f"  Confidence: {confidence_bar} {confidence:.1%}")
        lines.append("")
        
        # Key levels
        key_levels = output.get("key_levels")
        if key_levels:
            lines.append("KEY LEVELS:")
            
            resistance = key_levels.get("resistance", [])
            if resistance:
                lines.append(f"  Resistance: {', '.join(f'{r:.5f}' for r in resistance)}")
            
            support = key_levels.get("support", [])
            if support:
                lines.append(f"  Support: {', '.join(f'{s:.5f}' for s in support)}")
            
            invalidation = key_levels.get("invalidation")
            if invalidation:
                lines.append(f"  ⚠️  Invalidation: {invalidation:.5f}")
            
            lines.append("")
        
        # Setups
        setups = output.get("setups", [])
        if setups:
            lines.append(f"TRADE SETUPS ({len(setups)}):")
            lines.append("")
            
            for i, setup in enumerate(setups, 1):
                lines.extend(HiveUIRenderer._render_setup(setup, i))
                if i < len(setups):
                    lines.append("")
        
        # Position sizing
        position_sizing = output.get("position_sizing")
        if position_sizing:
            lines.append("")
            lines.append("POSITION SIZING:")
            method = position_sizing.get("method", "fixed_risk")
            risk_pct = position_sizing.get("risk_per_trade_pct", 0)
            max_daily = position_sizing.get("max_daily_loss_pct", 0)
            leverage = position_sizing.get("leverage_cap", 1)
            
            lines.append(f"  Method: {method.replace('_', ' ').title()}")
            lines.append(f"  Risk per trade: {risk_pct}%")
            lines.append(f"  Max daily loss: {max_daily}%")
            lines.append(f"  Leverage cap: {leverage}x")
            
            notes = position_sizing.get("sizing_notes", [])
            if notes:
                for note in notes:
                    lines.append(f"  📝 {note}")
        
        # Execution notes
        exec_notes = output.get("execution_notes", [])
        if exec_notes:
            lines.append("")
            lines.append("EXECUTION NOTES:")
            for note in exec_notes:
                lines.append(f"  • {note}")
        
        # Top risks
        risks = output.get("top_risks", [])
        if risks:
            lines.append("")
            lines.append("TOP RISKS:")
            for risk in risks:
                lines.append(f"  ⚠️  {risk}")
        
        # Cost model
        cost_model = output.get("cost_model")
        if cost_model:
            spread = cost_model.get("spread")
            fees = cost_model.get("fees_per_unit")
            if spread or fees:
                lines.append("")
                lines.append("COST MODEL:")
                if spread:
                    lines.append(f"  Spread: {spread}")
                if fees:
                    lines.append(f"  Fees per unit: {fees}")
        
        return "\n".join(lines)
    
    @staticmethod
    def _render_setup(setup: Dict[str, Any], number: int) -> List[str]:
        """Render individual trade setup"""
        lines = []
        
        name = setup.get("name", f"Setup {number}")
        scenario = setup.get("scenario", "base")
        
        lines.append(f"──────────────────────────────────────")
        lines.append(f"SETUP #{number}: {name} ({scenario})")
        lines.append(f"──────────────────────────────────────")
        
        # Trigger
        trigger = setup.get("trigger", "N/A")
        lines.append(f"Trigger: {trigger}")
        
        # Entry/Stop/Targets
        entry = setup.get("entry", 0)
        stop_loss = setup.get("stop_loss", 0)
        take_profit = setup.get("take_profit", [])
        expected_R = setup.get("expected_R", 0)
        
        lines.append(f"Entry: {entry:.5f}")
        lines.append(f"Stop Loss: {stop_loss:.5f}")
        
        if take_profit:
            lines.append(f"Take Profit:")
            for i, tp in enumerate(take_profit, 1):
                lines.append(f"  TP{i}: {tp:.5f}")
        
        # Risk/Reward
        r_color = "🟢" if expected_R >= 2.0 else "🟡" if expected_R >= 1.5 else "🔴"
        lines.append(f"Expected R:R: {r_color} {expected_R:.2f}")
        
        # OCO status
        oco = setup.get("oco", {})
        if oco.get("enabled"):
            lines.append("✅ OCO: ENABLED")
            oco_tp = oco.get("tp", [])
            oco_sl = oco.get("sl", 0)
            if oco_tp and oco_sl:
                lines.append(f"   TP: {', '.join(f'{tp:.5f}' for tp in oco_tp)}")
                lines.append(f"   SL: {oco_sl:.5f}")
        else:
            lines.append("❌ OCO: DISABLED (INVALID)")
        
        # Notes
        notes = setup.get("notes", [])
        if notes:
            lines.append("Notes:")
            for note in notes:
                lines.append(f"  • {note}")
        
        return lines
    
    @staticmethod
    def _confidence_bar(confidence: float) -> str:
        """Generate visual confidence bar"""
        filled = int(confidence * 10)
        bar = "█" * filled + "░" * (10 - filled)
        return f"[{bar}]"
    
    @staticmethod
    def render_compact(output: Dict[str, Any]) -> str:
        """Render compact one-line summary"""
        status = output.get("status", "unknown")
        instrument = output.get("instrument", "")
        bias = output.get("bias", "")
        confidence = output.get("confidence", 0.0)
        
        if status == "ok":
            setups = output.get("setups", [])
            num_setups = len(setups)
            return f"✅ {instrument} {bias.upper()} ({confidence:.0%}) - {num_setups} setup(s)"
        elif status == "no_trade":
            reason = output.get("reason", "")[:50]
            return f"🚫 {instrument} NO TRADE - {reason}"
        elif status == "need_input":
            missing = len(output.get("missing_fields", []))
            return f"❌ {instrument} NEED INPUT - {missing} field(s) missing"
        else:
            return f"⚠️  {instrument} {status.upper()}"
    
    @staticmethod
    def render_notification(output: Dict[str, Any]) -> str:
        """Render push notification text (short)"""
        status = output.get("status", "unknown")
        instrument = output.get("instrument", "")
        
        if status == "ok":
            bias = output.get("bias", "neutral")
            setups = output.get("setups", [])
            if setups:
                first_setup = setups[0]
                entry = first_setup.get("entry", 0)
                return f"{instrument} {bias.upper()} setup @ {entry:.5f}"
            return f"{instrument} analysis ready"
        elif status == "no_trade":
            return f"{instrument} NO TRADE"
        else:
            return f"{instrument} {status}"


# Quick render function
def render_hive_output(output: Dict[str, Any], mode: str = "full") -> str:
    """
    Render Hive output in specified mode
    
    Args:
        output: HiveOutput dict
        mode: "full", "compact", or "notification"
    
    Returns:
        Formatted string
    """
    renderer = HiveUIRenderer()
    
    if mode == "compact":
        return renderer.render_compact(output)
    elif mode == "notification":
        return renderer.render_notification(output)
    else:
        return renderer.render_summary(output)


# Export
__all__ = ['HiveUIRenderer', 'render_hive_output']
