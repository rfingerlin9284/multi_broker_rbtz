#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
🛤️  RBOTZILLA UNIFIED PATH CONFIGURATION
═══════════════════════════════════════════════════════════════════════════════

Single source of truth for all project paths.
Import this module to get consistent paths everywhere.

Usage:
    from tools.paths import PROJECT_ROOT, load_env, setup_paths
    
    load_env()      # Load .env file
    setup_paths()   # Add paths to sys.path
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

# ═══════════════════════════════════════════════════════════════════════════════
# CANONICAL PROJECT PATHS
# ═══════════════════════════════════════════════════════════════════════════════

# Project root is the MULTI_BROKER_PHOENIX folder
PROJECT_ROOT = Path(__file__).parent.parent.resolve()

# Core directories
CORE_DIR = PROJECT_ROOT / 'RBOTZILLA_CORE_EXTRACT'
HIVE_DIR = PROJECT_ROOT / 'hive_real'
TOOLS_DIR = PROJECT_ROOT / 'tools'
SCRIPTS_DIR = PROJECT_ROOT / 'scripts'
SECRETS_DIR = PROJECT_ROOT / 'secrets'
DATA_DIR = PROJECT_ROOT / 'data'
LOGS_DIR = PROJECT_ROOT / 'logs'

# The single canonical .env file (always at project root)
ENV_FILE = PROJECT_ROOT / '.env'


def load_env(env_path: Optional[Path] = None, override: bool = False) -> dict:
    """Load environment variables from .env file.
    
    Args:
        env_path: Path to .env file. Defaults to PROJECT_ROOT/.env
        override: If True, override existing env vars. Default False.
    
    Returns:
        Dict of loaded variables
    """
    env_path = env_path or ENV_FILE
    loaded = {}
    
    if not env_path.exists():
        return loaded
    
    with open(env_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            
            # Skip lines without =
            if '=' not in line:
                continue
            
            # Parse key=value
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip()
            
            # Skip empty keys
            if not key:
                continue
            
            # Handle inline comments (but not in values with #)
            # Only strip comments if there's a space before #
            if ' #' in value:
                value = value.split(' #')[0].strip()
            
            # Set environment variable
            if override or key not in os.environ:
                os.environ[key] = value
                loaded[key] = value
    
    return loaded


def setup_paths() -> None:
    """Add project paths to sys.path for imports.
    
    Adds:
        - PROJECT_ROOT (for tools.*, scripts.*)
        - CORE_DIR (for multi_broker_phoenix.*)
        - HIVE_DIR (for api_ai_hive.*)
    """
    paths_to_add = [
        str(PROJECT_ROOT),
        str(CORE_DIR),
        str(HIVE_DIR),
    ]
    
    for path in paths_to_add:
        if path not in sys.path:
            sys.path.insert(0, path)


def get_env(key: str, default: str = '') -> str:
    """Get environment variable, loading .env if needed."""
    if key not in os.environ:
        load_env()
    return os.environ.get(key, default)


def ensure_dirs() -> None:
    """Ensure all required directories exist."""
    for dir_path in [SECRETS_DIR, DATA_DIR, LOGS_DIR]:
        dir_path.mkdir(parents=True, exist_ok=True)


# ═══════════════════════════════════════════════════════════════════════════════
# AUTO-INITIALIZE ON IMPORT
# ═══════════════════════════════════════════════════════════════════════════════

# Automatically load .env when this module is imported
load_env()


if __name__ == '__main__':
    # Print path info for debugging
    print("═" * 60)
    print("🛤️  RBOTZILLA PATH CONFIGURATION")
    print("═" * 60)
    print(f"PROJECT_ROOT: {PROJECT_ROOT}")
    print(f"CORE_DIR:     {CORE_DIR}")
    print(f"HIVE_DIR:     {HIVE_DIR}")
    print(f"ENV_FILE:     {ENV_FILE} (exists: {ENV_FILE.exists()})")
    print(f"SECRETS_DIR:  {SECRETS_DIR}")
    print("═" * 60)
