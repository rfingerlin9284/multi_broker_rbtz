#!/usr/bin/env python3
"""
Simple terminal task menu: list tasks, show descriptions, and optionally execute with confirmation.
Real-money tasks require `ALLOW_REAL_LAUNCH=1` to be set in the environment.
"""
import json
from pathlib import Path
import subprocess
import os

REG = Path(__file__).parent / 'tasks_registry.json'


def list_tasks(tasks):
    for i, t in enumerate(tasks, 1):
        print(f"{i}. {t['id']:30} - {t['desc']}")


def run_task(task, cwd=None):
    path = Path(task['path'])
    print(f"⚠️  About to run: {task['id']} -> {task['path']}")
    confirm = input('Type YES to confirm execution: ')
    if confirm != 'YES':
        print('Aborted')
        return
    # Safety for real mode
    env = os.environ.copy()
    if 'real' in task['id'].lower() or 'real' in task['path'].lower():
        if env.get('ALLOW_REAL_LAUNCH') != '1':
            print('❌ Real-money task requires ALLOW_REAL_LAUNCH=1 in environment. Aborting.')
            return
    # Execute
    try:
        subprocess.run([str(path)], cwd=cwd)
    except Exception as e:
        print(f"Execution failed: {e}")


def main():
    if not REG.exists():
        print('⚠️ tasks_registry.json not found. Run tools/generate_tasks_registry.py first.')
        return
    tasks = json.loads(REG.read_text())
    while True:
        print('\nAvailable tasks:')
        list_tasks(tasks)
        choice = input('\nEnter number to show/execute, or q to quit: ')
        if choice.lower() == 'q':
            return
        try:
            idx = int(choice) - 1
            t = tasks[idx]
        except Exception:
            print('Invalid choice')
            continue
        print('\n---')
        print(f"ID: {t['id']}")
        print(f"Path: {t['path']}")
        print(f"Description: {t['desc']}")
        action = input("Enter 'r' to run, anything else to return: ")
        if action.lower() == 'r':
            run_task(t)


if __name__ == '__main__':
    main()
