import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
OUT = ROOT / 'build' / 'test-deployment.tar.gz'


def test_build_deployment_creates_archive(tmp_path):
    out = tmp_path / 'test-deployment.tar.gz'
    cmd = [sys.executable, str(ROOT / 'tools' / 'build_deployment.py'), '--output', str(out), '--include-secrets']
    rv = subprocess.run(cmd)
    assert rv.returncode == 0
    assert out.exists()


def test_manifest_and_report_exist(tmp_path):
    out = tmp_path / 'test-deployment2.tar.gz'
    cmd = [sys.executable, str(ROOT / 'tools' / 'build_deployment.py'), '--output', str(out), '--include-secrets']
    rv = subprocess.run(cmd)
    assert rv.returncode == 0
    # manifest and report located next to archive
    manifest = out.parent / 'release_manifest.json'
    report = out.parent / 'build_report.json'
    assert manifest.exists()
    assert report.exists()
