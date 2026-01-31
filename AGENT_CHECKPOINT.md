# Agent Checkpoint: Mandatory pre-action read of historical approvals

All automated agents or humans using CLI tooling must perform the following before any action affecting secrets or performing sensitive deployments:

1. Run `python3 tools/agent_compliance.py` or call `check_historical_log()` from `tools.agent_compliance`.
2. Review the last recorded approval(s) in `HISTORICAL_CHANGE_LOG.md`.
3. If performing a secrets inclusion or modification, ensure a valid approval exists and that you provide the approval id in commit messages or build commands (e.g., `--approval-id <id>`).

This check should be integrated into onboarding and agent runtime startup scripts where possible.
