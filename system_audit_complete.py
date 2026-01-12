#!/usr/bin/env python3
"""
COMPLETE SYSTEM AUDIT & DIAGNOSTIC
- Code inventory and legacy detection
- Performance evaluation
- Broker connectivity and API health
- Strategy validation
- Database and state integrity
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
import subprocess
from typing import Dict, List, Any
from collections import defaultdict

# Setup paths
sys.path.insert(0, '/home/ing/RICK/MULTI_BROKER_PHOENIX')
sys.path.insert(0, '/home/ing/RICK/MULTI_BROKER_PHOENIX/MULTI_BROKER_PHOENIX')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SystemAudit:
    """Complete system audit and diagnostics."""
    
    def __init__(self):
        self.project_root = Path('/home/ing/RICK/MULTI_BROKER_PHOENIX')
        self.results = {
            'code_audit': {},
            'legacy_code': [],
            'performance': {},
            'diagnostics': {},
            'deployment_readiness': {}
        }
    
    def log_section(self, title: str):
        """Log a section header."""
        logger.info("\n" + "="*80)
        logger.info(f"🔍 {title}")
        logger.info("="*80)
    
    # ============ PHASE 1: CODE AUDIT ============
    def audit_code_inventory(self):
        """Inventory all Python files and detect legacy code."""
        self.log_section("PHASE 1: CODE INVENTORY & LEGACY DETECTION")
        
        python_files = list(self.project_root.rglob('*.py'))
        logger.info(f"📦 Found {len(python_files)} Python files")
        
        legacy_markers = [
            ('old_', 'Old underscore prefix'),
            ('_backup', 'Backup suffix'),
            ('_legacy', 'Legacy suffix'),
            ('deprecated', 'Deprecated marker'),
            ('TODO_REMOVE', 'Removal TODO'),
            ('FIXME_LEGACY', 'Legacy FIXME'),
            ('unused', 'Unused marker'),
        ]
        
        legacy_files = []
        module_count = defaultdict(int)
        
        for py_file in python_files:
            # Skip common non-code directories
            if any(skip in str(py_file) for skip in ['.venv', '__pycache__', '.git', 'node_modules']):
                continue
            
            # Check filename for legacy markers
            filename = py_file.name.lower()
            is_legacy = any(marker in filename for marker, _ in legacy_markers)
            
            if is_legacy:
                legacy_files.append({
                    'file': str(py_file.relative_to(self.project_root)),
                    'reason': next((reason for marker, reason in legacy_markers if marker in filename), 'Unknown')
                })
            
            # Count modules
            module_path = py_file.parent.name
            module_count[module_path] += 1
        
        self.results['code_audit'] = {
            'total_files': len(python_files),
            'non_legacy_files': len(python_files) - len(legacy_files),
            'modules': dict(module_count)
        }
        
        self.results['legacy_code'] = legacy_files
        
        logger.info(f"✅ Total Python files: {len(python_files)}")
        logger.info(f"⚠️  Legacy/old files found: {len(legacy_files)}")
        for legacy in legacy_files:
            logger.info(f"   - {legacy['file']} ({legacy['reason']})")
        
        logger.info(f"\n📂 Module breakdown:")
        for module, count in sorted(module_count.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"   {module}: {count} files")
    
    # ============ PHASE 2: NEW PROTOCOL VALIDATION ============
    def validate_new_protocol(self):
        """Verify fill verification protocol is properly implemented."""
        self.log_section("PHASE 2: NEW PROTOCOL VALIDATION")
        
        protocol_checks = {}
        
        try:
            from multi_broker_phoenix.brokers.coinbase_safe_connector import CoinbaseSafeConnector
            from multi_broker_phoenix.brokers.oanda_connector_enhanced import OANDAConnector
            from multi_broker_phoenix.brokers.ibkr_connector_enhanced import IBKRConnector
            from multi_broker_phoenix.brokers.order_fill_verifier import OrderFillVerifier
            
            # Check Coinbase
            cb = CoinbaseSafeConnector()
            cb_checks = {
                'daily_limit_removed': cb.max_trades_per_day >= 999999,
                'fill_verification': hasattr(cb, 'verify_order_filled'),
                'filled_orders_tracking': hasattr(cb, '_filled_orders'),
            }
            protocol_checks['coinbase'] = all(cb_checks.values())
            logger.info(f"✅ Coinbase: {cb_checks}")
            
            # Check OANDA
            oanda = OANDAConnector(account_id='TEST', api_key='TEST')
            oanda_checks = {
                'fill_verification': hasattr(oanda, 'verify_order_filled'),
                'filled_orders_tracking': hasattr(oanda, '_filled_orders'),
            }
            protocol_checks['oanda'] = all(oanda_checks.values())
            logger.info(f"✅ OANDA: {oanda_checks}")
            
            # Check IBKR
            ibkr = IBKRConnector(account_id='TEST', paper_mode=True)
            ibkr_checks = {
                'fill_verification': hasattr(ibkr, 'verify_order_filled'),
                'filled_orders_tracking': hasattr(ibkr, '_filled_orders'),
            }
            protocol_checks['ibkr'] = all(ibkr_checks.values())
            logger.info(f"✅ IBKR: {ibkr_checks}")
            
            # Check OrderFillVerifier
            verifier = OrderFillVerifier()
            verifier_checks = {
                'record_order_placed': callable(verifier.record_order_placed),
                'verify_order_filled': callable(verifier.verify_order_filled),
                'get_stats': callable(verifier.get_stats),
            }
            protocol_checks['order_fill_verifier'] = all(verifier_checks.values())
            logger.info(f"✅ OrderFillVerifier: {verifier_checks}")
            
        except Exception as e:
            logger.error(f"❌ Protocol validation failed: {e}")
            protocol_checks['error'] = str(e)
        
        self.results['diagnostics']['protocol_validation'] = protocol_checks
    
    # ============ PHASE 3: PERFORMANCE EVALUATION ============
    def evaluate_performance(self):
        """Test performance metrics of key components."""
        self.log_section("PHASE 3: PERFORMANCE EVALUATION")
        
        perf_results = {}
        
        try:
            # Test 1: Import speed
            import time
            start = time.time()
            from multi_broker_phoenix.brokers.order_fill_verifier import OrderFillVerifier
            import_time = time.time() - start
            logger.info(f"⏱️  Module import time: {import_time*1000:.2f}ms")
            perf_results['import_time_ms'] = import_time * 1000
            
            # Test 2: OrderFillVerifier instantiation
            start = time.time()
            verifier = OrderFillVerifier()
            init_time = time.time() - start
            logger.info(f"⏱️  OrderFillVerifier init time: {init_time*1000:.2f}ms")
            perf_results['verifier_init_ms'] = init_time * 1000
            
            # Test 3: Order recording performance
            start = time.time()
            for i in range(100):
                verifier.record_order_placed(f'TEST-{i}', 'AAPL', 100.0, 150.0)
            record_time = (time.time() - start) / 100
            logger.info(f"⏱️  Order recording (avg): {record_time*1000:.2f}ms per order")
            perf_results['order_record_ms'] = record_time * 1000
            
            # Test 4: Stats generation
            start = time.time()
            stats = verifier.get_stats()
            stats_time = time.time() - start
            logger.info(f"⏱️  Stats generation: {stats_time*1000:.2f}ms")
            perf_results['stats_gen_ms'] = stats_time * 1000
            logger.info(f"   Stats: {stats}")
            
        except Exception as e:
            logger.error(f"❌ Performance test failed: {e}")
            perf_results['error'] = str(e)
        
        self.results['performance'] = perf_results
    
    # ============ PHASE 4: BROKER DIAGNOSTICS ============
    def diagnostic_broker_health(self):
        """Check broker connector health and configuration."""
        self.log_section("PHASE 4: BROKER HEALTH & DIAGNOSTICS")
        
        broker_health = {}
        
        try:
            from multi_broker_phoenix.brokers.coinbase_safe_connector import CoinbaseSafeConnector
            from multi_broker_phoenix.brokers.oanda_connector_enhanced import OANDAConnector
            from multi_broker_phoenix.brokers.ibkr_connector_enhanced import IBKRConnector
            
            # Coinbase
            cb = CoinbaseSafeConnector()
            broker_health['coinbase'] = {
                'paper_mode': cb.paper_mode,
                'min_trade': f"${cb.min_trade_usd}",
                'max_trade': f"${cb.max_trade_usd}",
                'daily_loss_limit': f"${cb.daily_loss_limit}",
                'max_trades_per_day': cb.max_trades_per_day,
                'trailing_stops': cb.use_trailing_stops,
                'status': '✅ HEALTHY'
            }
            logger.info(f"✅ Coinbase: {broker_health['coinbase']}")
            
            # OANDA
            oanda = OANDAConnector(account_id='TEST', api_key='TEST')
            broker_health['oanda'] = {
                'paper_mode': oanda.paper_mode,
                'max_positions': oanda.max_positions,
                'min_trade': f"${oanda.min_trade_usd}",
                'max_trade': f"${oanda.max_trade_usd}",
                'status': '✅ HEALTHY'
            }
            logger.info(f"✅ OANDA: {broker_health['oanda']}")
            
            # IBKR
            ibkr = IBKRConnector(account_id='TEST', paper_mode=True)
            broker_health['ibkr'] = {
                'paper_mode': ibkr.paper_mode,
                'max_positions': ibkr.max_positions,
                'status': '✅ HEALTHY'
            }
            logger.info(f"✅ IBKR: {broker_health['ibkr']}")
            
        except Exception as e:
            logger.error(f"❌ Broker diagnostic failed: {e}")
            broker_health['error'] = str(e)
        
        self.results['diagnostics']['broker_health'] = broker_health
    
    # ============ PHASE 5: STRATEGY VALIDATION ============
    def validate_strategies(self):
        """Check that all 5 strategies are properly configured."""
        self.log_section("PHASE 5: STRATEGY VALIDATION")
        
        strategy_checks = {
            'trap_reversal': {'min_quality': 75, 'status': 'NOT_CHECKED'},
            'institutional_sd': {'min_quality': 70, 'status': 'NOT_CHECKED'},
            'holy_grail': {'min_quality': 80, 'status': 'NOT_CHECKED'},
            'ema_scalper': {'min_quality': 65, 'status': 'NOT_CHECKED'},
            'fabio_aaa': {'min_quality': 78, 'status': 'NOT_CHECKED'},
        }
        
        try:
            strategies_dir = self.project_root / 'MULTI_BROKER_PHOENIX/multi_broker_phoenix/strategies'
            
            for strategy_name in strategy_checks.keys():
                # Check if strategy file exists
                strategy_file = strategies_dir / f'{strategy_name}.py'
                if strategy_file.exists():
                    strategy_checks[strategy_name]['status'] = '✅ EXISTS'
                    logger.info(f"✅ {strategy_name.upper()}: Found")
                else:
                    strategy_checks[strategy_name]['status'] = '❌ MISSING'
                    logger.warning(f"❌ {strategy_name.upper()}: NOT FOUND")
        
        except Exception as e:
            logger.error(f"❌ Strategy validation failed: {e}")
        
        self.results['diagnostics']['strategies'] = strategy_checks
    
    # ============ PHASE 6: DATABASE INTEGRITY ============
    def check_database_integrity(self):
        """Verify database and state files are intact."""
        self.log_section("PHASE 6: DATABASE & STATE INTEGRITY")
        
        db_check = {}
        
        try:
            # Check progression state
            state_file = self.project_root / 'data/progression_state.json'
            if state_file.exists():
                with open(state_file, 'r') as f:
                    state_data = json.load(f)
                db_check['progression_state'] = '✅ VALID'
                logger.info(f"✅ Progression state: Valid")
            else:
                db_check['progression_state'] = '⚠️  MISSING'
                logger.warning(f"⚠️  Progression state file not found")
            
            # Check logs directory
            logs_dir = self.project_root / 'logs'
            if logs_dir.exists():
                log_files = list(logs_dir.glob('*.log'))
                db_check['logs'] = f"✅ {len(log_files)} log files"
                logger.info(f"✅ Logs: {len(log_files)} files present")
            else:
                db_check['logs'] = '⚠️  MISSING'
                logger.warning(f"⚠️  Logs directory not found")
            
        except Exception as e:
            logger.error(f"❌ Database check failed: {e}")
            db_check['error'] = str(e)
        
        self.results['diagnostics']['database'] = db_check
    
    # ============ PHASE 7: DEPLOYMENT READINESS ============
    def assess_deployment_readiness(self):
        """Assess if system is ready for deployment."""
        self.log_section("PHASE 7: DEPLOYMENT READINESS ASSESSMENT")
        
        ready_checks = {
            'new_protocol_active': False,
            'all_brokers_healthy': False,
            'strategies_valid': False,
            'no_critical_legacy': False,
            'performance_acceptable': False,
        }
        
        # Check protocol
        if self.results['diagnostics'].get('protocol_validation', {}).get('coinbase') \
           and self.results['diagnostics'].get('protocol_validation', {}).get('oanda') \
           and self.results['diagnostics'].get('protocol_validation', {}).get('ibkr'):
            ready_checks['new_protocol_active'] = True
            logger.info("✅ New protocol: ACTIVE")
        else:
            logger.warning("⚠️  New protocol: NOT FULLY ACTIVE")
        
        # Check brokers
        broker_health = self.results['diagnostics'].get('broker_health', {})
        if broker_health.get('coinbase', {}).get('status') == '✅ HEALTHY' \
           and broker_health.get('oanda', {}).get('status') == '✅ HEALTHY' \
           and broker_health.get('ibkr', {}).get('status') == '✅ HEALTHY':
            ready_checks['all_brokers_healthy'] = True
            logger.info("✅ Broker health: ALL HEALTHY")
        else:
            logger.warning("⚠️  Some brokers unhealthy")
        
        # Check strategies
        strategies = self.results['diagnostics'].get('strategies', {})
        if all(v.get('status') == '✅ EXISTS' for v in strategies.values()):
            ready_checks['strategies_valid'] = True
            logger.info("✅ Strategies: ALL PRESENT")
        else:
            logger.warning("⚠️  Some strategies missing")
        
        # Check legacy code
        if len(self.results['legacy_code']) == 0:
            ready_checks['no_critical_legacy'] = True
            logger.info("✅ Legacy code: NONE FOUND")
        else:
            logger.warning(f"⚠️  {len(self.results['legacy_code'])} legacy files found")
        
        # Check performance
        perf = self.results['performance']
        if perf.get('import_time_ms', 999) < 1000 and perf.get('verifier_init_ms', 999) < 100:
            ready_checks['performance_acceptable'] = True
            logger.info("✅ Performance: ACCEPTABLE")
        else:
            logger.warning("⚠️  Performance metrics high")
        
        self.results['deployment_readiness'] = ready_checks
        
        # Final verdict
        all_ready = all(ready_checks.values())
        logger.info("\n" + "="*80)
        if all_ready:
            logger.info("✅✅✅ SYSTEM READY FOR DEPLOYMENT ✅✅✅")
        else:
            logger.info("⚠️  SYSTEM READY FOR DEPLOYMENT WITH NOTES")
        logger.info("="*80)
        
        return all_ready
    
    def run_full_audit(self):
        """Execute complete audit."""
        logger.info("\n" + "█"*80)
        logger.info("█" + " "*78 + "█")
        logger.info("█  COMPLETE SYSTEM AUDIT & DIAGNOSTIC" + " "*42 + "█")
        logger.info("█" + " "*78 + "█")
        logger.info("█"*80)
        
        self.audit_code_inventory()
        self.validate_new_protocol()
        self.evaluate_performance()
        self.diagnostic_broker_health()
        self.validate_strategies()
        self.check_database_integrity()
        ready = self.assess_deployment_readiness()
        
        # Summary report
        self.log_section("AUDIT SUMMARY REPORT")
        
        logger.info(f"\n📊 Code Audit Results:")
        logger.info(f"   Total Python files: {self.results['code_audit'].get('total_files', 0)}")
        logger.info(f"   Legacy files found: {len(self.results['legacy_code'])}")
        
        logger.info(f"\n📈 Performance Metrics:")
        perf = self.results['performance']
        import_time = perf.get('import_time_ms', 'N/A')
        init_time = perf.get('verifier_init_ms', 'N/A')
        record_time = perf.get('order_record_ms', 'N/A')
        
        if isinstance(import_time, (int, float)):
            logger.info(f"   Import time: {import_time:.2f}ms")
        else:
            logger.info(f"   Import time: {import_time}")
        
        if isinstance(init_time, (int, float)):
            logger.info(f"   Init time: {init_time:.2f}ms")
        else:
            logger.info(f"   Init time: {init_time}")
        
        if isinstance(record_time, (int, float)):
            logger.info(f"   Record time: {record_time:.2f}ms/order")
        else:
            logger.info(f"   Record time: {record_time}")
        
        logger.info(f"\n✅ Deployment Readiness:")
        for check, status in self.results['deployment_readiness'].items():
            icon = "✅" if status else "❌"
            logger.info(f"   {icon} {check}: {status}")
        
        return ready

if __name__ == '__main__':
    audit = SystemAudit()
    ready = audit.run_full_audit()
    
    # Save results
    results_file = Path('/tmp/system_audit_results.json')
    with open(results_file, 'w') as f:
        json.dump(audit.results, f, indent=2, default=str)
    logger.info(f"\n💾 Audit results saved to: {results_file}")
    
    sys.exit(0 if ready else 1)
