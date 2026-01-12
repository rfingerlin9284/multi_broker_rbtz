"""
HIVE COUNSEL INTEGRATION - AI Advisory System
Integrates GPT/Grok guidance for position management decisions
Provides high-probability direction for exits and position management
"""

import logging
from typing import Dict, Optional, Any
from datetime import datetime
import os

logger = logging.getLogger(__name__)

class HiveCounsel:
    """
    AI Hive Counsel - Provides guidance on position management.
    Uses GPT/Grok to analyze positions and recommend exits.
    Ensures system is "thinking" about what needs to be done.
    """
    
    def __init__(self, gpt_client=None, grok_client=None):
        """
        Initialize Hive Counsel with AI clients.
        
        Args:
            gpt_client: Optional OpenAI GPT client
            grok_client: Optional Grok client (xAI)
        """
        self.gpt = gpt_client
        self.grok = grok_client
        self.decision_history: List[Dict[str, Any]] = []
        self.enabled = bool(gpt_client or grok_client)
        
        logger.info(f"🧠 Hive Counsel initialized")
        logger.info(f"   GPT: {'✅' if gpt_client else '❌'}")
        logger.info(f"   Grok: {'✅' if grok_client else '❌'}")
        logger.info(f"   Status: {'🟢 ACTIVE' if self.enabled else '🔴 ADVISORY ONLY'}")
    
    def analyze_position(self, position: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze position with AI guidance.
        
        Args:
            position: Position data from UnifiedPositionManager
        
        Returns:
            Analysis with recommendations
        """
        if not self.enabled:
            return self._get_rule_based_guidance(position)
        
        # Build analysis prompt
        prompt = f"""
Analyze this trading position and provide recommendation:

Position: {position['symbol']}
Side: {position['side']}
Entry Price: ${position['entry_price']:.2f}
Current Price: ${position['current_price']:.2f}
Entry Time: {position['entry_time']}
Hours Held: {position['hours_open']:.2f}
Max Hold: 8 hours
P/L: ${position['unrealized_pnl']:+.2f} ({position['unrealized_pnl_pct']:+.2f}%)
Strategy: {position['strategy']}
Stop Loss: {position['stop_loss']}
Target: {position['target_price']}

Rules:
- Day/swing trades max 6-8 hours
- Exit if exceeding max hold time
- Look for momentum change signals
- Consider profit taking opportunities
- Manage risk automatically

Provide:
1. Exit recommendation (YES/NO/CONSIDER)
2. Confidence (0-100%)
3. Reasoning
4. Risk assessment
"""
        
        try:
            # Try GPT first, fallback to Grok
            if self.gpt:
                response = self.gpt.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3  # More analytical
                )
                analysis = response.choices[0].message.content
            elif self.grok:
                response = self.grok.chat.completions.create(
                    model="grok-2",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3
                )
                analysis = response.choices[0].message.content
            else:
                return self._get_rule_based_guidance(position)
            
            # Parse response
            result = {
                'analysis': analysis,
                'source': 'gpt' if self.gpt else 'grok',
                'timestamp': datetime.now().isoformat(),
                'position_id': position.get('symbol')
            }
            
            self.decision_history.append(result)
            
            logger.info(f"🧠 Hive Counsel analyzed: {position['symbol']}")
            logger.debug(f"   Analysis: {analysis[:200]}...")
            
            return result
        
        except Exception as e:
            logger.warning(f"⚠️  Hive Counsel AI error: {e}, using rule-based guidance")
            return self._get_rule_based_guidance(position)
    
    def should_exit_position(self, position: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Get AI recommendation on whether position should exit.
        
        Args:
            position: Position data
        
        Returns:
            Exit signal or None
        """
        if not self.enabled:
            return None
        
        # Analyze position
        analysis = self.analyze_position(position)
        
        # Look for exit signal in analysis
        analysis_text = analysis.get('analysis', '').lower()
        
        if 'yes' in analysis_text and 'exit' in analysis_text:
            confidence = self._extract_confidence(analysis_text)
            
            return {
                'should_exit': True,
                'reason': 'HIVE_COUNSEL_RECOMMENDATION',
                'confidence': confidence,
                'analysis': analysis['analysis'],
                'source': analysis['source']
            }
        
        return None
    
    def get_exit_guidance(self, position: Dict[str, Any], reason: str = None) -> Dict[str, Any]:
        """
        Get specific guidance on how to exit position.
        
        Args:
            position: Position data
            reason: Why exit is being considered
        
        Returns:
            Exit guidance from AI
        """
        if not self.enabled:
            return self._get_rule_based_exit_guidance(position, reason)
        
        prompt = f"""
Position {position['symbol']} needs to exit. Provide specific exit strategy:

Current situation:
- Entry: ${position['entry_price']:.2f}
- Current: ${position['current_price']:.2f}
- P/L: {position['unrealized_pnl_pct']:+.2f}%
- Reason: {reason or 'unclear'}

Provide:
1. Best exit price/range
2. Exit timing (immediate/staged)
3. Risk management notes
4. Expected outcome
"""
        
        try:
            if self.gpt:
                response = self.gpt.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2
                )
                guidance = response.choices[0].message.content
            elif self.grok:
                response = self.grok.chat.completions.create(
                    model="grok-2",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2
                )
                guidance = response.choices[0].message.content
            else:
                return self._get_rule_based_exit_guidance(position, reason)
            
            return {
                'guidance': guidance,
                'source': 'gpt' if self.gpt else 'grok',
                'timestamp': datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.warning(f"⚠️  Hive Counsel error: {e}")
            return self._get_rule_based_exit_guidance(position, reason)
    
    def get_emergency_exit_guidance(self, position: Dict[str, Any], 
                                   reason: str) -> Dict[str, Any]:
        """
        CRITICAL: Get guidance for emergency exit (max hold time exceeded, etc).
        
        Args:
            position: Position data
            reason: Emergency reason
        
        Returns:
            Urgent exit guidance
        """
        logger.critical(f"🚨 HIVE COUNSEL: Emergency exit needed for {position['symbol']}")
        
        if not self.enabled:
            return {'guidance': 'EXIT IMMEDIATELY AT MARKET', 'source': 'rule_based'}
        
        prompt = f"""
EMERGENCY: Position {position['symbol']} exceeded max hold time!

Status:
- Hours held: {position['hours_open']:.1f}h (Max: 8h)
- P/L: {position['unrealized_pnl_pct']:+.2f}%
- Reason: {reason}

This MUST exit. Provide:
1. Exit action (immediate/market order)
2. Risk acknowledgment
3. Why this is critical
"""
        
        try:
            if self.gpt:
                response = self.gpt.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0  # Deterministic
                )
                guidance = response.choices[0].message.content
            elif self.grok:
                response = self.grok.chat.completions.create(
                    model="grok-2",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0
                )
                guidance = response.choices[0].message.content
            else:
                return {
                    'guidance': 'EXIT IMMEDIATELY AT MARKET (no AI available)',
                    'source': 'rule_based'
                }
            
            return {
                'guidance': guidance,
                'source': 'gpt' if self.gpt else 'grok',
                'urgency': 'CRITICAL',
                'timestamp': datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.critical(f"❌ Hive Counsel error (emergency): {e}")
            return {
                'guidance': 'EXIT IMMEDIATELY AT MARKET (fallback)',
                'source': 'fallback',
                'urgency': 'CRITICAL'
            }
    
    def _get_rule_based_guidance(self, position: Dict[str, Any]) -> Dict[str, Any]:
        """
        Rule-based guidance when AI unavailable.
        """
        guidance = f"Rule-based analysis for {position['symbol']}:\n"
        
        if position['hours_open'] > 7.5:
            guidance += f"- CRITICAL: {position['hours_open']:.1f}h held, must exit within 30min\n"
        elif position['hours_open'] > 6:
            guidance += f"- WARNING: {position['hours_open']:.1f}h held, prepare exit\n"
        
        if position['unrealized_pnl_pct'] > 2:
            guidance += f"- Strong profit at +{position['unrealized_pnl_pct']:.1f}%, consider taking\n"
        
        if position['unrealized_pnl_pct'] < -1.5:
            guidance += f"- Loss at {position['unrealized_pnl_pct']:.1f}%, review stop loss\n"
        
        return {
            'analysis': guidance,
            'source': 'rule_based',
            'timestamp': datetime.now().isoformat()
        }
    
    def _get_rule_based_exit_guidance(self, position: Dict[str, Any], 
                                      reason: str = None) -> Dict[str, Any]:
        """
        Rule-based exit guidance when AI unavailable.
        """
        guidance = "Exit guidance (rule-based):\n"
        
        if reason == 'max_hold_time_exceeded':
            guidance += "EXIT IMMEDIATELY at market price - max hold time exceeded\n"
        else:
            guidance += f"Exit recommended\n"
        
        if position['unrealized_pnl'] > 0:
            guidance += f"Position is in profit (+{position['unrealized_pnl_pct']:.1f}%), favorable exit\n"
        else:
            guidance += f"Position is in loss ({position['unrealized_pnl_pct']:.1f}%), accept loss\n"
        
        return {
            'guidance': guidance,
            'source': 'rule_based',
            'timestamp': datetime.now().isoformat()
        }
    
    def _extract_confidence(self, text: str) -> int:
        """Extract confidence percentage from AI response."""
        import re
        matches = re.findall(r'(\d+)\s*%', text)
        if matches:
            return int(matches[0])
        return 50  # Default to medium confidence
    
    def print_counsel_summary(self):
        """Print recent counsel decisions."""
        logger.info("")
        logger.info("="*70)
        logger.info("🧠 HIVE COUNSEL DECISION HISTORY")
        logger.info("="*70)
        
        if not self.decision_history:
            logger.info("No decisions recorded yet")
        else:
            for decision in self.decision_history[-10:]:  # Last 10
                logger.info(f"Position: {decision['position_id']}")
                logger.info(f"Source: {decision['source']}")
                logger.info(f"Analysis: {decision['analysis'][:100]}...")
        
        logger.info("="*70)
        logger.info("")
