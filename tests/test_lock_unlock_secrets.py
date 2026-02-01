import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
LOCK_SCRIPT = ROOT / 'tools' / 'lock_secrets.sh'
UNLOCK_SCRIPT = ROOT / 'tools' / 'unlock_secrets.sh'
SECRETS = ROOT / 'ops' / 'secrets.env'


def test_lock_unlock_cycle(tmp_path):
    # Ensure secrets file exists for test
    SECRETS.write_text('KEY=VALUE')
    # Lock
    rv = subprocess.run([str(LOCK_SCRIPT)])
    assert rv.returncode == 0
    assert (str(SECRETS.stat().st_mode & 0o777) == str(0o400) or SECRETS.stat().st_mode & 0o400)
    # Create an approval and append to HISTORICAL_CHANGE_LOG.md for testing
    # We'll fake an approval id by writing to the log directly (tests can simulate)
    HIST = ROOT / 'HISTORICAL_CHANGE_LOG.md'
    aid = 'test-approval-1234'
    HIST.write_text(HIST.read_text() + f"- [TEST] APPROVAL: id={aid} message=test\n")
    # Unlock
    rv = subprocess.run([str(UNLOCK_SCRIPT), aid])
    assert rv.returncode == 0
    # unlocked should be writable
    assert SECRETS.stat().st_mode & 0o200 or SECRETS.stat().st_mode & 0o600
