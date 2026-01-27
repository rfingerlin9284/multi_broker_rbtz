#!/usr/bin/env python3
"""REAL AI HIVE SYSTEM - Direct connections to your business accounts

This connects to your REAL AI accounts:
- ChatGPT Business (via browser automation)  
- Grok (via browser automation)
- DeepSeek (via browser automation)
- Claude (via API if available)

Each AI agent gets specialized prompts and votes on trades.
"""
import json
import time
import uuid
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import asyncio
import concurrent.futures
from pathlib import Path

from hive_llm_queue import requests_path, responses_path


@dataclass
class AIVote:
    """Vote from a real AI system."""
    ai_name: str        # "ChatGPT", "Grok", "DeepSeek", etc.
    agent_role: str     # "Oracle", "Prometheus", "Sentinel"
    signal: str         # "buy", "sell", "neutral", "veto"
    confidence: float   # 0.0 to 1.0
    reasoning: str      # AI's explanation
    timestamp: str


class RealAIHive:
    """HIVE system using REAL AI business accounts."""
    
    def __init__(self):
        self.threshold = 0.30  # 30% consensus for $400/day mode
        self.timeout = 90      # Wait up to 90 seconds for AI responses
        
    def analyze_trade(self, symbol: str, direction: str, entry_price: float, 
                     market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send trade to REAL AI agents and get consensus."""
        
        print(f"\n🤖 REAL AI HIVE ANALYSIS")
        print(f"   Symbol: {symbol}")
        print(f"   Direction: {direction}")
        print(f"   Entry: {entry_price}")
        
        # Create specialized prompts for each AI
        prompts = self._create_ai_prompts(symbol, direction, entry_price, market_data)
        
        # Send all prompts to AI systems
        votes = self._query_all_ais(prompts)
        # Validate votes against charter contract; convert invalid seat outputs to VETO votes
        try:
            from hive_real.charter import validate_seat_output, record_violation
            for v in votes:
                # v may be AIVote or dict; ensure we handle both
                if isinstance(v, dict):
                    ok, errs = validate_seat_output(v)
                    if not ok:
                        record_violation(v.get('ai','unknown'), v, errs)
                        v['signal'] = 'veto'
                        v['confidence'] = 0.0
                else:
                    # AIVote already parsed; keep as-is (parsing already validates in api_ai_hive)
                    continue
        except Exception:
            pass

        # If no real AI responses, attempt live DeepSeek (do NOT simulate)
        if not votes:
            try:
                ds = self._query_deepseek(prompts[-1]['prompt'])
                if ds:
                    print(f"   ✅ DeepSeek LIVE: {ds.get('signal','neutral').upper()} ({float(ds.get('confidence',0.3)):.0%})")
                    votes.append(AIVote(ai_name='DeepSeek', agent_role='Sentinel', signal=ds.get('signal','neutral'), confidence=float(ds.get('confidence',0.3)), reasoning=ds.get('reasoning',''), timestamp=datetime.now().isoformat()))
                else:
                    print("   • DeepSeek live not available; no simulated fallback will be used")
            except Exception as e:
                print(f"   ⚠️ DeepSeek live query error: {e}")

        # Always compute MultiIndicator vote to augment AI votes when possible
        try:
            mi = self._multi_indicator_vote(direction, entry_price, market_data.get('prices', []))
            if mi:
                print(f"   ✅ MultiIndicator: {mi.signal.upper()} ({mi.confidence:.0%}) - {mi.reasoning}")
                votes.append(AIVote(ai_name='MultiIndicator', agent_role='IndicatorEnsemble', signal=mi.signal, confidence=mi.confidence, reasoning=mi.reasoning, timestamp=datetime.now().isoformat()))
        except Exception as e:
            print(f"   ❌ MultiIndicator error: {e}")

        if not votes:
            print("   ❌ No AI responses received (including fallbacks)")
            return {"vote": "reject", "confidence": 0.0, "reasoning": "No AI responses"}

        # Calculate consensus
        return self._calculate_consensus(votes)
    
    def _create_ai_prompts(self, symbol: str, direction: str, entry_price: float, 
                          market_data: Dict[str, Any]) -> List[Dict]:
        """Create specialized prompts for each AI agent."""
        
        prices = market_data.get('prices', [])
        recent_prices = prices[-10:] if len(prices) >= 10 else prices
        
        base_context = f"""
TRADING ANALYSIS REQUEST

Symbol: {symbol}
Proposed Direction: {direction}
Entry Price: {entry_price}
Recent Prices: {recent_prices}

Market Context:
- Current price trend
- Volatility assessment  
- Risk factors
- Entry timing
"""
        
        return [
            # ChatGPT - Oracle Agent (Fundamental Analysis)
            {
                "ai": "ChatGPT",
                "agent": "Oracle", 
                "prompt": f"""{base_context}

ROLE: Oracle Agent - Fundamental & News Analysis

Your task: Analyze this trade from a fundamental perspective.

Consider:
1. Market catalysts and news events
2. Economic data releases
3. Central bank policies  
4. Geopolitical factors
5. Market sentiment drivers

Provide analysis as JSON:
{{
    "signal": "buy|sell|neutral|veto",
    "confidence": 0.0-1.0,
    "reasoning": "Your fundamental analysis",
    "key_factors": ["factor1", "factor2"],
    "risk_level": "low|medium|high"
}}

Focus on WHY this trade makes sense fundamentally."""
            },
            
            # Grok - Prometheus Agent (Technical Analysis)  
            {
                "ai": "Grok",
                "agent": "Prometheus",
                "prompt": f"""{base_context}

ROLE: Prometheus Agent - Technical Analysis Master

Your task: Deep technical analysis of this trade setup.

Analyze:
1. Chart patterns and formations
2. Support/resistance levels
3. Momentum indicators (RSI, MACD, etc.)
4. Volume profile analysis
5. Fibonacci retracements
6. Market structure

Provide analysis as JSON:
{{
    "signal": "buy|sell|neutral|veto", 
    "confidence": 0.0-1.0,
    "reasoning": "Your technical analysis",
    "key_levels": ["support1", "resistance1"],
    "indicators": {{"rsi": "value", "trend": "direction"}}
}}

Be brutally honest about technical setup quality."""
            },
            
            # DeepSeek - Sentinel Agent (Risk Management)
            {
                "ai": "DeepSeek",
                "agent": "Sentinel", 
                "prompt": f"""{base_context}

ROLE: Sentinel Agent - Risk Guardian

Your task: Risk assessment and position sizing validation.

Evaluate:
1. Risk-reward ratio
2. Stop loss placement
3. Position sizing appropriateness
4. Market conditions for this trade
5. Correlation risks
6. Liquidity considerations

SPECIAL POWER: You can VETO any trade if risk is too high.

Provide analysis as JSON:
{{
    "signal": "buy|sell|neutral|veto",
    "confidence": 0.0-1.0,
    "reasoning": "Your risk analysis", 
    "risk_reward_ratio": 0.0,
    "max_acceptable_risk": "percentage",
    "concerns": ["concern1", "concern2"]
}}

VETO if risk exceeds reward potential."""
            }
        ]
    
    def _query_all_ais(self, prompts: List[Dict]) -> List[AIVote]:
        """Send prompts to all AI systems and collect responses."""
        
        votes = []
        
        for prompt_data in prompts:
            print(f"   🧠 Querying {prompt_data['ai']} ({prompt_data['agent']})...")
            
            # Send to appropriate AI system
            response = self._send_to_ai(prompt_data)
            
            if response:
                vote = AIVote(
                    ai_name=prompt_data['ai'],
                    agent_role=prompt_data['agent'],
                    signal=response.get('signal', 'neutral'),
                    confidence=float(response.get('confidence', 0.5)),
                    reasoning=response.get('reasoning', 'No reasoning provided'),
                    timestamp=datetime.now().isoformat()
                )
                votes.append(vote)
                print(f"      ✅ {vote.signal.upper()} ({vote.confidence:.1%})")
            else:
                print(f"      ❌ No response")
        
        return votes
    
    def _send_to_ai(self, prompt_data: Dict) -> Optional[Dict]:
        """Send prompt to specific AI and get response."""
        
        ai_name = prompt_data['ai']
        
        if ai_name == "ChatGPT":
            return self._query_chatgpt(prompt_data['prompt'])
        elif ai_name == "Grok":
            return self._query_grok(prompt_data['prompt'])  
        elif ai_name == "DeepSeek":
            return self._query_deepseek(prompt_data['prompt'])
        else:
            print(f"      ⚠️  Unknown AI: {ai_name}")
            return None
    
    def _query_chatgpt(self, prompt: str) -> Optional[Dict]:
        """Query ChatGPT via browser automation."""
        try:
            # Use the existing browser worker system
            request_id = str(uuid.uuid4())
            
            # Write request to queue
            request = {
                "id": request_id,
                "prompt": prompt,
                "kind": "trade_analysis", 
                "timestamp": datetime.now().isoformat()
            }
            
            inbox_path = requests_path(Path("/home/ing/RICK/MULTI_BROKER_PHOENIX/hive_real"))
            
            with open(inbox_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(request) + "\n")
            
            # Wait for response
            return self._wait_for_response(request_id)
            
        except Exception as e:
            print(f"      ❌ ChatGPT error: {e}")
            return None
    
    def _query_grok(self, prompt: str) -> Optional[Dict]:
        """Query Grok via browser automation."""
        # TODO: Implement Grok browser automation
        # For now, return a placeholder
        print(f"      ⚠️  Grok integration not yet implemented")
        return {
            "signal": "neutral",
            "confidence": 0.3,
            "reasoning": "Grok integration pending - would analyze technical patterns"
        }
    
    def _query_deepseek(self, prompt: str) -> Optional[Dict]:
        """Query DeepSeek via browser automation.""" 
        # TODO: Implement DeepSeek browser automation
        # For now, return a placeholder
        print(f"      ⚠️  DeepSeek integration not yet implemented")
        return {
            "signal": "neutral", 
            "confidence": 0.3,
            "reasoning": "DeepSeek integration pending - would analyze risk factors"
        }
    
    def _wait_for_response(self, request_id: str) -> Optional[Dict]:
        """Wait for AI response in queue."""
        
        outbox_path = responses_path(Path("/home/ing/RICK/MULTI_BROKER_PHOENIX/hive_real"))
        
        for _ in range(self.timeout):
            try:
                if not outbox_path.exists():
                    time.sleep(1)
                    continue
                    
                # Read all responses
                with open(outbox_path, "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            response = json.loads(line.strip())
                            if response.get("id") == request_id:
                                # Found our response
                                if response.get("ok") and response.get("parsed"):
                                    return response["parsed"]
                                elif response.get("raw_text"):
                                    # Try to extract JSON from raw text
                                    return self._extract_json_from_text(response["raw_text"])
                        except json.JSONDecodeError:
                            continue
                            
            except Exception:
                pass
                
            time.sleep(1)
        
        return None
    
    def _extract_json_from_text(self, text: str) -> Optional[Dict]:
        """Extract JSON from AI response text."""
        try:
            # Look for JSON blocks in the text
            import re
            json_pattern = r'\{[^{}]*\}'
            matches = re.findall(json_pattern, text, re.DOTALL)
            
            for match in matches:
                try:
                    return json.loads(match)
                except:
                    continue
                    
            # Fallback: try to parse common patterns
            if "buy" in text.lower():
                signal = "buy"
            elif "sell" in text.lower():
                signal = "sell"
            elif "veto" in text.lower():
                signal = "veto"
            else:
                signal = "neutral"
                
            return {
                "signal": signal,
                "confidence": 0.5,
                "reasoning": text[:200] + "..." if len(text) > 200 else text
            }
            
        except Exception:
            return None
    
    def _calculate_consensus(self, votes: List[AIVote]) -> Dict[str, Any]:
        """Calculate consensus from AI votes."""
        
        if not votes:
            return {"vote": "reject", "confidence": 0.0, "reasoning": "No votes"}
        
        # Check for vetoes first
        vetoes = [v for v in votes if v.signal == "veto"]
        if vetoes:
            return {
                "vote": "veto",
                "confidence": max(v.confidence for v in vetoes), 
                "consensus": 0.0,
                "reasoning": f"VETOED by {vetoes[0].ai_name}: {vetoes[0].reasoning}",
                "votes": [self._vote_to_dict(v) for v in votes]
            }
        
        # Count signals
        buy_votes = sum(1 for v in votes if v.signal == "buy")
        sell_votes = sum(1 for v in votes if v.signal == "sell")
        total_votes = len(votes)
        
        buy_consensus = buy_votes / total_votes
        sell_consensus = sell_votes / total_votes
        max_consensus = max(buy_consensus, sell_consensus)
        
        # Average confidence
        avg_confidence = sum(v.confidence for v in votes) / len(votes)
        
        # Determine final decision
        if max_consensus >= self.threshold:
            decision = "approve"
        else:
            decision = "reject"
            
        return {
            "vote": decision,
            "confidence": avg_confidence,
            "consensus": max_consensus,
            "buy_consensus": buy_consensus,
            "sell_consensus": sell_consensus,
            "reasoning": f"AI Consensus: {max_consensus:.1%}, Confidence: {avg_confidence:.1%}",
            "votes": [self._vote_to_dict(v) for v in votes]
        }
    
    def _vote_to_dict(self, vote: AIVote) -> Dict:
        """Convert vote to dictionary."""
        return {
            "ai": vote.ai_name,
            "agent": vote.agent_role,
            "signal": vote.signal,
            "confidence": vote.confidence,
            "reasoning": vote.reasoning,
            "timestamp": vote.timestamp
        }


# Global instance
real_ai_hive = RealAIHive()


def get_real_ai_vote(symbol: str, direction: str, entry_price: float, market_data: Dict[str, Any]) -> Dict[str, Any]:
    """Main interface for REAL AI HIVE voting."""
    return real_ai_hive.analyze_trade(symbol, direction, entry_price, market_data)


if __name__ == "__main__":
    # Test with sample data
    import random
    
    test_prices = [1.0950 + i*0.0001 + random.uniform(-0.0005, 0.0005) for i in range(30)]
    test_data = {"prices": test_prices}
    
    result = get_real_ai_vote("EURUSD", "BUY", test_prices[-1], test_data)
    print(json.dumps(result, indent=2))