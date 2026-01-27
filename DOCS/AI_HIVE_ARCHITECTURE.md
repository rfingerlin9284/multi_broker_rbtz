# AI Hive Architecture - System/User Message Separation

## Problem Statement

The original AI Hive implementation repeated role instructions and output format requirements in every single API call, mixing them with market data. This caused:

1. **"Need_input" loops** - Models correctly refused to analyze without actual market data
2. **Token waste** - Repeating the same instructions 20+ times instead of using system messages
3. **Poor separation of concerns** - Role definitions mixed with trading data
4. **Limited context** - Only basic prices provided, no timeframe/objective/risk rules

## Solution: System/User Message Architecture

### Two-Message Pattern

**System Message (Static):**
- Agent role definition (Oracle/Tactician/Analyst)
- Output format requirements (STRICT JSON schema)
- Core rules (VETO authority, analytical focus)
- Sent once, applies to entire conversation context

**User Message (Dynamic):**
- Specific trade to analyze RIGHT NOW
- Comprehensive market data (price, high/low, momentum, volatility)
- Trading parameters (timeframe, objective, risk rules)
- Changes with every trade analysis

### Think of it Like a Deli

**System Message = "You are a sandwich maker. Always wrap in paper. Always label the order."**

**User Message = "Turkey on rye, mustard, no tomato."**

You don't keep yelling "Always wrap in paper!" every time. You say it once, then focus on the actual order.

## New API Interface

### Before (Insufficient Context)
```python
result = get_api_ai_vote(
    symbol="EURUSD",
    direction="BUY", 
    entry_price=1.0950,
    market_data={"prices": [1.0940, 1.0945, 1.0950]}  # Too minimal
)
```

### After (Comprehensive Context)
```python
result = get_api_ai_vote(
    symbol="EURUSD",
    direction="BUY",
    entry_price=1.0950,
    market_data={
        "prices": [...],     # Last 50 closes
        "high": 1.0980,      # 24h high
        "low": 1.0920,       # 24h low
        "candles": [...]     # Optional OHLC
    },
    timeframe="1h",          # NEW: Chart timeframe
    objective="day",         # NEW: Scalp/day/swing
    risk_rules={             # NEW: Risk parameters
        "max_loss_pct": 0.5,
        "max_daily_loss_pct": 2.0,
        "leverage_cap": 2.0,
        "oco_required": True
    }
)
```

## What Each Agent Now Receives

### Oracle Agent (Fundamental/Sentiment)
```
ANALYZE THIS TRADE:

INSTRUMENT: EURUSD
TIMEFRAME: 1h
OBJECTIVE: day trade

CURRENT MARKET:
- Current Price: 1.0950
- 24h High: 1.0980
- 24h Low: 1.0920
- Recent Price Action: [1.0940, 1.0942, 1.0945, 1.0948, 1.0950]

PROPOSED TRADE:
- Direction: BUY
- Entry: 1.0950

RISK RULES:
- Max Loss Per Trade: 0.5%
- Max Daily Loss: 2.0%
- Leverage Cap: 2.0x
- OCO Required: true

Evaluate from fundamental and sentiment perspective...
```

### Tactician Agent (Technical Analysis)
```
ANALYZE THIS TRADE:

INSTRUMENT: EURUSD
TIMEFRAME: 1h
OBJECTIVE: day trade

CURRENT MARKET:
- Current Price: 1.0950
- 24h High: 1.0980
- 24h Low: 1.0920
- Range Position: 50.0% (0=low, 100=high)
- Recent Momentum: +0.15% over last 20 bars
- Recent Closes: [1.0940, 1.0942, 1.0945, 1.0948, 1.0950]

PROPOSED TRADE:
- Direction: BUY
- Entry: 1.0950

RISK RULES:
- Max Loss Per Trade: 0.5%
- Max Daily Loss: 2.0%
- Leverage Cap: 2.0x
- OCO Required: true

Evaluate from technical analysis perspective...
```

### Analyst Agent (Quantitative/Statistical)
```
ANALYZE THIS TRADE:

INSTRUMENT: EURUSD
TIMEFRAME: 1h
OBJECTIVE: day trade

CURRENT MARKET:
- Current Price: 1.0950
- 24h High: 1.0980
- 24h Low: 1.0920
- Volatility: 1.23%
- Recent Price Series: [1.0935, 1.0938, 1.0940, 1.0942, 1.0945, 1.0948, 1.0950]

PROPOSED TRADE:
- Direction: BUY
- Entry: 1.0950

RISK RULES:
- Max Loss Per Trade: 0.5%
- Max Daily Loss: 2.0%
- Leverage Cap: 2.0x
- OCO Required: true

Evaluate from quantitative and statistical perspective...
```

## Key Architectural Principles

### 1. Static Role, Dynamic Data
- **Role definitions don't change** → System message
- **Market data changes constantly** → User message
- Don't repeat yourself (DRY principle applied to prompts)

### 2. Comprehensive Market Context
Each analysis needs minimum:
- Instrument + timeframe
- Current price + recent range
- Recent price action (at least 10-20 bars)
- Trading objective (scalp/day/swing)
- Risk rules (max loss, leverage, OCO)

### 3. Human Inputs ≠ JSON
- **Humans** interact with UI (dropdowns, text boxes)
- **Software** converts to structured data
- **Models** output JSON for parsing
- **UI** renders JSON back to human-readable format

### 4. Trust the "Need_Input" Response
When a model says "need_input", it's being **honest**:
- It can't hallucinate trade plans from thin air
- It needs actual data to analyze
- This is GOOD behavior (disciplined, not lazy)

## Integration Points

### From Price Feeds
```python
# Your feed should provide:
market_data = {
    "prices": last_50_closes,
    "high": session_high,
    "low": session_low,
    "candles": ohlc_data  # if available
}
```

### From Strategy Layer
```python
# Your strategy provides:
timeframe = "1h"           # From strategy config
objective = "day"          # From strategy type
direction = "BUY"          # From signal
entry_price = current_ask  # From order book
```

### From Risk Manager
```python
# Your risk manager provides:
risk_rules = {
    "max_loss_pct": 0.5,
    "max_daily_loss_pct": 2.0,
    "leverage_cap": 2.0,
    "oco_required": True
}
```

## Response Format (Unchanged)

Models still return strict JSON:
```json
{
    "signal": "buy|sell|neutral|veto",
    "confidence": 0.0-1.0,
    "reasoning": "1-2 sentence analysis"
}
```

Your system aggregates votes into consensus:
```json
{
    "vote": "approve|reject|veto",
    "confidence": 0.75,
    "consensus": 0.67,
    "buy_consensus": 0.67,
    "sell_consensus": 0.0,
    "reasoning": "AI Consensus: 67%, Confidence: 75%",
    "votes": [...]
}
```

## Migration Path

### Phase 1: Update API Calls (Done ✅)
- Separated system/user messages
- Added timeframe, objective, risk_rules parameters
- Enhanced market data with high/low/momentum/volatility
- Better JSON parsing with markdown code block handling

### Phase 2: Update Callers (Next)
- Modify strategy layer to provide timeframe + objective
- Update price feeds to include high/low + more candles
- Connect risk manager to provide risk_rules
- Test with real market data

### Phase 3: UI Integration (Future)
- Build input form: symbol search + timeframe dropdown
- Add autofill for current price/high/low
- Risk rule checkboxes (OCO, leverage slider)
- Render JSON responses as readable panels

## Expected Improvements

### Before (Minimal Context)
- 40% "need_input" responses
- Generic reasoning
- Token waste on repeated instructions
- No timeframe/objective awareness

### After (Comprehensive Context)
- 5-10% "need_input" (only when data truly insufficient)
- Specific, actionable analysis
- Efficient token usage (system message cached)
- Context-aware recommendations (scalp vs swing)

## Testing Checklist

Test each agent with:
- [x] Basic forex pair (EURUSD)
- [ ] Crypto pair (BTCUSD)
- [ ] Different timeframes (5m, 1h, 4h, 1D)
- [ ] Different objectives (scalp, day, swing)
- [ ] Various risk rules
- [ ] Edge cases (low volatility, range-bound, trending)

## Notes

- **Grok model name**: Changed from `grok-2-latest` to `grok-beta` (404 error on latest)
- **OpenAI model**: Using `gpt-4` (works, tested)
- **DeepSeek**: Ready but needs funded account
- **Markdown handling**: Added code block stripping (```json...```)
- **Fallback parsing**: Still works if JSON fails (parses plain text)

---

**Bottom Line:** We fixed the "prayer wheel" problem. The system now has a stable role definition (said once) and dynamic market data (provided fresh each time). No more repeating the same instructions endlessly. The models now get actual context to analyze instead of being asked to conjure trade plans from nothing.
