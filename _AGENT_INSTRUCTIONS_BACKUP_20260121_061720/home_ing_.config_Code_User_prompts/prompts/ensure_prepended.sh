#!/usr/bin/env bash
# Print the universal prepended block and run the local validator to emit the AFFIRM/CHECKSUM/SUMMARY-REMINDER
FILE="/home/ing/universal_prepended_instructions.md"
VALIDATOR="/home/ing/.config/Code/User/prompts/validate_prepended.py"

if [ ! -f "$FILE" ]; then
  echo "ERROR: universal prepended file not found at $FILE" >&2
  exit 2
fi

if [ ! -x "$VALIDATOR" ]; then
  # try to run with python if not executable
  python3 "$VALIDATOR" "$FILE"
else
  "$VALIDATOR" "$FILE"
fi

echo "---" 
echo "Preview of universal prepended instructions ($FILE):"
sed -n '1,120p' "$FILE"
