"""
Multi-broker orchestrator.

This module implements the thin orchestration layer that:
- Watches broker heartbeat files
- Restarts failed brokers (process isolation)
- Aggregates broker status
- Does NOT share runtime state that can cascade failures

Key principles:
- Each broker runs as its own process
- Orchestrator watches heartbeats, not in-process state
- Broker failure is isolated (restart only that broker)
- Orchestrator itself is stateless and restartable
"""

import os
import json
import time
import logging
import subprocess
import signal
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass
class BrokerConfig:
    """Configuration for a single broker."""
    name: str
    enabled: bool
    start_script: str
    heartbeat_file: Path
    max_heartbeat_age_sec: float = 60.0
    restart_delay_sec: float = 10.0


class Orchestrator:
    """
    Thin orchestrator for multi-broker system.
    
    Responsibilities:
    - Monitor broker heartbeat files
    - Restart dead/stale brokers (if enabled)
    - Write aggregated status summary
    - Provide process management commands
    
    Does NOT:
    - Share runtime state between brokers
    - Execute trading logic
    - Maintain positions or orders
    """
    
    def __init__(
        self,
        repo_root: Path,
        broker_configs: list[BrokerConfig],
        check_interval_sec: float = 30.0,
    ):
        """
        Initialize orchestrator.
        
        Args:
            repo_root: Repository root path
            broker_configs: List of broker configurations
            check_interval_sec: Seconds between heartbeat checks
        """
        self.repo_root = Path(repo_root)
        self.broker_configs = {bc.name: bc for bc in broker_configs}
        self.check_interval_sec = check_interval_sec
        
        # Paths
        self.state_dir = self.repo_root / "ops" / "state" / "brokers"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.summary_file = self.state_dir / "summary.json"
        
        # Process tracking (PID per broker)
        self.broker_pids: Dict[str, Optional[int]] = {
            name: None for name in self.broker_configs
        }
        
        # Running flag
        self._running = False
        
        logger.info(
            f"Orchestrator initialized: {len(broker_configs)} brokers, "
            f"check_interval={check_interval_sec}s"
        )
    
    def start(self) -> None:
        """Start orchestrator monitoring loop."""
        logger.info("Orchestrator starting...")
        self._running = True
        
        # Initial broker startup
        for name, config in self.broker_configs.items():
            if config.enabled:
                self._start_broker(name)
        
        # Monitoring loop
        try:
            while self._running:
                self._check_brokers()
                self._write_summary()
                time.sleep(self.check_interval_sec)
        
        except KeyboardInterrupt:
            logger.info("Orchestrator interrupted by user")
            self.stop()
        
        except Exception as e:
            logger.error(f"Orchestrator error: {e}", exc_info=True)
            self.stop()
    
    def stop(self) -> None:
        """Stop orchestrator and optionally stop all brokers."""
        logger.info("Orchestrator stopping...")
        self._running = False
        
        # Note: We do NOT automatically stop broker processes here
        # They can continue running independently
        # Use stop_all_brokers() if you want to stop them
        
        logger.info("Orchestrator stopped")
    
    def _check_brokers(self) -> None:
        """Check all broker heartbeats and restart if needed."""
        now = datetime.now(timezone.utc)
        
        for name, config in self.broker_configs.items():
            if not config.enabled:
                # Broker disabled, skip
                continue
            
            # Check heartbeat file
            if not config.heartbeat_file.exists():
                logger.warning(
                    f"[{name}] Heartbeat file missing: {config.heartbeat_file}. "
                    f"Broker may not be running."
                )
                # Try to start if we don't have a PID
                if self.broker_pids.get(name) is None:
                    self._start_broker(name)
                continue
            
            # Read heartbeat
            try:
                with open(config.heartbeat_file, "r") as f:
                    heartbeat_data = json.load(f)
                
                # Check staleness
                last_heartbeat = datetime.fromisoformat(heartbeat_data["timestamp"])
                age = (now - last_heartbeat).total_seconds()
                
                if age > config.max_heartbeat_age_sec:
                    logger.warning(
                        f"[{name}] Heartbeat stale: {age:.1f}s (max={config.max_heartbeat_age_sec}s). "
                        f"State: {heartbeat_data.get('state')}. Restarting broker..."
                    )
                    self._restart_broker(name)
                else:
                    # Heartbeat fresh, update PID if needed
                    pid = heartbeat_data.get("pid")
                    if pid and self.broker_pids.get(name) != pid:
                        self.broker_pids[name] = pid
                        logger.info(f"[{name}] Heartbeat OK, PID={pid}, age={age:.1f}s")
            
            except Exception as e:
                logger.error(
                    f"[{name}] Error reading heartbeat: {e}. Attempting restart...",
                    exc_info=True
                )
                self._restart_broker(name)
    
    def _start_broker(self, name: str) -> bool:
        """
        Start a broker process.
        
        Args:
            name: Broker name
        
        Returns:
            True if started successfully, False otherwise
        """
        config = self.broker_configs.get(name)
        if not config or not config.enabled:
            logger.warning(f"[{name}] Cannot start: disabled or not configured")
            return False
        
        try:
            logger.info(f"[{name}] Starting broker via: {config.start_script}")
            
            # Start broker as background process
            # The start script should handle daemonization
            process = subprocess.Popen(
                [config.start_script, name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(self.repo_root),
                start_new_session=True,  # Detach from orchestrator
            )
            
            # Give it a moment to start
            time.sleep(2.0)
            
            # Check if process is still running
            if process.poll() is None:
                self.broker_pids[name] = process.pid
                logger.info(f"[{name}] Started successfully, PID={process.pid}")
                return True
            else:
                stdout, stderr = process.communicate()
                logger.error(
                    f"[{name}] Failed to start. Exit code={process.returncode}. "
                    f"stderr={stderr.decode()}"
                )
                return False
        
        except Exception as e:
            logger.error(f"[{name}] Exception starting broker: {e}", exc_info=True)
            return False
    
    def _stop_broker(self, name: str) -> bool:
        """
        Stop a broker process.
        
        Args:
            name: Broker name
        
        Returns:
            True if stopped successfully, False otherwise
        """
        pid = self.broker_pids.get(name)
        if not pid:
            logger.warning(f"[{name}] No PID tracked, cannot stop")
            return False
        
        try:
            logger.info(f"[{name}] Stopping broker, PID={pid}")
            os.kill(pid, signal.SIGTERM)
            
            # Wait for process to exit
            for _ in range(10):
                try:
                    os.kill(pid, 0)  # Check if process exists
                    time.sleep(0.5)
                except ProcessLookupError:
                    # Process exited
                    self.broker_pids[name] = None
                    logger.info(f"[{name}] Stopped successfully")
                    return True
            
            # Process did not exit, force kill
            logger.warning(f"[{name}] SIGTERM timeout, sending SIGKILL")
            os.kill(pid, signal.SIGKILL)
            self.broker_pids[name] = None
            return True
        
        except ProcessLookupError:
            # Process already dead
            self.broker_pids[name] = None
            logger.info(f"[{name}] Process already stopped")
            return True
        
        except Exception as e:
            logger.error(f"[{name}] Error stopping broker: {e}", exc_info=True)
            return False
    
    def _restart_broker(self, name: str) -> bool:
        """
        Restart a broker process.
        
        Args:
            name: Broker name
        
        Returns:
            True if restarted successfully, False otherwise
        """
        config = self.broker_configs.get(name)
        if not config:
            return False
        
        logger.info(f"[{name}] Restarting broker...")
        
        # Stop if running
        self._stop_broker(name)
        
        # Wait before restart
        time.sleep(config.restart_delay_sec)
        
        # Start
        return self._start_broker(name)
    
    def _write_summary(self) -> None:
        """Write aggregated broker status summary."""
        try:
            summary = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "epoch": time.time(),
                "orchestrator_running": self._running,
                "brokers": {},
            }
            
            for name, config in self.broker_configs.items():
                broker_status = {
                    "name": name,
                    "enabled": config.enabled,
                    "pid": self.broker_pids.get(name),
                    "heartbeat_file": str(config.heartbeat_file),
                }
                
                # Read heartbeat if exists
                if config.heartbeat_file.exists():
                    try:
                        with open(config.heartbeat_file, "r") as f:
                            heartbeat = json.load(f)
                        
                        broker_status["state"] = heartbeat.get("state")
                        broker_status["fail_count"] = heartbeat.get("fail_count")
                        broker_status["last_error"] = heartbeat.get("last_error")
                        broker_status["last_heartbeat"] = heartbeat.get("timestamp")
                        
                        # Calculate heartbeat age
                        if heartbeat.get("timestamp"):
                            last = datetime.fromisoformat(heartbeat["timestamp"])
                            age = (datetime.now(timezone.utc) - last).total_seconds()
                            broker_status["heartbeat_age_sec"] = age
                    
                    except Exception as e:
                        broker_status["heartbeat_error"] = str(e)
                else:
                    broker_status["state"] = "NO_HEARTBEAT"
                
                summary["brokers"][name] = broker_status
            
            # Atomic write
            temp_file = self.summary_file.with_suffix(".tmp")
            with open(temp_file, "w") as f:
                json.dump(summary, f, indent=2)
            temp_file.replace(self.summary_file)
        
        except Exception as e:
            logger.error(f"Error writing summary: {e}", exc_info=True)
    
    def stop_all_brokers(self) -> None:
        """Stop all broker processes."""
        logger.info("Stopping all brokers...")
        for name in list(self.broker_configs.keys()):
            self._stop_broker(name)
        logger.info("All brokers stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current orchestrator and broker status.
        
        Returns:
            Status dictionary
        """
        if self.summary_file.exists():
            try:
                with open(self.summary_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error reading summary: {e}")
        
        return {
            "error": "No summary file available",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


def load_broker_configs_from_env(repo_root: Path) -> list[BrokerConfig]:
    """
    Load broker configurations from environment variables.
    
    Expected env vars:
    - BROKER_OANDA_ENABLED=1/0
    - BROKER_COINBASE_ENABLED=1/0
    - BROKER_IBKR_ENABLED=1/0
    
    Args:
        repo_root: Repository root path
    
    Returns:
        List of BrokerConfig objects
    """
    state_dir = repo_root / "ops" / "state" / "brokers"
    tools_dir = repo_root / "tools"
    
    brokers = ["oanda", "coinbase", "ibkr"]
    configs = []
    
    for broker in brokers:
        env_key = f"BROKER_{broker.upper()}_ENABLED"
        enabled = os.getenv(env_key, "0") == "1"
        
        config = BrokerConfig(
            name=broker,
            enabled=enabled,
            start_script=str(tools_dir / "start_broker.sh"),
            heartbeat_file=state_dir / f"{broker}.json",
            max_heartbeat_age_sec=60.0,
            restart_delay_sec=10.0,
        )
        configs.append(config)
        
        logger.info(f"Broker config: {broker} enabled={enabled}")
    
    return configs


if __name__ == "__main__":
    # Example standalone orchestrator runner
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    
    # Resolve repo root correctly (prefer env override, fallback to repo root)
    repo_root = Path(
        os.getenv("RBOTZILLA_REPO_ROOT", str(Path(__file__).resolve().parents[2]))
    )
    configs = load_broker_configs_from_env(repo_root)
    
    orchestrator = Orchestrator(
        repo_root=repo_root,
        broker_configs=configs,
        check_interval_sec=30.0,
    )
    
    try:
        orchestrator.start()
    except KeyboardInterrupt:
        orchestrator.stop_all_brokers()
