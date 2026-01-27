#!/usr/bin/env python3
"""Reconcile IBKR platform orders with local paper ledger.

Usage:
  tools/reconcile_ibkr.py --report [--output report.json]

By default the script runs in report-only mode and prints a summary to stdout.
It will exit with code 0 if no discrepancies are found, or 2 if there are mismatches.
"""
from __future__ import annotations
import argparse
import json
import sys
from typing import Dict, Any, List

from multi_broker_phoenix.engines.paper_engine import PaperEngine


def load_platform_trades(connector) -> List[Dict[str, Any]]:
    """Attempt to fetch recent trades from the IBKR connector.
    The connector may implement `get_trades()` returning a list of platform trade dicts.
    """
    if connector is None:
        return []
    if hasattr(connector, 'get_trades'):
        try:
            return list(connector.get_trades()) or []
        except Exception:
            # fail-safe: return empty list and let reconciliation report platform empty
            return []
    return []


def reconcile(platform_trades: List[Dict[str, Any]], ledger_trades: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    by_platform = {t.get('order_id') or t.get('id'): t for t in platform_trades}
    by_ledger = {t.get('id'): t for t in ledger_trades}

    matched = []
    only_platform = []
    only_ledger = []
    mismatched = []

    # Orders present on platform
    for oid, p in by_platform.items():
        l = by_ledger.get(oid)
        if l is None:
            only_platform.append(p)
            continue
        # compare key fields
        diffs = []
        for f in ('symbol', 'side', 'size', 'fill_price'):
            pv = p.get(f)
            lv = l.get(f)
            if pv is None and f == 'fill_price':
                # platform may have 'fill' nested -> try to extract
                fill = p.get('fill')
                if isinstance(fill, dict):
                    pv = fill.get('price') or fill.get('filled_price')
            if pv != lv:
                diffs.append({'field': f, 'platform': pv, 'ledger': lv})
        if diffs:
            mismatched.append({'id': oid, 'platform': p, 'ledger': l, 'diffs': diffs})
        else:
            matched.append({'id': oid, 'platform': p, 'ledger': l})

    # Orders present on ledger but missing on platform
    for oid, l in by_ledger.items():
        if oid not in by_platform:
            only_ledger.append(l)

    return {
        'matched': matched,
        'only_platform': only_platform,
        'only_ledger': only_ledger,
        'mismatched': mismatched,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--db', default='data/paper_ledger.sqlite', help='Path to paper ledger DB')
    p.add_argument('--report', action='store_true', default=True)
    p.add_argument('--output', default=None)
    args = p.parse_args()

    engine = PaperEngine(db_path=args.db)
    # Attempt to import IBKR connector and instantiate
    platform_trades = []
    try:
        from ibkr_gateway.ibkr_connector import get_ibkr_connector
        ib = get_ibkr_connector()
        platform_trades = load_platform_trades(ib)
    except Exception:
        ib = None
        platform_trades = []

    ledger_trades = engine.list_trades()

    # Use library reconcile implementation
    from multi_broker_phoenix.tools.reconcile_ibkr import reconcile as reconcile_lib
    report = reconcile_lib(platform_trades, ledger_trades)

    summary = {
        'matched': len(report['matched']),
        'only_platform': len(report['only_platform']),
        'only_ledger': len(report['only_ledger']),
        'mismatched': len(report['mismatched']),
    }

    print(json.dumps({'summary': summary}, indent=2))

    if args.output:
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2)

    # Return non-zero if any discrepancies found
    if summary['only_platform'] or summary['only_ledger'] or summary['mismatched']:
        print('Discrepancies found. Please review report.')
        # Attempt to notify operators if enabled
        try:
            from tools.notify import notify_reconcile
            msg = f"Reconcile found discrepancies: {json.dumps(summary)}"
            notified = notify_reconcile(msg)
            print('Notified:', notified)
        except Exception:
            print('Notification attempt failed')
        sys.exit(2)
    print('No discrepancies found.')
    sys.exit(0)


if __name__ == '__main__':
    main()
