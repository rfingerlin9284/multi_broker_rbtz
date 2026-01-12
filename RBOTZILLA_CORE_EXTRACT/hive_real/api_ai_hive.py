#!/usr/bin/env python3
"""
REAL API-BASED AI HIVE
Direct connections to AI APIs without browser automation

This uses your actual API keys to connect to:
- OpenAI ChatGPT API (Oracle - fundamental analysis)
- xAI Grok API (Tactician - technical analysis)
(DeepSeek disabled - reactivate when account funded)
"""
import json
import time
import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class AIVote:
    ai_name: str
    agent_role: str
    signal: str
    confidence: float
    reasoning: str
    timestamp: str

class APIAIHive:
    """HIVE system using real AI APIs with automatic failover and load rotation."""
    
    def __init__(self):
        # PAPER MODE: Lower threshold for testing (env override available)
        self.threshold = float(os.getenv('HIVE_APPROVAL_THRESHOLD', '0.30'))
        self.timeout = 60
        
        # Check for API keys from environment
        self.openai_key = os.getenv('OPENAI_API_KEY')
        self.xai_key = os.getenv('XAI_API_KEY')
        self.deepseek_key = os.getenv('DEEPSEEK_API_KEY')

        # Model selection (configurable via env; keep defaults cost-effective)
        # NOTE: Using "gpt-4" can trigger access/quota issues on some accounts.
        self.openai_model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        # NOTE: Use grok-3-mini for cost-effective fast analysis
        self.xai_model = os.getenv('XAI_MODEL', 'grok-3-mini')
        
        # Track rate-limited providers (temporary disable)
        self._rate_limited = {}  # provider -> timestamp when limit expires
        self._rate_limit_cooldown = 60  # seconds to wait after rate limit
        
        # System messages (static role definitions) - STRICT HIVE PROTOCOL
        self.system_messages = {
            "oracle": """You are the Hive Trading Analyst for an automated trading system.

HARD RULES (NON-NEGOTIABLE)
1) Return STRICT JSON ONLY. No markdown. No commentary. No extra text outside the JSON object.
2) You may use general market knowledge, BUT you must NOT invent price data or pretend you have live market access.
3) The system calling you may provide inputs in plain English or JSON. You must normalize them into the output JSON schema.
4) If required fields are missing, you MUST return status "need_input" with a "missing" array and "template" object.
5) Always include "human_summary" inside the JSON: a plain-English summary intended for a non-technical user.
6) OCO is a core commandment: if oco_required is true, every setup must include an OCO bracket (tp[] + sl) and must be logically consistent.

OUTPUT SCHEMA:
{
  "signal": "buy|sell|neutral|veto",
  "confidence": 0.0-1.0,
  "reasoning": "1-2 sentence analysis from fundamental/sentiment perspective",
  "human_summary": "Plain-English summary of your analysis"
}

Your role: Oracle Agent - fundamental and sentiment analyst. Consider central bank policy, economic data, news sentiment, currency strength drivers, macro factors. VETO if fundamentals strongly oppose the trade.""",
            
            "tactician": """You are the Hive Trading Analyst for an automated trading system.

HARD RULES (NON-NEGOTIABLE)
1) Return STRICT JSON ONLY. No markdown. No commentary. No extra text outside the JSON object.
2) You may use general market knowledge, BUT you must NOT invent price data or pretend you have live market access.
3) The system calling you may provide inputs in plain English or JSON. You must normalize them into the output JSON schema.
4) If required fields are missing, you MUST return status "need_input" with a "missing" array and "template" object.
5) Always include "human_summary" inside the JSON: a plain-English summary intended for a non-technical user.
6) OCO is a core commandment: if oco_required is true, every setup must include an OCO bracket (tp[] + sl) and must be logically consistent.

OUTPUT SCHEMA:
{
  "signal": "buy|sell|neutral|veto",
  "confidence": 0.0-1.0,
  "reasoning": "1-2 sentence analysis from technical perspective",
  "human_summary": "Plain-English summary of your analysis"
}

Your role: Tactician Agent - technical analyst. Consider trend, momentum, support/resistance, patterns, entry timing, price action structure. VETO if technical setup is poor or high-risk. Focus on what the chart shows.""",
            
            "analyst": """You are the Hive Trading Analyst for an automated trading system.

HARD RULES (NON-NEGOTIABLE)
1) Return STRICT JSON ONLY. No markdown. No commentary. No extra text outside the JSON object.
2) You may use general market knowledge, BUT you must NOT invent price data or pretend you have live market access.
3) The system calling you may provide inputs in plain English or JSON. You must normalize them into the output JSON schema.
4) If required fields are missing, you MUST return status "need_input" with a "missing" array and "template" object.
5) Always include "human_summary" inside the JSON: a plain-English summary intended for a non-technical user.
6) OCO is a core commandment: if oco_required is true, every setup must include an OCO bracket (tp[] + sl) and must be logically consistent.

OUTPUT SCHEMA:
{
  "signal": "buy|sell|neutral|veto",
  "confidence": 0.0-1.0,
  "reasoning": "1-2 sentence analysis from quantitative perspective",
  "human_summary": "Plain-English summary of your analysis"
}

Your role: Analyst Agent - quantitative/statistical analyst. Consider historical patterns, statistical edges, probability distribution, risk/reward ratio, volatility context. VETO if statistical probability is unfavorable or volatility is extreme. Base decisions on quantifiable metrics."""
        }
        
    def analyze_trade(self, symbol: str, direction: str, entry_price: float, 
                     market_data: Dict[str, Any], timeframe: str = "1h",
                     objective: str = "day", risk_rules: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send trade to REAL AI APIs and get consensus.
        
        Args:
            symbol: Trading pair (e.g., "EURUSD", "BTCUSD")
            direction: Proposed direction ("BUY" or "SELL")
            entry_price: Current/proposed entry price
            market_data: Dict with 'prices' (recent closes), 'high', 'low', 'candles' (optional OHLC)
            timeframe: Chart timeframe (e.g., "5m", "15m", "1h", "4h", "1D")
            objective: Trading style ("scalp", "day", "swing")
            risk_rules: Dict with 'max_loss_pct', 'max_daily_loss_pct', 'leverage_cap', 'oco_required'
        """
        
        # Default risk rules if not provided
        if risk_rules is None:
            risk_rules = {
                'max_loss_pct': 0.5,
                'max_daily_loss_pct': 2.0,
                'leverage_cap': 2.0,
                'oco_required': True
            }
        
        print(f"\n🤖 API-BASED REAL AI HIVE ANALYSIS")
        print(f"   Symbol: {symbol}")
        print(f"   Direction: {direction}")
        print(f"   Timeframe: {timeframe}")
        print(f"   Entry: {entry_price}")
        print(f"   Objective: {objective}")
        
        votes = []
        current_time = time.time()
        
        # Helper: check if provider is rate-limited
        def is_rate_limited(provider):
            if provider in self._rate_limited:
                if current_time < self._rate_limited[provider]:
                    return True
                else:
                    del self._rate_limited[provider]  # Cooldown expired
            return False
        
        # Try xAI Grok API FIRST (fast, reliable, no rate limit issues)
        if self.xai_key and not is_rate_limited('grok'):
            print(f"   🧠 Querying xAI Grok API (Tactician)...")
            vote = self._query_grok(symbol, direction, entry_price, market_data,
                                   timeframe, objective, risk_rules)
            if vote:
                votes.append(vote)
                print(f"      ✅ {vote.signal.upper()} ({vote.confidence:.1%})")
            else:
                print(f"      ❌ No response")
        elif is_rate_limited('grok'):
            print(f"   ⏳ Grok rate-limited, skipping (cooldown)")
        else:
            print(f"   ⚠️  xAI API key not found (set XAI_API_KEY)")
        
        # Try DeepSeek API (cheap, fast, good for quant analysis)
        if self.deepseek_key and not is_rate_limited('deepseek'):
            print(f"   🧠 Querying DeepSeek API (Analyst)...")
            vote = self._query_deepseek(symbol, direction, entry_price, market_data,
                                       timeframe, objective, risk_rules)
            if vote:
                votes.append(vote)
                print(f"      ✅ {vote.signal.upper()} ({vote.confidence:.1%})")
            else:
                print(f"      ❌ No response")
        elif is_rate_limited('deepseek'):
            print(f"   ⏳ DeepSeek rate-limited, skipping (cooldown)")
        else:
            print(f"   ⚠️  DeepSeek API key not found (set DEEPSEEK_API_KEY)")
        
        # Try OpenAI ChatGPT API LAST (most likely to hit rate limits)
        if self.openai_key and not is_rate_limited('openai'):
            print(f"   🧠 Querying OpenAI ChatGPT API (Oracle)...")
            vote = self._query_openai(symbol, direction, entry_price, market_data, 
                                     timeframe, objective, risk_rules)
            if vote:
                votes.append(vote)
                print(f"      ✅ {vote.signal.upper()} ({vote.confidence:.1%})")
            else:
                print(f"      ❌ No response")
        elif is_rate_limited('openai'):
            print(f"   ⏳ OpenAI rate-limited, skipping (cooldown)")
        else:
            print(f"   ⚠️  OpenAI API key not found (set OPENAI_API_KEY)")
            
        # If no API keys, show what would happen
        if not votes and not self.openai_key and not self.xai_key and not self.deepseek_key:
            # Safety default: never fabricate approvals when no real AI is available.
            # If you explicitly want demo votes (for UI demos), set HIVE_DEMO_VOTES=true.
            demo = os.getenv('HIVE_DEMO_VOTES', 'false').strip().lower() in ('1', 'true', 'yes', 'on')
            if demo:
                print("   💡 No API keys configured - DEMO mode enabled (HIVE_DEMO_VOTES=true)")
                votes = [
                    AIVote("ChatGPT", "Oracle", "buy", 0.75,
                           "DEMO: Fundamental tilt supportive; no live data used.",
                           datetime.now().isoformat()),
                    AIVote("Grok", "Tactician", "buy", 0.80,
                           "DEMO: Technical tilt supportive; no live chart used.",
                           datetime.now().isoformat()),
                ]
            else:
                print("   ⚠️  No AI API keys configured - returning REJECT for safety")
                return {
                    "vote": "reject",
                    "decision": "reject",
                    "confidence": 0.0,
                    "confidence_score": 0.0,
                    "consensus": 0.0,
                    "consensus_score": 0.0,
                    "buy_consensus": 0.0,
                    "sell_consensus": 0.0,
                    "reasoning": "No AI votes (missing OPENAI_API_KEY / XAI_API_KEY).",
                    "votes": [],
                }

        return self._calculate_consensus(votes)
    
    def query_single_agent(self, agent_name: str, prompt: str, model: str = "gpt-4o-mini") -> Optional[str]:
        """
        Query a single AI agent with a simple prompt (for non-trading analysis).
        Used by universe filtering and other support functions.
        
        Args:
            agent_name: "strategist", "oracle", "tactician", "analyst"
            prompt: The question/task to send to the AI
            model: Model to use (default: gpt-4o-mini for speed/cost)
            
        Returns:
            String response from AI, or None on error
        """
        try:
            import openai
            
            if not self.openai_key:
                return None
                
            client = openai.OpenAI(api_key=self.openai_key)
            
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a financial market analyst. Provide concise, actionable answers."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            return (response.choices[0].message.content or "").strip()
            
        except Exception as e:
            print(f"      ⚠️  AI query error: {e}")
            return None
    
    def _query_openai(self, symbol: str, direction: str, entry_price: float, 
                      market_data: Dict[str, Any], timeframe: str, 
                      objective: str, risk_rules: Dict[str, Any]) -> Optional[AIVote]:
        """Query OpenAI ChatGPT API with proper system/user message separation."""
        try:
            import openai
            
            client = openai.OpenAI(api_key=self.openai_key)
            
            # Extract market context
            prices = market_data.get('prices', [])
            recent_prices = prices[-20:] if len(prices) >= 20 else prices
            high_24h = market_data.get('high', max(recent_prices) if recent_prices else entry_price)
            low_24h = market_data.get('low', min(recent_prices) if recent_prices else entry_price)
            candles = market_data.get('candles', [])
            
            # Build user message with actual market data
            user_message = f"""ANALYZE THIS TRADE:

INSTRUMENT: {symbol}
TIMEFRAME: {timeframe}
OBJECTIVE: {objective} trade

CURRENT MARKET:
- Current Price: {entry_price}
- 24h High: {high_24h}
- 24h Low: {low_24h}
- Recent Price Action: {recent_prices[-10:] if len(recent_prices) >= 10 else recent_prices}

PROPOSED TRADE:
- Direction: {direction}
- Entry: {entry_price}

RISK RULES:
- Max Loss Per Trade: {risk_rules['max_loss_pct']}%
- Max Daily Loss: {risk_rules['max_daily_loss_pct']}%
- Leverage Cap: {risk_rules['leverage_cap']}x
- OCO Required: {risk_rules['oco_required']}

Evaluate this trade from a fundamental and sentiment perspective. Consider economic drivers, central bank policy, market sentiment, and currency strength."""

            response = client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": self.system_messages["oracle"]},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.1,
                max_tokens=250
            )
            
            content = (response.choices[0].message.content or "").strip()
            
            # Parse JSON response
            try:
                # Remove markdown code blocks if present
                if '```json' in content:
                    content = content.split('```json')[1].split('```')[0].strip()
                elif '```' in content:
                    content = content.split('```')[1].split('```')[0].strip()
                    
                data = json.loads(content)
                return AIVote(
                    ai_name="ChatGPT",
                    agent_role="Oracle",
                    signal=data.get('signal', 'neutral'),
                    confidence=float(data.get('confidence', 0.5)),
                    reasoning=data.get('reasoning', 'No reasoning provided'),
                    timestamp=datetime.now().isoformat()
                )
            except json.JSONDecodeError:
                # Fallback parsing
                content_lower = content.lower()
                if 'veto' in content_lower:
                    signal = 'veto'
                elif 'buy' in content_lower:
                    signal = 'buy'
                elif 'sell' in content_lower:
                    signal = 'sell'
                else:
                    signal = 'neutral'
                    
                return AIVote("ChatGPT", "Oracle", signal, 0.5, content[:100], 
                             datetime.now().isoformat())
                             
        except Exception as e:
            error_str = str(e).lower()
            # Detect rate limit errors
            if '429' in str(e) or 'rate' in error_str or 'limit' in error_str:
                print(f"      ⚠️  OpenAI RATE LIMITED - disabling for {self._rate_limit_cooldown}s")
                self._rate_limited['openai'] = time.time() + self._rate_limit_cooldown
            else:
                print(f"      ❌ OpenAI error: {e}")
            return None
    
    def _query_grok(self, symbol: str, direction: str, entry_price: float,
                    market_data: Dict[str, Any], timeframe: str,
                    objective: str, risk_rules: Dict[str, Any]) -> Optional[AIVote]:
        """Query xAI Grok API with proper system/user message separation."""
        try:
            import requests
            
            # Extract market context
            prices = market_data.get('prices', [])
            recent_prices = prices[-20:] if len(prices) >= 20 else prices
            high_24h = market_data.get('high', max(recent_prices) if recent_prices else entry_price)
            low_24h = market_data.get('low', min(recent_prices) if recent_prices else entry_price)
            candles = market_data.get('candles', [])
            
            # Calculate some basic technical indicators
            recent_change = ((entry_price - recent_prices[0]) / recent_prices[0] * 100) if recent_prices else 0
            range_position = ((entry_price - low_24h) / (high_24h - low_24h) * 100) if high_24h != low_24h else 50
            
            # Build user message with actual market data
            user_message = f"""ANALYZE THIS TRADE:

INSTRUMENT: {symbol}
TIMEFRAME: {timeframe}
OBJECTIVE: {objective} trade

CURRENT MARKET:
- Current Price: {entry_price}
- 24h High: {high_24h}
- 24h Low: {low_24h}
- Range Position: {range_position:.1f}% (0=low, 100=high)
- Recent Momentum: {recent_change:+.2f}% over last {len(recent_prices)} bars
- Recent Closes: {recent_prices[-10:] if len(recent_prices) >= 10 else recent_prices}

PROPOSED TRADE:
- Direction: {direction}
- Entry: {entry_price}

RISK RULES:
- Max Loss Per Trade: {risk_rules['max_loss_pct']}%
- Max Daily Loss: {risk_rules['max_daily_loss_pct']}%
- Leverage Cap: {risk_rules['leverage_cap']}x
- OCO Required: {risk_rules['oco_required']}

Evaluate this trade from a technical analysis perspective. Consider trend, momentum, support/resistance, price action structure, and entry timing."""

            response = requests.post(
                'https://api.x.ai/v1/chat/completions',
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.xai_key}'
                },
                json={
                    'model': self.xai_model,
                    'messages': [
                        {'role': 'system', 'content': self.system_messages["tactician"]},
                        {'role': 'user', 'content': user_message}
                    ],
                    'temperature': 0.1,
                    'stream': False
                },
                timeout=30
            )
            
            if response.status_code == 429:
                print(f"      ⚠️  xAI RATE LIMITED (429) - disabling for {self._rate_limit_cooldown}s")
                self._rate_limited['grok'] = time.time() + self._rate_limit_cooldown
                return None
            elif response.status_code != 200:
                print(f"      ❌ xAI API error: {response.status_code} - {response.text[:100]}")
                return None
                
            content = response.json()['choices'][0]['message']['content'].strip()
            
            # Parse JSON response
            try:
                # Remove markdown code blocks if present
                if '```json' in content:
                    content = content.split('```json')[1].split('```')[0].strip()
                elif '```' in content:
                    content = content.split('```')[1].split('```')[0].strip()
                    
                data = json.loads(content)
                return AIVote(
                    ai_name="Grok",
                    agent_role="Tactician",
                    signal=data.get('signal', 'neutral'),
                    confidence=float(data.get('confidence', 0.5)),
                    reasoning=data.get('reasoning', 'No reasoning provided'),
                    timestamp=datetime.now().isoformat()
                )
            except json.JSONDecodeError:
                # Fallback parsing
                content_lower = content.lower()
                if 'veto' in content_lower:
                    signal = 'veto'
                elif 'buy' in content_lower:
                    signal = 'buy'
                elif 'sell' in content_lower:
                    signal = 'sell'
                else:
                    signal = 'neutral'
                    
                return AIVote("Grok", "Tactician", signal, 0.5, content[:100],
                             datetime.now().isoformat())
                             
        except Exception as e:
            error_str = str(e).lower()
            # Detect rate limit errors
            if '429' in str(e) or 'rate' in error_str or 'limit' in error_str:
                print(f"      ⚠️  Grok RATE LIMITED - disabling for {self._rate_limit_cooldown}s")
                self._rate_limited['grok'] = time.time() + self._rate_limit_cooldown
            else:
                print(f"      ❌ xAI error: {e}")
            return None
    
    def _query_deepseek(self, symbol: str, direction: str, entry_price: float,
                        market_data: Dict[str, Any], timeframe: str,
                        objective: str, risk_rules: Dict[str, Any]) -> Optional[AIVote]:
        """Query DeepSeek API with proper system/user message separation."""
        try:
            import requests
            
            # Extract market context
            prices = market_data.get('prices', [])
            recent_prices = prices[-20:] if len(prices) >= 20 else prices
            high_24h = market_data.get('high', max(recent_prices) if recent_prices else entry_price)
            low_24h = market_data.get('low', min(recent_prices) if recent_prices else entry_price)
            
            # Calculate volatility (simple standard deviation)
            if len(recent_prices) >= 10:
                avg_price = sum(recent_prices[-10:]) / 10
                variance = sum((p - avg_price) ** 2 for p in recent_prices[-10:]) / 10
                volatility = (variance ** 0.5) / avg_price * 100
            else:
                volatility = 0
            
            # Build user message with actual market data
            user_message = f"""ANALYZE THIS TRADE:

INSTRUMENT: {symbol}
TIMEFRAME: {timeframe}
OBJECTIVE: {objective} trade

CURRENT MARKET:
- Current Price: {entry_price}
- 24h High: {high_24h}
- 24h Low: {low_24h}
- Volatility: {volatility:.2f}%
- Recent Price Series: {recent_prices[-15:] if len(recent_prices) >= 15 else recent_prices}

PROPOSED TRADE:
- Direction: {direction}
- Entry: {entry_price}

RISK RULES:
- Max Loss Per Trade: {risk_rules['max_loss_pct']}%
- Max Daily Loss: {risk_rules['max_daily_loss_pct']}%
- Leverage Cap: {risk_rules['leverage_cap']}x
- OCO Required: {risk_rules['oco_required']}

Evaluate this trade from a quantitative and statistical perspective. Consider probability, risk/reward, historical patterns, and volatility context."""

            response = requests.post(
                'https://api.deepseek.com/v1/chat/completions',
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.deepseek_key}'
                },
                json={
                    'model': 'deepseek-chat',
                    'messages': [
                        {'role': 'system', 'content': self.system_messages["analyst"]},
                        {'role': 'user', 'content': user_message}
                    ],
                    'temperature': 0.1,
                    'stream': False
                },
                timeout=30
            )
            
            if response.status_code == 429:
                print(f"      ⚠️  DeepSeek RATE LIMITED (429) - disabling for {self._rate_limit_cooldown}s")
                self._rate_limited['deepseek'] = time.time() + self._rate_limit_cooldown
                return None
            elif response.status_code != 200:
                print(f"      ❌ DeepSeek API error: {response.status_code}")
                return None
                
            content = response.json()['choices'][0]['message']['content'].strip()
            
            # Parse JSON response
            try:
                # Remove markdown code blocks if present
                if '```json' in content:
                    content = content.split('```json')[1].split('```')[0].strip()
                elif '```' in content:
                    content = content.split('```')[1].split('```')[0].strip()
                    
                data = json.loads(content)
                return AIVote(
                    ai_name="DeepSeek",
                    agent_role="Analyst",
                    signal=data.get('signal', 'neutral'),
                    confidence=float(data.get('confidence', 0.5)),
                    reasoning=data.get('reasoning', 'No reasoning provided'),
                    timestamp=datetime.now().isoformat()
                )
            except json.JSONDecodeError:
                # Fallback parsing
                content_lower = content.lower()
                if 'veto' in content_lower:
                    signal = 'veto'
                elif 'buy' in content_lower:
                    signal = 'buy'
                elif 'sell' in content_lower:
                    signal = 'sell'
                else:
                    signal = 'neutral'
                    
                return AIVote("DeepSeek", "Analyst", signal, 0.5, content[:100],
                             datetime.now().isoformat())
                             
        except Exception as e:
            error_str = str(e).lower()
            # Detect rate limit errors
            if '429' in str(e) or 'rate' in error_str or 'limit' in error_str:
                print(f"      ⚠️  DeepSeek RATE LIMITED - disabling for {self._rate_limit_cooldown}s")
                self._rate_limited['deepseek'] = time.time() + self._rate_limit_cooldown
            else:
                print(f"      ❌ DeepSeek error: {e}")
            return None
    
    def _calculate_consensus(self, votes: List[AIVote]) -> Dict[str, Any]:
        """Calculate consensus from AI votes."""
        
        if not votes:
            return {
                "vote": "reject",
                "decision": "reject",
                "confidence": 0.0,
                "confidence_score": 0.0,
                "consensus": 0.0,
                "consensus_score": 0.0,
                "buy_consensus": 0.0,
                "sell_consensus": 0.0,
                "reasoning": "No AI votes",
                "votes": [],
            }
        
        # Focus only on actionable signals (buy/sell/neutral)
        actionable_votes = [v for v in votes if v.signal in {"buy", "sell", "neutral"}]
        if not actionable_votes:
            return {
                "vote": "reject",
                "decision": "reject",
                "confidence": 0.0,
                "confidence_score": 0.0,
                "consensus": 0.0,
                "consensus_score": 0.0,
                "buy_consensus": 0.0,
                "sell_consensus": 0.0,
                "reasoning": "No actionable AI signals",
                "votes": [self._vote_to_dict(v) for v in votes]
            }
        votes = actionable_votes
        
        # Count signals
        buy_votes = sum(1 for v in votes if v.signal == "buy")
        sell_votes = sum(1 for v in votes if v.signal == "sell")
        neutral_votes = sum(1 for v in votes if v.signal == "neutral")
        total_votes = len(votes)
        
        buy_consensus = buy_votes / total_votes
        sell_consensus = sell_votes / total_votes
        max_consensus = max(buy_consensus, sell_consensus)
        
        # Average confidence
        avg_confidence = sum(v.confidence for v in votes) / len(votes)
        
        # Determine final decision
        decision = "approve" if max_consensus >= self.threshold else "reject"
        
        return {
            "vote": decision,
            "decision": decision,
            "confidence": avg_confidence,
            "confidence_score": avg_confidence,
            "consensus": max_consensus,
            "consensus_score": max_consensus,
            "buy_consensus": buy_consensus,
            "sell_consensus": sell_consensus,
            "reasoning": f"AI Consensus (vetos ignored): {max_consensus:.1%}, Confidence: {avg_confidence:.1%}",
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

# Global instance - lazy initialization to ensure env vars loaded
_api_ai_hive = None

def get_api_ai_vote(symbol: str, direction: str, entry_price: float, 
                    market_data: Dict[str, Any], timeframe: str = "1h",
                    objective: str = "day", risk_rules: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Main interface for API-based REAL AI HIVE.
    
    Args:
        symbol: Trading pair (e.g., "EURUSD", "BTCUSD")
        direction: Proposed direction ("BUY" or "SELL")
        entry_price: Current/proposed entry price
        market_data: Dict with:
            - 'prices': list of recent closes (required)
            - 'high': 24h high (optional, calculated if not provided)
            - 'low': 24h low (optional, calculated if not provided)
            - 'candles': list of OHLC dicts (optional)
        timeframe: Chart timeframe (default: "1h")
        objective: Trading style - "scalp", "day", or "swing" (default: "day")
        risk_rules: Dict with max_loss_pct, max_daily_loss_pct, leverage_cap, oco_required
                   (optional, defaults provided)
    
    Returns:
        Dict with vote, confidence, consensus, reasoning, and individual votes
    """
    global _api_ai_hive
    if _api_ai_hive is None:
        _api_ai_hive = APIAIHive()
    return _api_ai_hive.analyze_trade(symbol, direction, entry_price, market_data,
                                     timeframe, objective, risk_rules)

if __name__ == "__main__":
    # Test the system with proper market context
    import random
    
    print("Testing API AI Hive with proper market context...")
    print()
    
    # Simulate realistic EURUSD data
    base_price = 1.0950
    test_prices = [base_price + i*0.0001 + random.uniform(-0.0005, 0.0005) for i in range(50)]
    
    test_data = {
        "prices": test_prices,
        "high": max(test_prices),
        "low": min(test_prices)
    }
    
    # Test with comprehensive parameters
    result = get_api_ai_vote(
        symbol="EURUSD",
        direction="BUY",
        entry_price=test_prices[-1],
        market_data=test_data,
        timeframe="1h",
        objective="day",
        risk_rules={
            'max_loss_pct': 0.5,
            'max_daily_loss_pct': 2.0,
            'leverage_cap': 2.0,
            'oco_required': True
        }
    )
    
    print("\n📋 API AI HIVE RESULT:")
    print(json.dumps(result, indent=2))