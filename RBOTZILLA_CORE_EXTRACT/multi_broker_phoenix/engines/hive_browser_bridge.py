"""
HIVE Browser Bridge - Connects HIVE agents to real ChatGPT browser worker

This bridges the gap between HIVE's voting system and the real browser automation.
Instead of fake research, HIVE agents now get REAL responses from ChatGPT via
the browser worker (hive_chatgpt_worker.py).

Flow:
1. HIVE agent needs research
2. Write request to inbox/hive_llm_requests.jsonl
3. Browser worker (running in background) picks it up
4. Worker sends to ChatGPT in real browser
5. Response written to outbox/hive_llm_responses.jsonl
6. HIVE agent reads response and votes
"""

import json
import time
import uuid
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timezone


class HiveBrowserBridge:
    """Bridge between HIVE agents and real ChatGPT browser worker"""
    
    def __init__(self, base_dir: Optional[Path] = None):
        """Initialize bridge
        
        Args:
            base_dir: Directory containing inbox/outbox folders
                     Defaults to MULTI_BROKER_PHOENIX/hive_real/
        """
        if base_dir is None:
            # Default to project hive_real directory
            project_root = Path(__file__).resolve().parent.parent.parent
            base_dir = project_root / "hive_real"
        
        self.base_dir = Path(base_dir)
        self.inbox_dir = self.base_dir / "inbox"
        self.outbox_dir = self.base_dir / "outbox"
        
        # Create directories if they don't exist
        self.inbox_dir.mkdir(parents=True, exist_ok=True)
        self.outbox_dir.mkdir(parents=True, exist_ok=True)
        
        self.requests_path = self.inbox_dir / "hive_llm_requests.jsonl"
        self.responses_path = self.outbox_dir / "hive_llm_responses.jsonl"
        
        # Ensure files exist
        self.requests_path.touch(exist_ok=True)
        self.responses_path.touch(exist_ok=True)
    
    def request_research(self, 
                        agent_name: str,
                        symbol: str,
                        direction: str,
                        entry_price: float,
                        context: Dict[str, Any],
                        custom_prompt: Optional[str] = None,
                        timeout: float = 60.0) -> Optional[Dict[str, Any]]:
        """Request research from browser worker and wait for response
        
        Args:
            agent_name: Name of HIVE agent making request
            symbol: Trading symbol (e.g., "GBP/USD")
            direction: "BUY" or "SELL"
            entry_price: Entry price for trade
            context: Additional context (timeframe, strategy, etc.)
            custom_prompt: Custom prompt (if None, uses default)
            timeout: Max seconds to wait for response
            
        Returns:
            Parsed response from ChatGPT or None if timeout/error
        """
        request_id = str(uuid.uuid4())
        
        # Build request
        request = {
            "id": request_id,
            "ts": datetime.now(timezone.utc).isoformat(),
            "agent": agent_name,
            "kind": "trade_analysis",
            "payload": {
                "symbol": symbol,
                "direction": direction,
                "entry_price": entry_price,
                "timeframe": context.get("timeframe", "M15"),
                "strategy": context.get("strategy", "unknown"),
                "current_price": entry_price,
                **context
            }
        }
        
        if custom_prompt:
            request["prompt"] = custom_prompt
        
        # Write request to inbox (browser worker will pick it up)
        with open(self.requests_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(request) + "\n")
        
        # Wait for response
        deadline = time.time() + timeout
        while time.time() < deadline:
            response = self._check_response(request_id)
            if response is not None:
                return response
            time.sleep(0.5)  # Poll every 500ms
        
        # Timeout
        return None
    
    def _check_response(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Check if response exists for given request ID"""
        try:
            with open(self.responses_path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        resp = json.loads(line.strip())
                        if resp.get("id") == request_id:
                            if resp.get("ok"):
                                return resp.get("parsed") or {"raw": resp.get("raw_text")}
                            else:
                                return {"error": resp.get("error")}
                    except:
                        continue
        except FileNotFoundError:
            pass
        return None
    
    def is_worker_running(self) -> bool:
        """Check if browser worker is running (heuristic)
        
        Returns:
            True if worker appears to be running
        """
        # Check if responses were written recently (last 60 seconds)
        try:
            mtime = self.responses_path.stat().st_mtime
            age = time.time() - mtime
            return age < 60.0
        except:
            return False


# Factory function
def create_browser_bridge(base_dir: Optional[Path] = None) -> HiveBrowserBridge:
    """Create bridge to browser worker"""
    return HiveBrowserBridge(base_dir)


if __name__ == "__main__":
    print("=" * 70)
    print("🌐 HIVE BROWSER BRIDGE - Testing")
    print("=" * 70)
    
    bridge = create_browser_bridge()
    
    print(f"\n📂 Directories:")
    print(f"   Base: {bridge.base_dir}")
    print(f"   Inbox: {bridge.inbox_dir}")
    print(f"   Outbox: {bridge.outbox_dir}")
    
    print(f"\n📝 Files:")
    print(f"   Requests: {bridge.requests_path}")
    print(f"   Responses: {bridge.responses_path}")
    
    print(f"\n🔍 Worker Status:")
    running = bridge.is_worker_running()
    if running:
        print("   ✅ Browser worker appears to be running")
    else:
        print("   ⚠️  Browser worker not detected")
        print("   Start with: python3 hive_real/hive_chatgpt_worker.py")
    
    print("\n🧪 Test Request (will timeout if worker not running):")
    print("   Sending test trade analysis request...")
    
    response = bridge.request_research(
        agent_name="TestAgent",
        symbol="GBP/USD",
        direction="BUY",
        entry_price=1.2750,
        context={"timeframe": "M15", "strategy": "test"},
        timeout=10.0  # Short timeout for test
    )
    
    if response:
        print(f"   ✅ Got response: {response}")
    else:
        print("   ⏱️  Timeout (worker probably not running)")
    
    print("\n" + "=" * 70)
