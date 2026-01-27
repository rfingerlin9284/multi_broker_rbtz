#!/usr/bin/env python3
"""
BROWSER AI LAUNCHER FOR WSL
Launches Chrome on Windows host for ChatGPT interaction

This solves the WSL browser automation issue by:
1. Launching Chrome on Windows (not WSL)
2. Creating a bridge between WSL and Windows Chrome
3. Monitoring ChatGPT interactions in real browser
"""
import subprocess
import time
import json
import os
from pathlib import Path

def launch_windows_chrome():
    """Launch Chrome on Windows host with debugging enabled."""
    print("🌐 LAUNCHING CHROME ON WINDOWS HOST")
    print("=" * 40)
    
    # Create Windows batch file
    batch_content = '''@echo off
echo Launching Chrome for AI HIVE...
"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" ^
  --remote-debugging-port=9222 ^
  --user-data-dir=C:\\temp\\chrome_hive ^
  --disable-web-security ^
  --disable-features=VizDisplayCompositor ^
  "https://chatgpt.com/"
'''
    
    # Write batch file to Windows temp
    batch_path = "/mnt/c/temp/launch_ai_hive_chrome.bat"
    os.makedirs("/mnt/c/temp", exist_ok=True)
    
    with open(batch_path, "w") as f:
        f.write(batch_content)
    
    print(f"   📝 Created: {batch_path}")
    
    # Launch Chrome via Windows
    try:
        print("   🚀 Starting Chrome...")
        result = subprocess.Popen([
            'cmd.exe', '/c', 'C:\\temp\\launch_ai_hive_chrome.bat'
        ], cwd='/mnt/c')
        
        print("   ⏳ Waiting for Chrome to start...")
        time.sleep(5)
        
        # Check if Chrome is running
        check_result = subprocess.run([
            'cmd.exe', '/c', 'tasklist | findstr chrome.exe'
        ], capture_output=True, text=True, cwd='/mnt/c')
        
        if 'chrome.exe' in check_result.stdout:
            print("   ✅ Chrome started successfully!")
            print("   🔗 Remote debugging on port 9222")
            print("   🌐 ChatGPT should be opening...")
            return True
        else:
            print("   ❌ Chrome failed to start")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def create_ai_bridge():
    """Create communication bridge for AI interactions."""
    print("\n💬 SETTING UP AI COMMUNICATION BRIDGE")
    print("=" * 40)
    
    # Create queue directories
    hive_dir = Path(__file__).resolve().parent
    inbox_dir = hive_dir / "inbox"
    outbox_dir = hive_dir / "outbox"
    
    inbox_dir.mkdir(exist_ok=True)
    outbox_dir.mkdir(exist_ok=True)
    
    # Create queue files
    requests_file = inbox_dir / "hive_llm_requests.jsonl"
    responses_file = outbox_dir / "hive_llm_responses.jsonl"
    
    # Clear old requests
    if requests_file.exists():
        requests_file.unlink()
    if responses_file.exists():
        responses_file.unlink()
    
    requests_file.touch()
    responses_file.touch()
    
    print(f"   📥 Requests: {requests_file}")
    print(f"   📤 Responses: {responses_file}")
    print("   ✅ Communication bridge ready")
    
    return requests_file, responses_file

def test_ai_integration():
    """Test the AI integration with a sample request."""
    print("\n🧠 TESTING AI INTEGRATION")
    print("=" * 40)
    
    # Create test request
    test_request = {
        "id": "test_001",
        "prompt": """
TRADING ANALYSIS TEST

Symbol: EURUSD
Direction: BUY
Entry: 1.0985

Quick analysis: Is this a good entry point?
Respond with your trading thoughts.
""",
        "kind": "test",
        "timestamp": "2025-12-30T19:45:00"
    }
    
    # Write to queue
    requests_file, responses_file = create_ai_bridge()
    
    with open(requests_file, "w") as f:
        f.write(json.dumps(test_request) + "\n")
    
    print("   📝 Test request sent to ChatGPT queue")
    print("   💭 In the browser, you would now:")
    print("      1. See the prompt appear in ChatGPT")
    print("      2. Get AI analysis of the trade")
    print("      3. Response would appear in outbox")
    print("      4. Trading system would use that analysis")
    
    print("\n🎯 WHAT YOU'D SEE IN BROWSER:")
    print("   ┌─ ChatGPT Interface ─────────────────┐")
    print("   │ > TRADING ANALYSIS TEST              │")
    print("   │                                     │")
    print("   │ Symbol: EURUSD                      │")
    print("   │ Direction: BUY                      │")
    print("   │ Entry: 1.0985                       │")
    print("   │                                     │")
    print("   │ Quick analysis: Is this a good      │")
    print("   │ entry point?                        │")
    print("   │                                     │")
    print("   │ [ChatGPT would respond with real    │")
    print("   │  market analysis here...]           │")
    print("   └─────────────────────────────────────┘")

def show_browser_monitoring():
    """Show how to monitor the browser AI interactions."""
    print("\n👀 MONITORING AI INTERACTIONS")
    print("=" * 40)
    
    print("With browser automation, you can:")
    print("   ✅ WATCH ChatGPT analyze trades in real-time")
    print("   ✅ SEE the actual AI reasoning process")
    print("   ✅ VERIFY responses are from real AI")
    print("   ✅ INTERVENE if AI gets stuck")
    print("   ✅ MONITOR costs and usage")
    
    print("\nVS pure API calls:")
    print("   ❌ No visual feedback")
    print("   ❌ Can't see AI 'thinking'")
    print("   ❌ Harder to debug issues")
    print("   ✅ But faster and more reliable")
    
    print("\n🎯 BEST OF BOTH WORLDS (Hybrid):")
    print("   🌐 Browser for ChatGPT (visual monitoring)")
    print("   ⚡ API for Claude/DeepSeek (speed)")
    print("   🔄 Automatic fallback API->Browser->Demo")

def main():
    """Main launcher for browser-based AI."""
    import argparse
    import sys

    ap = argparse.ArgumentParser(description='Launch browser-based AI bridge')
    ap.add_argument('--yes', action='store_true', help='Run non-interactively (assume yes)')
    ap.add_argument('--no', action='store_true', help='Run non-interactively (assume no)')
    args = ap.parse_args()

    print("🚀 BROWSER AI HIVE LAUNCHER")
    print("=" * 50)
    
    print("This will set up browser-based AI interaction:")
    print("   1. Launch Chrome on Windows (avoids WSL issues)")
    print("   2. Open ChatGPT in browser")
    print("   3. Create communication bridge")
    print("   4. Enable visual AI monitoring")
    print()
    
    # Non-interactive safety: do not prompt (avoid EOFError) and default to cancel.
    if args.no:
        print("❌ Cancelled (--no)")
        return
    if args.yes:
        choice = 'y'
    else:
        if not sys.stdin.isatty():
            print("❌ Cancelled (non-interactive; pass --yes to run)")
            return
        try:
            choice = input("Launch browser AI system? (y/N): ").lower()
        except EOFError:
            print("❌ Cancelled (EOF on stdin; pass --yes to run)")
            return

    if choice != 'y':
        print("❌ Cancelled")
        return
    
    print()
    
    # Step 1: Launch Chrome
    if launch_windows_chrome():
        print("\n✅ Browser launched successfully!")
    else:
        print("\n❌ Browser launch failed")
        print("   💡 Try manually opening Chrome and going to chatgpt.com")
    
    # Step 2: Set up communication
    create_ai_bridge()
    
    # Step 3: Test integration
    test_ai_integration()
    
    # Step 4: Show monitoring
    show_browser_monitoring()
    
    print("\n🎯 NEXT STEPS:")
    print("1. Check if Chrome opened to ChatGPT")
    print("2. Log in to your business account")
    print("3. Run trading system to see AI analysis")
    print("4. Monitor browser for real AI responses")
    
    print("\n💡 COMMANDS:")
    print("   Start trading: python3 tools/run_headless.py --mode daily_target")
    print("   Test AI: python3 hive_real/hybrid_ai_hive.py")
    print("   Monitor: tail -f hive_real/inbox/hive_llm_requests.jsonl")

if __name__ == "__main__":
    main()