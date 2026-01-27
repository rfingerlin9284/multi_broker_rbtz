"""Self-heal and scaling ladder checks executed periodically and at boot."""
from __future__ import annotations
import time
import json
from pathlib import Path
from typing import Dict, Any
import logging
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
OPS = ROOT / 'ops' / 'state'
OPS.mkdir(parents=True, exist_ok=True)
SELF_HEAL_FILE = OPS / 'self_heal.json'


def _write_state(state: Dict[str, Any]):
    state['ts'] = time.time()
    try:
        with open(SELF_HEAL_FILE, 'w') as f:
            json.dump(state, f, indent=2)
    except Exception:
        logger.exception('Failed to write self_heal state')


def run_self_heal_check(oanda_connector, broker_link) -> Dict[str, Any]:
    """Perform basic self-heal checks and return recommended actions.

    Actions are one of: RECONNECT, CANCEL_STALES, RECONCILE, NONE
    """
    actions = []

    # A: Broker health
    try:
        if broker_link is not None and not broker_link.is_connected():
            actions.append('RECONNECT')
    except Exception:
        actions.append('RECONNECT')

    # B: Order integrity - best-effort: check for open trades without OCO via oanda api
    try:
        client = oanda_connector
        # If list_open_trades available
        if hasattr(client, 'list_open_trades'):
            open_trades = client.list_open_trades().get('trades', [])
            for t in open_trades:
                # OANDA trade structure: expect stopLossOnFill / takeProfitOnFill
                if not t.get('stopLossOnFill') or not t.get('takeProfitOnFill'):
                    actions.append('CANCEL_STALES')
                    break
    except Exception:
        # If check fails, recommend RECONCILE as conservative measure
        actions.append('RECONCILE')

    # C: Seat health - check last hive confirm
    try:
        hive_file = OPS / 'hive.json'
        if hive_file.exists():
            st = json.load(open(hive_file))
            if not st.get('hive_confirmed'):
                actions.append('RECONCILE')
    except Exception:
        actions.append('RECONCILE')

    if not actions:
        actions = ['NONE']

    state = {'actions': actions}
    _write_state(state)
    # Emit logs for downstream agents to pick
    for a in actions:
        logger.info('SELF_HEAL_ACTION %s', a)
    return state


def run_self_heal_periodic(oanda_connector, broker_link, interval_sec: int = 30):
    while True:
        try:
            run_self_heal_check(oanda_connector, broker_link)
        except Exception:
            logger.exception('Self-heal periodic check failed')
        time.sleep(interval_sec)
