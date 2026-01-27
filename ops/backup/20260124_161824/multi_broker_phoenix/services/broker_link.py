"""Broker Link service: maintain a resilient always-on connection to OANDA.

Usage:
  - Import BrokerLink and start it with an initialized OANDA connector.
  - Or run as a module for a standalone daemon: `python3 -m multi_broker_phoenix.services.broker_link`

Features:
  - Periodic heartbeat checks (verify_credentials)
  - Exponential backoff reconnect with jitter
  - Writes JSON state to ops/state/broker_link.json
  - Small HTTP health endpoint at localhost:8765/health
  - Emits durable events via _log_event when transitions occur
"""
from __future__ import annotations
import threading
import time
import json
import os
import socket
import random
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# State path
ROOT = Path(__file__).resolve().parent.parent.parent
STATE_DIR = ROOT / 'ops' / 'state'
STATE_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE = STATE_DIR / 'broker_link.json'

DEFAULT_PORT = int(os.getenv('BROKER_LINK_PORT', '8765'))
HEARTBEAT_INTERVAL = int(os.getenv('BROKER_LINK_INTERVAL', '10'))

# Durable event logger (best-effort)
try:
    from multi_broker_phoenix.monitor.pnl_kill_switch import _log_event
except Exception:
    def _log_event(*a, **k):
        try:
            logger.info('EVENT %s %s', a, k)
        except Exception:
            pass


class BrokerLink:
    def __init__(self, connector, mode: str = 'PAPER'):
        self.connector = connector
        self.mode = mode
        self._lock = threading.Lock()
        self._connected = False
        self._last_heartbeat = None
        self._last_error = None
        self._reconnect_count = 0
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._http_server: Optional[HTTPServer] = None

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name='broker-link')
        self._thread.start()
        # Start health HTTP server in background
        threading.Thread(target=self._start_http_server, daemon=True, name='broker-link-http').start()
        logger.info('BrokerLink started')

    def stop(self):
        self._stop.set()
        try:
            if self._http_server:
                self._http_server.shutdown()
        except Exception:
            pass

    def _start_http_server(self):
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path != '/health':
                    self.send_response(404)
                    self.end_headers()
                    return
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                state = self.server.shared_state()
                self.wfile.write(json.dumps(state).encode())

            def log_message(self, format, *args):
                return

        # Bind to localhost only
        server = HTTPServer(('127.0.0.1', DEFAULT_PORT), Handler)
        # attach helper
        server.shared_state = lambda: self.get_state()
        self._http_server = server
        logger.info('BrokerLink HTTP health listening on http://127.0.0.1:%d/health', DEFAULT_PORT)
        try:
            server.serve_forever()
        except Exception:
            logger.exception('BrokerLink HTTP server stopped')

    def _run(self):
        backoff_base = 1.0
        max_backoff = 120.0
        while not self._stop.is_set():
            try:
                ok = False
                try:
                    res = self.connector.verify_credentials()
                    ok = bool(res.get('success'))
                except Exception as e:
                    ok = False
                    err = str(e)
                    logger.debug('Broker verify error: %s', err)

                with self._lock:
                    prev = self._connected
                    if ok:
                        self._connected = True
                        self._last_heartbeat = time.time()
                        self._last_error = None
                        self._reconnect_count = 0
                        if not prev:
                            _log_event('BROKER_CONNECTED', {'mode': self.mode})
                            logger.info('BROKER_CONNECTED: trading allowed')
                    else:
                        self._connected = False
                        self._last_error = 'verify_failed'
                        # increment reconnect counter
                        self._reconnect_count += 1
                        if prev:
                            _log_event('BROKER_DISCONNECTED', {'mode': self.mode})
                            logger.warning('BROKER_DISCONNECTED: trading paused')

                # Write state file
                self._write_state()

                if ok:
                    # Success: sleep normal interval
                    time.sleep(HEARTBEAT_INTERVAL)
                    backoff_base = 1.0
                else:
                    # Backoff with jitter
                    delay = min(max_backoff, backoff_base * (2 ** min(self._reconnect_count, 6)))
                    jitter = random.uniform(0, delay * 0.2)
                    delay = max(1.0, delay + jitter)
                    _log_event('BROKER_RECONNECTING', {'attempt': self._reconnect_count, 'delay': delay})
                    time.sleep(delay)
            except Exception as e:
                logger.exception('BrokerLink run loop error: %s', e)
                time.sleep(5)

    def _write_state(self):
        state = self.get_state()
        try:
            with open(STATE_FILE, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception:
            logger.exception('Failed to write broker state')

    def get_state(self) -> Dict[str, Any]:
        with self._lock:
            return {
                'connected': bool(self._connected),
                'last_heartbeat': self._last_heartbeat,
                'last_error': self._last_error,
                'mode': self.mode,
                'env': os.getenv('TRADING_MODE', 'PAPER'),
                'reconnect_count': int(self._reconnect_count)
            }

    def is_connected(self) -> bool:
        with self._lock:
            return bool(self._connected)


# Module-level helper for starting as script
def _create_default_connector():
    # Lightweight fallback connector used for standalone heartbeat checking when no oanda client is passed.
    class Dummy:
        def verify_credentials(self):
            return {'success': True}
    return Dummy()


def main():
    connector = _create_default_connector()
    bl = BrokerLink(connector, mode=os.getenv('TRADING_MODE', 'PAPER'))
    bl.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        bl.stop()


if __name__ == '__main__':
    main()
