#!/usr/bin/env python3
"""
REAL AI HIVE LAUNCHER
Start your REAL AI connections and test them

This script will:
1. Launch browser workers for ChatGPT/Grok/DeepSeek
2. Test connections to your business accounts
3. Show you proof the AI is REAL
"""
import subprocess
import sys
import time
from pathlib import Path

def main():
    print("🚀 REAL AI HIVE LAUNCHER")
    print("=" * 50)
    print()
    print("This will connect to your REAL business accounts:")
    print("   ✅ ChatGPT Business Account")
    print("   ⚠️  Grok Account (coming soon)")
    print("   ⚠️  DeepSeek Account (coming soon)")
    print()
    
    choice = input("Launch REAL AI workers? (y/N): ").lower()
    if choice != 'y':
        print("Cancelled.")
        return
    
    hive_dir = Path(__file__).parent
    
    print("\n🤖 Starting AI workers...")
    
    # Launch AI workers
    print("1. Starting multi-AI launcher...")
    launcher_path = hive_dir / "launch_all_ais.py"
    
    if launcher_path.exists():
        subprocess.Popen([sys.executable, str(launcher_path)])
        print("   ✅ AI workers starting...")
        time.sleep(5)
    else:
        print("   ❌ Launcher script not found")
    
    print("\n🔍 Testing AI connections...")
    
    # Test connections
    test_script = hive_dir / "test_real_ai.py"
    if test_script.exists():
        print("2. Running connection tests...")
        result = subprocess.run([sys.executable, str(test_script)], 
                               capture_output=False, text=True)
        print(f"   Test completed with exit code: {result.returncode}")
    else:
        print("   ❌ Test script not found")
    
    print("\n🎯 NEXT STEPS:")
    print("   1. Check the test results above")
    print("   2. If ChatGPT worker started, browser should be open") 
    print("   3. Make sure you're logged into your business accounts")
    print("   4. Run your trading engine to use REAL AI")
    print()
    print("💡 To use in trading:")
    print("   python3 tools/run_headless.py --mode daily_target")
    print()
    print("🔧 Troubleshooting:")
    print("   - If no browser opens: WSL may need X11 forwarding")
    print("   - If 'Simple HIVE' appears: Real AI workers not connected")
    print("   - Check business account login status in browser")

if __name__ == "__main__":
    main()