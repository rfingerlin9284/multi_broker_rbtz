#!/usr/bin/env python3
"""
Scan the repository for taskable scripts (launch_* and tools) and generate tools/tasks_registry.json.
"""
from pathlib import Path
import json
import re

ROOT = Path(__file__).parent.parent
OUT = Path(__file__).parent / "tasks_registry.json"


def extract_desc(p: Path):
    try:
        text = p.read_text(errors='ignore')
    except Exception:
        return ""
    # First look for triple-quoted module docstring
    m = re.search(r'"""(.*?)"""', text, re.S)
    if m:
        s = m.group(1).strip().splitlines()[0]
        return s
    # Fallback to first commented line
    for line in text.splitlines()[:10]:
        line = line.strip()
        if line.startswith('#'):
            return line.lstrip('#').strip()
    return "(no description)"


def main():
    tasks = []
    # Search for scripts in root matching launch_*.sh and launch_*.py
    for p in ROOT.glob('launch_*'):
        if p.is_file():
            tasks.append({"id": p.name, "path": str(p.relative_to(ROOT)), "desc": extract_desc(p)})
    # Tools with main guards
    for p in (ROOT / 'tools').glob('*.py'):
        text = p.read_text(errors='ignore')
        if 'if __name__' in text or p.name.startswith('run_'):
            tasks.append({"id": p.stem, "path": str(p.relative_to(ROOT)), "desc": extract_desc(p)})
    OUT.write_text(json.dumps(tasks, indent=2))
    print(f"✅ tasks_registry.json created with {len(tasks)} entries -> {OUT}")


if __name__ == '__main__':
    main()
