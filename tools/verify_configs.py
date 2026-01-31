#!/usr/bin/env python3
"""
Verify existence and basic shape of `ops/secrets.env` without modifying it.
"""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).parent.parent
SECRETS = ROOT / "ops" / "secrets.env"

REQUIRED_HINTS = [
    r"OANDA|OANDA.*TOKEN|OANDA.*KEY",
    r"COINBASE|COINBASE.*KEY",
    r"IBKR|IBKR.*KEY|IBKR.*TOKEN",
]


def inspect_secrets(path: Path):
    if not path.exists():
        print(f"❌ Missing secrets file: {path}")
        return 2
    text = path.read_text()
    findings = {}
    for pat in REQUIRED_HINTS:
        findings[pat] = bool(re.search(pat, text, re.IGNORECASE))
    print(f"🔍 Secrets present: {path} (read-only check)")
    for k, v in findings.items():
        print(f" - contains /{k}/: {'YES' if v else 'NO'}")
    missing = [k for k, v in findings.items() if not v]
    if missing:
        print("⚠️  Some expected key patterns are missing (see above). If you are intentionally omitting exchanges, this is okay.")
        return 1
    print("✅ Basic verification passed (read-only).")
    return 0


def main():
    rc = inspect_secrets(SECRETS)
    sys.exit(rc)


if __name__ == '__main__':
    main()
