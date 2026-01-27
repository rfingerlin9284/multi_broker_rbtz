"""Tests for environment loader and doctor.

Tests verify:
1. Secrets override toggles (same key in both -> secrets win)
2. Duplicates are detected and cause env_doctor to exit nonzero
3. Missing required key causes env_doctor to exit nonzero when seat is required
"""
import os
import tempfile
import subprocess
from pathlib import Path
import json


def test_secrets_override_toggles():
    """Test that secrets file overrides toggles file for duplicate keys."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        
        # Create mock repo structure
        tools_dir = tmppath / "tools"
        config_dir = tmppath / "config"
        ops_state_dir = tmppath / "ops" / "state"
        tools_dir.mkdir(parents=True)
        config_dir.mkdir(parents=True)
        ops_state_dir.mkdir(parents=True)
        
        # Copy env_load.sh
        repo_root = Path(__file__).parent.parent
        env_load_src = repo_root / "tools" / "env_load.sh"
        env_load_dst = tools_dir / "env_load.sh"
        env_load_dst.write_text(env_load_src.read_text())
        env_load_dst.chmod(0o755)
        
        # Create toggles with TEST_KEY=toggles_value
        toggles = config_dir / "toggles.env"
        toggles.write_text("TEST_KEY=toggles_value\n")
        
        # Create secrets with TEST_KEY=secrets_value
        secrets = tmppath / "ops" / "secrets.env"
        secrets.parent.mkdir(parents=True, exist_ok=True)
        secrets.write_text("TEST_KEY=secrets_value\n")
        
        # Create test script that sources env_load and prints TEST_KEY
        test_script = tmppath / "test.sh"
        test_script.write_text(f"""#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="{tmppath}"
source "{env_load_dst}"
echo "$TEST_KEY"
""")
        test_script.chmod(0o755)
        
        # Run test script
        result = subprocess.run(
            [str(test_script)],
            capture_output=True,
            text=True,
            cwd=tmppath
        )
        
        # Assert secrets value wins
        assert result.stdout.strip() == "secrets_value", \
            f"Expected 'secrets_value', got '{result.stdout.strip()}'"


def test_env_doctor_detects_duplicates():
    """Test that env_doctor exits nonzero when duplicates are detected."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        
        # Create mock repo structure
        tools_dir = tmppath / "tools"
        config_dir = tmppath / "config"
        ops_state_dir = tmppath / "ops" / "state"
        tools_dir.mkdir(parents=True)
        config_dir.mkdir(parents=True)
        ops_state_dir.mkdir(parents=True)
        
        # Copy scripts
        repo_root = Path(__file__).parent.parent
        env_load_src = repo_root / "tools" / "env_load.sh"
        env_doctor_src = repo_root / "tools" / "env_doctor.sh"
        
        env_load_dst = tools_dir / "env_load.sh"
        env_doctor_dst = tools_dir / "env_doctor.sh"
        
        env_load_dst.write_text(env_load_src.read_text())
        env_doctor_dst.write_text(env_doctor_src.read_text())
        
        env_load_dst.chmod(0o755)
        env_doctor_dst.chmod(0o755)
        
        # Create toggles and secrets with duplicate key
        toggles = config_dir / "toggles.env"
        toggles.write_text("ENABLE_OANDA=1\nDUPLICATE_KEY=value1\n")
        
        secrets = tmppath / "ops" / "secrets.env"
        secrets.parent.mkdir(parents=True, exist_ok=True)
        secrets.write_text("DUPLICATE_KEY=value2\nOANDA_API_TOKEN=test\nOANDA_ACCOUNT_ID=test\n")
        
        # Run env_doctor
        result = subprocess.run(
            [str(env_doctor_dst)],
            capture_output=True,
            text=True,
            cwd=tmppath,
            env={**os.environ, "REPO_ROOT": str(tmppath)}
        )
        
        # Assert exit code 2 (duplicates) or 4 (duplicates + missing)
        assert result.returncode in (2, 4), \
            f"Expected exit code 2 or 4 (duplicates), got {result.returncode}"
        
        # Assert output mentions duplicates
        assert "DUPLICATE" in result.stdout.upper(), \
            "Expected 'DUPLICATE' in output"


def test_env_doctor_detects_missing_required_keys():
    """Test that env_doctor exits nonzero when required keys are missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        
        # Create mock repo structure
        tools_dir = tmppath / "tools"
        config_dir = tmppath / "config"
        ops_state_dir = tmppath / "ops" / "state"
        tools_dir.mkdir(parents=True)
        config_dir.mkdir(parents=True)
        ops_state_dir.mkdir(parents=True)
        
        # Copy scripts
        repo_root = Path(__file__).parent.parent
        env_load_src = repo_root / "tools" / "env_load.sh"
        env_doctor_src = repo_root / "tools" / "env_doctor.sh"
        
        env_load_dst = tools_dir / "env_load.sh"
        env_doctor_dst = tools_dir / "env_doctor.sh"
        
        env_load_dst.write_text(env_load_src.read_text())
        env_doctor_dst.write_text(env_doctor_src.read_text())
        
        env_load_dst.chmod(0o755)
        env_doctor_dst.chmod(0o755)
        
        # Create toggles requiring OANDA but no secrets file
        toggles = config_dir / "toggles.env"
        toggles.write_text("ENABLE_OANDA=1\n")
        
        # No secrets.env created - keys will be missing
        
        # Run env_doctor
        result = subprocess.run(
            [str(env_doctor_dst)],
            capture_output=True,
            text=True,
            cwd=tmppath,
            env={**os.environ, "REPO_ROOT": str(tmppath)}
        )
        
        # Assert exit code 3 (missing) or 4 (both)
        assert result.returncode in (3, 4), \
            f"Expected exit code 3 or 4 (missing keys), got {result.returncode}"
        
        # Assert output mentions missing or empty
        output_upper = result.stdout.upper()
        assert "MISSING" in output_upper or "EMPTY" in output_upper, \
            "Expected 'MISSING' or 'EMPTY' in output"


def test_env_state_json_written():
    """Test that env_load.sh writes ops/state/env_state.json."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        
        # Create mock repo structure
        tools_dir = tmppath / "tools"
        config_dir = tmppath / "config"
        ops_state_dir = tmppath / "ops" / "state"
        tools_dir.mkdir(parents=True)
        config_dir.mkdir(parents=True)
        ops_state_dir.mkdir(parents=True)
        
        # Copy env_load.sh
        repo_root = Path(__file__).parent.parent
        env_load_src = repo_root / "tools" / "env_load.sh"
        env_load_dst = tools_dir / "env_load.sh"
        env_load_dst.write_text(env_load_src.read_text())
        env_load_dst.chmod(0o755)
        
        # Create minimal toggles
        toggles = config_dir / "toggles.env"
        toggles.write_text("TEST_KEY=value\n")
        
        # Create test script that sources env_load
        test_script = tmppath / "test.sh"
        test_script.write_text(f"""#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="{tmppath}"
source "{env_load_dst}"
""")
        test_script.chmod(0o755)
        
        # Run test script
        subprocess.run([str(test_script)], check=True, cwd=tmppath)
        
        # Assert state file was written
        state_file = ops_state_dir / "env_state.json"
        assert state_file.exists(), "env_state.json was not written"
        
        # Assert it's valid JSON
        state_data = json.loads(state_file.read_text())
        assert "last_loaded_utc" in state_data
        assert "toggles_path" in state_data
        assert "required_keys_presence" in state_data


if __name__ == "__main__":
    # Run tests manually if not using pytest
    test_secrets_override_toggles()
    print("✅ test_secrets_override_toggles passed")
    
    test_env_doctor_detects_duplicates()
    print("✅ test_env_doctor_detects_duplicates passed")
    
    test_env_doctor_detects_missing_required_keys()
    print("✅ test_env_doctor_detects_missing_required_keys passed")
    
    test_env_state_json_written()
    print("✅ test_env_state_json_written passed")
    
    print("\n✅ All tests passed!")
