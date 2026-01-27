"""
LIVE EXTREME ENGINE - AUTONOMOUS HIVE INTEGRATION
Integrates autonomous hive agent into main trading loop
All systems on by default, fully autonomous execution
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class LiveExtremeAutonomousIntegration:
    """
    Integration layer that plugs autonomous hive agent into live_extreme_engine.
    Handles the main trading loop with all systems active.
    """
    
    def __init__(self, hive_agent, broker_connectors: Dict[str, Any]):
        """
        Initialize integration.
        
        Args:
            hive_agent: Autonomous hive agent instance
            broker_connectors: Dict with 'coinbase', 'oanda', 'ibkr' connectors
        """
        self.hive_agent = hive_agent
        self.brokers = broker_connectors
        self.iteration_count = 0
        self.autonomous_enabled = True
        
        logger.info("✅ LiveExtremeAutonomousIntegration initialized")
    
    def execute_autonomous_iteration(self, market_data: Dict[str, Any],
                                     current_price: Dict[str, float]) -> Dict[str, Any]:
        """
        Execute single autonomous trading iteration.
        All 5 strategies, AI, hedging, risk management active.
        
        Args:
            market_data: Current market snapshot
            current_price: Current prices for all symbols
        
        Returns:
            Results of this iteration
        """
        self.iteration_count += 1
        
        if not self.autonomous_enabled or not self.hive_agent.is_ready:
            logger.warning("⚠️  Autonomous mode not enabled or not ready")
            return {'success': False}
        
        try:
            # Run main autonomous loop
            results = self.hive_agent.autonomous_execution_loop(
                market_data=market_data,
                brokers=self.brokers
            )
            
            # Log iteration results
            if results.get('positions_opened', 0) > 0 or results.get('positions_closed', 0) > 0:
                logger.info(f"📊 Iteration {self.iteration_count}: "
                           f"Opened: {results['positions_opened']}, "
                           f"Closed: {results['positions_closed']}, "
                           f"Hedges: {results['hedges_deployed']}")
            
            return results
        
        except Exception as e:
            logger.error(f"❌ Autonomous iteration failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def disable_autonomous_mode(self):
        """Temporarily disable autonomous execution."""
        self.autonomous_enabled = False
        logger.warning("⚠️  Autonomous mode DISABLED")
    
    def enable_autonomous_mode(self):
        """Re-enable autonomous execution."""
        self.autonomous_enabled = True
        logger.info("✅ Autonomous mode ENABLED")


def integrate_autonomous_hive_into_engine(engine_instance, 
                                         hive_agent,
                                         broker_connectors: Dict[str, Any]) -> None:
    """
    Integrate autonomous hive agent into live_extreme_engine.
    
    Args:
        engine_instance: The live_extreme_engine instance
        hive_agent: Autonomous hive agent instance
        broker_connectors: Dict with broker connectors
    """
    
    logger.info("")
    logger.info("="*80)
    logger.info("🔗 INTEGRATING AUTONOMOUS HIVE AGENT INTO LIVE EXTREME ENGINE")
    logger.info("="*80)
    logger.info("")
    
    # Create integration layer
    integration = LiveExtremeAutonomousIntegration(hive_agent, broker_connectors)
    
    # Inject into engine
    engine_instance.autonomous_integration = integration
    engine_instance.autonomous_enabled = True
    
    logger.info("✅ Integration complete")
    logger.info("")
    logger.info("AUTONOMOUS SYSTEMS ACTIVE:")
    logger.info("  🤖 Strategy Execution: ON (all 5 strategies)")
    logger.info("  🧠 AI Hunting: ON (GPT-4/Grok)")
    logger.info("  ⚡ Synergy Engine: ON (coordinated positions)")
    logger.info("  🛡️  Risk Management: ON (time limits, stops, hedges)")
    logger.info("  📍 Position Awareness: ON (6-8h enforcement)")
    logger.info("  💡 Quality Gating: ON (70%+ quality minimum)")
    logger.info("  ⚙️  Auto-Tuning: ON (learning from trades)")
    logger.info("")


def inject_autonomous_loop_into_main_iteration(engine_instance) -> None:
    """
    Inject autonomous execution into main engine iteration.
    
    This modifies the main iteration loop to call autonomous hive agent.
    
    Args:
        engine_instance: The live_extreme_engine instance
    """
    
    if not hasattr(engine_instance, 'autonomous_integration'):
        logger.error("❌ Autonomous integration not attached to engine")
        return
    
    # Get original iteration method
    original_iteration = engine_instance.main_iteration
    
    def autonomous_main_iteration(market_data, prices):
        """Wrapper that injects autonomous hive execution."""
        
        # Run autonomous hive loop
        if engine_instance.autonomous_enabled:
            autonomous_results = engine_instance.autonomous_integration.execute_autonomous_iteration(
                market_data=market_data,
                current_price=prices
            )
            
            # If autonomous executed trades, return
            if autonomous_results.get('positions_opened', 0) > 0:
                return autonomous_results
        
        # Fall back to original iteration if no autonomous execution
        return original_iteration(market_data, prices)
    
    # Replace iteration method
    engine_instance.main_iteration = autonomous_main_iteration
    
    logger.info("✅ Autonomous loop injected into main iteration")


# Configuration snippet for live_extreme_engine initialization
AUTONOMOUS_ENGINE_CONFIG = {
    'autonomous_mode_enabled': True,
    'autonomous_default_on': True,
    'autonomous_strategies': [
        'trap_reversal',
        'institutional_sd', 
        'holy_grail',
        'ema_scalper',
        'fabio_aaa'
    ],
    'autonomous_brokers': [
        'coinbase',
        'oanda',
        'ibkr'
    ],
    'autonomous_ai_active': True,
    'autonomous_risk_management_active': True,
    'autonomous_hedging_active': True,
    'autonomous_learning_active': True,
    'autonomous_quality_minimum': 70.0,
    'autonomous_execution_interval': 60  # seconds
}
