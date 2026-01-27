# PROMPT 14 — BUILD WOLFPACKS (select, backtest, bundle)

**Run**

RICK> RUN:14 ROOT=~/ing/RICK/A_NEW_UNIBOT_v001 YEARS=10
CSV_DIR=<path/to/csv> OUT=artifacts/wolfpacks_<UTC>
TF=M15,M30,H1 ENFORCE=costs,slippage,ttl,session
FX_SESS=LN_NY_OVERLAP
CRYPTO_REGIMES='ASIA=00-08,EU=08-16,US=16-24;WEEKEND=tight;OVN_RISK=0.6'

**Artifacts**
- `single_scores.csv`, `synergy_scores.csv`, `packs/*.yaml`
- `strategy_weights.json`, `selection_report.md`