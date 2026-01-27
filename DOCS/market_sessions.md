# Market Sessions Configuration Guide

## Overview

The system now includes **timezone-aware market session tracking** for major global exchanges:

- 🇺🇸 **NEW_YORK** (NYSE/NASDAQ): 9:30 AM - 4:00 PM EST
- 🇬🇧 **LONDON** (LSE): 8:00 AM - 4:30 PM GMT
- 🇯🇵 **TOKYO** (TSE): 9:00 AM - 3:00 PM JST
- 🇦🇺 **SYDNEY** (ASX): 10:00 AM - 4:00 PM AEDT
- 🇭🇰 **HONG_KONG** (HKEX): 9:30 AM - 4:00 PM HKT
- 🌐 **CRYPTO_24H**: 24/7
- 💱 **FOREX_24H**: 24/5 (Mon-Fri)

---

## Configuration (.env)

```bash
# Enable session-aware trading
SESSION_AWARE_TRADING=true

# Which sessions to trade during (comma-separated)
PREFERRED_SESSIONS=NEW_YORK,LONDON,TOKYO

# Only trade during session overlaps (highest liquidity)
TRADE_DURING_OVERLAP_ONLY=false

# Disable trading during quiet hours
QUIET_HOURS_ENABLED=false
```

---

## Session Overlaps (Best Trading Times)

### 🔥 London-New York Overlap
- **Time**: 8:00 AM - 12:00 PM EST / 1:00 PM - 5:00 PM GMT
- **Duration**: ~4 hours
- **Volume**: Highest (40% of daily forex volume)
- **Best for**: EUR/USD, GBP/USD, Gold, Oil

### Tokyo-London Overlap
- **Time**: 3:00 AM - 4:00 AM EST
- **Duration**: ~1 hour
- **Best for**: JPY pairs, Asian stocks

### Sydney-Tokyo Overlap
- **Time**: 7:00 PM - 2:00 AM EST
- **Duration**: ~2 hours
- **Best for**: AUD pairs, Asian markets

---

## Usage in Code

### Check Active Sessions

```python
from multi_broker_phoenix.config.market_sessions import get_active_sessions

active = get_active_sessions()
print(f"Currently trading: {active}")
# Output: ['TOKYO', 'HONG_KONG', 'CRYPTO_24H']
```

### Check if Should Trade

```python
from multi_broker_phoenix.config.market_sessions import should_trade_now

should_trade, reason = should_trade_now('BTC-USD')
if should_trade:
    print(f"✓ TRADE: {reason}")
else:
    print(f"✗ WAIT: {reason}")
```

### Detect Overlaps

```python
from multi_broker_phoenix.config.market_sessions import is_session_overlap, get_current_overlap

if is_session_overlap():
    overlap = get_current_overlap()
    print(f"High liquidity period: {overlap['name']}")
    print(f"Optimal for: {overlap['optimal_for']}")
```

### Get Session Info

```python
from multi_broker_phoenix.config.market_sessions import format_session_status

print(format_session_status())
```

Output:
```
Current Time (UTC): 2025-12-29 04:39:33
Active Sessions: TOKYO, SYDNEY, HONG_KONG, CRYPTO_24H, FOREX_24H
Primary Session: TOKYO
Session Overlap: YES (High Liquidity)
```

---

## Integration with Strategies

### Example: Session-Aware Strategy

```python
from multi_broker_phoenix.config.market_sessions import get_primary_session, is_session_overlap

def generate_candidate(self, market_data):
    # Get current session
    session = get_primary_session()
    
    # Adjust strategy based on session
    if session == 'NEW_YORK':
        # US market hours - trade aggressively
        threshold = 0.6
    elif session == 'TOKYO':
        # Asian session - more conservative
        threshold = 0.75
    elif is_session_overlap():
        # High liquidity overlap - optimal trading
        threshold = 0.5
    else:
        # Off-hours - be very selective
        threshold = 0.9
    
    # Rest of strategy logic...
```

---

## Session-Specific Trading Rules

### New York Session (9:30 AM - 4:00 PM EST)
- ✅ US stocks (SPY, QQQ, AAPL, etc.)
- ✅ USD pairs (EUR/USD, GBP/USD)
- ✅ Gold, Oil, Commodities
- ⚠️ Highest volatility at open (9:30 AM) and close (4:00 PM)

### London Session (8:00 AM - 4:30 PM GMT)
- ✅ EUR, GBP pairs
- ✅ European stocks
- ✅ Best for forex (overlaps with NY)

### Tokyo Session (9:00 AM - 3:00 PM JST)
- ✅ JPY pairs (USD/JPY, EUR/JPY)
- ✅ Asian stocks
- ✅ AUD, NZD pairs
- ⚠️ Lower volume than London/NY

### Crypto (24/7)
- ✅ Always tradeable
- ⚠️ Higher volatility during NY/London hours
- ⚠️ Lower volume on weekends

---

## Best Practices

### DO:
- ✅ Trade during session overlaps (highest liquidity)
- ✅ Match instrument to appropriate session
- ✅ Increase position size during high-liquidity periods
- ✅ Use tighter stops during overlaps

### DON'T:
- ❌ Trade illiquid pairs outside their primary session
- ❌ Use same strategy parameters across all sessions
- ❌ Ignore session transitions (volatility spikes)
- ❌ Trade low-volume instruments during off-hours

---

## Testing

Run the test to see current session status:

```bash
cd MULTI_BROKER_PHOENIX
PYTHONPATH=$PWD python3 multi_broker_phoenix/config/market_sessions.py
```

---

## Advanced: Custom Sessions

Add custom sessions in `market_sessions.py`:

```python
SESSIONS['CUSTOM'] = MarketSession(
    name='CUSTOM',
    timezone='Your/Timezone',
    open_time=time(9, 0),
    close_time=time(17, 0),
    days=[0, 1, 2, 3, 4]  # Mon-Fri
)
```

---

## Current Status

✅ **Module Created**: `multi_broker_phoenix/config/market_sessions.py`  
✅ **Configuration Added**: `.env` and `.env.example`  
✅ **Tested**: Working correctly (detected Tokyo-Sydney overlap)  
✅ **Ready**: Can be integrated into strategies and headless runner

---

## Next Steps

1. **Integrate into headless runner** - Add session checks before trading
2. **Update strategies** - Make them session-aware
3. **Add session filters** - Block trades outside preferred sessions
4. **Performance tracking** - Monitor P&L by session
5. **Session-specific parameters** - Optimize per session

---

**Created**: December 29, 2025  
**Status**: Operational  
**Location**: `MULTI_BROKER_PHOENIX/multi_broker_phoenix/config/market_sessions.py`
