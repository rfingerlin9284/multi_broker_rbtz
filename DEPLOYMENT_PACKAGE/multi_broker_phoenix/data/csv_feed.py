"""CSV feed replayer that streams price ticks like a live feed."""
from __future__ import annotations
import csv
from datetime import datetime
import time
from typing import Iterator, Dict, Any, Optional


class CSVFeed:
    def __init__(self, csv_path: str, timestamp_col: str = 'timestamp', price_col: str = 'price', symbol: str = 'SYM'):
        self.csv_path = csv_path
        self.timestamp_col = timestamp_col
        self.price_col = price_col
        self.symbol = symbol

    def stream(self, delay: float = 0.0, speed: float = 1.0) -> Iterator[Dict[str, Any]]:
        """Yield dicts: {timestamp, symbol, price}

        delay: seconds between yields (0 = as-fast-as-possible)
        speed: >1 accelerates time sleep spacing using relative timestamp gaps
        """
        with open(self.csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            prev_ts: Optional[datetime] = None
            for row in reader:
                ts_raw = row.get(self.timestamp_col)
                price_raw = row.get(self.price_col)
                try:
                    ts = datetime.fromisoformat(ts_raw) if ts_raw else datetime.utcnow()
                except Exception:
                    # try common formats
                    ts = datetime.strptime(ts_raw, '%Y-%m-%d %H:%M:%S') if ts_raw else datetime.utcnow()
                price = float(price_raw)
                if prev_ts is not None and delay > 0:
                    gap = (ts - prev_ts).total_seconds()
                    sleep_time = gap / float(max(1.0, speed))
                    if sleep_time > 0:
                        time.sleep(sleep_time)
                prev_ts = ts
                yield {'timestamp': ts.isoformat(), 'symbol': self.symbol, 'price': price}
