"""
Per-broker circuit breaker and state machine.

This module implements:
- Per-broker state management (STARTING → PAUSED → ACTIVE → FAILED)
- Circuit breaker with failure counting and automatic state transitions
- Heartbeat file writing for orchestrator monitoring
- Isolated failure handling (one broker failure does not affect others)

Key behaviors:
- Failed broker increments fail_count; above threshold → FAILED state
- FAILED state stops all trading for that broker only
- Heartbeat written every N seconds to ops/state/brokers/{name}.json
- State transitions are logged and auditable
"""

import os
import json
import time
import logging
import threading
from pathlib import Path
from typing import Optional, Callable, Any
from datetime import datetime, timezone

from multi_broker_phoenix.core.interfaces import (
    BrokerState,
    BrokerConnectorProtocol,
    GateCheckResult,
)


logger = logging.getLogger(__name__)


class BrokerSupervisor:
    """
    Manages a single broker's lifecycle, state, and circuit breaker.
    
    Responsibilities:
    - Track broker state (DISABLED/STARTING/PAUSED/ACTIVE/FAILED)
    - Circuit breaker: increment fail_count on errors, trip at threshold
    - Write heartbeat files for orchestrator monitoring
    - Provide state query interface for risk modules
    
    Thread-safe: state changes are protected by threading.Lock
    """
    
    def __init__(
        self,
        broker_name: str,
        connector: BrokerConnectorProtocol,
        repo_root: Path,
        fail_threshold: int = 5,
        heartbeat_interval_sec: float = 10.0,
    ):
        """
        Initialize broker supervisor.
        
        Args:
            broker_name: Broker identifier (oanda, coinbase, ibkr)
            connector: Broker connector implementing BrokerConnectorProtocol
            repo_root: Repository root path
            fail_threshold: Number of failures before circuit breaker trips
            heartbeat_interval_sec: Seconds between heartbeat file writes
        """
        self.broker_name = broker_name
        self.connector = connector
        self.repo_root = Path(repo_root)
        self.fail_threshold = fail_threshold
        self.heartbeat_interval_sec = heartbeat_interval_sec
        
        self._state = BrokerState.STARTING
        self._fail_count = 0
        self._last_error: Optional[str] = None
        self._state_lock = threading.Lock()
        
        # Paths
        self.state_dir = self.repo_root / "ops" / "state" / "brokers"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.heartbeat_path = self.state_dir / f"{broker_name}.json"
        
        # Heartbeat thread
        self._heartbeat_stop_event = threading.Event()
        self._heartbeat_thread: Optional[threading.Thread] = None
        
        logger.info(
            f"BrokerSupervisor initialized: {broker_name} "
            f"(fail_threshold={fail_threshold}, heartbeat={heartbeat_interval_sec}s)"
        )
    
    @property
    def state(self) -> BrokerState:
        """Get current broker state (thread-safe)."""
        with self._state_lock:
            return self._state
    
    @property
    def state_machine(self):
        """Return self for compatibility with legacy code accessing supervisor.state_machine.state."""
        return self
    
    @property
    def fail_count(self) -> int:
        """Get current failure count (thread-safe)."""
        with self._state_lock:
            return self._fail_count
    
    def set_state(self, new_state: BrokerState, reason: str = "") -> None:
        """
        Set broker state (thread-safe).
        
        Args:
            new_state: Target state
            reason: Reason for state transition (for logging)
        """
        with self._state_lock:
            old_state = self._state
            self._state = new_state
            
            logger.info(
                f"[{self.broker_name}] State transition: {old_state.value} → {new_state.value} "
                f"({reason})"
            )
            
            # Write immediate heartbeat on state change
            self._write_heartbeat()
    
    def record_failure(self, error: str) -> None:
        """
        Record a failure and potentially trip circuit breaker.
        
        Args:
            error: Error description
        """
        with self._state_lock:
            self._fail_count += 1
            self._last_error = error
            
            logger.warning(
                f"[{self.broker_name}] Failure recorded: {error} "
                f"(count={self._fail_count}/{self.fail_threshold})"
            )
            
            if self._fail_count >= self.fail_threshold and self._state != BrokerState.FAILED:
                self._state = BrokerState.FAILED
                logger.error(
                    f"[{self.broker_name}] CIRCUIT BREAKER TRIPPED: "
                    f"{self._fail_count} failures. State → FAILED. "
                    f"Last error: {error}"
                )
                self._write_heartbeat()
    
    def reset_failures(self) -> None:
        """Reset failure count (typically after successful health check)."""
        with self._state_lock:
            if self._fail_count > 0:
                logger.info(f"[{self.broker_name}] Resetting fail_count from {self._fail_count} to 0")
            self._fail_count = 0
            self._last_error = None
    
    def can_trade(self) -> bool:
        """Check if broker is in a state where trading is allowed."""
        state = self.state
        return state == BrokerState.ACTIVE
    
    def can_accept_new_signals(self) -> bool:
        """Check if broker can accept new trade signals."""
        state = self.state
        return state in (BrokerState.ACTIVE, BrokerState.PAUSED)
    
    def start_heartbeat(self) -> None:
        """Start background heartbeat thread."""
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            logger.warning(f"[{self.broker_name}] Heartbeat thread already running")
            return
        
        self._heartbeat_stop_event.clear()
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            name=f"{self.broker_name}_heartbeat",
            daemon=True
        )
        self._heartbeat_thread.start()
        logger.info(f"[{self.broker_name}] Heartbeat thread started")
    
    def stop_heartbeat(self) -> None:
        """Stop background heartbeat thread."""
        if not self._heartbeat_thread:
            return
        
        self._heartbeat_stop_event.set()
        if self._heartbeat_thread.is_alive():
            self._heartbeat_thread.join(timeout=5.0)
        
        logger.info(f"[{self.broker_name}] Heartbeat thread stopped")
    
    def _heartbeat_loop(self) -> None:
        """Background thread that writes heartbeat files."""
        while not self._heartbeat_stop_event.is_set():
            try:
                self._write_heartbeat()
            except Exception as e:
                logger.error(f"[{self.broker_name}] Heartbeat write error: {e}", exc_info=True)
            
            # Wait but allow early exit if stop event is set
            self._heartbeat_stop_event.wait(timeout=self.heartbeat_interval_sec)
    
    def _write_heartbeat(self) -> None:
        """Write current state to heartbeat file."""
        try:
            with self._state_lock:
                data = {
                    "broker": self.broker_name,
                    "state": self._state.value,
                    "fail_count": self._fail_count,
                    "last_error": self._last_error,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "epoch": time.time(),
                }
            
            # Atomic write (write to temp, then rename)
            temp_path = self.heartbeat_path.with_suffix(".tmp")
            with open(temp_path, "w") as f:
                json.dump(data, f, indent=2)
            temp_path.replace(self.heartbeat_path)
            
        except Exception as e:
            logger.error(f"[{self.broker_name}] Failed to write heartbeat: {e}", exc_info=True)
    
    def run_health_check(self) -> tuple[bool, dict[str, Any]]:
        """
        Run broker health check via connector.
        
        Returns:
            (is_healthy: bool, details: dict)
        """
        try:
            result = self.connector.health_check()
            
            if result.ok:
                self.reset_failures()
                return True, result.details
            else:
                self.record_failure(f"Health check failed: {result.errors}")
                return False, {"errors": result.errors}
        
        except Exception as e:
            error_msg = f"Health check exception: {e}"
            self.record_failure(error_msg)
            logger.error(f"[{self.broker_name}] {error_msg}", exc_info=True)
            return False, {"exception": str(e)}
    
    def handle_gate_checks(self, gate_results: list[GateCheckResult]) -> None:
        """
        Process gate check results and update state accordingly.
        
        Args:
            gate_results: List of gate check results
        """
        all_passed = all(r.passed for r in gate_results)
        
        if all_passed:
            if self.state == BrokerState.PAUSED:
                self.set_state(BrokerState.ACTIVE, "All gates passed")
        else:
            failed_gates = [r.gate_name for r in gate_results if not r.passed]
            if self.state == BrokerState.ACTIVE:
                self.set_state(
                    BrokerState.PAUSED,
                    f"Gate check failed: {', '.join(failed_gates)}"
                )
            
            # Record failure for failed gates
            for result in gate_results:
                if not result.passed:
                    self.record_failure(f"Gate {result.gate_name}: {result.errors}")
    
    def mark_active(self) -> None:
        """Transition broker to ACTIVE state (trading allowed)."""
        with self._state_lock:
            self._state = BrokerState.ACTIVE
            self._fail_count = 0  # Reset failures on successful activation
            self._last_error = None
        self._write_heartbeat()
        logger.info(f"[{self.broker_name}] State → ACTIVE (trading enabled)")
    
    def mark_paused(self, reason: str = "") -> None:
        """Transition broker to PAUSED state (healthy but not trading)."""
        with self._state_lock:
            self._state = BrokerState.PAUSED
            if reason:
                self._last_error = reason
        self._write_heartbeat()
        logger.info(f"[{self.broker_name}] State → PAUSED (reason: {reason or 'manual'})")
    
    def mark_failed(self, error: str) -> None:
        """Transition broker to FAILED state (circuit breaker tripped)."""
        with self._state_lock:
            self._state = BrokerState.FAILED
            self._last_error = error
        self._write_heartbeat()
        logger.error(f"[{self.broker_name}] State → FAILED (error: {error})")
    
    def record_error(self, error: str) -> None:
        """
        Record error and increment fail count.
        Trips circuit breaker if threshold reached.
        """
        with self._state_lock:
            self._fail_count += 1
            self._last_error = error
            
            if self._fail_count >= self.fail_threshold:
                self._state = BrokerState.FAILED
                logger.error(
                    f"[{self.broker_name}] Circuit breaker TRIPPED "
                    f"({self._fail_count}/{self.fail_threshold} consecutive failures)"
                )
            else:
                logger.warning(
                    f"[{self.broker_name}] Error recorded ({self._fail_count}/{self.fail_threshold}): {error}"
                )
        
        self._write_heartbeat()
    
    def stop(self) -> None:
        """Stop heartbeat writer thread (alias for stop_heartbeat)."""
        self.stop_heartbeat()
        logger.info(f"[{self.broker_name}] Supervisor stopped")
    
    def shutdown(self) -> None:
        """Graceful shutdown."""
        logger.info(f"[{self.broker_name}] Shutting down supervisor")
        self.stop_heartbeat()
        self.set_state(BrokerState.DISABLED, "Shutdown requested")
    
    def get_status_summary(self) -> dict[str, Any]:
        """
        Get comprehensive status summary.
        
        Returns:
            Dict with state, fail_count, last_error, can_trade, etc.
        """
        with self._state_lock:
            return {
                "broker": self.broker_name,
                "state": self._state.value,
                "can_trade": self.can_trade(),
                "fail_count": self._fail_count,
                "fail_threshold": self.fail_threshold,
                "last_error": self._last_error,
                "heartbeat_path": str(self.heartbeat_path),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
