#!/usr/bin/env python3
"""
Wrapper to list git changed files, requiring approval id + PIN verification.
Agents must request the approval id and PIN from the user in chat before running this script.
"""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SEC = Path(__file__).parent / 'secure_env_manager.py'
HISTORY = ROOT / 'HISTORICAL_CHANGE_LOG.md'


def verify_with_pin(approval_id: str, pin: str) -> bool:
    # Import the secure env manager functions
    import importlib.util
    spec = importlib.util.spec_from_file_location('secure_env_manager', str(SEC))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.verify_approval_with_pin(approval_id, pin)


def list_changed_files():
    # Use git to list changed files (porcelain)
    try:
        out = subprocess.check_output(['git', 'status', '--porcelain']).decode('utf-8')
    except subprocess.CalledProcessError as e:
        print('Failed to run git:', e)
        return 2
    files = [line[3:] for line in out.splitlines() if line]
    if not files:
        print('No changed files')
        return 0
    print('Changed files:')
    for f in files:
        print('-', f)
    return 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--approval-id', required=True)
    p.add_argument('--pin', help='PIN (optional; if not provided will prompt)')
    args = p.parse_args()
    pin = args.pin
    if pin is None:
        import getpass
        pin = getpass.getpass('Enter PIN to approve: ')
    ok = verify_with_pin(args.approval_id, pin)
    if not ok:
        print('Approval verification failed. Aborting.')
        sys.exit(2)
    sys.exit(list_changed_files())


if __name__ == '__main__':
    main()
