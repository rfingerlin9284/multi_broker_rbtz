import subprocess
import sys
import os
from pathlib import Path
import json

ROOT = Path(__file__).parent.parent
SECURE = ROOT / '.secure'
PIN_FILE = SECURE / 'pin.hash'


def write_pin_hash(pin='testpin'):
    import hashlib, os
    ITER = 200_000
    SALT_LEN = 16
    salt = os.urandom(SALT_LEN)
    dk = hashlib.pbkdf2_hmac('sha256', pin.encode('utf-8'), salt, ITER)
    SECURE.mkdir(exist_ok=True)
    PIN_FILE.write_bytes(salt + dk)


def test_approval_and_build(tmp_path):
    # Set up pin file
    write_pin_hash('testpin')

    # Create an approval
    cmd = [sys.executable, str(ROOT / 'tools' / 'secure_env_manager.py'), 'approve', '--message', 'test approval', '--pin', 'testpin']
    rv = subprocess.run(cmd, capture_output=True, text=True)
    assert rv.returncode == 0
    out = rv.stdout + rv.stderr
    # Extract approval id printed
    import re
    m = re.search(r'Approval created: ([0-9a-fA-F\-]+)', out)
    assert m, out
    aid = m.group(1)

    # Running build with include-secrets but no approval should fail
    out_path = tmp_path / 'x.tar.gz'
    cmd = [sys.executable, str(ROOT / 'tools' / 'build_deployment.py'), '--output', str(out_path), '--include-secrets']
    rv = subprocess.run(cmd)
    assert rv.returncode != 0

    # Running build with approval should succeed
    cmd = [sys.executable, str(ROOT / 'tools' / 'build_deployment.py'), '--output', str(out_path), '--include-secrets', '--approval-id', aid]
    rv = subprocess.run(cmd)
    assert rv.returncode == 0
    assert out_path.exists()
