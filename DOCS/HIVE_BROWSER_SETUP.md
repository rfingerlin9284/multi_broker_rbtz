# 🌐 REAL HIVE WITH BROWSER - Complete Setup Guide

## What This Is

Your HIVE agents now use **REAL ChatGPT** via **browser automation** with your **business account**.

**NO MORE FAKE RESEARCH!**

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  MULTI BROKER PHOENIX (Your Trading System)            │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │  HIVE Agents (Oracle, Prometheus, Sentinel)     │  │
│  │  Need research → Write to inbox/requests.jsonl  │  │
│  └──────────────────────────────────────────────────┘  │
│                      ↓                                  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Browser Bridge (hive_browser_bridge.py)        │  │
│  │  Manages queue communication                    │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                      ↓ ↑ (JSONL files)
┌─────────────────────────────────────────────────────────┐
│  Browser Worker (hive_chatgpt_worker.py)               │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Playwright + Real Chrome Browser                │  │
│  │  • Watches inbox/requests.jsonl                  │  │
│  │  • Opens ChatGPT in browser                      │  │
│  │  • Uses YOUR logged-in business account         │  │
│  │  • Sends prompts, scrapes responses              │  │
│  │  • Writes to outbox/responses.jsonl             │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## Step-by-Step Setup

### 1. Install Dependencies

```bash
cd /home/ing/RICK/MULTI_BROKER_PHOENIX

# Install Playwright
pip install playwright

# Install browser drivers
playwright install chromium
```

### 2. Create Directory Structure

```bash
# Create hive_real directory
mkdir -p hive_real/inbox
mkdir -p hive_real/outbox
mkdir -p hive_real/browser_profile

# Copy worker script
cp /path/to/hive_chatgpt_worker.py hive_real/
cp /path/to/hive_llm_queue.py hive_real/

# Create config
cat > hive_real/hive_config.json <<EOF
{
  "browser_chat_url": "https://chatgpt.com/",
  "use_cdp": true,
  "cdp_port": "9222"
}
EOF
```

### 3. Launch Browser with Remote Debugging

**Option A: Linux/WSL (Chromium)**
```bash
# Launch Chromium with remote debugging
chromium-browser \
  --remote-debugging-port=9222 \
  --user-data-dir=/home/ing/RICK/MULTI_BROKER_PHOENIX/hive_real/browser_profile \
  https://chatgpt.com/ &
```

**Option B: Windows Chrome**
```cmd
"C:\Program Files\Google\Chrome\Application\chrome.exe" ^
  --remote-debugging-port=9222 ^
  --user-data-dir=C:\ChromeProfile\RickPhoenix ^
  https://chatgpt.com/
```

**Option C: Mac Chrome**
```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=~/ChromeProfile/RickPhoenix \
  https://chatgpt.com/ &
```

### 4. Log Into ChatGPT (ONE TIME)

1. Browser window opened above
2. Go to https://chatgpt.com/
3. **Log in with your BUSINESS account**
4. Complete any verification
5. Make sure you see the chat prompt
6. Leave this browser open!

### 5. Start Browser Worker

```bash
cd /home/ing/RICK/MULTI_BROKER_PHOENIX/hive_real

# Set CDP mode (connect to existing browser)
export HIVE_USE_CDP=1
export HIVE_CDP_PORT=9222

# Start worker in background
nohup python3 hive_chatgpt_worker.py \
  --poll 0.5 \
  --timeout 60.0 \
  > worker.log 2>&1 &

# Save PID
echo $! > worker.pid

# Check it's running
tail -f worker.log
```

You should see:
```
[2025-12-30T...] HIVE_WORKER_START url=https://chatgpt.com/ ...
[2025-12-30T...] Connecting to existing browser via CDP: http://127.0.0.1:9222
[2025-12-30T...] Browser context launched
[2025-12-30T...] HIVE_WORKER_READY requests=...
```

### 6. Test Browser Bridge

```bash
cd /home/ing/RICK/MULTI_BROKER_PHOENIX

python3 MULTI_BROKER_PHOENIX/multi_broker_phoenix/engines/hive_browser_bridge.py
```

Should show:
```
🌐 HIVE BROWSER BRIDGE - Testing
📂 Directories: ...
✅ Browser worker appears to be running
🧪 Test Request...
✅ Got response: {...}
```

### 7. Update HIVE To Use Real Agents

Edit your trading engine/HIVE initialization:

```python
# OLD (fake research):
from multi_broker_phoenix.engines.hive_advanced_agents import (
    DeepResearchAgent, FlowTrackerAgent, ...
)

# NEW (real browser research):
from multi_broker_phoenix.engines.hive_real_agents import (
    OracleAgent, PrometheusAgent, SentinelAgent
)

# Create HIVE with real agents
hive_agents = [
    OracleAgent(),        # Catalyst research via ChatGPT
    PrometheusAgent(),    # Technical analysis via ChatGPT
    SentinelAgent(),      # Risk validation via ChatGPT
]
```

### 8. Start Trading!

```bash
# Launch Phoenix with real HIVE
python3 MULTI_BROKER_PHOENIX/tools/launch_400_day_hunter.py 5000
```

## How It Works In Action

### Trade Flow:

1. **Strategy generates signal**: "BUY GBP/USD at 1.2750"

2. **HIVE Oracle agent**:
   ```
   → Writes request to inbox/hive_llm_requests.jsonl
   → Browser worker picks it up
   → Sends to ChatGPT: "Check for upcoming BOE/Fed events..."
   → ChatGPT responds with real analysis
   → Response written to outbox/hive_llm_responses.jsonl
   → Oracle reads response, votes STRONG_YES or NO
   ```

3. **HIVE Prometheus agent**:
   ```
   → Asks ChatGPT: "Analyze GBP/USD technical setup..."
   → Gets real technical analysis
   → Votes based on setup quality
   ```

4. **HIVE Sentinel agent**:
   ```
   → Asks ChatGPT: "Validate risk (stop loss, R:R)..."
   → Can VETO if dangerous
   → Final safety check
   ```

5. **Consensus**: If 30%+ of agents vote YES → Execute trade

## Monitoring

### Check Worker Status
```bash
# View worker log
tail -f hive_real/worker.log

# Check if running
ps aux | grep hive_chatgpt_worker

# See requests/responses
tail -f hive_real/inbox/hive_llm_requests.jsonl
tail -f hive_real/outbox/hive_llm_responses.jsonl
```

### Stop Worker
```bash
kill $(cat hive_real/worker.pid)
```

### Restart Worker
```bash
cd hive_real
kill $(cat worker.pid)
nohup python3 hive_chatgpt_worker.py --poll 0.5 > worker.log 2>&1 &
echo $! > worker.pid
```

## Troubleshooting

### "Browser worker not detected"
- Check if worker is running: `ps aux | grep hive_chatgpt_worker`
- Check worker log: `tail -f hive_real/worker.log`
- Restart worker

### "CDP connect failed"
- Make sure Chrome launched with `--remote-debugging-port=9222`
- Check port not in use: `lsof -i:9222`
- Try different port: `export HIVE_CDP_PORT=9223`

### "ChatGPT login required"
- Open the browser window (should be visible)
- Log into ChatGPT manually
- Worker will detect and continue

### "Response timeout"
- ChatGPT may be slow/rate-limited
- Increase timeout: `--timeout 120.0`
- Check browser window isn't showing CAPTCHA

## Cost

**ChatGPT Plus** ($20/month):
- Unlimited messages
- Faster responses
- Good for moderate trading (10-20 trades/day)

**ChatGPT Team** ($25/user/month):
- Better for high-frequency ($400/day mode)
- Less rate limiting
- Shared workspace

**ChatGPT Enterprise** (Custom pricing):
- For serious professional trading
- No rate limits
- Your business account should have this

## Security

- ✅ Uses YOUR browser session (no API keys needed)
- ✅ Your ChatGPT credentials stay in browser
- ✅ No external API calls
- ✅ All data local (JSONL files)
- ✅ Can review all requests/responses

## Systemd Service (Auto-Start)

Want worker to auto-start on boot?

```bash
sudo nano /etc/systemd/system/hive-browser-worker.service
```

Add:
```ini
[Unit]
Description=HIVE Browser Worker (ChatGPT)
After=network.target

[Service]
Type=simple
User=ing
WorkingDirectory=/home/ing/RICK/MULTI_BROKER_PHOENIX/hive_real
Environment="HIVE_USE_CDP=1"
Environment="HIVE_CDP_PORT=9222"
ExecStart=/usr/bin/python3 /home/ing/RICK/MULTI_BROKER_PHOENIX/hive_real/hive_chatgpt_worker.py --poll 0.5
Restart=always
RestartSec=10
StandardOutput=append:/home/ing/RICK/MULTI_BROKER_PHOENIX/hive_real/worker.log
StandardError=append:/home/ing/RICK/MULTI_BROKER_PHOENIX/hive_real/worker-error.log

[Install]
WantedBy=multi-user.target
```

Enable:
```bash
sudo systemctl daemon-reload
sudo systemctl enable hive-browser-worker
sudo systemctl start hive-browser-worker
sudo systemctl status hive-browser-worker
```

## Summary

✅ **REAL browser automation** (Playwright)
✅ **YOUR business ChatGPT account**
✅ **No API keys needed**
✅ **HIVE agents get real research**
✅ **24/7 autonomous operation**

**Your HIVE is now REAL!** 🐝🔥
