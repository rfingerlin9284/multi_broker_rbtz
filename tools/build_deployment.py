#!/usr/bin/env python3
"""
Build a clean, standalone deployment artifact.
- Copies required files into a temporary build dir
- Omits legacy/duplicate patterns
- Produces release_manifest.json and build_report.json
- Produces a tar.gz archive

Default behavior: includes `ops/secrets.env` if present (no modifications are made)
"""
import argparse
import json
import shutil
import hashlib
from pathlib import Path
import tempfile
import os
import sys

ROOT = Path(__file__).parent.parent
EXCLUDE_PATTERNS = ["*.bak", "*old*", "*backup*", "*.zip", "*.tar.gz", "*.tar.bz2"]
INCLUDE_DIRS = ["tools", "logs", "scripts"]
INCLUDE_FILES = ["launch_paper_trading.sh", "launch_real_money.py", "launch_control.sh", "tools/autonomous_trading.py", "README.md", "DEPLOYMENT_STANDALONE.md"]


def sha256_file(p: Path):
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def matches_exclude(p: Path):
    from fnmatch import fnmatch
    for pattern in EXCLUDE_PATTERNS:
        if fnmatch(p.name, pattern):
            return True
    return False


def gather_files(include_secrets: bool):
    files = []
    # Top-level includes
    for f in INCLUDE_FILES:
        p = ROOT / f
        if p.exists():
            files.append(p)
    # Directories to include (if they exist)
    for d in INCLUDE_DIRS:
        p = ROOT / d
        if p.exists():
            for fp in p.rglob("*"):
                if fp.is_file() and not matches_exclude(fp):
                    files.append(fp)
    # Always consider tools/*.py
    for fp in (ROOT / "tools").rglob("*.py"):
        if fp.is_file() and not matches_exclude(fp):
            files.append(fp)
    # Optionally include secrets
    secrets = ROOT / "ops" / "secrets.env"
    if include_secrets and secrets.exists():
        files.append(secrets)
    return sorted(set(files))


def build(output: Path, include_secrets: bool, approval_id: str = None):
    now = Path().resolve()
    tempd = Path(tempfile.mkdtemp(prefix="mbp_deploy_"))
    included = []
    excluded = []

    # If secrets inclusion requested, require an approval id recorded in HISTORICAL_CHANGE_LOG.md
    if include_secrets:
        if not approval_id:
            print('❌ Including secrets requires an explicit approval. Use --approval-id <id> (see HISTORICAL_CHANGE_LOG.md)')
            raise SystemExit(2)
        # Verify approval id exists
        hist = ROOT / 'HISTORICAL_CHANGE_LOG.md'
        if not hist.exists() or approval_id not in hist.read_text():
            print('❌ Approval id not found in HISTORICAL_CHANGE_LOG.md. Aborting.')
            raise SystemExit(2)

    try:
        files = gather_files(include_secrets)
        # Copy files preserving relative structure
        for f in files:
            rel = f.relative_to(ROOT)
            dest = tempd / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dest)
            included.append(str(rel))
        # Run a quick duplicate detector: same name, different dir
        names = {}
        duplicates = []
        for f in included:
            name = Path(f).name
            names.setdefault(name, []).append(f)
        for name, listv in names.items():
            if len(listv) > 1:
                duplicates.append({"name": name, "paths": listv})
        # Create manifest
        manifest = []
        for p in (tempd).rglob("*"):
            if p.is_file():
                rel = p.relative_to(tempd)
                manifest.append({"path": str(rel), "sha256": sha256_file(p), "size": p.stat().st_size})
        manifest_path = tempd / "release_manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2))
        # Create build report
        report = {"included": included, "duplicates": duplicates}
        report_path = tempd / "build_report.json"
        report_path.write_text(json.dumps(report, indent=2))
        # Create tar.gz
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.make_archive(str(output.with_suffix("")), 'gztar', root_dir=tempd)
        # Copy manifest and report next to archive for easy access
        shutil.copy2(manifest_path, output.parent / manifest_path.name)
        shutil.copy2(report_path, output.parent / report_path.name)
        print(f"✅ Deployment built: {output}")
        print(f"📋 Included files: {len(included)}  |  Duplicates: {len(duplicates)}")
        if include_secrets:
            print(f"🔒 Secrets were included by approval id: {approval_id}")
        return 0
    except Exception as e:
        print(f"❌ Build failed: {e}")
        raise
    finally:
        shutil.rmtree(tempd)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", default="build/multi_broker_phoenix-deployment.tar.gz")
    p.add_argument("--include-secrets", action="store_true", help="Include ops/secrets.env in the archive (read-only copy)")
    p.add_argument("--approval-id", default=None, help='Approval id for including secrets (required if --include-secrets)')
    args = p.parse_args()
    rv = build(Path(args.output), args.include_secrets, approval_id=args.approval_id)
    sys.exit(rv)


if __name__ == '__main__':
    main()
