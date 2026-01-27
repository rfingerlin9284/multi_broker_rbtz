#!/usr/bin/env python3
"""
Quick test of position narrator - see the narration in action
"""
import sys
import os
import time
import logging

# Add parent to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'MULTI_BROKER_PHOENIX'))

from multi_broker_phoenix.foundation.position_narrator import LivePositionNarrator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[logging.StreamHandler()]
)

def demo_narrator():
    """Demonstrate the narrator in action."""
    narrator = LivePositionNarrator()
    
    print("\n🎬 LIVE POSITION NARRATOR DEMO\n")
    time.sleep(1)
    
    # Open a position
    narrator.narrate_new_position(
        ticket="CB-12345",
        symbol="BTC-USD",
        side="BUY",
        entry_price=95420.50,
        size=0.001,
        initial_sl=94920.50
    )
    
    time.sleep(2)
    
    # Simulate price moving up
    print("\n💹 Price moving up...\n")
    narrator.update_position_price("CB-12345", 95520.30, +10.25)
    time.sleep(1)
    
    # First trailing stop adjustment
    narrator.narrate_trailing_stop_update(
        ticket="CB-12345",
        new_sl=95020.50,
        reason="Price moved +100 points, trailing SL by 100"
    )
    
    time.sleep(2)
    
    # More price movement
    print("\n💹 Price continuing higher...\n")
    narrator.update_position_price("CB-12345", 95720.80, +30.45)
    time.sleep(1)
    
    # Second trailing stop adjustment
    narrator.narrate_trailing_stop_update(
        ticket="CB-12345",
        new_sl=95220.80,
        reason="Price moved another +200 points, SL trailing tighter"
    )
    
    time.sleep(2)
    
    # Open another position
    narrator.narrate_new_position(
        ticket="CB-67890",
        symbol="ETH-USD",
        side="SELL",
        entry_price=3420.75,
        size=0.01,
        initial_sl=3445.75
    )
    
    time.sleep(2)
    
    # Show all positions
    narrator.display_all_positions()
    
    time.sleep(2)
    
    # Update ETH position
    print("\n💹 ETH price moving in our favor...\n")
    narrator.update_position_price("CB-67890", 3405.30, +15.45)
    time.sleep(1)
    
    narrator.narrate_trailing_stop_update(
        ticket="CB-67890",
        new_sl=3430.30,
        reason="Trailing down with SELL position"
    )
    
    time.sleep(2)
    
    # Close BTC position (win)
    narrator.narrate_position_close(
        ticket="CB-12345",
        exit_price=95750.25,
        realized_pnl=32.98,
        reason="Take profit target hit"
    )
    
    time.sleep(2)
    
    # Show remaining positions
    narrator.display_all_positions()
    
    time.sleep(2)
    
    # Close ETH position (win)
    narrator.narrate_position_close(
        ticket="CB-67890",
        exit_price=3398.50,
        realized_pnl=22.25,
        reason="Manual close - securing profit"
    )
    
    time.sleep(1)
    
    # Show empty positions
    narrator.display_all_positions()
    
    print("\n✅ Demo complete! This is what you'll see in real-time.\n")

if __name__ == "__main__":
    demo_narrator()
