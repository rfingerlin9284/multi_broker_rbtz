#!/usr/bin/env python3
"""Environment preflight checks for RBOTZILLA / MULTI_BROKER_PHOENIX.

Goals:
- Detect duplicate keys in `.env` (a frequent source of silent overrides).
- Optionally auto-fix duplicates safely by commenting out earlier occurrences,
  keeping the *last* occurrence active (shell-style semantics).
- Validate presence (and non-emptiness) of critical keys without printing secrets.

This script NEVER prints secret values.

Usage:
  python3 tools/env_preflight.py
  python3 tools/env_preflight.py --fix

Exit codes:
  0 = OK
  2 = duplicates found (and not fixed)
  3 = missing/empty critical keys
  4 = .env not found
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


_KEY_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=")


@dataclass(frozen=True)
class DotenvScan:
    path: Path
    keys: Dict[str, List[int]]  # key -> list of 1-based line numbers

    @property
    def duplicates(self) -> Dict[str, List[int]]:
        return {k: v for k, v in self.keys.items() if len(v) > 1}


def _repo_root_from_here() -> Path:
    # tools/env_preflight.py -> repo root
    return Path(__file__).resolve().parent.parent


def scan_dotenv(env_path: Path) -> DotenvScan:
    keys: Dict[str, List[int]] = {}
    with env_path.open("r", encoding="utf-8", errors="ignore") as f:
        for i, line in enumerate(f, start=1):
            s = line.lstrip()
            if not s or s.startswith("#"):
                continue
            m = _KEY_RE.match(s)
            if not m:
                continue
            key = m.group(1)
            keys.setdefault(key, []).append(i)
    return DotenvScan(path=env_path, keys=keys)


def _redact_line(line: str) -> str:
    """Return a safely redacted representation of a dotenv assignment line."""
    m = _KEY_RE.match(line)
    if not m:
        return line.rstrip("\n")
    return f"{m.group(1)}=<redacted>"


def fix_duplicates_in_place(env_path: Path, scan: DotenvScan) -> Tuple[Path, int]:
    """Comment out earlier duplicate key assignments, keeping last occurrence active.

    Returns: (backup_path, num_lines_changed)
    """
    if not scan.duplicates:
        return env_path, 0

    # Last occurrence line for each duplicate key
    last_line: Dict[str, int] = {k: max(v) for k, v in scan.duplicates.items()}

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = env_path.with_suffix(env_path.suffix + f".bak.{ts}")
    shutil.copy2(env_path, backup_path)

    changed = 0
    out_lines: List[str] = []
    with env_path.open("r", encoding="utf-8", errors="ignore") as f:
        for i, line in enumerate(f, start=1):
            m = _KEY_RE.match(line.lstrip())
            if m:
                key = m.group(1)
                if key in last_line and i != last_line[key] and not line.lstrip().startswith("#"):
                    # Comment out this earlier duplicate assignment but preserve it for audit.
                    redacted = _redact_line(line)
                    out_lines.append(
                        f"# DUPLICATE_DISABLED (kept later at line {last_line[key]}): {redacted}\n"
                    )
                    changed += 1
                    continue
            out_lines.append(line)

    env_path.write_text("".join(out_lines), encoding="utf-8")
    return backup_path, changed


def _is_nonempty_in_file(env_path: Path, key: str) -> bool:
    """Check whether key appears with a non-empty value in the file (last occurrence wins)."""
    found: Optional[str] = None
    key_re = re.compile(r"^\s*" + re.escape(key) + r"\s*=")
    with env_path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            if not key_re.match(s):
                continue
            # Strip inline comments after '='
            if "#" in s:
                eq = s.find("=")
                hp = s.find("#", eq)
                if hp > 0:
                    s = s[:hp].strip()
            _, v = s.split("=", 1)
            found = v.strip()
    return bool(found)


def _get_last_value_in_file(env_path: Path, key: str) -> Optional[str]:
    """Return the last-assigned value for key in the file (shell-style semantics).

    Strips inline comments that appear after the '='.
    Returns None if key not found.
    """
    found: Optional[str] = None
    key_re = re.compile(r"^\s*" + re.escape(key) + r"\s*=")
    with env_path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            if not key_re.match(s):
                continue
            # Strip inline comments after '='
            if "#" in s:
                eq = s.find("=")
                hp = s.find("#", eq)
                if hp > 0:
                    s = s[:hp].strip()
            _, v = s.split("=", 1)
            found = v.strip()
    return found


def _truthy(v: Optional[str]) -> bool:
    if v is None:
        return False
    return v.strip().lower() in ("1", "true", "yes", "y", "on")


def _upper(v: Optional[str], default: str = "") -> str:
    return (v or default).strip().upper()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", default=None, help="Path to .env (default: repo root/.env)")
    ap.add_argument("--fix", action="store_true", help="Auto-fix duplicates in-place (with backup)")
    ap.add_argument("--quiet", action="store_true", help="Less output")
    args = ap.parse_args()

    root = _repo_root_from_here()
    env_path = Path(args.env).expanduser().resolve() if args.env else (root / ".env")

    if not env_path.exists():
        if not args.quiet:
            print(f"❌ .env not found: {env_path}")
        return 4

    scan = scan_dotenv(env_path)

    if not args.quiet:
        print(f"✅ Scanned {env_path}: {len(scan.keys)} keys")

    dups = scan.duplicates
    if dups:
        if not args.quiet:
            print(f"⚠️  Duplicate keys detected: {len(dups)}")
            for k in sorted(dups):
                lines = ",".join(map(str, dups[k]))
                print(f"   DUP {k} @ {lines}")

        if args.fix:
            backup, changed = fix_duplicates_in_place(env_path, scan)
            if not args.quiet:
                print(f"🛠️  Fixed duplicates by commenting out earlier entries")
                print(f"   Backup: {backup}")
                print(f"   Lines disabled: {changed}")
            # re-scan after fix
            scan = scan_dotenv(env_path)
            if scan.duplicates:
                if not args.quiet:
                    print("❌ Duplicates still present after fix (unexpected)")
                return 2
        else:
            return 2

    # =========================================================
    # Conditional critical checks
    # =========================================================
    # Read mode flags from file (NOT process env) so this script
    # is deterministic and checks the actual canonical .env.
    headless_mode = (_get_last_value_in_file(env_path, "HEADLESS_MODE") or "").strip().lower()
    trading_mode = _upper(_get_last_value_in_file(env_path, "TRADING_MODE"), default="PAPER")

    enable_hive = (
        _truthy(_get_last_value_in_file(env_path, "ENABLE_AI_HIVE"))
        or _truthy(_get_last_value_in_file(env_path, "USE_HIVE_VALIDATION"))
    )

    hive_emergency_bypass = _truthy(_get_last_value_in_file(env_path, "HIVE_EMERGENCY_BYPASS"))
    hive_demo_votes = _truthy(_get_last_value_in_file(env_path, "HIVE_DEMO_VOTES"))
    hive_required = _truthy(_get_last_value_in_file(env_path, "HIVE_REQUIRED"))

    # Determine whether OANDA is expected to be used in this configuration.
    feed_symbols = _get_last_value_in_file(env_path, "FEED_SYMBOLS") or ""
    oanda_symbols = _get_last_value_in_file(env_path, "OANDA_SYMBOLS") or ""
    symbols_hint = ",".join(x for x in (feed_symbols, oanda_symbols) if x)
    symbols_include_oanda = "_" in symbols_hint

    needs_oanda = False
    if headless_mode in ("oanda-only", "multi-asset"):
        needs_oanda = True
    elif headless_mode in ("", "auto", "platform-paper") and symbols_include_oanda:
        needs_oanda = True

    oanda_required = _truthy(_get_last_value_in_file(env_path, "OANDA_REQUIRED")) or headless_mode == "oanda-only"

    # Determine whether REAL money pathways are intended.
    allow_live_real = _truthy(_get_last_value_in_file(env_path, "ALLOW_LIVE_REAL"))
    coinbase_live = _truthy(_get_last_value_in_file(env_path, "COINBASE_LIVE"))
    oanda_live = _truthy(_get_last_value_in_file(env_path, "OANDA_LIVE"))
    ibkr_live = _truthy(_get_last_value_in_file(env_path, "IBKR_LIVE"))
    intends_live = trading_mode == "LIVE" or coinbase_live or oanda_live or ibkr_live

    missing: List[str] = []
    problems: List[str] = []
    warnings: List[str] = []

    # OANDA requirements
    if needs_oanda:
        oanda_missing = [
            k
            for k in ("OANDA_API_TOKEN", "OANDA_API_URL", "OANDA_ACCOUNT_ID", "OANDA_PRACTICE_ACCOUNT_ID")
            if not _is_nonempty_in_file(env_path, k)
        ]
        if oanda_missing:
            if oanda_required or trading_mode == "LIVE":
                missing.extend(oanda_missing)
            else:
                warnings.append(
                    "OANDA is implied by config, but credentials are missing; OANDA connector will be disabled at runtime. "
                    "If you want preflight to enforce OANDA, set OANDA_REQUIRED=true."
                )

    # AI Hive requirements
    if enable_hive:
        if hive_emergency_bypass:
            warnings.append("AI Hive is enabled but HIVE_EMERGENCY_BYPASS=true; Hive will be skipped.")
        elif hive_demo_votes:
            warnings.append("AI Hive is enabled but HIVE_DEMO_VOTES=true; demo votes will be used if no API keys are configured.")
        else:
            have_openai = _is_nonempty_in_file(env_path, "OPENAI_API_KEY")
            have_xai = _is_nonempty_in_file(env_path, "XAI_API_KEY")
            have_deepseek = _is_nonempty_in_file(env_path, "DEEPSEEK_API_KEY")
            if not (have_openai or have_xai or have_deepseek):
                msg = (
                    "AI Hive is enabled (ENABLE_AI_HIVE/USE_HIVE_VALIDATION), but no AI provider key is configured. "
                    "Set at least one of OPENAI_API_KEY, XAI_API_KEY, or DEEPSEEK_API_KEY."
                )
                # In LIVE mode, this effectively freezes trading; in PAPER, it just blocks trades safely.
                if trading_mode == "LIVE" or hive_required:
                    problems.append(msg)
                else:
                    warnings.append(msg + " (PAPER mode: Hive will safely REJECT trades.)")

    # LIVE trading safety requirements (do not validate secrets unless LIVE is intended)
    if intends_live:
        if not allow_live_real:
            problems.append(
                "LIVE trading appears to be enabled (TRADING_MODE=LIVE and/or *_LIVE=true), "
                "but ALLOW_LIVE_REAL is not true. This is a safety gate."
            )

        # Coinbase live auth requirements only if Coinbase live is intended.
        if trading_mode == "LIVE" or coinbase_live:
            if not _is_nonempty_in_file(env_path, "COINBASE_API_KEY"):
                missing.append("COINBASE_API_KEY")

            have_secret = _is_nonempty_in_file(env_path, "COINBASE_API_SECRET")
            secret_file = _get_last_value_in_file(env_path, "COINBASE_API_SECRET_FILE")
            have_secret_file = bool(secret_file and secret_file.strip())
            if not (have_secret or have_secret_file):
                missing.append("COINBASE_API_SECRET or COINBASE_API_SECRET_FILE")
            elif have_secret_file:
                try:
                    assert secret_file is not None
                    p = Path(secret_file).expanduser()
                    if not p.exists():
                        problems.append(f"COINBASE_API_SECRET_FILE does not exist: {p}")
                except Exception:
                    problems.append("COINBASE_API_SECRET_FILE is set but could not be validated")

    # Report
    if missing or problems:
        if not args.quiet:
            print("❌ Preflight failed: missing/invalid required configuration")
            if missing:
                print("Missing/empty keys:")
                for k in missing:
                    print(f"   - {k}")
            if problems:
                print("Problems:")
                for p in problems:
                    print(f"   - {p}")

            if warnings:
                print("Warnings:")
                for w in warnings:
                    print(f"   - {w}")

            # Small helpful context (no secrets)
            print("Context:")
            print(f"   - TRADING_MODE={trading_mode}")
            if headless_mode:
                print(f"   - HEADLESS_MODE={headless_mode}")
            print(f"   - ENABLE_AI_HIVE={enable_hive}")
            print(f"   - needs_oanda={needs_oanda}")
            print(f"   - intends_live={intends_live}")
        return 3

    # If only warnings, still succeed (useful for PAPER smoke-tests).
    if warnings and not args.quiet:
        print("⚠️  Preflight warnings:")
        for w in warnings:
            print(f"   - {w}")

    if not args.quiet:
        print("✅ Preflight OK (no duplicates; critical keys present)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
