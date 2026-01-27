#!/usr/bin/env python3
import json, os, re, time, hashlib, subprocess, shutil
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests  # type: ignore
except Exception:
    requests = None

def utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def sh(cmd):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return p.returncode, p.stdout.strip(), p.stderr.strip()

def log_append(path, msg):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"[{utc_now()}] {msg}\n")

def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def save_json(path, obj):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True)
    os.replace(tmp, path)

def parse_env(env_path):
    env = {}
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line=line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                k,v = line.split("=",1)
                env[k.strip()] = v.strip()
    except Exception:
        pass
    return env

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def try_lock_env(env_path, ops_log):
    try:
        os.chmod(env_path, 0o400)
        log_append(ops_log, f"ENV_LOCK chmod 400 applied to {env_path}")
    except Exception as e:
        log_append(ops_log, f"ENV_LOCK chmod failed: {e}")
    sh(["bash","-lc", f"command -v chattr >/dev/null 2>&1 && sudo chattr +i '{env_path}' || true"])
    log_append(ops_log, f"ENV_LOCK chattr +i attempted on {env_path}")

def quarantine_extra_envs(repo_root, canonical_env, quarantine_dir, ops_log):
    repo_root = Path(repo_root).resolve()
    canonical_env = Path(canonical_env).resolve()
    quarantine_dir = Path(quarantine_dir).resolve()
    quarantine_dir.mkdir(parents=True, exist_ok=True)

    found = []
    for p in repo_root.rglob(".env"):
        try:
            rp = p.resolve()
        except Exception:
            continue
        if rp == canonical_env:
            continue
        if any(part in ("node_modules",".venv","venv","__pycache__",".git") for part in rp.parts):
            continue
        found.append(rp)

    for p in found:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        dest = quarantine_dir / f"{p.name}.{ts}.{p.parent.name}"
        try:
            shutil.move(str(p), str(dest))
            log_append(ops_log, f"ENV_QUARANTINE moved {p} -> {dest}")
        except Exception as e:
            log_append(ops_log, f"ENV_QUARANTINE failed for {p}: {e}")

def systemctl(action, unit):
    return sh(["bash","-lc", f"sudo systemctl {action} {unit}"])

def service_exists(unit):
    code, _, _ = sh(["bash","-lc", f"systemctl list-unit-files | awk '{{print $1}}' | grep -Fx '{unit}' >/dev/null 2>&1"])
    return code == 0

def stop_entry_services(entry_services, ops_log):
    for svc in entry_services:
        if service_exists(svc):
            systemctl("stop", svc)
            log_append(ops_log, f"CIRCUIT_RED stopped entry service: {svc}")

def start_entry_services(entry_services, ops_log):
    for svc in entry_services:
        if service_exists(svc):
            systemctl("start", svc)
            log_append(ops_log, f"CIRCUIT_GREEN started entry service: {svc}")

def ensure_manage_services(manage_services, ops_log):
    for svc in manage_services:
        if service_exists(svc):
            systemctl("start", svc)
            log_append(ops_log, f"MANAGE_ENSURE started manage service: {svc}")

def tail_file(path, max_bytes=200_000):
    p = Path(path)
    if not p.exists() or not p.is_file():
        return ""
    try:
        with open(p, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            seek = max(0, size - max_bytes)
            f.seek(seek)
            return f.read().decode("utf-8", errors="ignore")
    except Exception:
        return ""

def scan_logs(log_files, critical_patterns, noncritical_patterns):
    crit_hits = []
    noncrit_hits = []
    for lf in log_files:
        data = tail_file(lf)
        if not data:
            continue
        for pat in critical_patterns:
            if re.search(re.escape(pat), data, flags=re.IGNORECASE):
                crit_hits.append((lf, pat))
        for pat in noncritical_patterns:
            if re.search(re.escape(pat), data, flags=re.IGNORECASE):
                noncrit_hits.append((lf, pat))
    return crit_hits, noncrit_hits

def oanda_margin_check(env, cfg):
    if not cfg.get("enabled", False):
        return None
    if requests is None:
        return {"ok": True, "note": "requests_not_installed"}

    token = env.get("OANDA_API_KEY") or env.get("OANDA_TOKEN") or env.get("OANDA_ACCESS_TOKEN")
    acct  = env.get("OANDA_ACCOUNT_ID") or env.get("OANDA_ACCOUNT") or env.get("ACCOUNT_ID")
    base  = env.get("OANDA_API_URL") or env.get("OANDA_API_BASE") or cfg.get("practice_api_base_default")
    if not token or not acct or not base:
        return {"ok": False, "error": "missing_oanda_env", "token": bool(token), "acct": bool(acct), "base": bool(base)}

    url = f"{base}/v3/accounts/{acct}/summary"
    try:
        import requests as _rq  # type: ignore
        r = _rq.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=8)
        if r.status_code in (401,403):
            return {"ok": False, "error": f"auth_{r.status_code}", "status": r.status_code}
        r.raise_for_status()
        js = r.json()
        acct_js = js.get("account", {})
        margin_avail = float(acct_js.get("marginAvailable", "0") or "0")
        min_margin = float(cfg.get("min_margin_available_usd", 2.0))
        ok = margin_avail >= min_margin
        return {"ok": ok, "marginAvailable": margin_avail, "min": min_margin}
    except Exception as e:
        return {"ok": False, "error": f"oanda_exception:{type(e).__name__}"}

def bundle_incident(incident_dir, state, crit_hits, env_fingerprint, oanda_check, cfg):
    Path(incident_dir).mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    bundle = {
        "ts": utc_now(),
        "state": state,
        "critical_hits": crit_hits,
        "env_fingerprint": env_fingerprint,
        "oanda_check": oanda_check,
        "services": {"entry": cfg.get("entry_services", []), "manage": cfg.get("manage_services", [])},
        "logs": {}
    }
    for lf in cfg.get("log_files", []):
        bundle["logs"][lf] = tail_file(lf, max_bytes=120_000)
    out_path = Path(incident_dir) / f"incident_{ts}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(bundle, f, indent=2)
    return str(out_path)

def main():
    cfg_path = os.environ.get("OPS_GUARD_CONFIG", "")
    if not cfg_path:
        raise SystemExit("OPS_GUARD_CONFIG not set")

    cfg = load_json(cfg_path, {})
    ops_log = cfg.get("ops_log", "/tmp/ops_guard.log")
    state_file = cfg.get("state_file", "/tmp/circuit_state.json")

    repo_root = cfg.get("repo_root", ".")
    canonical_env = cfg.get("canonical_env", "")
    quarantine_dir = cfg.get("env_quarantine_dir", "./env_quarantine")

    entry_services = cfg.get("entry_services", [])
    manage_services = cfg.get("manage_services", [])
    log_files = cfg.get("log_files", [])

    critical_patterns = cfg.get("critical_patterns", [])
    noncritical_patterns = cfg.get("noncritical_patterns", [])

    failure_threshold = int(cfg.get("failure_threshold_red", 3))
    window_seconds = int(cfg.get("failure_window_seconds", 300))

    state = load_json(state_file, {
        "mode": "GREEN",
        "failures": [],
        "last_env_hash": "",
        "last_incident": "",
        "last_transition": utc_now()
    })

    ensure_manage_services(manage_services, ops_log)

    if canonical_env:
        if os.path.exists(canonical_env):
            quarantine_extra_envs(repo_root, canonical_env, quarantine_dir, ops_log)
            env_hash = sha256_file(canonical_env)
            if not state.get("last_env_hash"):
                state["last_env_hash"] = env_hash
                log_append(ops_log, f"ENV_FINGERPRINT set {env_hash[:12]} for {canonical_env}")
                if cfg.get("env_lock", True):
                    try_lock_env(canonical_env, ops_log)
            else:
                if env_hash != state.get("last_env_hash"):
                    log_append(ops_log, f"CRITICAL env_hash_changed {state['last_env_hash'][:12]} -> {env_hash[:12]}")
                    state["failures"].append({"ts": utc_now(), "type": "ENV_HASH_CHANGED"})
                    state["last_env_hash"] = env_hash
        else:
            log_append(ops_log, f"CRITICAL canonical_env_missing {canonical_env}")
            state["failures"].append({"ts": utc_now(), "type": "CANON_ENV_MISSING"})

    env = parse_env(canonical_env) if canonical_env else {}
    oanda_check = oanda_margin_check(env, cfg.get("oanda", {}))
    if oanda_check and not oanda_check.get("ok", True):
        state["failures"].append({"ts": utc_now(), "type": "OANDA_FAIL", "detail": oanda_check})
        log_append(ops_log, f"CRITICAL OANDA_FAIL {oanda_check}")

    crit_hits, _ = scan_logs(log_files, critical_patterns, noncritical_patterns)
    if crit_hits:
        state["failures"].append({"ts": utc_now(), "type": "LOG_CRITICAL", "detail": {"hit": crit_hits[0]}})
        log_append(ops_log, f"CRITICAL LOG_HIT {crit_hits[0]}")

    now = time.time()
    pruned = []
    for f in state.get("failures", []):
        try:
            dt = datetime.strptime(f["ts"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            if (now - dt.timestamp()) <= window_seconds:
                pruned.append(f)
        except Exception:
            pruned.append(f)
    state["failures"] = pruned

    failure_count = len(state["failures"])
    mode = state.get("mode", "GREEN")

    if failure_count >= failure_threshold and mode != "RED":
        state["mode"] = "RED"
        state["last_transition"] = utc_now()
        log_append(ops_log, f"CIRCUIT TRANSITION -> RED (failures={failure_count} threshold={failure_threshold})")
        stop_entry_services(entry_services, ops_log)
        ensure_manage_services(manage_services, ops_log)
        inc_path = bundle_incident(cfg.get("incident_dir", "./incidents"), state, crit_hits, state.get("last_env_hash",""), oanda_check, cfg)
        state["last_incident"] = inc_path
        log_append(ops_log, f"INCIDENT_BUNDLE saved {inc_path}")

    if failure_count == 0 and mode == "RED":
        state["mode"] = "GREEN"
        state["last_transition"] = utc_now()
        log_append(ops_log, "CIRCUIT TRANSITION RED -> GREEN (stable)")
        start_entry_services(entry_services, ops_log)

    save_json(state_file, state)

if __name__ == "__main__":
    main()
