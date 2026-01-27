# PROMPT 16 — ADVISORY SIGNALS (offline, file-drop only)

**Ingest → quantify → correlate → brief**

RICK> RUN:16 INGEST NEWS=./data/newsdrop/*.jsonl SOCIAL=./data/socialdrop/*.jsonl MAX_AGE_H=24
RICK> RUN:16 QUANTIFY LOOKBACK_D=180 DECAY_MIN=90 OUT=reports/news_edge_<UTC>.json
RICK> RUN:16 CORR ASSETS=BTC,ETH,SPX,DX_Y,GC,CL,UST2Y LAGS_H=6 OUT=reports/corr_<UTC>.json
RICK> RUN:16 BRIEF NEWS=reports/news_edge_<UTC>.json CORR=reports/corr_<UTC>.json OUT=reports/advisory_brief_<UTC>.md

*(Promotion to live risk needs CHANGE PROPOSAL + APPROVE 841921)*