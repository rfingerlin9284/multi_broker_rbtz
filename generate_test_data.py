#!/usr/bin/env python3
"""Generate test price data for backtesting."""
import pandas as pd
import numpy as np

# Generate 500 candles of realistic EUR_USD data
np.random.seed(42)
n = 500
base_price = 1.1000

# Generate price movement with trend and noise
trend = np.linspace(0, 0.01, n)  # Slight uptrend
noise = np.cumsum(np.random.randn(n) * 0.0005)
close_prices = base_price + trend + noise

# Generate OHLC
high = close_prices + np.abs(np.random.randn(n) * 0.0002)
low = close_prices - np.abs(np.random.randn(n) * 0.0002)
open_prices = close_prices + np.random.randn(n) * 0.0001
volume = np.random.randint(1000, 10000, n)

df = pd.DataFrame({
    'timestamp': pd.date_range('2025-01-01', periods=n, freq='5min'),
    'open': open_prices,
    'high': high,
    'low': low,
    'close': close_prices,
    'volume': volume
})

output_file = '/tmp/demo_zones_500candles.csv'
df.to_csv(output_file, index=False)
print(f"Generated {len(df)} candles")
print(f"Saved to: {output_file}")
print(f"Price range: {df['close'].min():.5f} - {df['close'].max():.5f}")
