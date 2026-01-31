#!/usr/bin/env python3
"""
Describe a registry task by id or filename using tools/tasks_registry.json
"""
import argparse
import json
from pathlib import Path

REG = Path(__file__).parent / 'tasks_registry.json'


def main():
    p = argparse.ArgumentParser()
    p.add_argument('task', help='task id or filename')
    args = p.parse_args()
    if not REG.exists():
        print('⚠️ tasks_registry.json not found. Run tools/generate_tasks_registry.py first.')
        return
    tasks = json.loads(REG.read_text())
    match = [t for t in tasks if t['id'] == args.task or t['path'].endswith(args.task)]
    if not match:
        print('Task not found in registry.')
        return
    t = match[0]
    print('---')
    print(f"ID: {t['id']}")
    print(f"Path: {t['path']}")
    print(f"Description: {t['desc']}")
    print('---')


if __name__ == '__main__':
    main()
