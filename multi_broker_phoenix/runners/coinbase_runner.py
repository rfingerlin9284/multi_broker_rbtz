"""Coinbase Supervised Runner - Real money trading (use with extreme caution).

WARNING: Coinbase has NO paper trading. All orders = REAL MONEY.

OCO SUPPORT: BLOCKED by default (Coinbase has no native OCO/bracket orders).
Broker will stay PAUSED unless COINBASE_EMULATED_OCO=true (NOT RECOMMENDED).

Safety limits:
- $5-10 per trade (nano-lot testing)
- Daily loss limit: $50
- Consecutive loss breaker: 5 losses
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
from multi_broker_phoenix.adapters.coinbase_adapter import CoinbaseAdapter

logger = logging.getLogger(__name__)


def start_coinbase_broker():
    """Start Coinbase broker engine with supervision."""
    if os.getenv('BROKER_COINBASE_ENABLED', '0') not in ('1', 'true'):
        print("❌ Coinbase broker disabled")
        sys.exit(0)
    
    print("=" * 80)
    print("🚀 COINBASE SUPERVISED BROKER STARTING")
    print("=" * 80)
    print("   ⚠️  WARNING: COINBASE HAS NO PAPER TRADING")
    print("   ⚠️  ALL ORDERS = REAL MONEY")
    print(f"   PID: {os.getpid()}")
    print("=" * 80)
    
    # Safety confirmation
    coinbase_live = os.getenv('COINBASE_LIVE', 'false').lower() == 'true'
    if coinbase_live:
        print("\n🔴 COINBASE_LIVE=true — REAL MONEY MODE")
        print("   Safety limits: $5-10 per trade, $50 daily loss")
    else:
        print("\n🟢 COINBASE_LIVE=false — Simulation mode")
    
    emulated_oco = os.getenv('COINBASE_EMULATED_OCO', 'false').lower() == 'true'
    if not emulated_oco:
        print("\n⚠️  OCO NOT SUPPORTED (broker will stay PAUSED)")
        print("   Coinbase has no native OCO/bracket orders")
        print("   Set COINBASE_EMULATED_OCO=true to enable (RISKY)")
    
    try:
        adapter = CoinbaseAdapter()
    except Exception as e:
        print(f"❌ FATAL: CoinbaseAdapter initialization failed: {e}")
        sys.exit(1)
    
    supervisor = BrokerSupervisor(broker_name='coinbase', connector=adapter, repo_root=REPO_ROOT)
    gates = BrokerGates(connector=adapter, broker_name='coinbase')
    
    pid_file = REPO_ROOT / 'ops' / 'state' / 'brokers' / 'coinbase.pid'
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    pid_file.write_text(str(os.getpid()))
    
    supervisor.start_heartbeat()
    print("✅ Heartbeat started")
    
    auto_arm = os.getenv('BROKER_COINBASE_AUTO_ARM', os.getenv('AUTO_ARM_ON_HEALTHY', '0')) == '1'
    if auto_arm:
        print("🤖 AUTO-ARM ENABLED")
    
    print("\n🔍 Initial gate checks...")
    all_passed, gate_results = gates.run_all_gates()
    for gate_name, result in gate_results.items():
        status = "✅" if result['passed'] else "❌"
        print(f"   {status} {gate_name}: {result.get('reason', 'OK')}")
    
    # Note: OCO_READINESS gate will FAIL if emulated OCO not enabled
    if not emulated_oco:
        print("\n❌ OCO_READINESS FAILED — Broker will stay PAUSED")
        print("   This is fail-closed behavior (safe by default)")
    
    if all_passed and auto_arm:
        supervisor.mark_active()
        print("\n✅ BROKER ACTIVE")
    else:
        print("\n⏸️  BROKER PAUSED")
    
    print("\n🔄 MAIN LOOP\n")
    poll_interval = int(os.getenv('COINBASE_POLL_INTERVAL', '30'))
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
            
            # TODO: Integrate strategy logic (if OCO ever enabled)
            
            if loop_count % 10 == 0:
                print(f"✅ Tick {loop_count}")
            
            time.sleep(poll_interval)
    
    except KeyboardInterrupt:
        print("\n🛑 Coinbase broker stopped")
    except Exception as e:
        logger.error(f"FATAL: {e}", exc_info=True)
        supervisor.mark_failed(str(e))
    finally:
        supervisor.stop()
        print("🏁 COINBASE SHUTDOWN")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    start_coinbase_broker()
