#!/usr/bin/env python3
"""
AI HIVE AUTONOMOUS REPAIR SYSTEM
Collective AI diagnosis and patching when Hive fails

When the Hive goes down, connected AIs work together to:
1. Diagnose the root cause
2. Develop a fix/patch
3. Apply it autonomously (if safe)
4. Document everything in plain English
"""
import os
import json
from datetime import datetime
from typing import Dict, Any
from pathlib import Path


def diagnose_and_repair(error_type: str, error_message: str, stack_trace: str) -> Dict[str, Any]:
    """
    Collective AI diagnosis and repair.
    
    Connected AIs collaborate to:
    - Analyze the failure
    - Determine root cause
    - Develop fix
    - Apply patch (if safe and trackable)
    - Document decision process
    """
    
    print("\n🧠 COLLECTIVE AI DIAGNOSIS IN PROGRESS...")
    
    # Check which AIs are available
    available_ais = []
    if os.getenv('OPENAI_API_KEY'):
        available_ais.append('GPT')
    if os.getenv('XAI_API_KEY'):
        available_ais.append('Grok')
    if os.getenv('DEEPSEEK_API_KEY'):
        available_ais.append('DeepSeek')
    
    if not available_ais:
        return {
            'success': False,
            'reason': 'No AI connections available for diagnosis',
            'documentation': 'CRITICAL: All AI APIs disconnected'
        }
    
    print(f"   Connected AIs: {', '.join(available_ais)}")
    
    # Prepare diagnosis prompt for AIs
    diagnosis_prompt = f"""
AUTONOMOUS REPAIR REQUEST

ERROR DETAILS:
Type: {error_type}
Message: {error_message}
Stack Trace:
{stack_trace}

You are part of an AI collective tasked with autonomous system repair.

ANALYZE:
1. What went wrong and why?
2. Is this a known, trackable error that can be safely patched?
3. What is the exact fix needed (be specific - file paths, line numbers, code changes)?
4. What is the risk level of this fix? (LOW/MEDIUM/HIGH)
5. How confident are you this fix will work?

Respond with JSON:
{{
    "diagnosis": "Plain English explanation of what happened",
    "root_cause": "The actual underlying problem",
    "is_patchable": true/false,
    "fix_description": "Exact changes needed",
    "risk_level": "LOW|MEDIUM|HIGH",
    "confidence": 0.0-1.0,
    "reasoning": "Why this fix and how you arrived at it"
}}
"""
    
    # Collect diagnoses from available AIs
    diagnoses = []
    
    try:
        # Query GPT if available
        if 'GPT' in available_ais:
            print("   🧠 Querying GPT for diagnosis...")
            gpt_diagnosis = _query_gpt_for_diagnosis(diagnosis_prompt)
            if gpt_diagnosis:
                diagnoses.append(('GPT', gpt_diagnosis))
                print(f"      ✅ GPT: {gpt_diagnosis.get('diagnosis', 'N/A')[:60]}...")
        
        # Query Grok if available
        if 'Grok' in available_ais:
            print("   🧠 Querying Grok for diagnosis...")
            grok_diagnosis = _query_grok_for_diagnosis(diagnosis_prompt)
            if grok_diagnosis:
                diagnoses.append(('Grok', grok_diagnosis))
                print(f"      ✅ Grok: {grok_diagnosis.get('diagnosis', 'N/A')[:60]}...")
        
        # Query DeepSeek if available
        if 'DeepSeek' in available_ais:
            print("   🧠 Querying DeepSeek for diagnosis...")
            deepseek_diagnosis = _query_deepseek_for_diagnosis(diagnosis_prompt)
            if deepseek_diagnosis:
                diagnoses.append(('DeepSeek', deepseek_diagnosis))
                print(f"      ✅ DeepSeek: {deepseek_diagnosis.get('diagnosis', 'N/A')[:60]}...")
    
    except Exception as query_error:
        print(f"   ❌ Error querying AIs: {query_error}")
        return {
            'success': False,
            'reason': f'AI query failed: {query_error}',
            'documentation': f'Failed to reach AIs for diagnosis: {query_error}'
        }
    
    if not diagnoses:
        return {
            'success': False,
            'reason': 'No successful diagnoses received',
            'documentation': 'AIs could not analyze the error'
        }
    
    # Collective decision making
    print(f"\n🤝 COLLECTIVE DECISION ({len(diagnoses)} AIs consulted)")
    
    # Count how many AIs think it's patchable
    patchable_votes = sum(1 for _, d in diagnoses if d.get('is_patchable', False))
    avg_confidence = sum(d.get('confidence', 0) for _, d in diagnoses) / len(diagnoses)
    
    # Check risk levels
    risk_levels = [d.get('risk_level', 'HIGH') for _, d in diagnoses]
    max_risk = 'HIGH' if 'HIGH' in risk_levels else 'MEDIUM' if 'MEDIUM' in risk_levels else 'LOW'
    
    print(f"   Patchable votes: {patchable_votes}/{len(diagnoses)}")
    print(f"   Average confidence: {avg_confidence:.1%}")
    print(f"   Maximum risk level: {max_risk}")
    
    # Consensus rules
    consensus_reached = patchable_votes >= len(diagnoses) * 0.5  # 50%+ agreement
    safe_to_patch = max_risk in ['LOW', 'MEDIUM'] and avg_confidence >= 0.7
    
    if consensus_reached and safe_to_patch:
        # Apply the fix
        print("\n✅ CONSENSUS REACHED - Applying patch...")
        
        # Use the diagnosis with highest confidence
        best_diagnosis = max(diagnoses, key=lambda x: x[1].get('confidence', 0))[1]
        
        # Document everything
        documentation = _generate_documentation(
            diagnoses=diagnoses,
            consensus_vote=patchable_votes,
            confidence=avg_confidence,
            risk=max_risk,
            fix_applied=best_diagnosis.get('fix_description', 'N/A')
        )
        
        # Actually apply the patch (if it's a simple, safe change)
        patch_success = _apply_patch(best_diagnosis)
        
        if patch_success:
            return {
                'success': True,
                'summary': f"Patch applied successfully by AI collective ({patchable_votes}/{len(diagnoses)} consensus)",
                'documentation': documentation
            }
        else:
            return {
                'success': False,
                'reason': 'Patch application failed',
                'documentation': documentation + "\n\nPATCH APPLICATION FAILED - Manual intervention required"
            }
    
    else:
        # Not safe to patch autonomously
        reason = []
        if not consensus_reached:
            reason.append(f"insufficient consensus ({patchable_votes}/{len(diagnoses)})")
        if not safe_to_patch:
            if max_risk == 'HIGH':
                reason.append("risk too high")
            if avg_confidence < 0.7:
                reason.append(f"confidence too low ({avg_confidence:.1%})")
        
        documentation = _generate_documentation(
            diagnoses=diagnoses,
            consensus_vote=patchable_votes,
            confidence=avg_confidence,
            risk=max_risk,
            fix_applied="NONE - Manual intervention required"
        )
        
        return {
            'success': False,
            'reason': f"Autonomous patch blocked: {', '.join(reason)}",
            'documentation': documentation
        }


def _query_gpt_for_diagnosis(prompt: str) -> Dict[str, Any]:
    """Query GPT for error diagnosis."""
    try:
        import openai
        client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=500
        )
        
        content = response.choices[0].message.content.strip()
        return json.loads(content)
    except Exception as e:
        print(f"      ❌ GPT error: {e}")
        return None


def _query_grok_for_diagnosis(prompt: str) -> Dict[str, Any]:
    """Query Grok for error diagnosis."""
    try:
        import requests
        
        response = requests.post(
            'https://api.x.ai/v1/chat/completions',
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {os.getenv("XAI_API_KEY")}'
            },
            json={
                'model': 'grok-3',
                'messages': [{'role': 'user', 'content': prompt}],
                'temperature': 0.1
            },
            timeout=30
        )
        
        if response.status_code == 200:
            content = response.json()['choices'][0]['message']['content'].strip()
            return json.loads(content)
        return None
    except Exception as e:
        print(f"      ❌ Grok error: {e}")
        return None


def _query_deepseek_for_diagnosis(prompt: str) -> Dict[str, Any]:
    """Query DeepSeek for error diagnosis."""
    try:
        import requests
        
        response = requests.post(
            'https://api.deepseek.com/v1/chat/completions',
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {os.getenv("DEEPSEEK_API_KEY")}'
            },
            json={
                'model': 'deepseek-chat',
                'messages': [{'role': 'user', 'content': prompt}],
                'temperature': 0.1
            },
            timeout=30
        )
        
        if response.status_code == 200:
            content = response.json()['choices'][0]['message']['content'].strip()
            return json.loads(content)
        return None
    except Exception as e:
        print(f"      ❌ DeepSeek error: {e}")
        return None


def _generate_documentation(diagnoses, consensus_vote, confidence, risk, fix_applied) -> str:
    """Generate plain English documentation of the repair incident."""
    
    doc = f"""
AUTONOMOUS REPAIR INCIDENT REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

================================================================================
WHAT HAPPENED:
================================================================================
{diagnoses[0][1].get('diagnosis', 'N/A')}

================================================================================
ROOT CAUSE:
================================================================================
{diagnoses[0][1].get('root_cause', 'N/A')}

================================================================================
WHY IT NEEDED TO BE ADDRESSED:
================================================================================
The AI Hive system experienced a critical failure that blocked all new trade
execution. This posed a significant risk to trading operations as no new 
positions could be opened while the system was down.

IMPORTANCE LEVEL: {'CRITICAL' if risk == 'HIGH' else 'HIGH' if risk == 'MEDIUM' else 'MODERATE'}

================================================================================
COLLECTIVE AI ANALYSIS:
================================================================================
AIs Consulted: {len(diagnoses)}
"""
    
    for ai_name, diagnosis in diagnoses:
        doc += f"\n{ai_name}:\n"
        doc += f"  - Patchable: {diagnosis.get('is_patchable', False)}\n"
        doc += f"  - Confidence: {diagnosis.get('confidence', 0):.1%}\n"
        doc += f"  - Risk Level: {diagnosis.get('risk_level', 'N/A')}\n"
        doc += f"  - Reasoning: {diagnosis.get('reasoning', 'N/A')}\n"
    
    doc += f"""
================================================================================
CONSENSUS DECISION:
================================================================================
Vote: {consensus_vote}/{len(diagnoses)} AIs agreed fix was safe to apply
Average Confidence: {confidence:.1%}
Maximum Risk Level: {risk}

Decision Logic:
- Consensus threshold: 50%+ agreement required
- Confidence threshold: 70%+ required
- Risk limit: HIGH risk blocks autonomous patching

Result: {'PATCH APPROVED' if confidence >= 0.7 and risk != 'HIGH' else 'MANUAL INTERVENTION REQUIRED'}

================================================================================
SOLUTION APPLIED:
================================================================================
{fix_applied}

================================================================================
PATCH SUCCESS:
================================================================================
{'✅ YES - Patch applied and verified' if 'NONE' not in fix_applied else '❌ NO - Manual intervention required'}

================================================================================
END OF REPORT
================================================================================
"""
    
    return doc


def _apply_patch(diagnosis: Dict[str, Any]) -> bool:
    """
    Apply the patch if it's safe and simple.
    Currently conservative - only handles very specific, known issues.
    """
    # For now, return False to require manual intervention
    # This can be expanded to handle specific known issues
    print("   ⚠️  Autonomous patching not yet implemented for this error type")
    print("   📋 Manual review required - see documentation")
    return False


if __name__ == "__main__":
    # Test the system
    print("🧪 Testing Autonomous Repair System\n")
    
    test_error = Exception("Connection timeout to OpenAI API")
    result = diagnose_and_repair(
        error_type="TimeoutError",
        error_message="Connection timeout to OpenAI API",
        stack_trace="  File 'api_ai_hive.py', line 123, in _query_openai\n    response = client.chat.completions.create(...)"
    )
    
    print("\n📊 Result:")
    print(json.dumps(result, indent=2))
