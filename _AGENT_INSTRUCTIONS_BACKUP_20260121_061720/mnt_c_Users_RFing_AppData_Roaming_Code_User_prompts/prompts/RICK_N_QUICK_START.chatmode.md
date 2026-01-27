# QUICK START — One-liners

RICK> MODE:ENGINEER
RICK> RULES:CHECK --print --env=venv --tz=UTC --seed=1337 --forbid="passphrase,api-fxpractice,practice,sandbox,ws-sandbox"
RICK> RUN:UI TMUX_SETUP NAME=RICKGRID STYLE=neon4k LAYOUT='3x panes per terminal; 4 terminals'
RICK> RUN:13 ROOT=~/ing/RICK/A_NEW_UNIBOT_v001 OUT=audits/deep_harvest_<UTC>
RICK> RUN:AUDIT ROOT=./ --grep 'passphrase|api-fxpractice|practice|paper|sandbox|demo' --secrets-literals --dotenv-perms=0600 --out=audits/compliance_<UTC>.md
RICK> RUN:14 ROOT=~/ing/RICK/A_NEW_UNIBOT_v001 YEARS=10 CSV_DIR=<csv> OUT=artifacts/wolfpacks_<UTC> TF=M15,M30,H1 ENFORCE=costs,slippage,ttl,session
RICK> RUN:15 INIT --csv-dir=<csv> --freeze-env --seed=1337
RICK> RUN:15 PACK=BULLISH_A YEARS=10 --net-of-fees --exact-window --seed=1337
RICK> RUN:15 PACK=BEARISH_A YEARS=10 --net-of-fees --exact-window --seed=1337
RICK> RUN:15 PACK=SIDEWAYS_A YEARS=10 --net-of-fees --exact-window --seed=1337
RICK> RUN:15 PACK=HYBRID_A YEARS=10 --net-of-fees --exact-window --seed=1337
RICK> RUN:18 DAILY OUT=reports/daily_<UTC>.md
RICK> RUN:19 ARM ERROR_RATE_MAX=0.02 SLIP_MULT_MAX=1.5 DD_DAY_MAX=0.05
RICK> RUN:20 PROPOSE RISK=0.001 CONCURRENCY=1