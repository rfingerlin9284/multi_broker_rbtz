# Historical Change Log

This file records all manual approvals and significant changes that affect sensitive files (for example `ops/secrets.env`).

Rules:

- Any approval to modify, copy, or include `ops/secrets.env` in a build must be recorded here via `tools/secure_env_manager.py approve`.
- Automated tools must verify the presence of a matching approval entry here before performing any action that affects secrets.

Entries (most recent first):
