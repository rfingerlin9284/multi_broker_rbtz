import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
REG = ROOT / 'tools' / 'tasks_registry.json'


def test_generate_tasks_registry():
    if REG.exists():
        REG.unlink()
    rv = subprocess.run([sys.executable, str(ROOT / 'tools' / 'generate_tasks_registry.py')])
    assert rv.returncode == 0
    assert REG.exists()
    data = REG.read_text()
    assert len(data) > 10
