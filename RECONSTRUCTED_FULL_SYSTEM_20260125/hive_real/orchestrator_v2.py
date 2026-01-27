#!/usr/bin/env python3
"""
HIVE ORCHESTRATOR V2
Complete pipeline: Data Gate → Payload Builder → AI Call → Validation → UI Render
NO MORE "need_input" LOOPS - Blocks bad calls before they happen
"""
import json
import os
from typing import Dict, Any, List, Optional, Literal, Tuple
from datetime import datetime

# Import all components
from hive_schema import (
    get_static_contract, get_dynamic_job_ticket,
    validate_json_structure, HiveOutput
)
from data_gate import DataCompletenessGate, validate_before_ai_call
from payload_builder import PayloadBuilder
from ui_renderer import HiveUIRenderer, render_hive_output

class HiveOrchestratorV2:
    """
    Complete Hive pipeline orchestrator
    Enforces: Data completeness → Valid payload → AI call → JSON validation → OCO enforcement
    """
    
    def __init__(self):
        self.gate = DataCompletenessGate()
        self.builder = PayloadBuilder()
        self.renderer = HiveUIRenderer()
        
        # Check for API keys
        self.openai_key = os.getenv('OPENAI_API_KEY')
        self.xai_key = os.getenv('XAI_API_KEY')

        # Model selection (configurable)
        # Default to a cost-effective OpenAI model to avoid gpt-4 access/quota issues.
        self.openai_model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        self.xai_model = os.getenv('XAI_MODEL', 'grok-2-latest')
        
        self.stats = {
            "total_calls": 0,
            "blocked_calls": 0,
            "successful_calls": 0,
            "failed_validations": 0,
            "oco_violations": 0
        }
    
    def analyze(self,
               instrument: str,
               timeframe: str,
               current_price: float,
               objective: Literal["scalp", "day", "swing", "hedge", "invest"] = "day",
               prices: Optional[List[float]] = None,
               candles: Optional[List[Dict]] = None,
               recent_high: Optional[float] = None,
               recent_low: Optional[float] = None,
               risk_rules: Optional[Dict[str, Any]] = None,
               cost_model: Optional[Dict[str, Any]] = None,
               session: Optional[str] = None,
               news_risk: Optional[str] = None,
               render_mode: str = "full") -> Dict[str, Any]:
        """
        Main entry point - complete analysis pipeline
        
        Args:
            instrument: Trading symbol
            timeframe: Chart timeframe
            current_price: Current market price
            objective: Trading style (scalp/day/swing)
            prices: List of recent closes
            candles: List of OHLC dicts
            recent_high: Session high
            recent_low: Session low
            risk_rules: Risk parameters
            cost_model: Spread/fees
            session: Market session
            news_risk: News risk level
            render_mode: "full", "compact", "notification", or "json"
        
        Returns:
            Dict with:
                - status: "ok", "blocked", "error"
                - output: AI output (if successful)
                - rendered: Human-readable text
                - errors: Error messages (if any)
                - stats: Call statistics
        """
        self.stats["total_calls"] += 1
        
        try:
            # STEP 1: Build payload
            print("🔧 STEP 1: Building payload...")
            payload = self.builder.build_payload(
                instrument=instrument,
                timeframe=timeframe,
                current_price=current_price,
                recent_high=recent_high,
                recent_low=recent_low,
                prices=prices,
                candles=candles,
                objective=objective,
                risk_rules=risk_rules,
                cost_model=cost_model,
                session=session,
                news_risk=news_risk
            )
            print(f"   ✅ Payload built - Tier {payload['price_context']['tier']}")
            
            # STEP 2: Data completeness gate
            print("🚪 STEP 2: Checking data completeness...")
            is_valid, missing, warnings, tier = self.gate.validate(payload)
            
            if not is_valid:
                self.stats["blocked_calls"] += 1
                error_msg = self.gate.format_error_message(missing, warnings, tier)
                print(f"   ❌ BLOCKED - Data incomplete")
                
                return {
                    "status": "blocked",
                    "output": None,
                    "rendered": error_msg,
                    "errors": missing,
                    "warnings": warnings,
                    "stats": self.stats.copy()
                }
            
            print(f"   ✅ Data complete - Tier {tier}")
            if warnings:
                print(f"   ⚠️  Warnings: {len(warnings)} optional fields missing")
            
            # STEP 3: Call AI agents
            print("🤖 STEP 3: Calling AI agents...")
            ai_output = self._call_ai_agents(payload)
            
            if not ai_output:
                return {
                    "status": "error",
                    "output": None,
                    "rendered": "❌ No AI response received",
                    "errors": ["No API keys configured or all agents failed"],
                    "stats": self.stats.copy()
                }
            
            print(f"   ✅ AI response received")
            
            # STEP 4: Validate JSON structure
            print("✓ STEP 4: Validating JSON structure...")
            json_valid, json_errors = validate_json_structure(ai_output)
            
            if not json_valid:
                self.stats["failed_validations"] += 1
                error_msg = "❌ JSON VALIDATION FAILED:\n" + "\n".join(f"  • {e}" for e in json_errors)
                print(f"   ❌ Validation failed")
                
                return {
                    "status": "error",
                    "output": ai_output,
                    "rendered": error_msg,
                    "errors": json_errors,
                    "stats": self.stats.copy()
                }
            
            print(f"   ✅ JSON structure valid")
            
            # STEP 5: Validate OCO enforcement (if status=ok)
            if ai_output.get("status") == "ok":
                print("🛡️  STEP 5: Checking OCO enforcement...")
                oco_valid, oco_errors = self._validate_oco(ai_output)
                
                if not oco_valid:
                    self.stats["oco_violations"] += 1
                    error_msg = "❌ OCO VALIDATION FAILED:\n" + "\n".join(f"  • {e}" for e in oco_errors)
                    print(f"   ❌ OCO violations detected")
                    
                    return {
                        "status": "error",
                        "output": ai_output,
                        "rendered": error_msg,
                        "errors": oco_errors,
                        "stats": self.stats.copy()
                    }
                
                print(f"   ✅ All setups have valid OCO brackets")
            
            # STEP 6: Render output
            print("🎨 STEP 6: Rendering UI...")
            if render_mode == "json":
                rendered = json.dumps(ai_output, indent=2)
            else:
                rendered = render_hive_output(ai_output, mode=render_mode)
            
            print(f"   ✅ Rendered in {render_mode} mode")
            
            self.stats["successful_calls"] += 1
            
            print("✅ PIPELINE COMPLETE\n")
            
            return {
                "status": "ok",
                "output": ai_output,
                "rendered": rendered,
                "errors": [],
                "stats": self.stats.copy()
            }
            
        except Exception as e:
            print(f"   ❌ Pipeline error: {e}")
            return {
                "status": "error",
                "output": None,
                "rendered": f"❌ Pipeline error: {str(e)}",
                "errors": [str(e)],
                "stats": self.stats.copy()
            }
    
    def _call_ai_agents(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Call AI agents with proper system/user message separation
        Returns validated JSON output or None
        """
        # Try OpenAI first
        if self.openai_key:
            try:
                result = self._call_openai(payload)
                if result:
                    return result
            except Exception as e:
                print(f"      ❌ OpenAI error: {e}")
        
        # Try xAI Grok
        if self.xai_key:
            try:
                result = self._call_grok(payload)
                if result:
                    return result
            except Exception as e:
                print(f"      ❌ Grok error: {e}")
        
        return None
    
    def _call_openai(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Call OpenAI with system/user message separation"""
        import openai
        
        client = openai.OpenAI(api_key=self.openai_key)
        
        # Build messages
        system_message = get_static_contract()
        user_message = get_dynamic_job_ticket(
            instrument=payload["instrument"],
            timeframe=payload["timeframe"],
            price_context=payload["price_context"],
            objective=payload["objective"],
            risk_rules=payload["risk_rules"],
            cost_model=payload.get("cost_model"),
            session=payload.get("session"),
            news_risk=payload.get("news_risk")
        )
        
        print(f"      🧠 Querying OpenAI ({self.openai_model})...")
        
        response = client.chat.completions.create(
            model=self.openai_model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            temperature=0.1,
            max_tokens=1500
        )
        
        content = response.choices[0].message.content.strip()
        
        # Parse JSON (remove markdown if present)
        if '```json' in content:
            content = content.split('```json')[1].split('```')[0].strip()
        elif '```' in content:
            content = content.split('```')[1].split('```')[0].strip()
        
        return json.loads(content)
    
    def _call_grok(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Call xAI Grok with system/user message separation"""
        import requests
        
        # Build messages
        system_message = get_static_contract()
        user_message = get_dynamic_job_ticket(
            instrument=payload["instrument"],
            timeframe=payload["timeframe"],
            price_context=payload["price_context"],
            objective=payload["objective"],
            risk_rules=payload["risk_rules"],
            cost_model=payload.get("cost_model"),
            session=payload.get("session"),
            news_risk=payload.get("news_risk")
        )
        
        print(f"      🧠 Querying xAI Grok ({self.xai_model})...")
        
        response = requests.post(
            'https://api.x.ai/v1/chat/completions',
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.xai_key}'
            },
            json={
                'model': self.xai_model,
                'messages': [
                    {'role': 'system', 'content': system_message},
                    {'role': 'user', 'content': user_message}
                ],
                'temperature': 0.1,
                'stream': False
            },
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"      ❌ Grok API error: {response.status_code}")
            return None
        
        content = response.json()['choices'][0]['message']['content'].strip()
        
        # Parse JSON (remove markdown if present)
        if '```json' in content:
            content = content.split('```json')[1].split('```')[0].strip()
        elif '```' in content:
            content = content.split('```')[1].split('```')[0].strip()
        
        return json.loads(content)
    
    def _validate_oco(self, output: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate OCO brackets on all setups
        Returns: (is_valid, list_of_errors)
        """
        errors = []
        
        setups = output.get("setups", [])
        if not setups:
            return (True, [])  # No setups = no OCO requirements
        
        for i, setup in enumerate(setups):
            setup_name = setup.get("name", f"Setup {i+1}")
            
            # Check OCO exists
            oco = setup.get("oco")
            if not oco:
                errors.append(f"{setup_name}: Missing 'oco' field")
                continue
            
            # Check OCO enabled
            if not oco.get("enabled"):
                errors.append(f"{setup_name}: OCO not enabled")
            
            # Check TP levels exist and valid
            tp = oco.get("tp", [])
            if not tp:
                errors.append(f"{setup_name}: OCO missing TP levels")
            elif not all(isinstance(t, (int, float)) and t > 0 for t in tp):
                errors.append(f"{setup_name}: OCO TP levels invalid")
            
            # Check SL exists and valid
            sl = oco.get("sl")
            if sl is None:
                errors.append(f"{setup_name}: OCO missing SL")
            elif not isinstance(sl, (int, float)) or sl <= 0:
                errors.append(f"{setup_name}: OCO SL invalid")
        
        return (len(errors) == 0, errors)
    
    def autofill_and_analyze(self, instrument: str, timeframe: str, **kwargs) -> Dict[str, Any]:
        """
        Convenience method: autofill from chart then analyze
        Simulates fetching live data from chart/feed
        """
        print(f"📡 Autofilling data for {instrument} {timeframe}...")
        payload = self.builder.autofill_from_chart(instrument, timeframe)
        
        # Extract objective from kwargs or use payload default
        objective = kwargs.pop("objective", payload.get("objective", "day"))
        
        return self.analyze(
            instrument=instrument,
            timeframe=timeframe,
            current_price=payload["price_context"]["current_price"],
            prices=payload["price_context"].get("last_10_closes"),
            candles=payload["price_context"].get("last_50_candles"),
            recent_high=payload["price_context"]["recent_high"],
            recent_low=payload["price_context"]["recent_low"],
            objective=objective,
            risk_rules=kwargs.pop("risk_rules", payload["risk_rules"]),
            cost_model=kwargs.pop("cost_model", payload["cost_model"]),
            session=kwargs.pop("session", payload["session"]),
            **kwargs
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics"""
        stats = self.stats.copy()
        if stats["total_calls"] > 0:
            stats["block_rate"] = stats["blocked_calls"] / stats["total_calls"]
            stats["success_rate"] = stats["successful_calls"] / stats["total_calls"]
        return stats


# Global instance
_orchestrator = None

def get_orchestrator() -> HiveOrchestratorV2:
    """Get global orchestrator instance"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = HiveOrchestratorV2()
    return _orchestrator


# Convenience functions
def analyze_trade(instrument: str, timeframe: str, current_price: float, **kwargs) -> str:
    """
    Quick analysis with autofilled defaults
    Returns: Rendered output (human-readable)
    """
    orchestrator = get_orchestrator()
    result = orchestrator.analyze(instrument, timeframe, current_price, **kwargs)
    return result["rendered"]


def autofill_and_analyze(instrument: str, timeframe: str, **kwargs) -> str:
    """
    Quick analysis with autofilled chart data
    Returns: Rendered output (human-readable)
    """
    orchestrator = get_orchestrator()
    result = orchestrator.autofill_and_analyze(instrument, timeframe, **kwargs)
    return result["rendered"]


# Export
__all__ = [
    'HiveOrchestratorV2',
    'get_orchestrator',
    'analyze_trade',
    'autofill_and_analyze'
]
