import csv
from pathlib import Path
from multi_broker_phoenix.data.csv_feed import CSVFeed


def test_csv_feed_streams(tmp_path: Path):
    p = tmp_path / 'feed.csv'
    with p.open('w', encoding='utf-8') as f:
        f.write('timestamp,price\n')
        f.write('2025-01-01T00:00:00,1.0\n')
        f.write('2025-01-01T00:00:01,1.001\n')
        f.write('2025-01-01T00:00:02,1.002\n')
    feed = CSVFeed(str(p), price_col='price')
    items = list(feed.stream(delay=0.0))
    assert len(items) == 3
    assert items[0]['price'] == 1.0
    assert items[-1]['price'] == 1.002
