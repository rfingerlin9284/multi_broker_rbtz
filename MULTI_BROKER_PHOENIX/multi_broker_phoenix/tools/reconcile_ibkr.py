from __future__ import annotations
from typing import Dict, Any, List


def load_platform_trades(connector) -> List[Dict[str, Any]]:
    if connector is None:
        return []
    if hasattr(connector, 'get_trades'):
        try:
            return list(connector.get_trades()) or []
        except Exception:
            return []
    return []


def reconcile(platform_trades: List[Dict[str, Any]], ledger_trades: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    by_platform = {t.get('order_id') or t.get('id'): t for t in platform_trades}
    by_ledger = {t.get('id'): t for t in ledger_trades}

    matched = []
    only_platform = []
    only_ledger = []
    mismatched = []

    for oid, p in by_platform.items():
        l = by_ledger.get(oid)
        if l is None:
            only_platform.append(p)
            continue
        diffs = []
        for f in ('symbol', 'side', 'size', 'fill_price'):
            pv = p.get(f)
            lv = l.get(f)
            if pv is None and f == 'fill_price':
                fill = p.get('fill')
                if isinstance(fill, dict):
                    pv = fill.get('price') or fill.get('filled_price')
            if pv != lv:
                diffs.append({'field': f, 'platform': pv, 'ledger': lv})
        if diffs:
            mismatched.append({'id': oid, 'platform': p, 'ledger': l, 'diffs': diffs})
        else:
            matched.append({'id': oid, 'platform': p, 'ledger': l})

    for oid, l in by_ledger.items():
        if oid not in by_platform:
            only_ledger.append(l)

    return {
        'matched': matched,
        'only_platform': only_platform,
        'only_ledger': only_ledger,
        'mismatched': mismatched,
    }
