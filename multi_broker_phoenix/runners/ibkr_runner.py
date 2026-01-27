"""IBKR Supervised Runner - Paper trading via TWS/Gateway.

Wraps existing IBKR connector with supervision framework.
Connects to IB Gateway or TWS on port 4002 (paper) or 4001 (live).

Prerequisites:
- IB Gateway or TWS running and configured
- Port 4002 accessible (paper trading)
- ib_insync library installed
"""
from __future__ import annotations
import os
import sys
import time
import logging
from pathlib import Path
from datetime import datetime

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Load .env
def _load_env():
    env_path = REPO_ROOT / '.env'
    if not env_path.exists():
        return
    loaded = 0
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            if '#' in line:
                eq_pos = line.index('=')
                hash_pos = line.find('#', eq_pos)
                if hash_pos > 0:
                    line = line[:hash_pos].strip()
            if '=' not in line:
                continue
            key, value = line.split('=', 1)
            key, value = key.strip(), value.strip()
            if key and key not in os.environ:
                os.environ[key] = value
                loaded += 1
    if loaded > 0:
        print(f"✅ Loaded {loaded} env vars")

_load_env()

from multi_broker_phoenix.core.broker_supervisor import BrokerSupervisor
from multi_broker_phoenix.core.gates import BrokerGates
from multi_broker_phoenix.adapters.ibkr_adapter import IbkrAdapter

logger = logging.getLogger(__name__)


def start_ibkr_broker():
    """Start IBKR broker engine with supervision."""
    if os.getenv('BROKER_IBKR_ENABLED', '0') not in ('1', 'true'):
        print("❌ IBKR broker disabled")
        sys.exit(0)
    
    print("=" * 80)
    print("🚀 IBKR SUPERVISED BROKER STARTING")
    print(f"   Gateway Port: {os.getenv('IBKR_PORT', '4002')}")
    print(f"   PID: {os.getpid()}")
    print("=" * 80)
    
    try:
        adapter = IbkrAdapter()
    except Exception as e:
        print(f"❌ FATAL: IbkrAdapter initialization failed: {e}")
        sys.exit(1)
    
    supervisor = BrokerSupervisor(broker_name='ibkr', connector=adapter, repo_root=REPO_ROOT)
    supervisor.start_heartbeat()
    print("✅ Heartbeat started")
    
    auto_arm = os.getenv('BROKER_IBKR_AUTO_ARM', os.getenv('AUTO_ARM_ON_HEALTHY', '0')) == '1'
    if auto_arm:
        print("🤖 AUTO-ARM ENABLED")
    
    print("\n🔍 Initial gate checks...")
    all_passed, gate_results = gates.run_all_gates()
    for gate_name, result in gate_results.items():
        status = "✅" if result['passed'] else "❌"
        print(f"   {status} {gate_name}")
    
    if all_passed and auto_arm:
        supervisor.mark_active()
        print("\n✅ BROKER ACTIVE")
    else:
        print("\n⏸️  BROKER PAUSED")
    
    print("\n🔄 MAIN LOOP\n")
    poll_interval = int(os.getenv('IBKR_POLL_INTERVAL', '30'))
    loop_count = 0
    
    try:
        while True:
            loop_count += 1
            
            if not supervisor.can_trade():
                print(f"⏸️  Trading paused - waiting {poll_interval}s")
                time.sleep(poll_interval)
                if loop_count % 6 == 0:
                    all_passed, _ = gates.run_all_gates()
                    if all_passed and auto_arm:
                        supervisor.mark_active()
                continue
            
            # TODO: Integrate strategy logic here (same pattern as OANDA runner)
            
            if loop_count % 10 == 0:
                print(f"✅ Tick {loop_count}")
            
            time.sleep(poll_interval)
    
    except KeyboardInterrupt:
        print("\n🛑 IBKR broker stopped")
    except Exception as e:
        logger.error(f"FATAL: {e}", exc_info=True)
        supervisor.mark_failed(str(e))
    finally:
        supervisor.stop()
        print("🏁 IBKR SHUTDOWN")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    start_ibkr_broker()
