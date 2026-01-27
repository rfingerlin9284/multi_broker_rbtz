# Research Engine API Setup

## Required API Keys

Create this file: `MULTI_BROKER_PHOENIX/config/research_api_keys.json`

```json
{
  "newsapi_key": "YOUR_NEWSAPI_KEY_HERE",
  "alphavantage_key": "YOUR_ALPHAVANTAGE_KEY_HERE",
  "twitter_bearer_token": "YOUR_TWITTER_BEARER_TOKEN_HERE",
  "business_accounts": {
    "tradingview": {
      "username": "your_username",
      "password": "your_password"
    },
    "finviz": {
      "username": "your_username",
      "password": "your_password"  
    }
  }
}
```

## How to Get API Keys

### 1. NewsAPI.org (FREE)
- Go to: https://newsapi.org/register
- Sign up for free account
- Get your API key
- Free tier: 100 requests/day

### 2. Alpha Vantage (FREE)
- Go to: https://www.alphavantage.co/support/#api-key
- Sign up for free
- Get your API key  
- Free tier: 5 API requests/minute, 500/day

### 3. Twitter/X API (Paid ~$100/month)
- Go to: https://developer.twitter.com/
- Apply for developer account
- Create project and app
- Get Bearer Token
- Basic tier: $100/month for API access

### 4. Business Account Credentials
- TradingView Pro ($15/month)
- Finviz Elite ($40/month)
- Or use your existing accounts

## Environment Variables (Alternative)

Instead of JSON file, you can use environment variables:

```bash
export NEWSAPI_KEY="your_key_here"
export ALPHAVANTAGE_KEY="your_key_here"
export TWITTER_BEARER_TOKEN="your_token_here"
```

Add to `~/.bashrc` to make permanent.

## Security

**NEVER commit API keys to git!**

Add to `.gitignore`:
```
config/research_api_keys.json
**/api_keys.json
**/*_credentials.json
```

## Cost Breakdown

| Service | Cost | What It Provides |
|---------|------|------------------|
| NewsAPI | FREE | Real-time news articles |
| Alpha Vantage | FREE | Economic data, market data |
| Twitter API | $100/mo | Social sentiment, trending |
| TradingView | $15/mo | Charts, screeners |
| Finviz | $40/mo | Stock screener, heat maps |
| **Total** | **~$155/mo** | **Full research capabilities** |

**Worth it?** If you're targeting $400/day ($8k/month), spending $155/month for real data is 2% of revenue.

## Test Your Setup

```bash
cd /home/ing/RICK/MULTI_BROKER_PHOENIX
python3 MULTI_BROKER_PHOENIX/multi_broker_phoenix/engines/real_research_engine.py
```

Should show:
- ✅ News articles found
- ✅ Economic events found
- ✅ Sentiment calculated

## What HIVE Gets With This

### Oracle Agent (Deep Research)
- **REAL news** from NewsAPI
- **REAL economic calendar** from Alpha Vantage
- **REAL social sentiment** from Twitter
- Actual catalyst identification

### Prometheus Agent (Technical)
- Chart data from TradingView
- Real-time price feeds
- Volume analysis

### Hydra Agent (Flow Tracking)
- **REAL whale alerts** from exchange APIs
- Order book analysis
- Institutional positioning

### Sphinx Agent (Volatility)
- **REAL VIX data**
- ATR calculations on live data
- Regime classification

### Zeus Agent (Macro)
- **REAL Fed data**
- Economic indicators
- Risk-on/off metrics

Now HIVE makes decisions based on **REAL WORLD DATA**, not fake simulated research.
