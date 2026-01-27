Usage: validator and integration notes

Files:
- `prepended instructions and rules.instructions.md` - original file with agent rules
- `validate_prepended.py` - Python validator that emits AFFIRM/CHECKSUM/SUMMARY-REMINDER for a given file
- `ensure_prepended.sh` - shell wrapper that runs the validator and prints a preview

How to use:
1) Run the shell wrapper to emit the header block (copy/paste into agent chat if desired):

```bash
/home/ing/.config/Code/User/prompts/ensure_prepended.sh
```

2) To integrate with a VS Code AI extension or other agent, configure the extension's "instructions" or "system prompt" field to include the contents of `/home/ing/universal_prepended_instructions.md`.

3) For automated enforcement inside scripts or CI, run `validate_prepended.py` at the start of any agent-run to produce the AFFIRM/CHECKSUM/SUMMARY-REMINDER block.

Limitations:
- These files are helpers: they cannot force third-party models or hosted services to obey the rules. The consuming agent must be configured to call/consume them.
- If you want automated enforcement inside VS Code chat, you must update the extension or create an extension that calls `ensure_prepended.sh` before sending messages.
