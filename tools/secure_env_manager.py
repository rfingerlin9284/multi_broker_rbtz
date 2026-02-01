#!/usr/bin/env python3
"""
Manage PIN-protected approvals for actions involving `ops/secrets.env`.

Usage:
  - Set PIN (local): python3 tools/secure_env_manager.py set-pin
  - Approve an action: python3 tools/secure_env_manager.py approve --message "Include secrets for backup"
  - List approvals: python3 tools/secure_env_manager.py list
  - Verify approval exists in HISTORICAL_CHANGE_LOG: python3 tools/secure_env_manager.py verify <approval_id>

Security notes:
- The PIN is stored only as a salted PBKDF2 hash in `.secure/pin.hash`.
- Approvals are stored in `.secure/approvals/<id>.approval` and an entry is appended to `HISTORICAL_CHANGE_LOG.md`.
- This tool does NOT read or modify `ops/secrets.env` itself.
"""
from pathlib import Path
import argparse
import getpass
import hashlib
import os
import json
import uuid
import time
import hmac

ROOT = Path(__file__).parent.parent
SECURE_DIR = ROOT / '.secure'
PIN_FILE = SECURE_DIR / 'pin.hash'
APPROVALS_DIR = SECURE_DIR / 'approvals'
HISTORY = ROOT / 'HISTORICAL_CHANGE_LOG.md'

# PBKDF2 params
ITER = 200_000
SALT_LEN = 16


def _ensure_dirs():
    SECURE_DIR.mkdir(exist_ok=True)
    APPROVALS_DIR.mkdir(exist_ok=True)


def set_pin():
    _ensure_dirs()
    if PIN_FILE.exists():
        confirm = input('A PIN already exists. Overwrite? Type YES to confirm: ')
        if confirm != 'YES':
            print('Aborted')
            return
    pin = getpass.getpass('Enter new PIN: ')
    pin2 = getpass.getpass('Confirm new PIN: ')
    if pin != pin2:
        print('Pins do not match')
        return
    salt = os.urandom(SALT_LEN)
    dk = hashlib.pbkdf2_hmac('sha256', pin.encode('utf-8'), salt, ITER)
    PIN_FILE.write_bytes(salt + dk)
    print('✅ PIN set (stored as salted hash in .secure/pin.hash)')


def _check_pin(pin: str):
    if not PIN_FILE.exists():
        print('No PIN is set. Run `set-pin` first.')
        return False
    data = PIN_FILE.read_bytes()
    salt = data[:SALT_LEN]
    stored = data[SALT_LEN:]
    dk = hashlib.pbkdf2_hmac('sha256', pin.encode('utf-8'), salt, ITER)
    return hmac.compare_digest(dk, stored)


def approve(message: str, pin: str = None):
    _ensure_dirs()
    if pin is None:
        pin = getpass.getpass('Enter PIN to approve: ')
    if not _check_pin(pin):
        print('Invalid PIN')
        return
    aid = str(uuid.uuid4())
    ts = int(time.time())
    # Create approval payload and signature (HMAC with PIN as key)
    payload = {"id": aid, "ts": ts, "message": message}
    payload_bytes = json.dumps(payload, sort_keys=True).encode('utf-8')
    sig = hmac.new(pin.encode('utf-8'), payload_bytes, 'sha256').hexdigest()
    record = {"payload": payload, "sig": sig}
    path = APPROVALS_DIR / f"{aid}.approval"
    path.write_text(json.dumps(record, indent=2))
    # Append to historical log
    entry = f"- [{time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(ts))}] APPROVAL: id={aid} message={message}\n"
    HISTORY.write_text(HISTORY.read_text() + entry)
    print(f"✅ Approval created: {aid}")
    print('Note: This approval id is recorded in HISTORICAL_CHANGE_LOG.md')


def list_approvals():
    _ensure_dirs()
    rows = []
    for p in sorted(APPROVALS_DIR.glob('*.approval')):
        try:
            j = json.loads(p.read_text())
            rows.append((p.name, j.get('payload', {}).get('message', ''), j.get('payload', {}).get('ts', 0)))
        except Exception:
            rows.append((p.name, '(invalid)', 0))
    if not rows:
        print('No approvals found')
        return
    for name, msg, ts in rows:
        print(f"{name:40}  {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(ts))}  - {msg}")


def verify_approval(approval_id: str):
    _ensure_dirs()
    path = APPROVALS_DIR / f"{approval_id}.approval"
    if not path.exists():
        print('Approval file not found')
        return False
    try:
        rec = json.loads(path.read_text())
        payload = rec['payload']
        # verify that HISTORICAL_CHANGE_LOG contains this id
        text = HISTORY.read_text()
        if approval_id not in text:
            print('Approval id not recorded in HISTORICAL_CHANGE_LOG.md')
            return False
        print('✅ Approval exists and is recorded')
        return True
    except Exception as e:
        print(f'Invalid approval file: {e}')
        return False


def verify_approval_with_pin(approval_id: str, pin: str) -> bool:
    """Verify approval signature using provided PIN. Returns True if signature matches."""
    _ensure_dirs()
    path = APPROVALS_DIR / f"{approval_id}.approval"
    if not path.exists():
        print('Approval file not found')
        return False
    try:
        rec = json.loads(path.read_text())
        payload = rec['payload']
        sig = rec.get('sig')
        if not sig:
            print('Approval record missing signature')
            return False
        # Recompute HMAC
        payload_bytes = json.dumps(payload, sort_keys=True).encode('utf-8')
        import hmac
        import hashlib
        calc = hmac.new(pin.encode('utf-8'), payload_bytes, 'sha256').hexdigest()
        if hmac.compare_digest(calc, sig):
            print('✅ Signature verified with provided PIN')
            # Also verify recorded in history
            text = HISTORY.read_text()
            if approval_id not in text:
                print('Approval id not recorded in HISTORICAL_CHANGE_LOG.md')
                return False
            return True
        else:
            print('❌ Signature mismatch - invalid PIN')
            return False
    except Exception as e:
        print(f'Invalid approval file or error: {e}')
        return False


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='cmd')
    sub.add_parser('set-pin')
    ap = sub.add_parser('approve')
    ap.add_argument('--message', required=True)
    ap.add_argument('--pin', help='PIN (optional; prefer entering interactively)')
    sub.add_parser('list')
    vp = sub.add_parser('verify')
    vp.add_argument('approval_id')
    vpp = sub.add_parser('verify-pin')
    vpp.add_argument('approval_id')
    vpp.add_argument('--pin', help='PIN (optional; prefer entering interactively)')
    args = p.parse_args()
    if args.cmd == 'set-pin':
        set_pin()
    elif args.cmd == 'approve':
        approve(args.message, getattr(args, 'pin', None))
    elif args.cmd == 'list':
        list_approvals()
    elif args.cmd == 'verify':
        ok = verify_approval(args.approval_id)
        if not ok:
            exit(2)
    elif args.cmd == 'verify-pin':
        pin = getattr(args, 'pin', None)
        if pin is None:
            import getpass
            pin = getpass.getpass('Enter PIN to verify approval: ')
        ok = verify_approval_with_pin(args.approval_id, pin)
        if not ok:
            exit(2)
    else:
        p.print_help()


if __name__ == '__main__':
    main()
