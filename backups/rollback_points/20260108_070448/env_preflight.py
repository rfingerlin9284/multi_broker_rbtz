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

    # Critical keys: only validate presence/non-empty; never print values.
    critical = [
        "OPENAI_API_KEY",
        "XAI_API_KEY",
        # DEEPSEEK may be optional depending on your funding status
        # "DEEPSEEK_API_KEY",
        "OANDA_API_TOKEN",
        "OANDA_API_URL",
        "OANDA_ACCOUNT_ID",
        "OANDA_PRACTICE_ACCOUNT_ID",
    ]

    missing = [k for k in critical if not _is_nonempty_in_file(env_path, k)]
    if missing:
        if not args.quiet:
            print("❌ Missing/empty critical keys in .env:")
            for k in missing:
                print(f"   - {k}")
        return 3

    if not args.quiet:
        print("✅ Preflight OK (no duplicates; critical keys present)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
