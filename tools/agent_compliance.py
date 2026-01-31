#!/usr/bin/env python3
"""
Agent compliance helpers: read HISTORICAL_CHANGE_LOG.md and report recent approvals.
Agents should call `check_historical_log()` at start of sensitive operations.
"""
from pathlib import Path

ROOT = Path(__file__).parent.parent
HISTORY = ROOT / 'HISTORICAL_CHANGE_LOG.md'


def read_history():
    if not HISTORY.exists():
        return []
    lines = HISTORY.read_text().splitlines()
    # return approval lines only
    return [l for l in lines if 'APPROVAL:' in l]


def check_historical_log():
    entries = read_history()
    if not entries:
        print('⚠️  HISTORICAL_CHANGE_LOG.md: no approvals recorded')
        return {'count': 0, 'last': None}
    last = entries[-1]
    return {'count': len(entries), 'last': last}


if __name__ == '__main__':
    print(check_historical_log())
