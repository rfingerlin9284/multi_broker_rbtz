#!/usr/bin/env python3
"""Validate and emit the AFFIRM/CHECKSUM/SUMMARY-REMINDER block for the prepended instructions file.

Usage: ./validate_prepended.py [path-to-file]
If no path provided it uses the default prompts file in this directory.
"""
import sys
import hashlib
from datetime import datetime, timezone

DEFAULT_PATH = '/home/ing/.config/Code/User/prompts/prepended instructions and rules.instructions.md'


def sha256_hex(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def summarize_sections(lines):
    # crude parse for top-level section headers A) .. H)
    sections = {c: '' for c in list('ABCDEFGH')}
    for line in lines:
        line = line.strip()
        if line.startswith('A)'):
            sections['A'] = line[2:].strip()
        elif line.startswith('B)'):
            sections['B'] = line[2:].strip()
        elif line.startswith('C)'):
            sections['C'] = line[2:].strip()
        elif line.startswith('D)'):
            sections['D'] = line[2:].strip()
        elif line.startswith('E)'):
            sections['E'] = line[2:].strip()
        elif line.startswith('F)'):
            sections['F'] = line[2:].strip()
        elif line.startswith('G)'):
            sections['G'] = line[2:].strip()
        elif line.startswith('H)'):
            sections['H'] = line[2:].strip()
    return sections


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PATH
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"ERROR: cannot read file '{path}': {e}", file=sys.stderr)
        sys.exit(2)

    checksum = sha256_hex(path)
    utc = datetime.now(timezone.utc).isoformat()

    # emit required block
    print(f"AFFIRM: I have read and will follow the prepended instructions — {utc}")
    print(f"CHECKSUM: {checksum}")
    print("SUMMARY-REMINDER:")
    lines = content.splitlines()
    secs = summarize_sections(lines)
    labels = ['A','B','C','D','E','F','G','H']
    for lab in labels:
        val = secs.get(lab,'') or '<no summary found>'
        print(f"{lab}) {val}")


if __name__ == '__main__':
    main()
