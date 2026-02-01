#!/usr/bin/env python3
"""
Agent executor used to run potentially sensitive commands after mandatory PIN approval.
- Agents must call this script to execute any command that would modify repository secrets or perform critical actions.
- The script asks for approval id and verifies it exists in `HISTORICAL_CHANGE_LOG.md` before proceeding.

Usage:
  python3 tools/agent_executor.py --approval-id <id> -- command args...
"""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
HISTORY = ROOT / 'HISTORICAL_CHANGE_LOG.md'


def verify_approval(aid: str) -> bool:
    if not HISTORY.exists():
        return False
    return aid in HISTORY.read_text()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--approval-id', required=True)
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('cmd', nargs=argparse.REMAINDER)
    args = p.parse_args()
    if not verify_approval(args.approval_id):
        print(f"❌ Approval id {args.approval_id} not found in HISTORICAL_CHANGE_LOG.md")
        sys.exit(2)
    if not args.cmd:
        print('No command provided to execute')
        sys.exit(1)
    if args.dry_run:
        print('DRY RUN: Would execute:', ' '.join(args.cmd))
        sys.exit(0)
    try:
        rv = subprocess.run(args.cmd)
        sys.exit(rv.returncode)
    except Exception as e:
        print('Execution failed:', e)
        sys.exit(1)


if __name__ == '__main__':
    main()
