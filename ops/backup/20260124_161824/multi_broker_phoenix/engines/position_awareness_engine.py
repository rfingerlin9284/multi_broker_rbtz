"""
POSITION AWARENESS ENGINE - Active Position Management Loop
Runs every iteration to monitor ALL positions across ALL brokers
Enforces rules, detects exits, executes management
THIS IS THE MISSING PIECE THAT ALLOWED OANDA POSITION TO OVERSTAY
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import os
from .unified_position_manager import UnifiedPositionManager

logger = logging.getLogger(__name__)

class PositionAwarenessEngine:
    """
    Active monitoring engine that runs on every trading iteration.
    Ensures NO position is overlooked or forgotten.
    Enforces time-based rules automatically.
    Coordinates exits across all brokers.
    """
    
    def __init__(self, 
                 unified_manager: UnifiedPositionManager,
                 broker_managers: Dict[str, Any],
                 hive_counsel: Optional[Any] = None):
        """
        Initialize position awareness engine.
        
        Args:
            unified_manager: Central position tracker
            broker_managers: {broker_name: manager_instance}
                           - 'coinbase': CoinbaseSafeConnector
                           - 'oanda': OANDAPositionManager
                           - 'ibkr': IBKRConnector
            hive_counsel: Optional AI guidance system
        """
        self.unified = unified_manager
        self.brokers = broker_managers  # ALL brokers managed here
        self.hive = hive_counsel
        
        self.iteration_count = 0
        self.checks_executed = 0
        self.exits_triggered = 0
        self.alerts_issued = 0
        
        logger.info(f"🎯 Position Awareness Engine initialized")
        logger.info(f"   Monitoring brokers: {list(broker_managers.keys())}")
        logger.info(f"   Hive counsel: {'✅ ACTIVE' if hive_counsel else '❌ DISABLED'}")
        logger.info(f"   Max hold time: {unified_manager.max_hold_hours}h")
    
    def execute_awareness_loop(self) -> Dict[str, Any]:
        """
        Execute the position awareness loop.
        THIS MUST RUN ON EVERY TRADING ITERATION.
        
        Returns:
            Loop results with checks, alerts, exits
        """
        self.iteration_count += 1
        
        start_time = datetime.now()
        results = {
            'iteration': self.iteration_count,
            'timestamp': datetime.now().isoformat(),
            'total_positions': 0,
            'positions_by_broker': {},
            'checks_executed': 0,
            'alerts_critical': [],
            'alerts_warning': [],
            'exits_executed': [],
            'exits_pending': [],
            'execution_time_ms': 0
        }
        
        try:
            # STEP 1: Sync positions from all brokers
            logger.debug(f"--- POSITION AWARENESS LOOP {self.iteration_count} ---")
            
            for broker_name, manager in self.brokers.items():
                if hasattr(manager, 'sync_live_positions'):
                    logger.debug(f"Syncing {broker_name} positions...")
                    positions = manager.sync_live_positions()
                    results['positions_by_broker'][broker_name] = len(positions)
            
            # STEP 2: Get unified view of all positions
            all_positions = self.unified.get_all_open_positions()
            results['total_positions'] = len(all_positions)
            
            if results['total_positions'] == 0:
                logger.debug("No open positions to monitor")
                results['execution_time_ms'] = (datetime.now() - start_time).total_seconds() * 1000
                return results
            
            logger.info(f"📊 Monitoring {results['total_positions']} position(s) across "
                       f"{list(results['positions_by_broker'].keys())}")
            
            # STEP 3: Check each position for exit conditions
            for pos in all_positions:
                self.checks_executed += 1
                results['checks_executed'] += 1
                
                # Get position ID
                pos_id = f"{pos['broker']}:{pos['symbol']}:{int(pos['entry_time'].timestamp())}"
                
                # Update with current price (if available)
                current_price = self._get_current_price(pos['broker'], pos['symbol'])
                if current_price:
                    self.unified.update_position(pos_id, current_price)
                
                # Check exit conditions
                exit_signal = self.unified.check_exit_conditions(pos_id)
                
                if exit_signal and exit_signal.get('should_exit'):
                    results['exits_pending'].append({
                        'symbol': pos['symbol'],
                        'broker': pos['broker'],
                        'reason': exit_signal.get('reason'),
                        'severity': exit_signal.get('severity', 'NORMAL')
                    })
                    
                    # Log severity
                    if exit_signal.get('severity') == 'CRITICAL':
                        logger.critical(f"🚨 CRITICAL EXIT: {pos['symbol']} ({pos['broker']})")
                        logger.critical(f"   Reason: {exit_signal['reason']}")
                        results['alerts_critical'].append({
                            'symbol': pos['symbol'],
                            'reason': exit_signal['reason']
                        })
                        self.alerts_issued += 1
                    elif exit_signal.get('severity') == 'HIGH':
                        logger.warning(f"⚠️  HIGH PRIORITY EXIT: {pos['symbol']}")
                        results['alerts_warning'].append({
                            'symbol': pos['symbol'],
                            'reason': exit_signal['reason']
                        })
                        self.alerts_issued += 1
                    
                    # STEP 4: Execute exit if available
                    if exit_signal.get('auto_execute', False):
                        success = self._execute_position_exit(pos, exit_signal)
                        if success:
                            results['exits_executed'].append({
                                'symbol': pos['symbol'],
                                'broker': pos['broker'],
                                'reason': exit_signal['reason']
                            })
                            self.exits_triggered += 1
            
            # STEP 5: Print awareness report
            self._print_awareness_report(results)
        
        except Exception as e:
            logger.error(f"❌ Position awareness loop error: {e}")
            results['error'] = str(e)
        
        finally:
            results['execution_time_ms'] = (datetime.now() - start_time).total_seconds() * 1000
        
        return results
    
    def _get_current_price(self, broker: str, symbol: str) -> Optional[float]:
        """Get current price from broker."""
        try:
            manager = self.brokers.get(broker)
            if not manager:
                return None
            
            if hasattr(manager, 'get_current_price'):
                return manager.get_current_price(symbol)
            elif hasattr(manager, 'get_last_price'):
                return manager.get_last_price(symbol)
            
            return None
        except Exception as e:
            logger.warning(f"Could not get price for {broker}:{symbol}: {e}")
            return None
    
    def _execute_position_exit(self, position: Dict[str, Any], 
                              exit_signal: Dict[str, Any]) -> bool:
        """
        Execute position exit on correct broker.
        
        Args:
            position: Position data
            exit_signal: Exit signal
        
        Returns:
            True if exit executed successfully
        """
        broker = position['broker']
        symbol = position['symbol']
        reason = exit_signal.get('reason', 'system_exit')
        
        try:
            manager = self.brokers.get(broker)
            if not manager:
                logger.error(f"No manager for broker: {broker}")
                return False
            
            # Execute based on broker
            if broker == 'oanda' and hasattr(manager, 'execute_exit'):
                logger.warning(f"📤 Executing OANDA exit: {symbol}")
                success = manager.execute_exit(symbol, reason)
            elif broker == 'coinbase' and hasattr(manager, 'close_position'):
                logger.warning(f"📤 Executing Coinbase exit: {symbol}")
                success = manager.close_position(symbol)
            elif broker == 'ibkr' and hasattr(manager, 'close_position'):
                logger.warning(f"📤 Executing IBKR exit: {symbol}")
                success = manager.close_position(symbol)
            else:
                logger.error(f"Cannot execute exit for {broker}")
                return False
            
            if success:
                logger.info(f"✅ Exit executed: {symbol}")
            
            return success
        
        except Exception as e:
            logger.error(f"❌ Exit execution error: {e}")
            return False
    
    def _print_awareness_report(self, results: Dict[str, Any]):
        """Print awareness loop report."""
        if results['total_positions'] == 0:
            return
        
        logger.info("")
        logger.info("="*70)
        logger.info(f"🎯 POSITION AWARENESS REPORT - Iteration {results['iteration']}")
        logger.info("="*70)
        
        logger.info(f"Total positions: {results['total_positions']}")
        logger.info(f"Checks executed: {results['checks_executed']}")
        
        if results['positions_by_broker']:
            for broker, count in results['positions_by_broker'].items():
                logger.info(f"  {broker}: {count} position(s)")
        
        if results['alerts_critical']:
            logger.critical(f"CRITICAL ALERTS: {len(results['alerts_critical'])}")
            for alert in results['alerts_critical']:
                logger.critical(f"  🚨 {alert['symbol']}: {alert['reason']}")
        
        if results['alerts_warning']:
            logger.warning(f"WARNING ALERTS: {len(results['alerts_warning'])}")
            for alert in results['alerts_warning']:
                logger.warning(f"  ⚠️  {alert['symbol']}: {alert['reason']}")
        
        if results['exits_executed']:
            logger.info(f"Exits executed: {len(results['exits_executed'])}")
            for exit_ in results['exits_executed']:
                logger.info(f"  ✅ {exit_['symbol']}: {exit_['reason']}")
        
        if results['exits_pending']:
            logger.info(f"Exits pending: {len(results['exits_pending'])}")
            for pending in results['exits_pending']:
                logger.info(f"  ⏳ {pending['symbol']}: {pending['reason']}")
        
        logger.info(f"Execution time: {results['execution_time_ms']:.1f}ms")
        logger.info("="*70)
        logger.info("")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status."""
        all_positions = self.unified.get_all_open_positions()
        critical = len(self.unified.get_positions_exceeding_hold_time())
        warning = len(self.unified.get_positions_near_hold_limit())
        
        return {
            'engine_status': 'ACTIVE',
            'iterations_run': self.iteration_count,
            'total_checks': self.checks_executed,
            'total_exits_triggered': self.exits_triggered,
            'total_alerts': self.alerts_issued,
            'current_positions': len(all_positions),
            'critical_alerts': critical,
            'warning_alerts': warning,
            'brokers_monitored': list(self.brokers.keys())
        }
    
    def print_system_status(self):
        """Print system status."""
        status = self.get_system_status()
        
        logger.info("")
        logger.info("="*70)
        logger.info("🎯 POSITION AWARENESS ENGINE STATUS")
        logger.info("="*70)
        logger.info(f"Status: {status['engine_status']}")
        logger.info(f"Iterations: {status['iterations_run']}")
        logger.info(f"Checks executed: {status['total_checks']}")
        logger.info(f"Exits triggered: {status['total_exits_triggered']}")
        logger.info(f"Alerts issued: {status['total_alerts']}")
        logger.info(f"Current positions: {status['current_positions']}")
        logger.info(f"Critical alerts: {status['critical_alerts']}")
        logger.info(f"Warning alerts: {status['warning_alerts']}")
        logger.info(f"Brokers: {', '.join(status['brokers_monitored'])}")
        logger.info("="*70)
        logger.info("")
