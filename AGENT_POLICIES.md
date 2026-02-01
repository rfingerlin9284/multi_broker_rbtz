# Agent Policies (enforced)

Purpose
-------
Ensure agents (AI, human-assisted, Copilot) do not modify or access secrets without explicit manual approval recorded by the repository owner.

Mandatory Rules
---------------
1. Agents must NOT overwrite, edit, rename, or otherwise alter `ops/secrets.env` or any `.locked` snapshot files.
2. Any action that would modify the canonical `ops/secrets.env` must be executed via `tools/agent_executor.py` and accompanied by an approval id recorded in `HISTORICAL_CHANGE_LOG.md`.
3. Agents must request the approval id from the user and never accept the pin directly via environment variables or other automatic stores.
4. Agents must consult `AGENT_CHECKPOINT.md` and `HISTORICAL_CHANGE_LOG.md` before proposing actions that affect secrets.

VS Code Guidance
----------------
- Add `.vscode/settings.json` (recommended) to discourage accidental edits to secrets by marking snapshot files as excluded and adding clear README files in `secrets_snapshot/`.
- Note: VS Code and Copilot may still open files for editing; the strongest technical guards are permission locks and git hooks.

Enforcement
-----------
- Git hooks (`pre-commit` and `commit-msg`) will block commits that include changes to `ops/secrets.env` without an approval id.
- `tools/lock_secrets.sh` sets tight file permissions (0400) to block most unprivileged edits.

If an agent requests a secret-modifying action, the agent must:
1. Ask the user to create an approval id using: `python3 tools/secure_env_manager.py approve --message "reason"` (user uses PIN interactively).
2. Wait for the user to confirm approval id and provide it to the agent.
3. Use `tools/agent_executor.py --approval-id <id> -- <command>` to run the command.

Special rule for listing changed files (`get_changed_files`):
- Agents must not call `get_changed_files` or equivalent git status functions directly.
- Agents must request the approval id and request the user's PIN **in chat** (do not accept PINs from env vars or files).
- After receiving approval id and PIN, agents must execute `python3 tools/require_get_changed_files.py --approval-id <id>` (the script will prompt for PIN if not provided) to obtain the changed-files list.

All approvals are recorded in `HISTORICAL_CHANGE_LOG.md` and are auditable.
