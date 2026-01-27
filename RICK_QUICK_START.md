# 🚀 RICK QUICK START GUIDE

## The Problem You Had
- Browser opened but showed **blank white page** at http://127.0.0.1:8080
- **Why?** The Flask web server wasn't running (only the browser opened)
- Too many confusing scripts - didn't know which one to use

## The Solution: ONE MASTER SCRIPT

```bash
./RICK_START.sh full
```

**That's it!** This ONE command:
1. ✅ Starts the Flask web server (fixes blank page)
2. ✅ Opens Chrome with AI agents
3. ✅ Starts autonomous trading engine
4. ✅ Opens http://127.0.0.1:8080 working dashboard

---

## Quick Commands

| Command | What It Does |
|---------|-------------|
| `./RICK_START.sh` | Interactive menu (choose what to run) |
| `./RICK_START.sh full` | **Start EVERYTHING** (recommended) |
| `./RICK_START.sh web` | Just web server (fixes blank page) |
| `./RICK_START.sh engine` | Just trading engine |
| `./RICK_START.sh stop` | Stop all services |
| `./RICK_START.sh explain` | See detailed info about all scripts |

---

## What Each Component Does

### 🌐 Web UI (`web`)
- **Starts:** Flask server on port 8080
- **Why needed:** Without this, browser shows blank page
- **URL:** http://127.0.0.1:8080
- **Shows:** Trades, P&L, AI decisions, live charts

### 🤖 Browser (`browser`)
- **Starts:** Chrome with ChatGPT.com
- **Why needed:** AI agents query ChatGPT via browser automation
- **Bonus:** You can watch AI making decisions in real-time

### 📈 Engine (`engine`)
- **Starts:** Autonomous trading engine
- **Mode:** PAPER (no real money) by default
- **Features:**
  - 10x leverage on win streaks
  - 100% compounding
  - AI-filtered universe
  - Session-aware risk

---

## First Time Setup

1. Open terminal in project folder
2. Run the master script:
   ```bash
   cd /home/ing/RICK/MULTI_BROKER_PHOENIX
   ./RICK_START.sh full
   ```
3. Wait 10 seconds for everything to start
4. Open browser: http://127.0.0.1:8080
5. Watch the AI trade autonomously!

---

## Troubleshooting

**Q: Still seeing blank page?**
```bash
# Stop everything and restart
./RICK_START.sh stop
sleep 2
./RICK_START.sh full
```

**Q: Port 8080 already in use?**
```bash
# Kill whatever is using it
pkill -f "hive_web_interface"
lsof -ti:8080 | xargs kill -9
./RICK_START.sh web
```

**Q: Engine not trading?**
- Check if AI confidence is too low (needs 60%+ signals)
- Ensure API keys set in .env (OPENAI_API_KEY, XAI_API_KEY)
- Run `./RICK_START.sh explain` to verify setup

---

## Other Scripts (You Can Ignore These Now)

| Old Script | What It Did | Use Instead |
|------------|-------------|-------------|
| `tools/start_battlestation.sh` | Old launcher | `./RICK_START.sh full` |
| `tools/start_hive_browser.sh` | Just browser | `./RICK_START.sh browser` |
| `tools/launch_hive_browser*.sh` | Browser variants | `./RICK_START.sh browser` |
| `hive_dashboard/start-*.sh` | Dashboard attempts | `./RICK_START.sh web` |

**Keep them?** Yes, for advanced users. But YOU don't need them.

---

## Advanced: Running Components Separately

**Web UI only** (if you just need dashboard):
```bash
./RICK_START.sh web
# Open http://127.0.0.1:8080
```

**Engine only** (if UI already running):
```bash
./RICK_START.sh engine
```

**Stop everything**:
```bash
./RICK_START.sh stop
```

---

## Live Trading (Real Money) 💰

**NOT RECOMMENDED YET** - test in paper mode first!

When ready:
```bash
cd hive_real
python3 autonomous_trading_engine.py --mode live
# Type 'YES' to confirm
```

---

## Need Help?

```bash
./RICK_START.sh explain  # Shows detailed task info
./RICK_START.sh          # Interactive menu
```

**Bottom line:** Just use `./RICK_START.sh full` and you're done! 🚀
