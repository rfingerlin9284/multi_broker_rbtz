# 🎮 MULTI BROKER PHOENIX - Task Control Reference

## Tasks That Control the System

From your VS Code tasks (shown in screenshot):

### 🚀 MAIN CONTROL TASKS

1. **🚀 RICK BATTLESTATION: Launch** ✅ MAIN LAUNCHER
   - Starts entire Phoenix system
   - Launches HUD dashboard
   - Initializes all engines
   - **USE THIS TO START EVERYTHING**

2. **Run Headless (choose mode)** ✅ BACKGROUND TRADING
   - Runs Phoenix without UI
   - Choose trading mode on launch
   - Good for 24/7 autonomous operation
   - Located: `MULTI_BROKER_PHOENIX/tools/run_headless.py`

3. **🛑 RICK BATTLESTATION: Shutdown** ✅ SAFE SHUTDOWN
   - Gracefully stops all engines
   - Closes positions safely
   - Saves state
   - **USE THIS TO STOP EVERYTHING**

### 🤖 RBOTZILLA TASKS (Coinbase Integration)

4. **🟡 RBOTzilla: Start Coinbase Canary Mode**
   - Paper trading on Coinbase
   - Test mode before live

5. **📊 RBOTzilla: View Live Status**
   - Check what's running
   - Position status
   - P&L updates

6. **📅 RBOTzilla: Check Market Sessions**
   - See market hours
   - Session overlaps

7. **🔥 Coinbase Advanced: Start Engine**
   - Start live Coinbase trading
   - Real execution

8. **🚨 RBOTzilla: Emergency Stop**
   - KILLS ALL TRADING IMMEDIATELY
   - Use if something goes wrong
   - Closes all positions

### 🔄 ENGINE CONTROL

9. **Stop Trading Engine**
   - Stops trading but keeps system running
   - Positions stay open

10. **Echo User** / **Reset**
    - System utilities
    - Not trading related

## 🎯 For $400/Day Autonomous 24/7 Trading

### Option 1: Full Battlestation (With HUD)
```bash
# Click task: "RICK BATTLESTATION: Launch"
# Opens browser with live dashboard
# Runs 24/7 with monitoring
```

### Option 2: Headless Mode (No UI, Background)
```bash
# Click task: "Run Headless (choose mode)"
# Select: "daily_target_400"
# Runs in background, logs to file
```

### Option 3: Command Line
```bash
cd /home/ing/RICK/MULTI_BROKER_PHOENIX

# Start 24/7 $400/day mode
python3 MULTI_BROKER_PHOENIX/tools/run_headless.py \
    --mode daily_target_400 \
    --capital 5000 \
    --broker oanda

# Or use launcher
python3 MULTI_BROKER_PHOENIX/tools/launch_400_day_hunter.py 5000
```

## 🔥 What You Need to Do NOW

### Step 1: Get Real Research APIs
```bash
# Edit this file with your API keys:
nano MULTI_BROKER_PHOENIX/config/research_api_keys.json
```

Add:
```json
{
  "newsapi_key": "GET_FROM_NEWSAPI.ORG",
  "alphavantage_key": "GET_FROM_ALPHAVANTAGE.CO",
  "twitter_bearer_token": "OPTIONAL_BUT_RECOMMENDED"
}
```

Cost: **FREE for NewsAPI + Alpha Vantage**

### Step 2: Configure Your Broker
```bash
# For OANDA:
bash tools/validate_oanda.sh

# For IBKR:
bash tools/validate_ibkr.sh

# For Coinbase:
# Use RBOTzilla tasks above
```

### Step 3: Start 24/7 Trading
```bash
# Click: "Run Headless (choose mode)"
# Type: "daily_target_400"
# Done - system runs 24/7
```

## 📊 Monitoring 24/7 System

### Check Status
```bash
# View logs
tail -f /home/ing/RICK/MULTI_BROKER_PHOENIX/logs/phoenix.log

# Check positions
python3 -c "from multi_broker_phoenix.engines.real_trading_engine import *; show_status()"

# See daily P&L
# Click: "RBOTzilla: View Live Status"
```

### Emergency Stop
```bash
# Click: "RBOTzilla: Emergency Stop"
# Or Ctrl+C in terminal
# Or:
bash tools/stop_battlestation.sh
```

## 🤖 Systemd Service (Linux 24/7 Auto-Restart)

Want it to auto-restart if crashed? Create systemd service:

```bash
sudo nano /etc/systemd/system/rick-phoenix-400day.service
```

Add:
```ini
[Unit]
Description=RICK Phoenix $400/Day Trading Bot
After=network.target

[Service]
Type=simple
User=ing
WorkingDirectory=/home/ing/RICK/MULTI_BROKER_PHOENIX
ExecStart=/usr/bin/python3 /home/ing/RICK/MULTI_BROKER_PHOENIX/MULTI_BROKER_PHOENIX/tools/run_headless.py --mode daily_target_400 --capital 5000
Restart=always
RestartSec=10
StandardOutput=append:/home/ing/RICK/MULTI_BROKER_PHOENIX/logs/phoenix.log
StandardError=append:/home/ing/RICK/MULTI_BROKER_PHOENIX/logs/phoenix-error.log

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl daemon-reload
sudo systemctl enable rick-phoenix-400day
sudo systemctl start rick-phoenix-400day

# Check status
sudo systemctl status rick-phoenix-400day

# View logs
journalctl -u rick-phoenix-400day -f
```

Now it runs 24/7 and auto-restarts if it crashes!

## Summary

**Main Tasks You'll Use:**
1. ✅ **RICK BATTLESTATION: Launch** - Start with HUD
2. ✅ **Run Headless** - Start 24/7 background mode
3. ✅ **RBOTzilla: View Live Status** - Check progress
4. ✅ **RBOTzilla: Emergency Stop** - Kill everything

**For autonomous 24/7 $400/day:**
- Use **"Run Headless (choose mode)"** → "daily_target_400"
- Or set up systemd service for auto-restart
- Monitor via "View Live Status" task
