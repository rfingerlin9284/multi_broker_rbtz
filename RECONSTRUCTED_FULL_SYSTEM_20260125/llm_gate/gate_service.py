#!/usr/bin/env python3
"""RBOTzilla LLM Gate Service - Trade proposal review + hard rule enforcement.

This service:
1. Runs basic hard checks (OCO, RR, side consistency, max_hold)
2. If hard checks pass, queries local LLM for approval/veto
3. Returns structured decision with reasons

Run standalone: uvicorn llm_gate.gate_service:app --host 127.0.0.1 --port 6060
"""
from __future__ import annotations
import os
import json
import time
import logging
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional

try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel, Field
except ImportError:
    FastAPI = None
    BaseModel = object
    HTTPException = Exception
    Field = lambda *a, **k: None

from llm_gate.ollama_gate import health_check, generate

logger = logging.getLogger(__name__)

# Hard rule thresholds
OCO_MIN_RR = float(os.getenv('OCO_MIN_RR', '1.0'))
OCO_MAX_RR = float(os.getenv('OCO_MAX_RR', '5.0'))
MAX_HOLD_SECONDS_MIN = 3600  # 1 hour minimum
MAX_HOLD_SECONDS_MAX = 28800  # 8 hours maximum
MAX_HOLD_SECONDS_DEFAULT = 21600  # 6 hours default


if FastAPI:
    app = FastAPI(title="RBOTzilla LLM Gate", version="1.0")
else:
    app = None


class TradeProposal(BaseModel if BaseModel else object):
    """Trade proposal submitted for review."""
    symbol: str = ""
    side: str = ""  # BUY or SELL
    units: float = 0.0
    entry: float = 0.0
    sl: float = 0.0
    tp: float = 0.0
    rr: Optional[float] = None
    reason: Optional[str] = None
    opened_at_ts: Optional[float] = None
    max_hold_seconds: int = MAX_HOLD_SECONDS_DEFAULT


@dataclass
class GateDecision:
    """Decision returned by the gate."""
    approve: bool
    seat: str  # "hard_checks", "ollama", or model name
    risk_score: int  # 0-100
    reasons: List[str]
    required_fixes: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def basic_hard_checks(t: TradeProposal) -> List[str]:
    """Run hard rule checks that don't need LLM."""
    fails = []

    # OCO: SL and TP must exist
    if t.sl == 0 or t.tp == 0:
        fails.append("Missing SL/TP (OCO requirement violated)")

    # Side consistency
    if t.side.upper() == "BUY":
        if t.sl >= t.entry:
            fails.append("BUY: SL must be below ENTRY")
        if t.tp <= t.entry:
            fails.append("BUY: TP must be above ENTRY")
        if t.sl > 0 and t.tp > 0 and not (t.sl < t.entry < t.tp):
            fails.append("BUY must satisfy SL < ENTRY < TP")
    elif t.side.upper() == "SELL":
        if t.sl <= t.entry:
            fails.append("SELL: SL must be above ENTRY")
        if t.tp >= t.entry:
            fails.append("SELL: TP must be below ENTRY")
        if t.sl > 0 and t.tp > 0 and not (t.tp < t.entry < t.sl):
            fails.append("SELL must satisfy TP < ENTRY < SL")
    elif t.side:
        fails.append(f"Invalid side: {t.side} (must be BUY or SELL)")

    # Max hold bounds
    if t.max_hold_seconds < MAX_HOLD_SECONDS_MIN:
        fails.append(f"max_hold_seconds too low ({t.max_hold_seconds} < {MAX_HOLD_SECONDS_MIN})")
    if t.max_hold_seconds > MAX_HOLD_SECONDS_MAX:
        fails.append(f"max_hold_seconds too high ({t.max_hold_seconds} > {MAX_HOLD_SECONDS_MAX})")

    # Risk:Reward calculation
    try:
        if t.entry > 0 and t.sl > 0 and t.tp > 0:
            risk = abs(t.entry - t.sl)
            reward = abs(t.tp - t.entry)
            rr = (reward / risk) if risk > 0 else 0.0
            if rr < OCO_MIN_RR:
                fails.append(f"RR too low ({rr:.2f} < {OCO_MIN_RR:.1f})")
            if rr > OCO_MAX_RR:
                fails.append(f"RR too high ({rr:.2f} > {OCO_MAX_RR:.1f})")
    except Exception:
        pass

    return fails


def review_trade_sync(proposal: Dict[str, Any]) -> GateDecision:
    """Synchronous trade review (for use outside FastAPI)."""
    t = TradeProposal(**proposal) if isinstance(proposal, dict) else proposal

    # Hard checks first
    hard_fails = basic_hard_checks(t)
    if hard_fails:
        return GateDecision(
            approve=False,
            seat="hard_checks",
            risk_score=95,
            reasons=["Hard rule failure"],
            required_fixes=hard_fails,
        )

    # LLM review
    system_prompt = (
        "You are RBOTzilla Local Brain. "
        "Your job is to APPROVE or REJECT trade proposals strictly for safety/rules. "
        "Return ONLY valid JSON with keys: approve(bool), risk_score(int 0-100), reasons(array), required_fixes(array). "
        "Reject if any rule is unclear, missing, or risky."
    )

    user_prompt = (
        f"TradeProposal:\n"
        f"symbol={t.symbol}\nside={t.side}\nunits={t.units}\nentry={t.entry}\nsl={t.sl}\ntp={t.tp}\n"
        f"max_hold_seconds={t.max_hold_seconds}\nreason={t.reason}\n"
        f"Rules:\n"
        f"- OCO REQUIRED (SL and TP must exist)\n"
        f"- RR >= {OCO_MIN_RR} and <= {OCO_MAX_RR}\n"
        f"- Must be internally consistent (BUY: SL<ENTRY<TP, SELL: TP<ENTRY<SL)\n"
        f"- If anything is missing/ambiguous: REJECT\n"
    )

    try:
        result = generate(user_prompt, system_prompt=system_prompt)
        if result.get('ok'):
            content = result.get('response', '{}')
            # Try to parse JSON from response
            try:
                j = json.loads(content)
                return GateDecision(
                    approve=bool(j.get("approve", False)),
                    seat="ollama",
                    risk_score=int(j.get("risk_score", 80)),
                    reasons=list(j.get("reasons", [])),
                    required_fixes=list(j.get("required_fixes", [])),
                )
            except json.JSONDecodeError:
                # LLM didn't return valid JSON - conservative rejection
                return GateDecision(
                    approve=False,
                    seat="ollama",
                    risk_score=70,
                    reasons=["LLM response not valid JSON"],
                    required_fixes=["Manual review required"],
                )
        else:
            # LLM unavailable - but hard checks passed
            # Conservative: allow with warning (local brain optional)
            return GateDecision(
                approve=True,
                seat="hard_checks_only",
                risk_score=50,
                reasons=["LLM unavailable, hard checks passed"],
                required_fixes=[],
            )
    except Exception as e:
        # Exception during LLM call - allow if hard checks passed
        return GateDecision(
            approve=True,
            seat="hard_checks_only",
            risk_score=50,
            reasons=[f"LLM exception: {e}, hard checks passed"],
            required_fixes=[],
        )


if app:
    @app.get("/health")
    async def health():
        """Health check endpoint."""
        try:
            result = health_check()
            return {"ok": result.get("ok", False), "ollama": result}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @app.post("/review_trade")
    async def review_trade(t: TradeProposal):
        """Review a trade proposal."""
        decision = review_trade_sync(t.model_dump() if hasattr(t, 'model_dump') else t.__dict__)
        return decision.to_dict()


def main():
    """Run the gate service."""
    import uvicorn
    port = int(os.getenv("LLM_GATE_PORT", "6060"))
    uvicorn.run("llm_gate.gate_service:app", host="127.0.0.1", port=port, reload=False)


if __name__ == "__main__":
    main()
