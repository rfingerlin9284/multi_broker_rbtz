#!/usr/bin/env python3
"""
Agent Charter - Global agent rules & enforcement for RICK agents
PIN: 841921
"""
from __future__ import annotations

from typing import Optional
import os
import hmac
import hashlib
from datetime import timezone
import time
from dataclasses import dataclass
from datetime import datetime
import logging

from foundation.rick_charter import RickCharter

logger = logging.getLogger("agent_charter")


@dataclass
class AgentCharter:
    """Global charter and enforcement helpers used by engines and tools
    This file is intended to be imported by engines at startup and to provide
    immutable behavioural constraints that all agents must obey.
    """

    PIN: int = 841921
    NO_FILE_RENAMES: bool = True
    # alias for legacy name requested in Phase 2: NO_RENAMES
    NO_RENAMES: bool = True
    REQUIRE_SNAPSHOT_BEFORE_CRITICAL_CHANGE: bool = True
    REQUIRE_CONSTRUCTION_LOG: bool = True
    APPROVAL_TAG: str = "confident with rbotzilla lawmakers=approval"
    # Practice trading gating: default False unless explicitly enabled.
    REQUIRE_PIN_FOR_PRACTICE: bool = True
    PRACTICE_PIN_ENV: str = "PRACTICE_PIN"
    # Allow the environment to explicitly opt-in to practice trading (still requires ALLOW_PRACTICE_ORDERS and CONFIRM_PRACTICE_ORDER)
    # If this is set (env var PRACTICE_TRADING_ALLOWED=1), the PIN requirement may be bypassed for convenience.
    PRACTICE_TRADING_ALLOWED: bool = False
    # Token TTL in seconds when validating override token
    PROTOCOL_UNCHAINED_TTL: int = 600  # 10 minutes
    # Environment variable storing the HMAC secret (must be kept secure)
    PROTOCOL_UNCHAINED_SECRET_ENV: str = 'UNLOCK_SECRET'
    OVERRIDE_AUDIT_LOG: str = 'logs/override_audit.log'

    @classmethod
    def enforce(cls) -> None:
        """Enforce the minimal charter rules at engine startup.

        This should be a fast check and avoid network calls. Additional
        checks may be added without modifying the PIN. If enforcement
        fails, a friendly PermissionError is raised to avoid accidental
        live execution.
        """
        # If unlocked token override is valid, skip all checks but log it
        try:
            if cls._verify_unlocked_token():
                logger.warning('AgentCharter enforcement bypassed by valid PROTOCOL_UNCHAINED token')
                return

        except Exception:
            # ignore verification errors and proceed to normal enforcement
            pass

        try:
            assert RickCharter.PIN == cls.PIN, "Charter PIN mismatch!"
            # If the charter requires a snapshot before critical changes, ensure one exists
            if getattr(cls, 'REQUIRE_SNAPSHOT_BEFORE_CRITICAL_CHANGE', False):
                try:
                    # Check if we're in a git repo and whether there are uncommitted changes
                    import subprocess
                    out = subprocess.check_output(['git', 'status', '--porcelain'], text=True)
                    if out.strip():
                        # There are uncommitted changes; attempt to create a snapshot
                        try:
                            from utils.snapshot_manager import create_snapshot
                            tag = create_snapshot('pre_run_snapshot')
                            logger.info('Auto-created pre-run snapshot: %s', tag)
                        except Exception as e:
                            logger.warning('Failed to auto-create snapshot: %s', e)
                except Exception:
                    # Not a git repo or git not available; skip
                    pass
            # Check for .env permissions and warn if insecure (group/other have permissions)
            # Unless SIMPLIFY_MODE is set, in which case we skip permission checks
            try:
                if os.getenv('SIMPLIFY_MODE', '0').lower() in ('1', 'true', 'yes'):
                    logger.info('SIMPLIFY_MODE is active: skipping .env permission checks')
                else:
                    import os as _os, stat as _stat
                    env_path = _os.environ.get('ENV_FILE', './.env')
                    if _os.path.exists(env_path):
                        st = _os.stat(env_path).st_mode
                        if st & (_stat.S_IRWXG | _stat.S_IRWXO):
                            logger.warning('ENV FILE INSECURE: %s permissions=%s; recommend chmod 600 or run ops/lock_secrets.sh', env_path, oct(st & 0o777))
            except Exception:
                # Best effort; don't break enforcement
                pass
        except AssertionError as e:
            logger.error("AgentCharter enforcement failed: %s", e)
            raise PermissionError("AgentCharter enforcement failed")

    @classmethod
    def approval_tag(cls, id_str: Optional[str] = None) -> str:
        if id_str:
            return f"{cls.APPROVAL_TAG} #{id_str}"
        return cls.APPROVAL_TAG

    @classmethod
    def practice_allowed(cls, pin: Optional[int] = None) -> bool:
        """Return whether practice trading is allowed for this environment.

        Decision criteria (strict):
        - ALLOW_PRACTICE_ORDERS must be explicitly set to 1/true/yes
        - CONFIRM_PRACTICE_ORDER must be explicitly set to 1/true/yes
        - If REQUIRE_PIN_FOR_PRACTICE is True, the correct PIN must be supplied either
          via the `pin` argument or via environment variable `PRACTICE_PIN`.

        This method is intended to be used by connectors and tooling that must explicitly gate
        practice order placement. It is intentionally conservative: practice orders are not
        allowed unless the operator has explicitly opted in and (optionally) provided a PIN.
        """
        # If override token is valid, allow practice trading immediately
        try:
            if cls._verify_unlocked_token():
                return True
        except Exception:
            pass

        allow_env = os.getenv('ALLOW_PRACTICE_ORDERS', '0').lower() in ('1', 'true', 'yes')
        if not allow_env:
            return False

        confirm_env = os.getenv('CONFIRM_PRACTICE_ORDER', '0').lower() in ('1', 'true', 'yes')
        if not confirm_env:
            return False

        # If the env flag PRACTICE_TRADING_ALLOWED is set, we will bypass the PIN requirement (but NOT the ALLOW/CONFIRM gating)
        env_allowed_flag = os.getenv('PRACTICE_TRADING_ALLOWED', '0').lower() in ('1', 'true', 'yes')
        if cls.REQUIRE_PIN_FOR_PRACTICE and not env_allowed_flag:
            # Validate provided pin or environment pin
            if pin is not None:
                try:
                    # Validate by using the RickCharter PIN constant
                    from foundation.rick_charter import RickCharter
                    if int(pin) == int(RickCharter.PIN):
                        return True
                except Exception:
                    return False
            env_pin = os.getenv(cls.PRACTICE_PIN_ENV)
            if env_pin and str(env_pin) == str(cls.PIN):
                return True
            return False

        return True

    @classmethod
    def _mask(cls, s: Optional[str], last_chars: int = 4) -> str:
        if not s:
            return 'N/A'
        if len(s) <= last_chars:
            return '****'
        return f"***{s[-last_chars:]}"

    @classmethod
    def _verify_unlocked_token(cls) -> bool:
        """Verify PROTOCOL_UNCHAINED token and TTL. Logs audit entries when used.

        Requires the following environment variables to be set:
        - PROTOCOL_UNCHAINED=1
        - PROTOCOL_UNCHAINED_TS: Unix epoch timestamp
        - PROTOCOL_UNCHAINED_TOKEN: hex HMAC of timestamp using secret
        - UNLOCK_SECRET: the HMAC secret used for verification (set in env locally)
        """
        if os.getenv('PROTOCOL_UNCHAINED', '0') != '1':
            return False

        # Ensure ALLOW/CONFIRM gating as minimal intent signals
        allow = os.getenv('ALLOW_PRACTICE_ORDERS', '0').lower() in ('1', 'true', 'yes')
        confirm = os.getenv('CONFIRM_PRACTICE_ORDER', '0').lower() in ('1', 'true', 'yes')
        if not (allow and confirm):
            return False

        ts = os.getenv('PROTOCOL_UNCHAINED_TS')
        token = os.getenv('PROTOCOL_UNCHAINED_TOKEN')
        secret = os.getenv(cls.PROTOCOL_UNCHAINED_SECRET_ENV)
        if not ts or not token or not secret:
            return False
        try:
            ts_int = int(ts)
        except Exception:
            return False
        # TTL check
        now = int(time.time())
        if abs(now - ts_int) > cls.PROTOCOL_UNCHAINED_TTL:
            return False
        # Compute HMAC and compare
        try:
            h = hmac.new(secret.encode('utf-8'), msg=ts.encode('utf-8'), digestmod=hashlib.sha256).hexdigest()
            if not hmac.compare_digest(h, token):
                return False
        except Exception:
            return False

        # Log the override audit: masked identity to avoid secrets in logs
        try:
            os.makedirs(os.path.dirname(cls.OVERRIDE_AUDIT_LOG), exist_ok=True)
            who = os.getenv('USER') or os.getenv('LOGNAME') or 'unknown'
            env_name = os.getenv('RICK_ENV', 'unknown')
            with open(cls.OVERRIDE_AUDIT_LOG, 'a', encoding='utf-8') as f:
                f.write(f"{datetime.now(timezone.utc).isoformat()} | OVERRIDE | user={who} | env={env_name} | token_ts={ts}\n")
        except Exception:
            # If audit log can't be written, still proceed - but warn
            logger.warning('Override audit log write failed')

        return True

    @classmethod
    def announce(cls) -> str:
        return f"AgentCharter v{RickCharter.CHARTER_VERSION} ({cls.PIN})"

__all__ = ["AgentCharter"]
