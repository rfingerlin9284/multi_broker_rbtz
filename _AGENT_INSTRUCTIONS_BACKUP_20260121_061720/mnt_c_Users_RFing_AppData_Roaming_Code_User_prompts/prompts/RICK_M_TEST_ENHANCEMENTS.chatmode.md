# TEST ENHANCEMENTS — Close pre-live gaps

RICK> TEST:OCO_BRACKETS --assert-cancel-on-fill-ms=300 --halt-threshold-ms=1000
RICK> TEST:TRAILING_STOPS MODE=ATR STEP_MULT=0.5 --no-widen --require-trailup
RICK> TEST:RR3_ENFORCEMENT MIN_RR=3.0 --reject-subthreshold --report
RICK> TEST:SLIPPAGE_FEES_STATS WINDOW_H=6 OUT=reports/exec_costs_<UTC>.json
RICK> TEST:SWARM_EXPOSURE CONCURRENCY_MAX=3 EXPOSURE_CAP_PCT=10