"""
FuSa Real-time Safety Monitoring Agent

Features:
- Ingest safety metrics/events via REST
- Configurable thresholds and evaluation intervals
- Scheduled evaluation using WhiteRabbit after cat bootstrap
- Encrypted, timestamped audit trail of all events and alerts
- Tools to query state, alerts, and update thresholds
- REST endpoints for integration with external monitoring systems
"""
import os
import json
import base64
import hashlib
import datetime
from typing import Dict, Any, Optional

from pydantic import BaseModel, Field
from cryptography.fernet import Fernet, InvalidToken

from cat.mad_hatter.decorators import tool, endpoint, plugin, hook
from cat.auth.permissions import check_permissions, AuthResource, AuthPermission
from cat.log import log


class MonitorSettings(BaseModel):
    encryption_enabled: bool = True
    storage_dir: str = "storage"
    evaluation_period_seconds: int = 30
    # threshold spec: name -> {"min": optional, "max": optional}
    thresholds: Dict[str, Dict[str, float]] = Field(default_factory=lambda: {
        "cpu_temp": {"max": 85.0},
        "brake_pressure": {"min": 10.0, "max": 200.0},
    })
    # if true, write every ingested event to audit log
    audit_ingest: bool = True
    # maximum number of audit log lines to keep in rotating log files (simple cap)
    audit_cap_lines: int = 50000
    # ISO reference corpus (optional, for cross-checks and visibility)
    reference_dir: str = "ISO26262"
    iso_edition: str = "2018"


@plugin
def settings_model():
    return MonitorSettings


def _derive_key() -> Optional[bytes]:
    if not settings.encryption_enabled:
        return None
    key = _derive_key()
    if not key:
        log.warning("fusa_realtime_monitor: encryption enabled but no secret found; falling back to plaintext")
        return None
    return Fernet(key)


def _root(cat=None) -> str:
    if cat:
        return cat.mad_hatter.get_plugin().path
    # Lazy instantiate to read plugin folder when endpoint context has no cat
    from cat.looking_glass.cheshire_cat import CheshireCat
    tmp = CheshireCat(None)
    return tmp.mad_hatter.get_plugin().path


def _store_dir(root: str, settings: MonitorSettings) -> str:
    d = os.path.join(root, settings.storage_dir)
    os.makedirs(d, exist_ok=True)
    return d


def _audit_path(root: str, cipher: Optional[Fernet]) -> str:
    return os.path.join(root, "audit_log.jsonl" + (".enc" if cipher else ""))


def _state_path(root: str, cipher: Optional[Fernet]) -> str:
    # Runtime state (latest metrics)
    return os.path.join(root, "state.json" + (".enc" if cipher else ""))


def _alerts_path(root: str, cipher: Optional[Fernet]) -> str:
    return os.path.join(root, "alerts.json" + (".enc" if cipher else ""))


def _write_encrypted_json(path: str, obj: Any, cipher: Optional[Fernet]):
    data = json.dumps(obj, indent=2).encode("utf-8")
    to_write = cipher.encrypt(data) if cipher else data
    with open(path, "wb") as f:
        f.write(to_write)


def _read_encrypted_json(path: str, cipher: Optional[Fernet]) -> Any:
    with open(path, "rb") as f:
        content = f.read()
    if cipher:
        content = cipher.decrypt(content)
    return json.loads(content.decode("utf-8"))


def _append_audit(root: str, event: Dict[str, Any], cipher: Optional[Fernet], cap: int):
    ap = _audit_path(root, cipher)
    line = json.dumps({"ts": datetime.datetime.utcnow().isoformat() + "Z", **event}, separators=(",", ":")).encode("utf-8")
    if cipher:
        line = cipher.encrypt(line)
    with open(ap, "ab") as f:
        f.write(line + b"\n")
    try:
        # crude cap: if file too big, truncate oldest lines by rewriting last N
        with open(ap, "rb") as f:
            lines = f.readlines()
        if len(lines) > cap:
            with open(ap, "wb") as f:
                f.writelines(lines[-cap:])
    except Exception:
        pass


def _load_state(root: str, cipher: Optional[Fernet]) -> Dict[str, Any]:
    sp = _state_path(root, cipher)
    if not os.path.exists(sp):
        return {"metrics": {}}
    return _read_encrypted_json(sp, cipher)


def _save_state(root: str, cipher: Optional[Fernet], state: Dict[str, Any]):
    _write_encrypted_json(_state_path(root, cipher), state, cipher)


def _load_alerts(root: str, cipher: Optional[Fernet]) -> Dict[str, Any]:
    ap = _alerts_path(root, cipher)
    if not os.path.exists(ap):
        return {"alerts": []}
    return _read_encrypted_json(ap, cipher)


def _save_alerts(root: str, cipher: Optional[Fernet], alerts: Dict[str, Any]):
    _write_encrypted_json(_alerts_path(root, cipher), alerts, cipher)

def _resolve_reference_dir(root: str, settings: MonitorSettings) -> Optional[str]:
    candidates = [
        os.path.join(root, settings.reference_dir),
        os.path.join(root, "reference", "ISO_26262", settings.iso_edition),
        os.path.join(root, "ISO_26262"),
        os.path.join(root, "ISO26262"),
    ]
    for p in candidates:
        if os.path.isdir(p):
            return p
    return None


def _evaluate_thresholds(metrics: Dict[str, Any], thresholds: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
    violations = []
    for name, value in metrics.items():
        if name in thresholds:
            spec = thresholds[name]
            min_v = spec.get("min", None)
            max_v = spec.get("max", None)
            if min_v is not None and value < min_v:
                violations.append({"metric": name, "value": value, "type": "below_min", "limit": min_v})
            if max_v is not None and value > max_v:
                violations.append({"metric": name, "value": value, "type": "above_max", "limit": max_v})
    return {"violations": violations}


# ---------------------------
# Hooks: start scheduler after bootstrap
# ---------------------------
@hook("after_cat_bootstrap", priority=1)
def start_periodic_evaluator(cat):
    settings = MonitorSettings(**(cat.mad_hatter.get_plugin().load_settings() or {}))
    if settings.evaluation_period_seconds <= 0:
        return
    # schedule interval job
    def job():
        try:
            # Recompute state/alerts
            root = _root(cat)
            cipher = _cipher(settings)
            state = _load_state(root, cipher)
            alerts = _load_alerts(root, cipher)
            res = _evaluate_thresholds(state.get("metrics", {}), settings.thresholds)
            if res["violations"]:
                ts = datetime.datetime.utcnow().isoformat() + "Z"
                for v in res["violations"]:
                    event = {"event": "threshold_violation", "detail": v, "ts": ts}
                    alerts["alerts"].append(event)
                    _append_audit(root, event, cipher, settings.audit_cap_lines)
                _save_alerts(root, cipher, alerts)
        except Exception as e:
            log.error(f"fusa_realtime_monitor evaluator error: {e}")

    cat.white_rabbit.schedule_interval_job(job, seconds=settings.evaluation_period_seconds)


# ---------------------------
# Tools
# ---------------------------
@tool("current_safety_state", return_direct=False)
def current_safety_state(_: str, cat) -> str:
    """
    Returns the current known metrics and last N alerts from the encrypted state store.
    """
    settings = MonitorSettings(**(cat.mad_hatter.get_plugin().load_settings() or {}))
    cipher = _cipher(settings)
    root = _root(cat)
    state = _load_state(root, cipher)
    alerts = _load_alerts(root, cipher)
    return json.dumps({"metrics": state.get("metrics", {}), "alerts": alerts.get("alerts", [])[-50:]}, indent=2)


@tool("set_thresholds", return_direct=False, examples=[
    "Set thresholds to {'cpu_temp': {'max': 80.0}, 'brake_pressure': {'min': 20, 'max': 180}}"
])
def set_thresholds(input_by_llm: str, cat) -> str:
    """
    Update threshold specification. Input: JSON like {'thresholds': {...}}.
    """
    try:
        payload = json.loads(input_by_llm)
    except Exception:
        payload = {}
    new_th = payload.get("thresholds", {})
    plugin = cat.mad_hatter.get_plugin()
    current = MonitorSettings(**(plugin.load_settings() or {}))
    current.thresholds.update(new_th)
    plugin.save_settings(json.loads(current.model_dump_json()))
    return json.dumps({"message": "thresholds updated", "thresholds": current.thresholds}, indent=2)


@tool("export_monitor_audit_trail", return_direct=False)
def export_monitor_audit_trail(_: str, cat) -> str:
    """
    Export the last 500 decrypted audit lines for analysis.
    """
    settings = MonitorSettings(**(cat.mad_hatter.get_plugin().load_settings() or {}))
    cipher = _cipher(settings)
    root = _root(cat)
    ap = _audit_path(root, cipher)
    if not os.path.exists(ap):
        return json.dumps({"message": "no audit"})
    lines = []
    with open(ap, "rb") as f:
        raw = f.readlines()
    for ln in raw[-500:]:
        try:
            ln = cipher.decrypt(ln.rstrip()) if cipher else ln.rstrip()
            lines.append(json.loads(ln.decode("utf-8")))
        except Exception:
            continue
    return json.dumps({"audit": lines}, indent=2)


# ---------------------------
# REST endpoints
# ---------------------------
@endpoint.post(
    path="/fusa/monitor/ingest",
    tags=["FuSa Monitor"],
    dependencies=[check_permissions(AuthResource.PLUGINS, AuthPermission.WRITE)],
)
def ingest_metric(item: Dict[str, Any]):
    """
    Ingest a metric/state event.
    Body example: {"metrics": {"cpu_temp": 72.3, "brake_pressure": 100.0}, "tags": {"vehicle_id": "car-01"}}
    """
    try:
        from cat.looking_glass.cheshire_cat import CheshireCat
        cat = CheshireCat(None)
        settings = MonitorSettings(**(cat.mad_hatter.get_plugin().load_settings() or {}))
        cipher = _cipher(settings)
        root = _root(cat)
        sd = _store_dir(root, settings)
        _ = sd  # ensure dir exists

        state = _load_state(root, cipher)
        metrics = item.get("metrics", {})
        state["metrics"] = {**state.get("metrics", {}), **metrics}
        _save_state(root, cipher, state)

        if settings.audit_ingest:
            _append_audit(root, {"event": "ingest", "metrics": metrics}, cipher, settings.audit_cap_lines)

        # quick threshold evaluation immediate feedback
        res = _evaluate_thresholds(state["metrics"], settings.thresholds)
        if res["violations"]:
            alerts = _load_alerts(root, cipher)
            ts = datetime.datetime.utcnow().isoformat() + "Z"
            for v in res["violations"]:
                event = {"event": "threshold_violation", "detail": v, "ts": ts}
                alerts["alerts"].append(event)
                _append_audit(root, event, cipher, settings.audit_cap_lines)
            _save_alerts(root, cipher, alerts)

        return {"status": "ok", "violations": res.get("violations", [])}
    except Exception as e:
        log.error(f"fusa_realtime_monitor ingest error: {e}")
        return {"error": "ingest failed"}


@endpoint.get(
    path="/fusa/monitor/audit",
    tags=["FuSa Monitor"],
    dependencies=[check_permissions(AuthResource.PLUGINS, AuthPermission.READ)],
)
def get_audit_preview():
    """
    Return last 200 audit entries (decrypted).
    """
    try:
        from cat.looking_glass.cheshire_cat import CheshireCat
        cat = CheshireCat(None)
        settings = MonitorSettings(**(cat.mad_hatter.get_plugin().load_settings() or {}))
        cipher = _cipher(settings)
        root = _root(cat)
        ap = _audit_path(root, cipher)
        out = []
        if os.path.exists(ap):
            with open(ap, "rb") as f:
                raw = f.readlines()
            for ln in raw[-200:]:
                try:
                    ln = cipher.decrypt(ln.rstrip()) if cipher else ln.rstrip()
                    out.append(json.loads(ln.decode("utf-8")))
                except Exception:
                    continue
        return {"audit": out}
    except Exception as e:
        log.error(f"fusa_realtime_monitor audit error: {e}")
        return {"error": "failed to read audit"}


@endpoint.get(
    path="/fusa/monitor/references",
    tags=["FuSa Real-time Monitor"],
    dependencies=[check_permissions(AuthResource.PLUGINS, AuthPermission.READ)],
)
def list_monitor_references():
    """
    Lists available ISO 26262 PDFs detected for this plugin (for verification).
    """
    try:
        root = _root()
        from cat.looking_glass.cheshire_cat import CheshireCat
        settings = MonitorSettings(**(CheshireCat(None).mad_hatter.get_plugin().load_settings() or {}))
        ref_dir = _resolve_reference_dir(root, settings)
        if not ref_dir:
            return {"edition": settings.iso_edition, "directory": None, "files": [], "parts_detected": []}
        files = [f for f in os.listdir(ref_dir) if f.lower().endswith(".pdf")]
        parts = sorted(list({int(m.group(1)) for f in files for m in [re.search(r"26262-(\\d+)", f)] if m}))
        return {"edition": settings.iso_edition, "directory": ref_dir, "files": files, "parts_detected": parts}
    except Exception as e:
        log.error(f"fusa_realtime_monitor references error: {e}")
        return {"error": "Unable to read references"}