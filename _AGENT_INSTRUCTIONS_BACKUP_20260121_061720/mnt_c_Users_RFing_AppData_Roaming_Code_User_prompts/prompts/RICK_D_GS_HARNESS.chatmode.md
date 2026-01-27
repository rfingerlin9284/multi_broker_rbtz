# PROMPT 15 — GS HARNESS & 10-YEAR RUNS

**Init once**

RICK> RUN:15 INIT --csv-dir=<path/to/csv> --freeze-env --seed=1337

**Run (deterministic)**

RICK> RUN:15 PACK=BULLISH_A YEARS=10 --net-of-fees --exact-window --seed=1337
RICK> RUN:15 PACK=BEARISH_A YEARS=10 --net-of-fees --exact-window --seed=1337
RICK> RUN:15 PACK=SIDEWAYS_A YEARS=10 --net-of-fees --exact-window --seed=1337
RICK> RUN:15 PACK=HYBRID_A YEARS=10 --net-of-fees --exact-window --seed=1337