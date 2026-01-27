#!/usr/bin/env python3
"""Import a Coinbase Advanced API key JSON and install it for the connector.

This script expects the JSON downloaded from Coinbase when creating a new API key
(which contains a privateKey PEM string and the apiKey or keyName). It will:
- Parse the JSON file
- Extract the private key PEM
- Write it to ~/.coinbase/<safe_name>.pem with 0600 permissions
- Update the workspace .env to set COINBASE_API_SECRET_FILE and COINBASE_API_KEY
- Optionally run the debug script to verify credentials

Usage:
  python3 tools/import_coinbase_key.py --file /path/to/coinbase_key.json [--verify]

"""
from pathlib import Path
import argparse
import json
import os
import stat
import subprocess
import sys
import shutil

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = WORKSPACE_ROOT / '.env'
DEFAULT_DEST_DIR = Path.home() / '.coinbase'


def safe_filename(name: str) -> str:
    # Keep only safe chars
    import re
    return re.sub(r"[^A-Za-z0-9._-]", "-", name)[:120]


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except Exception as e:
        print(f"Failed to read JSON from {path}: {e}")
        raise


def write_pem(dest_dir: Path, key_name: str, pem_text: str) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    safe_name = safe_filename(key_name or 'coinbase_key')
    pem_path = dest_dir / f"{safe_name}.pem"
    pem_path.write_text(pem_text)
    # Restrict permissions
    pem_path.chmod(0o600)
    print(f"Wrote PEM to {pem_path} (mode 0600)")
    return pem_path


def backup_env(env_path: Path):
    if env_path.exists():
        bak = env_path.with_suffix(env_path.suffix + '.bak')
        shutil.copy2(env_path, bak)
        print(f"Backed up {env_path} -> {bak}")


def update_env(env_path: Path, key_name: str, pem_path: Path):
    # Read existing .env lines, update/add COINBASE_API_SECRET_FILE and COINBASE_API_KEY
    lines = []
    if env_path.exists():
        lines = env_path.read_text().splitlines()

    def set_value(lines, key, value):
        found = False
        out = []
        for line in lines:
            if line.strip().startswith(f"{key}="):
                out.append(f'{key}="{value}"')
                found = True
            else:
                out.append(line)
        if not found:
            out.append(f'{key}="{value}"')
        return out

    lines = set_value(lines, 'COINBASE_API_SECRET_FILE', str(pem_path))
    lines = set_value(lines, 'COINBASE_API_KEY', key_name)

    env_path.write_text('\n'.join(lines) + '\n')
    print(f"Updated {env_path} with COINBASE_API_SECRET_FILE and COINBASE_API_KEY")


def run_verify(python_path: str = sys.executable):
    cmd = [python_path, str(WORKSPACE_ROOT / 'tools' / 'debug_coinbase_auth.py')]
    print(f"Running: {' '.join(cmd)}")
    proc = subprocess.run(cmd, cwd=str(WORKSPACE_ROOT), capture_output=False)
    return proc.returncode


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--file', '-f', type=str, required=True, help='Path to Coinbase key JSON file')
    p.add_argument('--verify', action='store_true', help='Run tools/debug_coinbase_auth.py after import')
    args = p.parse_args()

    json_path = Path(args.file).expanduser().resolve()
    if not json_path.exists():
        print(f"File not found: {json_path}")
        return 2

    data = load_json(json_path)

    # Common fields: 'privateKey' (PEM), sometimes 'private_key' or nested 'key' structures.
    pem_text = data.get('privateKey') or data.get('private_key') or data.get('private')
    key_name = data.get('apiKey') or data.get('keyName') or data.get('name') or data.get('key')

    if not pem_text:
        # Try to find any PEM-like value
        for v in data.values():
            if isinstance(v, str) and '-----BEGIN' in v:
                pem_text = v
                break

    if not pem_text:
        print('Could not find a private key PEM in the provided JSON. Please pass the file Coinbase gave you (it contains the private key PEM).')
        return 3

    if not key_name:
        # Ask user
        key_name = input('Enter a name for this API key (example: organizations/....): ').strip()

    pem_path = write_pem(DEFAULT_DEST_DIR, key_name, pem_text)

    # Backup and update .env
    backup_env(ENV_FILE)
    update_env(ENV_FILE, key_name, pem_path)

    print('Import complete.')

    if args.verify:
        print('Running verification script...')
        rc = run_verify()
        if rc == 0:
            print('Verification succeeded')
        else:
            print('Verification script exited with code', rc)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
