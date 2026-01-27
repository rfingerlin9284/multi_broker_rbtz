#!/usr/bin/env python3
import json, os
from datetime import datetime, timezone
from pathlib import Path

def utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def append(path, msg):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"[{utc_now()}] {msg}\n")

def main():
    cfg_path = os.environ.get("OPS_GUARD_CONFIG","")
    if not cfg_path:
        raise SystemExit("OPS_GUARD_CONFIG not set")
    with open(cfg_path,"r",encoding="utf-8") as f:
        cfg = json.load(f)

    state = load_json(cfg.get("state_file","/tmp/circuit_state.json"), {})
    out = cfg.get("hourly_report","/tmp/hourly_report.log")

    mode = state.get("mode","UNKNOWN")
    failures = state.get("failures",[])
    last_inc = state.get("last_incident","")
    last_tr = state.get("last_transition","")
    env_hash = state.get("last_env_hash","")

    append(out, f"OPS_GUARD mode={mode} failures={len(failures)} last_transition={last_tr} env_hash={env_hash[:12]} last_incident={last_inc}")

if __name__ == "__main__":
    main()
