"""Provider repair agent with health probes and URL recovery."""
from __future__ import annotations
import os
import time
import logging
from typing import Dict, Any, List

from .seat_router import AISeatRouter, GrokSeat, DeepSeekSeat, OpenAISeat, OllamaSeat, BaseSeat

logger = logging.getLogger(__name__)


def _log_event(event_type: str, details: Dict[str, Any]) -> None:
    try:
        from multi_broker_phoenix.monitor.pnl_kill_switch import _log_event as durable_log
        durable_log(event_type, details)
    except Exception:
        logger.info("%s %s", event_type, details)


def _candidates_from_env(name: str) -> List[str]:
    raw = os.getenv(name, "")
    return [x.strip().rstrip("/") for x in raw.split(",") if x.strip()]


class ProviderRepairAgent:
    def __init__(self, router: AISeatRouter | None = None):
        self.router = router or AISeatRouter()
        self.max_success_to_reenable = int(os.getenv("SEAT_REPAIR_SUCCESS_COUNT", "2"))

    def _repair_seat(self, seat: BaseSeat) -> Dict[str, Any]:
        status = {"seat": seat.name, "action": "none", "result": "skipped"}
        ok, reason = seat.health_check()
        if ok:
            seat.status.mark_success()
            status["result"] = "healthy"
            return status

        if reason == "AUTH_FAIL":
            seat.status.mark_failure("AUTH_FAIL")
            status["action"] = "disabled"
            status["result"] = "AUTH_FAIL"
            _log_event("SEAT_AUTH_FAIL", {"seat": seat.name})
            return status

        candidates = []
        if isinstance(seat, GrokSeat):
            candidates = _candidates_from_env("XAI_BASE_URL_CANDIDATES")
        elif isinstance(seat, DeepSeekSeat):
            candidates = _candidates_from_env("DEEPSEEK_BASE_URL_CANDIDATES")
        elif isinstance(seat, OpenAISeat):
            candidates = _candidates_from_env("OPENAI_BASE_URL_CANDIDATES")
        elif isinstance(seat, OllamaSeat):
            candidates = _candidates_from_env("OLLAMA_BASE_URL_CANDIDATES")

        for candidate in candidates:
            try:
                old = getattr(seat, "base_url", None)
                setattr(seat, "base_url", candidate.rstrip("/"))
                ok2, reason2 = seat.health_check()
                if ok2:
                    seat.status.mark_success()
                    status["action"] = "base_url_switch"
                    status["result"] = "recovered"
                    status["new_base_url"] = candidate
                    _log_event("SEAT_RECOVER", {"seat": seat.name, "base_url": candidate})
                    return status
                if old:
                    setattr(seat, "base_url", old)
            except Exception:
                continue

        seat.status.mark_failure(reason)
        status["result"] = reason
        return status

    def run_once(self) -> Dict[str, Any]:
        results = []
        for seat in self.router.seats:
            results.append(self._repair_seat(seat))
        return {"results": results, "timestamp": time.time()}
