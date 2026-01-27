#!/usr/bin/env python3
"""
Autonomous Trading Launcher
Simplified wrapper for RICK Battlestation autonomous operation
"""
import sys
import os
import asyncio
from pathlib import Path

# Setup paths
workspace = Path(__file__).parent.parent
sys.path.insert(0, str(workspace))
sys.path.insert(0, str(workspace / "MULTI_BROKER_PHOENIX"))

from MULTI_BROKER_PHOENIX.multi_broker_phoenix.engines.rick_battlestation import RickBattlestation

async def main():
    """Launch autonomous battlestation"""
    print("=" * 80)
    print("🚀 AUTONOMOUS RICK BATTLESTATION - STARTING")
    print("=" * 80)
    print("Mode: FULLY AUTONOMOUS")
    print("Brokers: OANDA Practice + Coinbase Advanced")
    print("Scan Interval: 45 seconds")
    print("=" * 80)
    print()
    
    battlestation = RickBattlestation(pin=841921)
    await battlestation.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️  Shutting down gracefully...")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
