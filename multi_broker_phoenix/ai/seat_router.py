"""AI Seat Router with quorum and rotation.

Rules:
- At least REQUIRE_SEATS_MIN healthy seats required to allow entries.
- REQUIRE_XAI/REQUIRE_DEEPSEEK are treated as preferred (not mandatory)
  unless *_MANDATORY flags are enabled.
- Seats with AUTH_FAIL/HTTP_404/5xx are quarantined with backoff.
"""
from __future__ import annotations
import os
import time
import json
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Tuple

try:
    import requests
except Exception:  # pragma: no cover
    requests = None

logger = logging.getLogger(__name__)


def _log_event(event_type: str, details: Dict[str, Any]) -> None:
    try:
        from multi_broker_phoenix.monitor.pnl_kill_switch import _log_event as durable_log
        durable_log(event_type, details)
    except Exception:
        logger.info("%s %s", event_type, details)


@dataclass
class SeatStatus:
    healthy: bool = False
    last_error: Optional[str] = None
    quarantine_until: float = 0.0
    backoff_sec: float = 10.0
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    last_check: Optional[float] = None

    def in_quarantine(self) -> bool:
        return time.time() < self.quarantine_until

    def mark_failure(self, reason: str) -> None:
        self.healthy = False
        self.last_error = reason
        self.consecutive_failures += 1
        self.consecutive_successes = 0
        self.quarantine_until = time.time() + self.backoff_sec
        self.backoff_sec = min(self.backoff_sec * 2, 300.0)

    def mark_success(self) -> None:
        self.healthy = True
        self.last_error = None
        self.consecutive_successes += 1
        self.consecutive_failures = 0
        if self.consecutive_successes >= 2:
            self.backoff_sec = 10.0
            self.quarantine_until = 0.0


class BaseSeat:
    name: str = "base"
    preferred: bool = False
    mandatory: bool = False

    def __init__(self, name: str, preferred: bool = False, mandatory: bool = False):
        self.name = name
        self.preferred = preferred
        self.mandatory = mandatory
        self.status = SeatStatus()

    def health_check(self) -> Tuple[bool, str]:
        raise NotImplementedError

    def chat(self, prompt: str, system_prompt: str) -> Tuple[bool, str]:
        raise NotImplementedError


class OllamaSeat(BaseSeat):
    def __init__(self):
        super().__init__(
            name="ollama",
            preferred=True,
            mandatory=os.getenv("OLLAMA_MANDATORY", "false").lower() in ("true", "1", "yes"),
        )
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
        self.model = os.getenv("OLLAMA_MODEL", "llama3.2")
        self.format = os.getenv("OLLAMA_FORMAT", "json")

    def health_check(self) -> Tuple[bool, str]:
        if requests is None:
            return False, "REQUESTS_MISSING"
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=2)
            if r.status_code == 200:
                return True, "OK"
            return False, f"HTTP_{r.status_code}"
        except Exception as e:
            return False, f"EXCEPTION_{e}"

    def chat(self, prompt: str, system_prompt: str) -> Tuple[bool, str]:
        if requests is None:
            return False, "REQUESTS_MISSING"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
        }
        if self.format:
            payload["format"] = self.format
        try:
            r = requests.post(f"{self.base_url}/api/chat", json=payload, timeout=10)
            if r.status_code != 200:
                return False, f"HTTP_{r.status_code}"
            data = r.json()
            content = (data.get("message") or {}).get("content", "")
            return True, content
        except Exception as e:
            return False, f"EXCEPTION_{e}"


class GrokSeat(BaseSeat):
    def __init__(self):
        super().__init__(
            name="grok",
            preferred=os.getenv("REQUIRE_XAI", "0").lower() in ("1", "true", "yes"),
            mandatory=os.getenv("REQUIRE_XAI_MANDATORY", "false").lower() in ("true", "1", "yes"),
        )
        self.base_url = os.getenv("XAI_BASE_URL", "https://api.x.ai/v1").rstrip("/")
        self.model = os.getenv("XAI_MODEL", "grok-4-latest")
        self.key = os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY")

    def _headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.key}",
        }

    def health_check(self) -> Tuple[bool, str]:
        if not self.key:
            return False, "NO_KEY"
        if requests is None:
            return False, "REQUESTS_MISSING"
        try:
            r = requests.get(f"{self.base_url}/models", headers=self._headers(), timeout=5)
            if r.status_code == 200:
                return True, "OK"
            if r.status_code in (401, 403):
                return False, "AUTH_FAIL"
            return False, f"HTTP_{r.status_code}"
        except Exception as e:
            return False, f"EXCEPTION_{e}"

    def chat(self, prompt: str, system_prompt: str) -> Tuple[bool, str]:
        if not self.key:
            return False, "NO_KEY"
        if requests is None:
            return False, "REQUESTS_MISSING"
        try:
            r = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.1,
                },
                timeout=15,
            )
            if r.status_code != 200:
                return False, f"HTTP_{r.status_code}"
            content = r.json()["choices"][0]["message"]["content"].strip()
            return True, content
        except Exception as e:
            return False, f"EXCEPTION_{e}"


class DeepSeekSeat(BaseSeat):
    def __init__(self):
        super().__init__(
            name="deepseek",
            preferred=os.getenv("REQUIRE_DEEPSEEK", "0").lower() in ("1", "true", "yes"),
            mandatory=os.getenv("REQUIRE_DEEPSEEK_MANDATORY", "false").lower() in ("true", "1", "yes"),
        )
        self.base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1").rstrip("/")
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        self.key = os.getenv("DEEPSEEK_API_KEY")

    def _headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.key}",
        }

    def health_check(self) -> Tuple[bool, str]:
        if not self.key:
            return False, "NO_KEY"
        if requests is None:
            return False, "REQUESTS_MISSING"
        try:
            r = requests.get(f"{self.base_url}/models", headers=self._headers(), timeout=5)
            if r.status_code == 200:
                return True, "OK"
            if r.status_code in (401, 403):
                return False, "AUTH_FAIL"
            return False, f"HTTP_{r.status_code}"
        except Exception as e:
            return False, f"EXCEPTION_{e}"

    def chat(self, prompt: str, system_prompt: str) -> Tuple[bool, str]:
        if not self.key:
            return False, "NO_KEY"
        if requests is None:
            return False, "REQUESTS_MISSING"
        try:
            r = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.1,
                },
                timeout=15,
            )
            if r.status_code != 200:
                return False, f"HTTP_{r.status_code}"
            content = r.json()["choices"][0]["message"]["content"].strip()
            return True, content
        except Exception as e:
            return False, f"EXCEPTION_{e}"


class OpenAISeat(BaseSeat):
    def __init__(self):
        super().__init__(
            name="openai",
            preferred=os.getenv("REQUIRE_OPENAI", "0").lower() in ("1", "true", "yes"),
            mandatory=os.getenv("REQUIRE_OPENAI_MANDATORY", "false").lower() in ("true", "1", "yes"),
        )
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.key = os.getenv("OPENAI_API_KEY")

    def _headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.key}",
        }

    def health_check(self) -> Tuple[bool, str]:
        if not self.key:
            return False, "NO_KEY"
        if requests is None:
            return False, "REQUESTS_MISSING"
        try:
            r = requests.get(f"{self.base_url}/models", headers=self._headers(), timeout=5)
            if r.status_code == 200:
                return True, "OK"
            if r.status_code in (401, 403):
                return False, "AUTH_FAIL"
            return False, f"HTTP_{r.status_code}"
        except Exception as e:
            return False, f"EXCEPTION_{e}"

    def chat(self, prompt: str, system_prompt: str) -> Tuple[bool, str]:
        if not self.key:
            return False, "NO_KEY"
        if requests is None:
            return False, "REQUESTS_MISSING"
        try:
            r = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.1,
                },
                timeout=15,
            )
            if r.status_code != 200:
                return False, f"HTTP_{r.status_code}"
            content = r.json()["choices"][0]["message"]["content"].strip()
            return True, content
        except Exception as e:
            return False, f"EXCEPTION_{e}"


class AISeatRouter:
    def __init__(self, seats: Optional[List[BaseSeat]] = None):
        self.seats = seats or [OllamaSeat(), GrokSeat(), DeepSeekSeat(), OpenAISeat()]
        self.require_min = int(os.getenv("REQUIRE_SEATS_MIN", "1"))

    def _eligible(self, seat: BaseSeat) -> bool:
        if seat.status.in_quarantine():
            return False
        return True

    def _check_seat(self, seat: BaseSeat) -> None:
        ok, reason = seat.health_check()
        seat.status.last_check = time.time()
        if ok:
            if not seat.status.healthy:
                _log_event("SEAT_RECOVER", {"seat": seat.name})
            seat.status.mark_success()
        else:
            seat.status.mark_failure(reason)
            _log_event("SEAT_FAIL", {"seat": seat.name, "reason": reason})
            _log_event("SEAT_QUARANTINE", {"seat": seat.name, "until": seat.status.quarantine_until})

    def refresh_health(self) -> Dict[str, Any]:
        status = {}
        for seat in self.seats:
            self._check_seat(seat)
            status[seat.name] = {
                "healthy": seat.status.healthy,
                "last_error": seat.status.last_error,
                "quarantine_until": seat.status.quarantine_until,
            }
        return status

    def any_healthy(self) -> bool:
        return any(s.status.healthy and not s.status.in_quarantine() for s in self.seats)

    def healthy_count(self) -> int:
        return len([s for s in self.seats if s.status.healthy and not s.status.in_quarantine()])

    def select_seat(self) -> Optional[BaseSeat]:
        preferred = [s for s in self.seats if s.preferred and self._eligible(s) and s.status.healthy]
        if preferred:
            seat = preferred[0]
            _log_event("SEAT_PICKED", {"seat": seat.name, "preferred": True})
            return seat
        healthy = [s for s in self.seats if self._eligible(s) and s.status.healthy]
        if healthy:
            seat = healthy[0]
            _log_event("SEAT_PICKED", {"seat": seat.name, "preferred": False})
            return seat
        return None

    def chat(self, prompt: str, system_prompt: str) -> Dict[str, Any]:
        self.refresh_health()
        if self.healthy_count() < self.require_min:
            return {"ok": False, "reason": "NO_HEALTHY_SEATS", "seat": None, "content": None}

        for seat in self.seats:
            if not self._eligible(seat) or not seat.status.healthy:
                continue
            ok, content = seat.chat(prompt, system_prompt)
            if ok:
                _log_event("SEAT_PICKED", {"seat": seat.name, "preferred": seat.preferred})
                return {"ok": True, "seat": seat.name, "content": content}
            else:
                seat.status.mark_failure(str(content))
                _log_event("SEAT_FAIL", {"seat": seat.name, "reason": str(content)})
                _log_event("SEAT_QUARANTINE", {"seat": seat.name, "until": seat.status.quarantine_until})
                continue

        return {"ok": False, "reason": "ALL_SEATS_FAILED", "seat": None, "content": None}

    def status_snapshot(self) -> Dict[str, Any]:
        return {
            "require_min": self.require_min,
            "seats": {
                s.name: {
                    "healthy": s.status.healthy,
                    "preferred": s.preferred,
                    "mandatory": s.mandatory,
                    "last_error": s.status.last_error,
                    "quarantine_until": s.status.quarantine_until,
                }
                for s in self.seats
            },
        }
