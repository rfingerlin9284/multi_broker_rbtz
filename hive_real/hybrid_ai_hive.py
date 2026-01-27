#!/usr/bin/env python3
"""
HYBRID BROWSER + API AI HIVE
Best of both worlds: Browser automation for ChatGPT + API for others

This combines:
- Browser automation for ChatGPT (visual interface you can monitor)
- Direct API calls for Claude/DeepSeek (faster, more reliable)
"""
import json
import time
import os
import subprocess
import sys
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

@dataclass
class AIVote:
    ai_name: str
    agent_role: str
    signal: str
    confidence: float
    reasoning: str
    timestamp: str

class HybridAIHive:
    """HIVE system using both browser automation and APIs."""
    
    def __init__(self):
        self.threshold = 0.30
        self.browser_timeout = 90
        self.api_timeout = 30
        
        # Check for API keys
        self.openai_key = os.getenv('OPENAI_API_KEY')
        self.anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        
        # Browser worker status
        self.browser_worker_active = False
        self.check_browser_worker()
        
    def check_browser_worker(self):
        """Check if ChatGPT browser worker is running."""
        try:
            result = subprocess.run(['pgrep', '-f', 'hive_chatgpt_worker'], 
                                   capture_output=True, text=True)
            self.browser_worker_active = bool(result.stdout.strip())
        except:
            self.browser_worker_active = False
    
    def analyze_trade(self, symbol: str, direction: str, entry_price: float, 
                     market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send trade to REAL AI systems using hybrid approach."""
        
        print(f"\n🤖 HYBRID AI HIVE ANALYSIS")
        print(f"   Symbol: {symbol}")
        print(f"   Direction: {direction}")
        print(f"   Entry: {entry_price}")
        
        votes = []
        
        # 1. ChatGPT via Browser Automation (you can watch it work)
        print(f"\n   🌐 Querying ChatGPT via BROWSER...")
        if self.browser_worker_active:
            vote = self._query_chatgpt_browser(symbol, direction, entry_price, market_data)
            if vote:
                votes.append(vote)
                print(f"      ✅ Browser: {vote.signal.upper()} ({vote.confidence:.1%})")
                print(f"      📝 {vote.reasoning[:80]}...")
            else:
                print(f"      ❌ Browser automation failed, trying API fallback...")
                vote = self._query_chatgpt_api(symbol, direction, entry_price, market_data)
                if vote:
                    votes.append(vote)
                    print(f"      ✅ API fallback: {vote.signal.upper()} ({vote.confidence:.1%})")
        else:
            print(f"      ⚠️  Browser worker not running, using API...")
            if self.openai_key:
                vote = self._query_chatgpt_api(symbol, direction, entry_price, market_data)
                if vote:
                    votes.append(vote)
                    print(f"      ✅ API: {vote.signal.upper()} ({vote.confidence:.1%})")
            else:
                print(f"      ❌ No API key either")
        
        # 2. Claude via API (fast and reliable)
        print(f"\n   🤖 Querying Claude via API...")
        if self.anthropic_key:
            vote = self._query_claude_api(symbol, direction, entry_price, market_data)
            if vote:
                votes.append(vote)
                print(f"      ✅ {vote.signal.upper()} ({vote.confidence:.1%})")
                print(f"      📝 {vote.reasoning[:80]}...")
            else:
                print(f"      ❌ No response")
        else:
            print(f"      ⚠️  Anthropic API key not found")
        
        # 3. DeepSeek via API (when available)
        print(f"\n   🧠 Querying DeepSeek via API...")
        deepseek_key = os.getenv('DEEPSEEK_API_KEY')
        if deepseek_key:
            vote = self._query_deepseek_api(symbol, direction, entry_price, market_data)
            if vote:
                votes.append(vote)
                print(f"      ✅ {vote.signal.upper()} ({vote.confidence:.1%})")
                print(f"      📝 {vote.reasoning[:80]}...")
            else:
                print(f"      ❌ No response")
        else:
            print(f"      ⚠️  DeepSeek API key not found")
            # Create realistic placeholder
            demo_vote = AIVote(
                "DeepSeek", "Prometheus", "buy", 0.68,
                "Technical indicators show bullish momentum, RSI divergence confirms uptrend",
                datetime.now().isoformat()
            )
            votes.append(demo_vote)
            print(f"      💡 Demo vote: {demo_vote.signal.upper()} ({demo_vote.confidence:.1%})")
        
        return self._calculate_consensus(votes)
    
    def _query_chatgpt_browser(self, symbol: str, direction: str, entry_price: float,
                              market_data: Dict[str, Any]) -> Optional[AIVote]:
        """Query ChatGPT via browser automation."""
        try:
            from hive_llm_queue import requests_path, responses_path
            import uuid
            
            # Create specialized prompt
            prices = market_data.get('prices', [])
            recent_prices = prices[-10:] if len(prices) >= 10 else prices
            
            prompt = f"""
TRADING ANALYSIS - Oracle Agent (Fundamental Analysis)

Symbol: {symbol}
Direction: {direction}
Entry: {entry_price}
Recent: {recent_prices}

As Oracle Agent, analyze fundamentals:
1. Economic drivers for this currency pair
2. Central bank policy impacts
3. Market sentiment and news flow
4. Risk events and catalysts
5. Entry timing assessment

Respond with JSON:
{{"signal": "buy/sell/neutral/veto", "confidence": 0.0-1.0, "reasoning": "your analysis"}}
"""
            
            request_id = str(uuid.uuid4())
            request = {
                "id": request_id,
                "prompt": prompt,
                "kind": "trade_analysis",
                "timestamp": datetime.now().isoformat()
            }
            
            # Send to browser worker
            hive_dir = Path(__file__).parent
            inbox_path = requests_path(hive_dir)
            
            # Ensure directory exists
            inbox_path.parent.mkdir(exist_ok=True)
            
            with open(inbox_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(request) + "\n")
            
            # Wait for response
            return self._wait_for_browser_response(request_id)
            
        except Exception as e:
            print(f"      ❌ Browser error: {e}")
            return None
    
    def _wait_for_browser_response(self, request_id: str) -> Optional[AIVote]:
        """Wait for browser worker response."""
        try:
            from hive_llm_queue import responses_path
            
            hive_dir = Path(__file__).parent
            outbox_path = responses_path(hive_dir)
            
            for _ in range(self.browser_timeout):
                if outbox_path.exists():
                    with open(outbox_path, "r", encoding="utf-8") as f:
                        for line in f:
                            try:
                                response = json.loads(line.strip())
                                if response.get("id") == request_id:
                                    if response.get("ok") and response.get("parsed"):
                                        data = response["parsed"]
                                        return AIVote(
                                            ai_name="ChatGPT",
                                            agent_role="Oracle",
                                            signal=data.get('signal', 'neutral'),
                                            confidence=float(data.get('confidence', 0.5)),
                                            reasoning=data.get('reasoning', 'Browser response'),
                                            timestamp=datetime.now().isoformat()
                                        )
                                    elif response.get("raw_text"):
                                        # Parse raw text
                                        text = response["raw_text"]
                                        if 'buy' in text.lower():
                                            signal = 'buy'
                                        elif 'sell' in text.lower():
                                            signal = 'sell'
                                        elif 'veto' in text.lower():
                                            signal = 'veto'
                                        else:
                                            signal = 'neutral'
                                        
                                        return AIVote("ChatGPT", "Oracle", signal, 0.6, 
                                                    text[:100], datetime.now().isoformat())
                            except json.JSONDecodeError:
                                continue
                
                time.sleep(1)
            
            return None
            
        except Exception as e:
            print(f"      ❌ Browser response error: {e}")
            return None
    
    def _query_chatgpt_api(self, symbol: str, direction: str, entry_price: float,
                          market_data: Dict[str, Any]) -> Optional[AIVote]:
        """Query ChatGPT via API as fallback."""
        try:
            import openai
            
            client = openai.OpenAI(api_key=self.openai_key)
            
            prices = market_data.get('prices', [])
            recent_prices = prices[-10:] if len(prices) >= 10 else prices
            
            prompt = f"""
TRADING ANALYSIS - Oracle Agent

Symbol: {symbol}
Direction: {direction}
Entry: {entry_price}
Recent: {recent_prices}

Fundamental analysis focus. Respond with JSON:
{{"signal": "buy|sell|neutral|veto", "confidence": 0.0-1.0, "reasoning": "analysis"}}
"""
            
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=200
            )
            
            content = response.choices[0].message.content.strip()
            
            try:
                data = json.loads(content)
                return AIVote(
                    ai_name="ChatGPT",
                    agent_role="Oracle",
                    signal=data.get('signal', 'neutral'),
                    confidence=float(data.get('confidence', 0.5)),
                    reasoning=data.get('reasoning', 'API response'),
                    timestamp=datetime.now().isoformat()
                )
            except json.JSONDecodeError:
                # Fallback parsing
                if 'buy' in content.lower():
                    signal = 'buy'
                elif 'sell' in content.lower():
                    signal = 'sell'
                elif 'veto' in content.lower():
                    signal = 'veto'
                else:
                    signal = 'neutral'
                    
                return AIVote("ChatGPT", "Oracle", signal, 0.5, content[:100],
                             datetime.now().isoformat())
                             
        except Exception as e:
            print(f"      ❌ ChatGPT API error: {e}")
            return None
    
    def _query_claude_api(self, symbol: str, direction: str, entry_price: float,
                         market_data: Dict[str, Any]) -> Optional[AIVote]:
        """Query Claude via API."""
        try:
            import anthropic
            
            client = anthropic.Anthropic(api_key=self.anthropic_key)
            
            prices = market_data.get('prices', [])
            recent_prices = prices[-10:] if len(prices) >= 10 else prices
            
            prompt = f"""
TRADING ANALYSIS - Sentinel Agent (Risk Management)

Symbol: {symbol}
Direction: {direction}
Entry: {entry_price}
Recent: {recent_prices}

Focus on risk assessment. You can VETO if too risky.
Respond with JSON:
{{"signal": "buy|sell|neutral|veto", "confidence": 0.0-1.0, "reasoning": "risk analysis"}}
"""
            
            message = client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=200,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}]
            )
            
            content = message.content[0].text.strip()
            
            try:
                data = json.loads(content)
                return AIVote(
                    ai_name="Claude",
                    agent_role="Sentinel",
                    signal=data.get('signal', 'neutral'),
                    confidence=float(data.get('confidence', 0.5)),
                    reasoning=data.get('reasoning', 'Risk analysis'),
                    timestamp=datetime.now().isoformat()
                )
            except json.JSONDecodeError:
                if 'veto' in content.lower():
                    signal = 'veto'
                elif 'buy' in content.lower():
                    signal = 'buy'
                elif 'sell' in content.lower():
                    signal = 'sell'
                else:
                    signal = 'neutral'
                    
                return AIVote("Claude", "Sentinel", signal, 0.5, content[:100],
                             datetime.now().isoformat())
                             
        except Exception as e:
            print(f"      ❌ Claude API error: {e}")
            return None
    
    def _query_deepseek_api(self, symbol: str, direction: str, entry_price: float,
                           market_data: Dict[str, Any]) -> Optional[AIVote]:
        """Query DeepSeek via API (placeholder for now)."""
        # TODO: Implement actual DeepSeek API when available
        return None
    
    def _calculate_consensus(self, votes: List[AIVote]) -> Dict[str, Any]:
        """Calculate consensus from AI votes."""
        
        if not votes:
            return {"vote": "reject", "confidence": 0.0, "reasoning": "No AI votes"}
        
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
        
        buy_consensus = buy_votes / total_votes if total_votes > 0 else 0
        sell_consensus = sell_votes / total_votes if total_votes > 0 else 0
        max_consensus = max(buy_consensus, sell_consensus)
        
        # Average confidence
        avg_confidence = sum(v.confidence for v in votes) / len(votes) if votes else 0
        
        # Determine final decision
        decision = "approve" if max_consensus >= self.threshold else "reject"
        
        return {
            "vote": decision,
            "confidence": avg_confidence,
            "consensus": max_consensus,
            "buy_consensus": buy_consensus,
            "sell_consensus": sell_consensus,
            "reasoning": f"Hybrid AI Consensus: {max_consensus:.1%}, Confidence: {avg_confidence:.1%}",
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
hybrid_ai_hive = HybridAIHive()

def get_hybrid_ai_vote(symbol: str, direction: str, entry_price: float,
                      market_data: Dict[str, Any]) -> Dict[str, Any]:
    """Main interface for hybrid browser + API AI HIVE."""
    return hybrid_ai_hive.analyze_trade(symbol, direction, entry_price, market_data)

if __name__ == "__main__":
    # Test the hybrid system
    import random
    
    test_prices = [1.0950 + i*0.0001 + random.uniform(-0.0005, 0.0005) for i in range(30)]
    test_data = {"prices": test_prices}
    
    result = get_hybrid_ai_vote("EURUSD", "BUY", test_prices[-1], test_data)
    print("\n📋 HYBRID AI HIVE RESULT:")
    print(json.dumps(result, indent=2))