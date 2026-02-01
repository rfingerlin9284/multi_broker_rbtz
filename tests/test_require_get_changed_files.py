import subprocess
import sys
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
SECURE = ROOT / 'tools' / 'secure_env_manager.py'
REQUIRE = ROOT / 'tools' / 'require_get_changed_files.py'


def test_require_get_changed_files(tmp_path):
    # Create a PIN and approval via the CLI
    # Set PIN (non-interactive isn't supported directly, so write hash directly for test)
    import hashlib, os
    ITER = 200_000
    SALT_LEN = 16
    pin = 'testpin'
    salt = os.urandom(SALT_LEN)
    dk = hashlib.pbkdf2_hmac('sha256', pin.encode('utf-8'), salt, ITER)
    sdir = ROOT / '.secure'
    sdir.mkdir(exist_ok=True)
    (sdir / 'pin.hash').write_bytes(salt + dk)
    # Call approve to create an approval
    rv = subprocess.run([sys.executable, str(SECURE), 'approve', '--message', 'test approval', '--pin', pin], capture_output=True, text=True)
    assert rv.returncode == 0
    m = re.search(r'Approval created: ([0-9a-fA-F\-]+)', rv.stdout + rv.stderr)
    assert m, (rv.stdout + rv.stderr)
    aid = m.group(1)
    # Make a dummy change to repo
    p = ROOT / 'tmp_test_file.txt'
    p.write_text('x')
    subprocess.run(['git', 'add', str(p)])
    # Run the require script with approval and PIN
    proc = subprocess.run([sys.executable, str(REQUIRE), '--approval-id', aid, '--pin', pin], capture_output=True, text=True)
    assert proc.returncode == 0
    assert 'tmp_test_file.txt' in proc.stdout
    # Cleanup
    subprocess.run(['git', 'reset', 'HEAD', '--', str(p)])
    p.unlink()
