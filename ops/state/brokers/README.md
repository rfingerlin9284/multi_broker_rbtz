# Broker State Directory

This directory contains runtime state files for the multi-broker system.

## Files

### Per-Broker Heartbeat Files

- `oanda.json` - OANDA broker heartbeat and state
- `coinbase.json` - Coinbase broker heartbeat and state
- `ibkr.json` - IBKR broker heartbeat and state

Each broker heartbeat file contains:

```json
{
  "broker": "oanda",
  "state": "ACTIVE|PAUSED|FAILED|DISABLED|STARTING",
  "fail_count": 0,
  "last_error": "error description or null",
  "timestamp": "2026-01-25T12:34:56.789Z",
  "epoch": 1706184896.789
}
```

### Orchestrator Summary

- `summary.json` - Aggregated status from all brokers
  - Written by orchestrator every check interval
  - Contains broker process states, heartbeat ages, and errors

### PID Files

- `oanda.pid` - OANDA broker process ID
- `coinbase.pid` - Coinbase broker process ID
- `ibkr.pid` - IBKR broker process ID
- `../orchestrator.pid` - Orchestrator process ID (one level up)

## State Machine

Each broker follows this state machine:

1. **DISABLED** - Broker toggle is off (`BROKER_X_ENABLED=0`)
2. **STARTING** - Process starting up
3. **PAUSED** - Healthy but not trading (gate failure or guard locked)
4. **ACTIVE** - Healthy and trading
5. **FAILED** - Circuit breaker tripped, needs manual intervention

## Circuit Breaker

Each broker has an independent circuit breaker:

- Failure count increments on errors
- Circuit trips at threshold (default: 5 failures)
- Failed broker → FAILED state
- Other brokers continue unaffected

## Monitoring

Watch broker status in real-time:

```bash
# View all heartbeats
watch -n 2 'cat ops/state/brokers/*.json | jq .'

# View summary
cat ops/state/brokers/summary.json | jq .

# Use status script
./tools/status_full_system.sh
```

## Troubleshooting

If a broker is FAILED:

1. Check `last_error` in heartbeat file
2. Check broker logs: `logs/{broker}/engine.log`
3. Check fail_count vs threshold
4. Reset by stopping and starting the broker:
   ```bash
   ./tools/stop_broker.sh {broker}
   ./tools/start_broker.sh {broker}
   ```
