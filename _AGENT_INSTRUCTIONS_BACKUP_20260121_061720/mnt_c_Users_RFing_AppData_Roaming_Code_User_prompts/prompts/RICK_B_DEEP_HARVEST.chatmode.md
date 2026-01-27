# PROMPT 13 — DEEP HARVEST (file census, safety, param map)

**Use**

RICK> MODE:ENGINEER
RICK> RUN:13 ROOT=~/ing/RICK/A_NEW_UNIBOT_v001 OUT=audits/deep_harvest_<UTC>

**Produces**
- `manifest.json` (hashes), `strategy_index.csv`
- `safety_findings.md` (forbidden strings, literal secrets)
- `coverage_gaps.md` (missing tests: OCO, trailing, RR≥3, fees/slip, swarm)