#!/usr/bin/env python3
"""
AI HIVE - Clean Implementation
Grok (xAI) as primary, OpenAI as backup with rate-limit handling.
"""
import json
import time
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class AIVote:
    ai_name: str
    signal: str  # buy, sell, neutral, veto
    confidence: float
    reasoning: str


class AIHive:
    """Simple AI Hive: Grok primary, OpenAI backup."""
    
    def __init__(self):
        self.grok_key = os.getenv('XAI_API_KEY')
        self.openai_key = os.getenv('OPENAI_API_KEY')
        self.grok_model = os.getenv('XAI_MODEL', 'grok-3-mini')
        self.openai_model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        self.threshold = float(os.getenv('HIVE_APPROVAL_THRESHOLD', '0.30'))
        
        # Rate limit tracking
        self._openai_blocked_until = 0
        self._rate_limit_cooldown = 60
        
        self.system_prompt = """You are a trading analyst. Analyze the trade and return ONLY valid JSON:
{"signal": "buy|sell|neutral|veto", "confidence": 0.0-1.0, "reasoning": "brief explanation"}

Rules:
- VETO if the trade is clearly bad
- Be decisive, not wishy-washy
- Consider risk/reward, momentum, and market context"""

    def analyze(self, symbol: str, direction: str, price: float, 
                prices: list = None) -> Dict[str, Any]:
        """Get AI consensus on a trade. Returns decision dict."""
        
        prices = prices or []
        votes = []
        
        prompt = f"""Trade Analysis Request:
Symbol: {symbol}
Direction: {direction}
Entry Price: {price}
Recent Prices: {prices[-10:] if len(prices) >= 10 else prices}

Should this trade be taken? Analyze and respond with JSON only."""

        # 1. Try Grok (primary)
        if self.grok_key:
            vote = self._query_grok(prompt)
            if vote:
                votes.append(vote)
                print(f"   ✅ Grok: {vote.signal.upper()} ({vote.confidence:.0%})")
        
        # 2. Try OpenAI (backup) - only if not rate-limited
        if self.openai_key and time.time() > self._openai_blocked_until:
            vote = self._query_openai(prompt)
            if vote:
                votes.append(vote)
                print(f"   ✅ OpenAI: {vote.signal.upper()} ({vote.confidence:.0%})")
        elif self._openai_blocked_until > time.time():
            remaining = int(self._openai_blocked_until - time.time())
            print(f"   ⏳ OpenAI: rate-limited ({remaining}s remaining)")
        
        return self._consensus(votes)
    
    def _query_grok(self, prompt: str) -> Optional[AIVote]:
        """Query xAI Grok API."""
        try:
            import requests
            
            resp = requests.post(
                'https://api.x.ai/v1/chat/completions',
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.grok_key}'
                },
                json={
                    'model': self.grok_model,
                    'messages': [
                        {'role': 'system', 'content': self.system_prompt},
                        {'role': 'user', 'content': prompt}
                    ],
                    'temperature': 0.1
                },
                timeout=30
            )
            
            if resp.status_code == 429:
                print("   ⚠️  Grok rate-limited")
                return None
            if resp.status_code != 200:
                print(f"   ❌ Grok error: {resp.status_code}")
                return None
            
            content = resp.json()['choices'][0]['message']['content'].strip()
            return self._parse_response(content, "Grok")
            
        except Exception as e:
            print(f"   ❌ Grok error: {e}")
            return None
    
    def _query_openai(self, prompt: str) -> Optional[AIVote]:
        """Query OpenAI API with rate-limit detection."""
        try:
            import openai
            client = openai.OpenAI(api_key=self.openai_key)
            
            resp = client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {'role': 'system', 'content': self.system_prompt},
                    {'role': 'user', 'content': prompt}
                ],
                temperature=0.1,
                max_tokens=200
            )
            
            content = resp.choices[0].message.content.strip()
            return self._parse_response(content, "OpenAI")
            
        except Exception as e:
            err = str(e).lower()
            if '429' in str(e) or 'rate' in err or 'limit' in err:
                print(f"   ⚠️  OpenAI RATE LIMITED - disabled for {self._rate_limit_cooldown}s")
                self._openai_blocked_until = time.time() + self._rate_limit_cooldown
            else:
                print(f"   ❌ OpenAI error: {e}")
            return None
    
    def _parse_response(self, content: str, source: str) -> Optional[AIVote]:
        """Parse AI JSON response."""
        try:
            # Strip markdown if present
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0]
            elif '```' in content:
                content = content.split('```')[1].split('```')[0]
            
            data = json.loads(content.strip())
            return AIVote(
                ai_name=source,
                signal=data.get('signal', 'neutral'),
                confidence=float(data.get('confidence', 0.5)),
                reasoning=data.get('reasoning', '')[:100]
            )
        except:
            # Fallback: extract signal from text
            cl = content.lower()
            if 'veto' in cl:
                sig = 'veto'
            elif 'buy' in cl:
                sig = 'buy'
            elif 'sell' in cl:
                sig = 'sell'
            else:
                sig = 'neutral'
            return AIVote(source, sig, 0.5, content[:50])
    
    def _consensus(self, votes: list) -> Dict[str, Any]:
        """Calculate consensus from votes."""
        if not votes:
            return {
                'decision': 'reject',
                'confidence': 0.0,
                'reasoning': 'No AI votes received',
                'votes': []
            }
        
        # Check for veto
        for v in votes:
            if v.signal == 'veto':
                return {
                    'decision': 'reject',
                    'confidence': v.confidence,
                    'reasoning': f'VETO by {v.ai_name}: {v.reasoning}',
                    'votes': [self._vote_dict(v) for v in votes]
                }
        
        # Count signals
        buy = sum(1 for v in votes if v.signal == 'buy')
        sell = sum(1 for v in votes if v.signal == 'sell')
        total = len(votes)
        
        buy_pct = buy / total
        sell_pct = sell / total
        avg_conf = sum(v.confidence for v in votes) / total
        
        # Decision
        if buy_pct >= self.threshold:
            decision = 'approve'
            reasoning = f'BUY consensus: {buy_pct:.0%}'
        elif sell_pct >= self.threshold:
            decision = 'approve'
            reasoning = f'SELL consensus: {sell_pct:.0%}'
        else:
            decision = 'reject'
            reasoning = f'No consensus (buy:{buy_pct:.0%}, sell:{sell_pct:.0%})'
        
        return {
            'decision': decision,
            'confidence': avg_conf,
            'reasoning': reasoning,
            'votes': [self._vote_dict(v) for v in votes]
        }
    
    def _vote_dict(self, v: AIVote) -> dict:
        return {'ai': v.ai_name, 'signal': v.signal, 'confidence': v.confidence}


# Global instance
_hive = None

def get_api_ai_vote(symbol: str, direction: str, entry_price: float,
                    market_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """Main entry point for AI Hive analysis."""
    global _hive
    if _hive is None:
        _hive = AIHive()
    
    prices = market_data.get('prices', [])
    
    print(f"\n🤖 AI HIVE ANALYSIS: {symbol} {direction}")
    result = _hive.analyze(symbol, direction, entry_price, prices)
    print(f"   📊 Decision: {result['decision'].upper()} ({result['confidence']:.0%})")
    
    # Add compatibility fields
    result['vote'] = result['decision']
    result['consensus'] = result['confidence']
    result['consensus_score'] = result['confidence']
    result['confidence_score'] = result['confidence']
    
    return result


if __name__ == '__main__':
    # Quick test
    import random
    prices = [91000 + random.uniform(-100, 100) for _ in range(20)]
    
    result = get_api_ai_vote(
        symbol='BTC-USD',
        direction='BUY', 
        entry_price=prices[-1],
        market_data={'prices': prices}
    )
    print(f"\nResult: {result['decision']}")
