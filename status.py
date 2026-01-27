#!/usr/bin/env python3
"""
ONE-COMMAND AUTO-TUNING STATUS
Run this anytime to see what system is learning
"""

import subprocess
import sys
from pathlib import Path

def main():
    script = Path("/home/ing/RICK/MULTI_BROKER_PHOENIX/view_auto_tuning.py")
    subprocess.run([sys.executable, str(script)])

if __name__ == "__main__":
    main()
