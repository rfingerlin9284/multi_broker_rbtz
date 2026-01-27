#!/usr/bin/env python3
"""hive_chatgpt_worker.py

REAL Hive input worker (browser-seat).

- Uses Playwright persistent profile in hive_real/browser_profile
- Watches inbox/hive_llm_requests.jsonl for new requests
- Posts prompt into ChatGPT (chatgpt.com) using the logged-in session
- Writes results to outbox/hive_llm_responses.jsonl
- Emits lightweight events into top-level narration.jsonl for HUD crosstalk

No external API usage.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from playwright.sync_api import sync_playwright

from hive_llm_queue import requests_path, responses_path


BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
NARRATION_PATH = PROJECT_DIR / "narration.jsonl"


def _log(msg: str) -> None:
    """Write a timestamped line to stdout (captured by nohup log)."""
    ts = _utc_now_iso()
    try:
        print(f"[{ts}] {msg}", file=sys.stdout, flush=True)
    except Exception:
        # Don't let logging break the worker.
        pass


def _looks_like_closed(e: BaseException) -> bool:
    s = str(e).lower()
    return "has been closed" in s or "target page" in s or "browser has been closed" in s


def _ensure_page(ctx, chat_url: str):
    """Return an open page navigated to chat_url.

    The ChatGPT tab can be closed accidentally; we recreate it.
    """

    # Prefer an existing open ChatGPT tab (users may open other tabs).
    try:
        pages = list(getattr(ctx, "pages", []) or [])

        page = None
        for p in pages:
            try:
                if p.is_closed():
                    continue
                u = ""
                try:
                    u = p.url or ""
                except Exception:
                    u = ""
                if "chatgpt" in u:
                    page = p
                    break
            except Exception:
                continue

        if page is None:
            for p in pages:
                try:
                    if not p.is_closed():
                        page = p
                        break
                except Exception:
                    continue

        if page is None:
            page = ctx.new_page()
    except Exception:
        # If the context is gone, propagate so caller can relaunch.
        raise

    # Ensure we're on the correct URL.
    try:
        current_url = ""
        try:
            current_url = page.url or ""
        except Exception:
            current_url = ""

        # Always steer back to chatgpt.com if we're blank/newtab/other.
        if (not current_url) or current_url == "about:blank" or ("chatgpt" not in current_url):
            page.goto(chat_url, wait_until="domcontentloaded")
            page.wait_for_timeout(800)
    except Exception:
        # If navigation fails (e.g., page closed), propagate.
        raise

    return page


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_narration(event_type: str, details: Dict[str, Any]) -> None:
    try:
        payload = {
            "ts": _utc_now_iso(),
            "event_type": event_type,
            "venue": "hive",
            "details": details,
        }
        with open(NARRATION_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, separators=(",", ":"), ensure_ascii=False) + "\n")
    except Exception:
        pass


def _append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, separators=(",", ":"), ensure_ascii=False) + "\n")


def _wsl_host_ip() -> Optional[str]:
    """Best-effort: WSL2 often exposes the Windows host as the resolv.conf nameserver."""
    try:
        with open("/etc/resolv.conf", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("nameserver "):
                    ip = line.split()[1].strip()
                    if ip:
                        return ip
    except Exception:
        return None
    return None


def _candidate_cdp_urls(primary: Optional[str], port: str) -> list[str]:
    if primary:
        return [primary]

    urls: list[str] = []
    # Local (Linux host)
    urls.append(f"http://127.0.0.1:{port}")
    urls.append(f"http://localhost:{port}")

    # WSL2: Windows host is commonly reachable at the resolv.conf nameserver IP.
    host_ip = _wsl_host_ip()
    if host_ip and host_ip not in ("127.0.0.1", "localhost"):
        urls.append(f"http://{host_ip}:{port}")

    # Deduplicate while preserving order
    seen: set[str] = set()
    out: list[str] = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def _ensure_prompt_box(page):
    """Return a locator for a *visible* prompt input element."""

    # ChatGPT UI changes; keep a small selector set.
    selectors = [
        "textarea[data-testid='prompt-textarea']",
        "textarea#prompt-textarea",
        "div[contenteditable='true']",
        # Fallback last (often matches hidden/backup textareas)
        "textarea",
    ]
    last_err: Optional[Exception] = None
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            loc.wait_for(state="visible", timeout=8000)
            return loc
        except Exception as e:
            last_err = e
    raise RuntimeError(f"Could not find prompt box (last error: {last_err})")


def _wait_until_logged_in(ctx, chat_url: str):
    """Block until ChatGPT is ready for prompts.

    We do NOT attempt to bypass any verification; this simply keeps the browser open
    and waits for the operator to complete login/verification in the visible window.
    """

    while True:
        # Re-acquire a valid page each loop; the tab can be closed or crash.
        page = _ensure_page(ctx, chat_url)
        try:
            _ensure_prompt_box(page)

            # Even if the prompt is visible, ChatGPT may show logged-out/rate-limit overlays
            # that intercept clicks (e.g. modal-no-auth-rate-limit). Treat that as NOT ready.
            try:
                if page.locator("[data-testid='modal-no-auth-rate-limit']").first.is_visible():
                    raise RuntimeError("ChatGPT is showing a logged-out rate-limit modal; please log in in the visible browser window")
            except Exception as e:
                # If is_visible() fails due to timing, ignore; other checks below will still work.
                if isinstance(e, RuntimeError):
                    raise

            # Heuristic: login landing often includes a visible 'Log in' button.
            try:
                if page.get_by_role("button", name="Log in").first.is_visible():
                    raise RuntimeError("ChatGPT login required (Log in button visible)")
            except Exception as e:
                if isinstance(e, RuntimeError):
                    raise

            return page
        except Exception as e:
            # If the page/context/browser is closed, bubble up so the caller can relaunch.
            if _looks_like_closed(e):
                raise

            # Attach a little context (URL/title) to make manual recovery faster.
            page_url = ""
            page_title = ""
            try:
                page_url = page.url or ""
            except Exception:
                page_url = ""
            try:
                page_title = page.title() or ""
            except Exception:
                page_title = ""

            _append_narration(
                "HIVE_NEEDS_LOGIN",
                {"message": str(e), "page_url": page_url, "page_title": page_title},
            )
            _log(f"HIVE_NEEDS_LOGIN {e} url={page_url!r} title={page_title!r}")
            time.sleep(2.0)


def _send_prompt_and_get_answer(page, prompt: str, timeout_s: float) -> str:
    """Send prompt and return latest assistant message text."""

    prompt_loc = _ensure_prompt_box(page)

    # Count assistant messages before sending
    def assistant_blocks():
        return page.locator("div[data-message-author-role='assistant']")

    before = 0
    try:
        before = assistant_blocks().count()
    except Exception:
        before = 0

    # Focus prompt box and submit
    try:
        prompt_loc.scroll_into_view_if_needed(timeout=3000)
    except Exception:
        pass
    prompt_loc.click(timeout=10000)

    # Use fill for textarea, type for contenteditable fallback
    try:
        # Works for textarea
        prompt_loc.fill("")
        prompt_loc.type(prompt, delay=5)
        prompt_loc.press("Enter")
    except Exception:
        # Fallback: type-only (works for contenteditable)
        prompt_loc.type(prompt, delay=5)
        prompt_loc.press("Enter")

    # Wait for a new assistant block
    deadline = time.time() + max(5.0, timeout_s)
    last_text = ""
    stable_since = None

    while time.time() < deadline:
        try:
            blocks = assistant_blocks()
            cnt = blocks.count()
            if cnt > before:
                latest = blocks.nth(cnt - 1)
                txt = latest.inner_text().strip()

                # wait for it to stabilize (heuristic)
                if txt and txt == last_text:
                    if stable_since is None:
                        stable_since = time.time()
                    elif time.time() - stable_since >= 2.0:
                        return txt
                else:
                    stable_since = None
                    last_text = txt

                # If we have something, keep waiting for stabilization briefly
                if txt:
                    time.sleep(0.25)
                    continue
        except Exception:
            pass

        time.sleep(0.25)

    # Return best effort (may be partial)
    return last_text.strip() or ""


def _build_trade_prompt(payload: Dict[str, Any]) -> str:
    """Create a strict-output prompt so the engine can parse it."""

    symbol = payload.get("symbol", "UNKNOWN")
    direction = payload.get("direction") or payload.get("action") or "UNKNOWN"
    entry = payload.get("entry_price") or payload.get("entry") or payload.get("current_price")
    timeframe = payload.get("timeframe", "M15")

    return (
        "You are the Hive trading analyst. Use ONLY the information in this prompt and your market knowledge. "
        "Return STRICT JSON ONLY (no markdown, no commentary).\n\n"
        f"SYMBOL: {symbol}\n"
        f"DIRECTION: {direction}\n"
        f"ENTRY_PRICE: {entry}\n"
        f"TIMEFRAME: {timeframe}\n\n"
        "Output JSON schema:\n"
        "{\n"
        "  \"signal\": \"strong_buy|buy|neutral|sell|strong_sell\",\n"
        "  \"confidence\": 0.0,\n"
        "  \"reasoning\": \"short rationale\",\n"
        "  \"risk_notes\": [\"...\"],\n"
        "  \"trade_ok\": true\n"
        "}\n"
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=None)
    ap.add_argument("--profile-dir", default=str(BASE_DIR / "browser_profile"))
    ap.add_argument(
        "--cdp-url",
        default=None,
        help="Attach to an already-running Chrome/Chromium via CDP (e.g., http://127.0.0.1:9222).",
    )
    ap.add_argument("--poll", type=float, default=0.5)
    ap.add_argument("--timeout", type=float, default=60.0)
    ap.add_argument("--from-beginning", action="store_true")
    args = ap.parse_args()

    cfg_url = None
    try:
        cfg = json.loads((BASE_DIR / "hive_config.json").read_text(encoding="utf-8"))
        cfg_url = cfg.get("browser_chat_url")
    except Exception:
        cfg_url = None

    chat_url = args.url or os.getenv("HIVE_CHAT_URL") or cfg_url or "https://chatgpt.com/"

    # CDP attach mode is the most reliable way to keep a BUSINESS-account session stable.
    # Operators typically launch a real Chrome/Chromium with --remote-debugging-port and a persistent user-data-dir,
    # then we attach here.
    cdp_url = args.cdp_url or os.getenv("HIVE_CDP_URL")
    use_cdp = (os.getenv("HIVE_USE_CDP") or "").strip().lower() in ("1", "true", "yes", "on")
    cdp_port = (os.getenv("HIVE_CDP_PORT") or "9222").strip()
    if not cdp_url and use_cdp:
        # We'll try multiple candidates (useful in WSL where the browser may be on Windows).
        cdp_url = None

    req_path = requests_path(BASE_DIR)
    resp_path = responses_path(BASE_DIR)

    req_path.parent.mkdir(parents=True, exist_ok=True)
    resp_path.parent.mkdir(parents=True, exist_ok=True)
    req_path.touch(exist_ok=True)
    resp_path.touch(exist_ok=True)

    # Preload processed IDs so restarts don't duplicate work
    processed: set[str] = set()
    try:
        with open(resp_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    processed.add(json.loads(line).get("id"))
                except Exception:
                    continue
    except Exception:
        pass

    _append_narration(
        "HIVE_WORKER_START",
        {
            "url": chat_url,
            "profile_dir": args.profile_dir,
            "cdp_url": cdp_url,
        },
    )

    _log(
        f"HIVE_WORKER_START url={chat_url} profile_dir={args.profile_dir} "
        f"cdp_url={cdp_url or ''} use_cdp={'1' if use_cdp else '0'}"
    )

    # Playwright's driver is a Node process. If the Python side exits unexpectedly or the driver glitches,
    # you can see a Node-side EPIPE. To avoid the worker dying permanently, we wrap Playwright in a
    # restart loop that can recover from driver failures.
    while True:
        try:
            with sync_playwright() as p:
                ctx = None
                browser = None  # CDP mode

                def _launch_ctx():
                    nonlocal browser
                    if cdp_url is not None or use_cdp:
                        # Attach to an already-open user browser (recommended for stable business-account login)
                        if browser is None:
                            for candidate in _candidate_cdp_urls(cdp_url, cdp_port):
                                try:
                                    _log(f"Connecting to existing browser via CDP: {candidate}")
                                    browser = p.chromium.connect_over_cdp(candidate)
                                    break
                                except Exception as e:
                                    _log(f"CDP connect failed for {candidate}: {e}")
                                    browser = None
                            if browser is None:
                                raise RuntimeError(
                                    "CDP attach failed for all candidates. "
                                    "Make sure Chrome/Chromium is running with --remote-debugging-port."
                                )
                        # Reuse first context when possible (avoid creating many contexts)
                        if browser.contexts:
                            return browser.contexts[0]
                        return browser.new_context(viewport={"width": 1280, "height": 900})

                    _log("Launching Playwright persistent context...")
                    return p.chromium.launch_persistent_context(
                        args.profile_dir,
                        headless=False,
                        viewport={"width": 1280, "height": 900},
                    )

                # Browser session (can be relaunched if page/context is closed)
                while True:
                    try:
                        if ctx is None:
                            ctx = _launch_ctx()
                            _log("Browser context launched")

                        page = _ensure_page(ctx, chat_url)
                        page = _wait_until_logged_in(ctx, chat_url)

                        # Decide where to start reading
                        pos = 0
                        if not args.from_beginning:
                            try:
                                pos = req_path.stat().st_size
                            except Exception:
                                pos = 0

                        _append_narration("HIVE_WORKER_READY", {"requests": str(req_path), "responses": str(resp_path)})
                        _log(f"HIVE_WORKER_READY requests={req_path} responses={resp_path}")

                        while True:
                            try:
                                browser_reset = False

                                with open(req_path, "r", encoding="utf-8") as f:
                                    f.seek(pos)
                                    while True:
                                        line = f.readline()
                                        if not line:
                                            break
                                        pos = f.tell()

                                        line = line.strip()
                                        if not line:
                                            continue
                                        try:
                                            req = json.loads(line)
                                        except Exception:
                                            continue

                                        rid = str(req.get("id", ""))
                                        if not rid or rid in processed:
                                            continue

                                        kind = str(req.get("kind", "trade_analysis"))
                                        payload = req.get("payload") or {}
                                        prompt = str(req.get("prompt") or "").strip()
                                        if not prompt and kind == "trade_analysis":
                                            prompt = _build_trade_prompt(payload)

                                        _append_narration(
                                            "HIVE_LLM_REQUEST",
                                            {"id": rid, "kind": kind, "symbol": payload.get("symbol")},
                                        )
                                        _log(f"HIVE_LLM_REQUEST id={rid} kind={kind} symbol={payload.get('symbol')}")

                                        ok = False
                                        raw_text = ""
                                        parsed = None
                                        err = None
                                        try:
                                            # Re-acquire a valid page each request (tab can be closed).
                                            page = _ensure_page(ctx, chat_url)
                                            raw_text = _send_prompt_and_get_answer(page, prompt, timeout_s=args.timeout)
                                            ok = bool(raw_text)
                                            # Best-effort parse of strict JSON
                                            try:
                                                parsed = json.loads(raw_text)
                                            except Exception:
                                                parsed = None
                                        except Exception as e:
                                            ok = False
                                            err = str(e)

                                            if _looks_like_closed(e):
                                                _append_narration("HIVE_BROWSER_RESET", {"error": err})
                                                _log(f"HIVE_BROWSER_RESET error={err}")
                                                try:
                                                    if ctx is not None:
                                                        ctx.close()
                                                except Exception:
                                                    pass
                                                ctx = None
                                                browser_reset = True
                                                break

                                        resp = {
                                            "id": rid,
                                            "ts": _utc_now_iso(),
                                            "ok": ok,
                                            "raw_text": raw_text,
                                            "parsed": parsed,
                                            "error": err,
                                            "schema": "hive_llm_response_v1",
                                        }
                                        _append_jsonl(resp_path, resp)
                                        processed.add(rid)

                                        _append_narration(
                                            "HIVE_LLM_RESPONSE",
                                            {
                                                "id": rid,
                                                "ok": ok,
                                                "error": err,
                                                "excerpt": (raw_text[:240] + "…")
                                                if raw_text and len(raw_text) > 240
                                                else raw_text,
                                            },
                                        )
                                        _log(f"HIVE_LLM_RESPONSE id={rid} ok={ok} err={err or ''}")

                                if browser_reset:
                                    # Relaunch outer context loop
                                    time.sleep(1.0)
                                    continue

                            except KeyboardInterrupt:
                                raise
                            except Exception as e:
                                _append_narration("HIVE_WORKER_ERROR", {"error": str(e)})
                                _log(f"HIVE_WORKER_ERROR error={e}")
                                _log(traceback.format_exc())

                            time.sleep(max(0.1, args.poll))

                    except KeyboardInterrupt:
                        raise
                    except Exception as e:
                        _append_narration("HIVE_WORKER_ERROR", {"error": str(e)})
                        _log(f"HIVE_WORKER_ERROR error={e}")
                        _log(traceback.format_exc())

                        # Relaunch on any browser/controller errors.
                        try:
                            if ctx is not None:
                                ctx.close()
                        except Exception:
                            pass
                        ctx = None
                        time.sleep(2.0)

        except KeyboardInterrupt:
            _append_narration("HIVE_WORKER_STOP", {"reason": "KeyboardInterrupt"})
            _log("HIVE_WORKER_STOP reason=KeyboardInterrupt")
            break
        except Exception as e:
            # This catches Playwright driver failures (including EPIPE-style issues) and restarts cleanly.
            _append_narration("HIVE_WORKER_ERROR", {"error": str(e), "stage": "playwright_outer"})
            _log(f"HIVE_WORKER_ERROR stage=playwright_outer error={e}")
            _log(traceback.format_exc())
            time.sleep(2.0)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
