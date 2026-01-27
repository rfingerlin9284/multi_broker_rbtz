"""
HIVE AGENTS WITH REAL BROWSER RESEARCH

These agents now use REAL ChatGPT via browser automation!
No more fake research - actual web browsing and analysis.

Each agent sends specialized prompts to ChatGPT and gets real responses.
"""

from .hive_consensus import HiveAgent, AgentRole, AgentVote, VoteDecision, TradeOpportunity
from .hive_browser_bridge import create_browser_bridge
from typing import Dict, Any, Optional
import time


class RealBrowserAgent(HiveAgent):
    """Base agent that can use real browser for research"""
    
    def __init__(self, name: str, role: AgentRole, expertise_weight: float = 1.0):
        super().__init__(name, role, expertise_weight)
        self.browser_bridge = None
        self._browser_available = None
    
    def _ensure_bridge(self):
        """Lazy init browser bridge"""
        if self.browser_bridge is None:
            self.browser_bridge = create_browser_bridge()
    
    def _browser_is_available(self) -> bool:
        """Check if browser worker is running (cached for 30s)"""
        now = time.time()
        if self._browser_available is not None:
            cache_time, available = self._browser_available
            if now - cache_time < 30.0:
                return available
        
        self._ensure_bridge()
        available = self.browser_bridge.is_worker_running()
        self._browser_available = (now, available)
        return available
    
    def _ask_chatgpt(self, prompt: str, context: Dict[str, Any], timeout: float = 30.0) -> Optional[Dict]:
        """Send prompt to ChatGPT via browser and get response"""
        if not self._browser_is_available():
            return None
        
        self._ensure_bridge()
        
        return self.browser_bridge.request_research(
            agent_name=self.name,
            symbol=context.get('symbol', 'UNKNOWN'),
            direction=context.get('direction', 'UNKNOWN'),
            entry_price=context.get('entry_price', 0.0),
            context=context,
            custom_prompt=prompt,
            timeout=timeout
        )


class OracleAgent(RealBrowserAgent):
    """Deep research agent using ChatGPT for catalyst analysis"""
    
    def __init__(self):
        super().__init__("Oracle", AgentRole.FUNDAMENTALS, expertise_weight=1.3)
    
    def research_opportunity(self, opportunity: TradeOpportunity) -> Dict:
        """Research using REAL ChatGPT"""
        
        # Build specialized prompt for catalyst research
        prompt = f"""You are Oracle, the HIVE catalyst research agent.

Analyze this trade opportunity for upcoming catalysts and events:

SYMBOL: {opportunity.symbol}
DIRECTION: {opportunity.side}
ENTRY: {opportunity.entry_price}
STOP: {opportunity.stop_loss}

Your task:
1. Identify upcoming high-impact economic events (next 48 hours)
2. Check for central bank decisions, major data releases
3. Assess catalyst strength (0.0 to 1.0)
4. Recommend if timing is good

Return STRICT JSON:
{{
  "upcoming_events": ["event1", "event2"],
  "catalyst_score": 0.0,
  "timing_ok": true,
  "reasoning": "brief explanation"
}}
"""
        
        context = {
            'symbol': opportunity.symbol,
            'direction': opportunity.side,
            'entry_price': opportunity.entry_price,
            'agent_role': 'catalyst_research'
        }
        
        response = self._ask_chatgpt(prompt, context, timeout=30.0)
        
        if response and not response.get('error'):
            return response
        
        # Fallback if browser not available
        return {
            'upcoming_events': [],
            'catalyst_score': 0.5,
            'timing_ok': True,
            'reasoning': 'Browser worker not available - neutral stance',
            'browser_unavailable': True
        }
    
    def vote(self, opportunity: TradeOpportunity, research: Dict) -> AgentVote:
        """Vote based on catalyst analysis"""
        
        if research.get('browser_unavailable'):
            # Neutral if no real data
            return AgentVote(
                VoteDecision.NEUTRAL,
                "Browser worker offline - cannot verify catalysts",
                confidence=0.3
            )
        
        catalyst_score = research.get('catalyst_score', 0.5)
        timing_ok = research.get('timing_ok', True)
        events = research.get('upcoming_events', [])
        
        if not timing_ok:
            return AgentVote(
                VoteDecision.STRONG_NO,
                f"Bad timing - major events upcoming: {', '.join(events)}",
                confidence=0.9
            )
        
        if catalyst_score > 0.7:
            return AgentVote(
                VoteDecision.STRONG_YES,
                f"Strong catalyst detected: {research.get('reasoning', '')}",
                confidence=0.85
            )
        elif catalyst_score > 0.4:
            return AgentVote(
                VoteDecision.YES,
                f"Moderate catalyst support",
                confidence=0.6
            )
        else:
            return AgentVote(
                VoteDecision.NEUTRAL,
                "No strong catalysts",
                confidence=0.5
            )


class PrometheusAgent(RealBrowserAgent):
    """Technical analysis using ChatGPT"""
    
    def __init__(self):
        super().__init__("Prometheus", AgentRole.TECHNICALS, expertise_weight=1.2)
    
    def research_opportunity(self, opportunity: TradeOpportunity) -> Dict:
        """Technical analysis via ChatGPT"""
        
        prompt = f"""You are Prometheus, HIVE technical analysis expert.

Analyze this trade setup:

SYMBOL: {opportunity.symbol}
DIRECTION: {opportunity.side}
ENTRY: {opportunity.entry_price}
STOP: {opportunity.stop_loss}

Evaluate:
1. Is this a clean technical setup?
2. Support/resistance levels
3. Momentum indicators (RSI, MACD)
4. Chart patterns visible
5. Risk/reward ratio

Return STRICT JSON:
{{
  "setup_quality": 0.0,
  "key_levels": {{"support": 0.0, "resistance": 0.0}},
  "momentum": "bullish|neutral|bearish",
  "patterns": ["pattern1"],
  "technical_ok": true,
  "reasoning": "brief"
}}
"""
        
        context = {
            'symbol': opportunity.symbol,
            'direction': opportunity.side,
            'entry_price': opportunity.entry_price,
            'agent_role': 'technical_analysis'
        }
        
        response = self._ask_chatgpt(prompt, context, timeout=30.0)
        
        if response and not response.get('error'):
            return response
        
        return {
            'setup_quality': 0.5,
            'technical_ok': True,
            'reasoning': 'Browser worker offline',
            'browser_unavailable': True
        }
    
    def vote(self, opportunity: TradeOpportunity, research: Dict) -> AgentVote:
        """Vote based on technical setup"""
        
        if research.get('browser_unavailable'):
            return AgentVote(
                VoteDecision.NEUTRAL,
                "Browser offline - no technical data",
                confidence=0.3
            )
        
        setup_quality = research.get('setup_quality', 0.5)
        technical_ok = research.get('technical_ok', True)
        
        if not technical_ok:
            return AgentVote(
                VoteDecision.NO,
                f"Technical setup flawed: {research.get('reasoning', '')}",
                confidence=0.7
            )
        
        if setup_quality > 0.7:
            return AgentVote(
                VoteDecision.STRONG_YES,
                "Excellent technical setup",
                confidence=0.8
            )
        elif setup_quality > 0.5:
            return AgentVote(
                VoteDecision.YES,
                "Good technical alignment",
                confidence=0.6
            )
        else:
            return AgentVote(
                VoteDecision.NEUTRAL,
                "Mediocre technicals",
                confidence=0.5
            )


class SentinelAgent(RealBrowserAgent):
    """Risk validation using ChatGPT"""
    
    def __init__(self):
        super().__init__("Sentinel", AgentRole.RISK_CONTROL, expertise_weight=1.5)
    
    def research_opportunity(self, opportunity: TradeOpportunity) -> Dict:
        """Risk analysis via ChatGPT"""
        
        rr_ratio = opportunity.calculate_risk_reward_ratio()
        stop_distance_pct = abs(opportunity.entry_price - opportunity.stop_loss) / opportunity.entry_price * 100
        
        prompt = f"""You are Sentinel, HIVE risk guardian with VETO power.

Validate this trade for safety:

SYMBOL: {opportunity.symbol}
DIRECTION: {opportunity.side}
ENTRY: {opportunity.entry_price}
STOP: {opportunity.stop_loss}
RISK/REWARD: {rr_ratio:.2f}:1
STOP DISTANCE: {stop_distance_pct:.2f}%

Check:
1. Is stop loss too tight? (<1% is dangerous, 3-5% is ideal)
2. Is R:R ratio acceptable? (minimum 2:1, prefer 3:1)
3. Any hidden risks?
4. Should this trade be VETOED?

Return STRICT JSON:
{{
  "stop_ok": true,
  "rr_ok": true,
  "veto": false,
  "risk_score": 0.0,
  "reasoning": "brief"
}}
"""
        
        context = {
            'symbol': opportunity.symbol,
            'direction': opportunity.side,
            'entry_price': opportunity.entry_price,
            'stop_loss': opportunity.stop_loss,
            'rr_ratio': rr_ratio,
            'stop_distance_pct': stop_distance_pct,
            'agent_role': 'risk_validation'
        }
        
        response = self._ask_chatgpt(prompt, context, timeout=30.0)
        
        if response and not response.get('error'):
            return response
        
        # Fallback: Use local risk checks
        return {
            'stop_ok': stop_distance_pct >= 1.0,
            'rr_ok': rr_ratio >= 2.0,
            'veto': (stop_distance_pct < 1.0 or rr_ratio < 2.0),
            'risk_score': 0.5,
            'reasoning': 'Browser offline - using local checks',
            'browser_unavailable': True
        }
    
    def vote(self, opportunity: TradeOpportunity, research: Dict) -> AgentVote:
        """Vote with VETO power"""
        
        veto = research.get('veto', False)
        stop_ok = research.get('stop_ok', True)
        rr_ok = research.get('rr_ok', True)
        
        if veto or not stop_ok or not rr_ok:
            return AgentVote(
                VoteDecision.VETO,
                f"VETOED: {research.get('reasoning', 'Risk parameters violated')}",
                confidence=1.0
            )
        
        risk_score = research.get('risk_score', 0.5)
        
        if risk_score < 0.3:
            return AgentVote(
                VoteDecision.STRONG_YES,
                "Excellent risk profile",
                confidence=0.9
            )
        elif risk_score < 0.6:
            return AgentVote(
                VoteDecision.YES,
                "Acceptable risk",
                confidence=0.7
            )
        else:
            return AgentVote(
                VoteDecision.NO,
                f"High risk: {research.get('reasoning', '')}",
                confidence=0.8
            )


# Export all agents
__all__ = [
    'RealBrowserAgent',
    'OracleAgent',
    'PrometheusAgent',
    'SentinelAgent',
]
