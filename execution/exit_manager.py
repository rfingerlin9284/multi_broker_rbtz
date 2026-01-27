"""Broker-verified exit manager.
Provides quick-cut and time-stop behavior.
"""
from __future__ import annotations
import time
import threading
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)
try:
    from global_config import FEATURE_FLAGS as _FF
except Exception:
    _FF = {}


def run_quick_cut_once(oanda_connector, cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    cfg = cfg or _FF.get('EXIT_MANAGER', {}).get('quick_cut', {})
    if not cfg.get('enabled', True):
        return {'handled': False, 'reason': 'disabled'}

    max_loss = float(cfg.get('max_loss_usd', 3.0))
    max_age = int(cfg.get('max_age_seconds', 60))

    try:
        client_cls = None
        try:
            from execution.oanda_practice_client import OandaPracticeClient as client_cls
        except Exception:
            client_cls = None
        client = None
        if client_cls:
            client = client_cls(token=oanda_connector.token, account_id=oanda_connector.account_id, base_url=oanda_connector.base_url, http_client=oanda_connector.http)
            if callable(client) and not hasattr(client, 'list_open_trades'):
                client = client()
    except Exception:
        logger.exception('EXIT_MANAGER: failed to init client')
        return {'handled': False, 'reason': 'client_init_failed'}

    if client is None:
        return {'handled': False, 'reason': 'client_missing'}

    actions = {'closed': [], 'skipped': []}
    try:
        trades = client.list_open_trades().get('trades', [])
        now = time.time()
        for t in trades:
            try:
                tid = t.get('tradeID') or t.get('id')
                entry_time = float(t.get('openTimeTs', t.get('openTimeTs', now))) if t.get('openTimeTs') else now
                age = now - entry_time
                pnl = float(t.get('unrealizedPL', 0.0) or 0.0)
                if age <= max_age and pnl <= -abs(max_loss):
                    # Attempt close
                    try:
                        inst = t.get('instrument')
                        client.close_position(inst)
                        actions['closed'].append(tid)
                        logger.info('EXIT_MANAGER: quick_cut closed %s (%s usd, age=%s)', tid, pnl, age)
                    except Exception:
                        logger.exception('EXIT_MANAGER: failed to close trade %s', tid)
                else:
                    actions['skipped'].append({'tradeID': tid, 'pnl': pnl, 'age': age})
            except Exception:
                logger.exception('EXIT_MANAGER: error processing trade')
    except Exception:
        logger.exception('EXIT_MANAGER: failed to list trades')

    return actions


def start_exit_worker(oanda_connector, cfg: Optional[Dict[str, Any]] = None):
    cfg = cfg or _FF.get('EXIT_MANAGER', {})
    interval = int(cfg.get('check_interval_sec', 30)) if cfg.get('check_interval_sec') else 30

    def _run():
        while True:
            try:
                run_quick_cut_once(oanda_connector, cfg.get('quick_cut', {}))
            except Exception:
                logger.exception('EXIT_MANAGER worker failed')
            time.sleep(interval)

    t = threading.Thread(target=_run, daemon=True, name='exit_manager')
    t.start()
    return t
