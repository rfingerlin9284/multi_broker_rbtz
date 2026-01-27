#!/usr/bin/env python3
"""
MULTI-AI BROWSER LAUNCHER
Starts browser workers for ChatGPT, Grok, and DeepSeek

This launches your REAL AI connections using browser automation.
"""
import subprocess
import time
import sys
from pathlib import Path

def start_chatgpt_worker():
    """Start ChatGPT browser worker."""
    print("🤖 Starting ChatGPT Browser Worker...")
    
    script_path = Path(__file__).parent / "hive_chatgpt_worker.py"
    
    # Start in background with proper environment
    process = subprocess.Popen([
        sys.executable, str(script_path)
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    time.sleep(3)  # Give it time to start
    
    if process.poll() is None:
        print("   ✅ ChatGPT worker started (PID:", process.pid, ")")
        return process
    else:
        print("   ❌ ChatGPT worker failed to start")
        stdout, stderr = process.communicate()
        print(f"   STDOUT: {stdout.decode()}")
        print(f"   STDERR: {stderr.decode()}")
        return None

def start_grok_worker():
    """Start Grok browser worker.""" 
    print("🤖 Grok Browser Worker...")
    print("   ⚠️  Not yet implemented - would connect to X.AI/Grok")
    return None

def start_deepseek_worker():
    """Start DeepSeek browser worker."""
    print("🤖 DeepSeek Browser Worker...")
    print("   ⚠️  Not yet implemented - would connect to DeepSeek")
    return None

def main():
    """Launch all AI workers."""
    print("🚀 LAUNCHING REAL AI HIVE WORKERS")
    print("=" * 50)
    
    workers = []
    
    # Start ChatGPT worker
    chatgpt_process = start_chatgpt_worker()
    if chatgpt_process:
        workers.append(("ChatGPT", chatgpt_process))
    
    # Start Grok worker (placeholder)
    grok_process = start_grok_worker()
    if grok_process:
        workers.append(("Grok", grok_process))
    
    # Start DeepSeek worker (placeholder)  
    deepseek_process = start_deepseek_worker()
    if deepseek_process:
        workers.append(("DeepSeek", deepseek_process))
    
    print("\n📋 WORKER STATUS:")
    for name, process in workers:
        if process.poll() is None:
            print(f"   ✅ {name}: Running (PID {process.pid})")
        else:
            print(f"   ❌ {name}: Stopped")
    
    if workers:
        print("\n🎯 AI Workers are running!")
        print("   💡 Use real_ai_hive.py to send analysis requests")
        print("   🛑 Press Ctrl+C to stop all workers")
        
        try:
            # Keep script alive
            while True:
                time.sleep(60)
                # Check if workers are still alive
                active_workers = [(name, p) for name, p in workers if p.poll() is None]
                if not active_workers:
                    print("⚠️  All workers stopped, exiting...")
                    break
                    
        except KeyboardInterrupt:
            print("\n🛑 Stopping all workers...")
            for name, process in workers:
                try:
                    process.terminate()
                    print(f"   Stopped {name}")
                except:
                    pass
    else:
        print("\n❌ No workers started successfully")
        print("   💡 Make sure Chrome is installed and WSL supports X11")
        sys.exit(1)

if __name__ == "__main__":
    main()