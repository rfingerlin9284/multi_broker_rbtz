#!/usr/bin/env python3
"""
IBKR TWS Connection Troubleshooting

Common issues:
1. API not enabled in TWS settings
2. Wrong port (4002 for paper, 4001 for live)
3. Socket connections not allowed
4. Firewall blocking connection
"""
import sys
import socket

def check_port(host, port):
    """Check if port is open."""
    print(f"🔍 Checking if port {port} is open on {host}...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            print(f"✅ Port {port} is OPEN and accepting connections")
            return True
        else:
            print(f"❌ Port {port} is CLOSED (error code: {result})")
            return False
    except Exception as e:
        print(f"❌ Error checking port: {e}")
        return False

def main():
    print("=" * 60)
    print("IBKR TWS/Gateway Connection Diagnostic")
    print("=" * 60)
    print()
    
    # Check both paper and live ports
    ports_to_check = [
        (4002, "Paper Trading"),
        (4001, "Live Trading"),
        (7496, "TWS Live (default)"),
        (7497, "TWS Paper (default)")
    ]
    
    for port, description in ports_to_check:
        print(f"\n{description} (Port {port}):")
        print("-" * 60)
        if check_port('127.0.0.1', port):
            print(f"   → This port is available for connection")
        else:
            print(f"   → This port is not accessible")
    
    print("\n" + "=" * 60)
    print("🔧 TROUBLESHOOTING STEPS:")
    print("=" * 60)
    print()
    print("If ports are CLOSED, check these settings in TWS:")
    print()
    print("1. Open TWS → File → Global Configuration → API → Settings")
    print("   ✓ Enable ActiveX and Socket Clients")
    print("   ✓ Socket port: 4002 (for paper)")
    print("   ✓ Master API client ID: 0 (or leave blank)")
    print()
    print("2. Check 'Allow connections from localhost only' (should be checked)")
    print()
    print("3. Click 'OK' and restart TWS if you made changes")
    print()
    print("4. Look for message in TWS: 'Waiting for socket connection...'")
    print()
    print("=" * 60)

if __name__ == '__main__':
    main()
