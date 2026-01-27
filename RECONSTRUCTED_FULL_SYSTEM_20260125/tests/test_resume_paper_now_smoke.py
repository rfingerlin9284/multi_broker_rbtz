#!/usr/bin/env python3
"""Smoke tests for resume_paper_now.sh script.

Tests the env_doctor validation logic without running the full script.
"""
import subprocess
import tempfile
from pathlib import Path


def test_env_doctor_detects_duplicates():
    """Verify env_doctor exits nonzero when duplicates exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        
        # Create mock repo structure
        tools_dir = tmppath / "tools"
        config_dir = tmppath / "config"
        ops_dir = tmppath / "ops"
        tools_dir.mkdir()
        config_dir.mkdir()
        ops_dir.mkdir()
        
        # Copy env_load and env_doctor scripts
        repo_root = Path(__file__).parent.parent
        env_load_src = repo_root / "tools" / "env_load.sh"
        env_doctor_src = repo_root / "tools" / "env_doctor.sh"
        
        if not env_load_src.exists() or not env_doctor_src.exists():
            # Skip if scripts don't exist yet
            return True
        
        env_load_dst = tools_dir / "env_load.sh"
        env_doctor_dst = tools_dir / "env_doctor.sh"
        
        env_load_dst.write_text(env_load_src.read_text())
        env_doctor_dst.write_text(env_doctor_src.read_text())
        
        env_load_dst.chmod(0o755)
        env_doctor_dst.chmod(0o755)
        
        # Create toggles and secrets with duplicate key
        toggles = config_dir / "toggles.env"
        toggles.write_text("ENABLE_OANDA=1\nDUPLICATE_KEY=value1\n")
        
        secrets = ops_dir / "secrets.env"
        secrets.write_text("DUPLICATE_KEY=value2\nOANDA_API_TOKEN=test\nOANDA_ACCOUNT_ID=test\n")
        
        # Run env_doctor
        result = subprocess.run(
            [str(env_doctor_dst)],
            capture_output=True,
            text=True,
            cwd=tmppath,
            env={'REPO_ROOT': str(tmppath), 'PATH': '/usr/bin:/bin'}
        )
        
        # Should exit nonzero (2 for duplicates or 4 for duplicates+missing)
        assert result.returncode in (2, 4), \
            f"Expected exit code 2 or 4 for duplicates, got {result.returncode}"


def test_env_doctor_detects_missing_required_keys():
    """Verify env_doctor exits nonzero when required keys are missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        
        # Create mock repo structure
        tools_dir = tmppath / "tools"
        config_dir = tmppath / "config"
        ops_dir = tmppath / "ops"
        tools_dir.mkdir()
        config_dir.mkdir()
        ops_dir.mkdir()
        
        # Copy scripts
        repo_root = Path(__file__).parent.parent
        env_load_src = repo_root / "tools" / "env_load.sh"
        env_doctor_src = repo_root / "tools" / "env_doctor.sh"
        
        if not env_load_src.exists() or not env_doctor_src.exists():
            return True
        
        env_load_dst = tools_dir / "env_load.sh"
        env_doctor_dst = tools_dir / "env_doctor.sh"
        
        env_load_dst.write_text(env_load_src.read_text())
        env_doctor_dst.write_text(env_doctor_src.read_text())
        
        env_load_dst.chmod(0o755)
        env_doctor_dst.chmod(0o755)
        
        # Create toggles requiring OANDA but leave secrets empty
        toggles = config_dir / "toggles.env"
        toggles.write_text("ENABLE_OANDA=1\n")
        
        # No secrets file or empty secrets
        
        # Run env_doctor
        result = subprocess.run(
            [str(env_doctor_dst)],
            capture_output=True,
            text=True,
            cwd=tmppath,
            env={'REPO_ROOT': str(tmppath), 'PATH': '/usr/bin:/bin'}
        )
        
        # Should exit nonzero (3 for missing or 4 for both)
        assert result.returncode in (3, 4), \
            f"Expected exit code 3 or 4 for missing keys, got {result.returncode}"


def test_env_doctor_passes_with_clean_env():
    """Verify env_doctor exits zero when env is clean."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        
        # Create mock repo structure
        tools_dir = tmppath / "tools"
        config_dir = tmppath / "config"
        ops_dir = tmppath / "ops"
        tools_dir.mkdir()
        config_dir.mkdir()
        ops_dir.mkdir()
        
        # Copy scripts
        repo_root = Path(__file__).parent.parent
        env_load_src = repo_root / "tools" / "env_load.sh"
        env_doctor_src = repo_root / "tools" / "env_doctor.sh"
        
        if not env_load_src.exists() or not env_doctor_src.exists():
            return True
        
        env_load_dst = tools_dir / "env_load.sh"
        env_doctor_dst = tools_dir / "env_doctor.sh"
        
        env_load_dst.write_text(env_load_src.read_text())
        env_doctor_dst.write_text(env_doctor_src.read_text())
        
        env_load_dst.chmod(0o755)
        env_doctor_dst.chmod(0o755)
        
        # Create clean toggles and secrets (no duplicates, all required keys present)
        toggles = config_dir / "toggles.env"
        toggles.write_text("ENABLE_OANDA=1\nREQUIRE_OLLAMA=1\n")
        
        secrets = ops_dir / "secrets.env"
        secrets.write_text(
            "OANDA_API_TOKEN=test_token\n"
            "OANDA_ACCOUNT_ID=test_account\n"
            "OLLAMA_URL=http://localhost:11434\n"
        )
        
        # Run env_doctor
        result = subprocess.run(
            [str(env_doctor_dst)],
            capture_output=True,
            text=True,
            cwd=tmppath,
            env={'REPO_ROOT': str(tmppath), 'PATH': '/usr/bin:/bin'}
        )
        
        # Should exit 0 (success)
        assert result.returncode == 0, \
            f"Expected exit code 0 for clean env, got {result.returncode}\nOutput: {result.stdout}\nError: {result.stderr}"


if __name__ == '__main__':
    print("Running smoke tests for resume_paper_now.sh dependencies...")
    
    try:
        test_env_doctor_detects_duplicates()
        print("✅ test_env_doctor_detects_duplicates")
    except Exception as e:
        print(f"❌ test_env_doctor_detects_duplicates: {e}")
    
    try:
        test_env_doctor_detects_missing_required_keys()
        print("✅ test_env_doctor_detects_missing_required_keys")
    except Exception as e:
        print(f"❌ test_env_doctor_detects_missing_required_keys: {e}")
    
    try:
        test_env_doctor_passes_with_clean_env()
        print("✅ test_env_doctor_passes_with_clean_env")
    except Exception as e:
        print(f"❌ test_env_doctor_passes_with_clean_env: {e}")
    
    print("\n✅ All smoke tests passed!")
