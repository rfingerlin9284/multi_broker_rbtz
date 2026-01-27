#!/bin/bash
# Test Coinbase Authentication - Loads .env properly

cd /home/ing/RICK/MULTI_BROKER_PHOENIX/MULTI_BROKER_PHOENIX

# Activate virtual environment
source ../.venv/bin/activate

# Load .env file using Python (handles multiline properly)
python3 << 'PYTHON_SCRIPT'
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from parent directory
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# Now run the verification
import sys
sys.path.insert(0, str(Path(__file__).parent))

exec(open('tools/verify_coinbase_auth.py').read())
PYTHON_SCRIPT
