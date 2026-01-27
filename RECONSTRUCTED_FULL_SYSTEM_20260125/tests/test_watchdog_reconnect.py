import time
import threading
import sys
from pathlib import Path

# Ensure package path is available for imports
REPO_ROOT = Path(__file__).resolve().parents[1]
PKG_ROOT = REPO_ROOT / 'MULTI_BROKER_PHOENIX'
if str(PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(PKG_ROOT))

from multi_broker_phoenix.monitor import watchdog  # type: ignore


def test_reconnect_callbacks_invoked(monkeypatch):
    # Force watchdog state to simulate prior failure
    watchdog.WATCHDOG_STATE['ok'] = False

    called = {'v': False}

    def cb(conn):
        called['v'] = True

    watchdog.register_reconnect_callback(cb)

    class FakeConnector:
        def verify_credentials(self):
            return {'success': True}

    # Call run_watchdog_once which should detect recovery and invoke cb synchronously in test
    watchdog.run_watchdog_once(FakeConnector(), None, None, invoke_callbacks_async=False)

    # No sleep required; synchronous invocation should have set called
    assert called['v'] is True

    # Clean up callback registration to avoid test leakage
    watchdog.unregister_reconnect_callback(cb)


def test_watchdog_emits_events_on_transition(monkeypatch):
    # Ensure starting from frozen state
    watchdog.WATCHDOG_STATE['ok'] = False

    # Spy on durable _log_event (from pnl_kill_switch)
    import multi_broker_phoenix.monitor.pnl_kill_switch as pk  # type: ignore

    recorded = []

    def fake_log_event(event_type, details):
        recorded.append((event_type, details))

    monkeypatch.setattr(pk, '_log_event', fake_log_event)

    class FakeConnector:
        def verify_credentials(self):
            return {'success': True}

    # Run synchronous (no background threads) and ensure WATCHDOG_UNFREEZE recorded
    watchdog.run_watchdog_once(FakeConnector(), None, None, invoke_callbacks_async=False)

    types = [t for t, _ in recorded]
    assert 'WATCHDOG_UNFREEZE' in types


def test_watchdog_unfreezes_with_ollama_even_if_cloud_down(monkeypatch):
    watchdog.WATCHDOG_STATE['ok'] = False

    # Require AI but allow any single seat healthy
    monkeypatch.setenv('REQUIRE_AI', 'true')
    monkeypatch.setenv('REQUIRE_XAI', 'true')
    monkeypatch.setenv('REQUIRE_DEEPSEEK', 'true')
    monkeypatch.setenv('REQUIRE_OLLAMA', 'true')
    monkeypatch.setenv('MIN_BRAIN_SEATS', '1')

    # Cloud seats fail
    def fake_get_fail(url, timeout=5, headers=None):
        class Resp:
            status_code = 503
        return Resp()

    monkeypatch.setattr(watchdog.requests, 'get', fake_get_fail)

    # Ollama healthy
    class FakeOllama:
        @staticmethod
        def health(timeout=2.0):
            return {'ok': True, 'model_present': True}

    import multi_broker_phoenix.llm.ollama_client as oc  # type: ignore
    monkeypatch.setattr(oc, 'health', FakeOllama.health)

    class FakeConnector:
        def verify_credentials(self):
            return {'success': True}

    state = watchdog.run_watchdog_once(FakeConnector(), None, None, invoke_callbacks_async=False)
    assert state['ok'] is True
