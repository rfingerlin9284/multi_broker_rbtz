#!/usr/bin/env python3
"""
Create a snapshot folder containing canonical env files and related secret files.
- Copies the following files (if present):
  - ops/secrets.env
  - ops/secrets_*.env
- Creates a README explaining the canonical file and restore instructions.
- Marks snapshot files with `.locked` suffix to discourage edits.
- Produces a compressed archive `build/secrets_snapshot-<iso>.tar.gz`.
"""
from pathlib import Path
import shutil
import argparse
import time
import tarfile
import os

ROOT = Path(__file__).parent.parent
SNAP_DIR = ROOT / 'secrets_snapshot'
OPS_DIR = ROOT / 'ops'

DEFAULT_FILES = ['secrets.env', 'secrets_1.env', 'secrets_backtest.env']


def make_snapshot(include_patterns=None, output=None):
    ts = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
    dest = SNAP_DIR / f'current_{ts}'
    dest.mkdir(parents=True, exist_ok=True)
    copied = []
    # copy default known secret files
    for name in DEFAULT_FILES:
        p = OPS_DIR / name
        if p.exists():
            out = dest / f'{name}.locked'
            shutil.copy2(p, out)
            copied.append(out)
    # Optionally include other patterns
    if include_patterns:
        for pat in include_patterns:
            for p in ROOT.glob(pat):
                if p.is_file():
                    out = dest / f'{p.name}.locked'
                    shutil.copy2(p, out)
                    copied.append(out)
    # create README
    readme = dest / 'README_SECRETS_SNAPSHOT.md'
    readme.write_text("""# Secrets Snapshot (READ-ONLY)

This folder contains a snapshot of the canonical secrets files for this repository state.

Rules:
- The canonical file to use at runtime is `ops/secrets.env` (not the locked copies here).
- Do NOT edit these `.locked` files directly. To restore, follow the steps below.

Restore steps:
1. Ensure you have physical access to the machine holding the snapshot or flash drive.
2. Copy `secrets.env.locked` to `ops/secrets.env` (preserve file permissions).
3. Run `bash tools/lock_secrets.sh` to re-lock the canonical file (sets read-only permissions).
4. Create an approval entry with: `python3 tools/secure_env_manager.py approve --message "Restoring secrets snapshot"` and record the id in `HISTORICAL_CHANGE_LOG.md`.

Security:
- These snapshot files are exact copies of the environment files at snapshot time. Protect this dataset physically.
- Agents and Copilot are explicitly blocked from automated editing operations targeting the canonical `ops/secrets.env` (see `AGENT_POLICIES.md`).
""")
    copied.append(readme)
    # create tar.gz
    output = Path(output) if output else (ROOT / 'build' / f'secrets_snapshot_{ts}.tar.gz')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(output, 'w:gz') as tar:
        tar.add(dest, arcname=dest.name)
    print(f"✅ Secrets snapshot created: {output}")
    return dest, output


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--include', action='append', help='Additional glob patterns to include')
    p.add_argument('--output', help='Output archive path')
    args = p.parse_args()
    make_snapshot(include_patterns=args.include, output=args.output)
