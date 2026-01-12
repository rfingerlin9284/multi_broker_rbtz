
class FVGWolf:
    def __init__(self):
        self.name = "FVGWolf"

    def get_signal(self, df):
        # Simplified FVG Detection
        # Bearish FVG: Low[0] > High[2]
        # Bullish FVG: High[0] < Low[2]
        
        if len(df) < 3:
            return "NEUTRAL", 0.0

        last_candle = df.iloc[-1]
        prev_candle = df.iloc[-2]
        third_candle = df.iloc[-3]
        
        confidence = 0.0
        signal = "NEUTRAL"
        
        # Detect Bullish FVG (Gap Up support)
        if last_candle['low'] > third_candle['high']:
            confidence = 0.75
            signal = "BUY"
            
        # Detect Bearish FVG (Gap Down resistance)
        if last_candle['high'] < third_candle['low']:
            confidence = 0.75
            signal = "SELL"
            
        return signal, confidence
