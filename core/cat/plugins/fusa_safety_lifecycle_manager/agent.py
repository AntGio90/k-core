"""
FuSa Safety Lifecycle Manager
- Orchestrates safety lifecycle workflows and work products
- Manages artifacts, traceability, verification, and safety case generation
- Aligns with ISO 26262 and IEC 61508 at a process level (non-normative)

Endpoints (all under /custom/fusa/lifecycle):
- POST /init          Initialize project state
- POST /update        Add/update artifacts and phase statuses
- GET  /state         Retrieve current lifecycle state
- GET  /traceability  Compute and retrieve traceability matrix
- GET  /safety-case   Generate and retrieve path to latest safety case report

Tools (same capabilities via tools):
- bootstrap_safety_lifecycle(JSON)
- add_or_update_artifacts(JSON)
- run_compliance_verification(JSON)
- compute_traceability_matrix()
- generate_safety_case()
"""
import os, json, base64, hashlib, datetime
from typing import Dict, Any, Optional, List

from pydantic import BaseModel, Field
from cryptography.fernet import Fernet

from cat.mad_hatter.decorators import tool, endpoint, plugin
from cat.auth.permissions import check_permissions, AuthResource, AuthPermission
from cat.log import log


# ---------------------------
# Settings
# ---------------------------
class LifecycleSettings(BaseModel):
    encryption_enabled: bool = False
    storage_dir: str = "storage"
    retention_reports: int = 25
    compliance_modes: List[str] = Field(default_factory=lambda: ["ISO 26262", "IEC 61508"])
    default_standard: str = "ISO 26262"
    default_asil: str = "QM"
    phases: List[str] = Field(default_factory=lambda: [
        "Item Definition", "HARA", "Safety Goals", "FSC", "TSC",
        "System Design", "Hardware", "Software", "Integration & Testing",
        "Validation", "Production & Operation", "Safety Case"
    ])


@plugin
def settings_model():
    return LifecycleSettings


# ---------------------------
# Helpers (encryption and storage)
# ---------------------------
def _env_key() -> Optional[bytes]:
    raw = os.getenv("CCAT_FUSA_SECRET") or os.getenv("CCAT_JWT_SECRET")
    if not raw:
        return None
    return base64.urlsafe_b64encode(hashlib.sha256(raw.encode("utf-8")).digest())


def _cipher(settings: LifecycleSettings) -> Optional[Fernet]:
    if not settings.encryption_enabled:
        return None
    key = _env_key()
    if not key:
        log.warning("fusa_safety_lifecycle_manager: encryption enabled but no secret found; using plaintext")
        return None
    return Fernet(key)


def _root(cat=None) -> str:
    if cat is not None:
        return cat.mad_hatter.get_plugin().path
    from cat.looking_glass.cheshire_cat import CheshireCat
    return CheshireCat(None).mad_hatter.get_plugin().path


def _store(root: str, folder: str) -> str:
    p = os.path.join(root, folder)
    os.makedirs(p, exist_ok=True)
    return p


def _w_json(path: str, obj: Any, cipher: Optional[Fernet]):
    data = json.dumps(obj, indent=2).encode("utf-8")
    with open(path, "wb") as f:
        f.write(cipher.encrypt(data) if cipher else data)


def _r_json(path: str, cipher: Optional[Fernet]) -> Any:
    with open(path, "rb") as f:
        data = f.read()
    if cipher:
        data = cipher.decrypt(data)
    return json.loads(data.decode("utf-8"))


def _audit_line(event: Dict[str, Any]) -> bytes:
    return json.dumps({"ts": datetime.datetime.utcnow().isoformat()+"Z", **event}, separators=(",", ":")).encode("utf-8")


def _append_audit(root: str, cipher: Optional[Fernet], event: Dict[str, Any]):
    ap = os.path.join(root, "audit_log.jsonl" + (".enc" if cipher else ""))
    line = _audit_line(event)
    with open(ap, "ab") as f:
        f.write(cipher.encrypt(line) if cipher else line)
        f.write(b"\n")


# ---------------------------
# Core state and logic
# ---------------------------
def _state_path(store: str, cipher: Optional[Fernet]) -> str:
    return os.path.join(store, "state.json" + (".enc" if cipher else ""))


def _load_state(store: str, cipher: Optional[Fernet]) -> Dict[str, Any]:
    p = _state_path(store, cipher)
    if not os.path.exists(p):
        return {}
    return _r_json(p, cipher)


def _save_state(store: str, cipher: Optional[Fernet], state: Dict[str, Any]):
    _w_json(_state_path(store, cipher), state, cipher)


def _init_state(payload: Dict[str, Any], settings: LifecycleSettings, store: str, cipher: Optional[Fernet]) -> Dict[str, Any]:
    project = payload.get("project", {})
    now = datetime.datetime.utcnow().isoformat()+"Z"
    state = {
        "project": {
            "id": project.get("id") or f"proj-{datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "name": project.get("name", "Safety Project"),
            "owner": project.get("owner", "unknown"),
            "standard": project.get("standard", settings.default_standard),
            "asil": project.get("asil", settings.default_asil),
            "created_utc": now
        },
        "phases": {ph: {"status": "planned", "updated": now} for ph in settings.phases},
        "artifacts": {
            "hazards": [],
            "safety_goals": [],
            "requirements": [],
            "designs": [],
            "tests": [],
            "work_products": []
        },
        "compliance": {"last_check": None, "issues": [], "score": 0},
    }
    _save_state(store, cipher, state)
    return state


def _merge_artifacts(state: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
    arts = state.setdefault("artifacts", {})
    for k in ["hazards", "safety_goals", "requirements", "designs", "tests", "work_products"]:
        if k in data:
            if not isinstance(arts.get(k), list):
                arts[k] = []
            # naive merge by id if present
            incoming = data[k] or []
            by_id = {a.get("id"): a for a in arts[k] if isinstance(a, dict) and a.get("id")}
            out: List[Dict[str, Any]] = []
            for item in incoming:
                if isinstance(item, dict) and item.get("id") in by_id:
                    by_id[item["id"]].update(item)
                else:
                    out.append(item)
            arts[k] = [v for _, v in by_id.items()] + out
    # phase updates
    for ph, status in (data.get("phases") or {}).items():
        if ph in state.get("phases", {}):
            state["phases"][ph]["status"] = status
            state["phases"][ph]["updated"] = datetime.datetime.utcnow().isoformat()+"Z"
    return state


def _compute_traceability(state: Dict[str, Any]) -> Dict[str, Any]:
    arts = state.get("artifacts", {})
    reqs = [r for r in arts.get("requirements", []) if isinstance(r, dict)]
    fmea = [h for h in arts.get("hazards", []) if isinstance(h, dict)]
    tests = [t for t in arts.get("tests", []) if isinstance(t, dict)]
    designs = [d for d in arts.get("designs", []) if isinstance(d, dict)]
    tr: Dict[str, Dict[str, List[str]]] = {}
    def add_link(map_: Dict[str, List[str]], key: str, val: str):
        map_.setdefault(key, [])
        if val not in map_[key]:
            map_[key].append(val)
    for r in reqs:
        rid = r.get("id")
        tr[rid] = {"hazards": [], "tests": [], "designs": []}
    # links are read from each item under key 'links': [{type: 'requirement'|'hazard'|'test'|'design', id: '...'}]
    for h in fmea:
        for lk in h.get("links", []):
            if lk.get("type") == "requirement" and lk.get("id") in tr:
                add_link(tr[lk["id"]], "hazards", h.get("id", "unknown"))
    for t in tests:
        for lk in t.get("links", []):
            if lk.get("type") == "requirement" and lk.get("id") in tr:
                add_link(tr[lk["id"]], "tests", t.get("id", "unknown"))
    for d in designs:
        for lk in d.get("links", []):
            if lk.get("type") == "requirement" and lk.get("id") in tr:
                add_link(tr[lk["id"]], "designs", d.get("id", "unknown"))
    return tr


def _verify_compliance(state: Dict[str, Any], standard: str) -> Dict[str, Any]:
    issues: List[str] = []
    arts = state.get("artifacts", {})
    # Minimal heuristic checks common to ISO 26262 / IEC 61508
    if not arts.get("hazards"):
        issues.append("No hazards provided (HARA)")
    if not arts.get("safety_goals"):
        issues.append("No safety goals defined")
    if not arts.get("requirements"):
        issues.append("No safety requirements defined")
    # Check IDs format and links presence
    for r in arts.get("requirements", []):
        if isinstance(r, dict):
            if not r.get("id"):
                issues.append("Requirement without id")
            if not any(lk.get("type") == "hazard" for lk in r.get("links", [])):
                issues.append(f"Requirement {r.get('id','?')} not linked to any hazard")
    tr = _compute_traceability(state)
    untested = [rid for rid, m in tr.items() if len(m.get("tests", [])) == 0]
    if untested:
        issues.append(f"Requirements without tests: {', '.join(untested[:10])}{'...' if len(untested)>10 else ''}")
    score = max(0, 100 - 10*len(issues))
    return {"standard": standard, "issues": issues, "score": score, "generated_utc": datetime.datetime.utcnow().isoformat()+"Z"}


def _safety_case_markdown(state: Dict[str, Any], tr: Dict[str, Any], check: Dict[str, Any]) -> str:
    p = state.get("project", {})
    lines = []
    lines.append(f"# Safety Case Summary\n")
    lines.append(f"Project: {p.get('name','')} (ID: {p.get('id','')})  ")
    lines.append(f"Standard: {p.get('standard','')}  ASIL: {p.get('asil','')}  ")
    lines.append(f"Generated: {datetime.datetime.utcnow().isoformat()}Z\n")
    lines.append("## Phases\n")
    for ph, st in state.get("phases", {}).items():
        lines.append(f"- {ph}: {st.get('status')} (updated {st.get('updated')})")
    lines.append("\n## Traceability Coverage\n")
    total = len(tr)
    tested = sum(1 for m in tr.values() if m.get("tests"))
    lines.append(f"- Requirements total: {total}")
    lines.append(f"- With tests: {tested}")
    lines.append(f"- Coverage: { (tested/total*100.0) if total else 0:.1f}%\n")
    lines.append("## Compliance Check (heuristic)\n")
    lines.append(f"- Standard: {check.get('standard')}  Score: {check.get('score')}\n")
    if check.get("issues"):
        lines.append("- Issues:")
        for it in check["issues"]:
            lines.append(f"  - {it}")
    else:
        lines.append("- No issues detected by heuristics.")
    return "\n".join(lines) + "\n"


# ---------------------------
# Tools
# ---------------------------
@tool("bootstrap_safety_lifecycle", return_direct=False)
def bootstrap_safety_lifecycle(input_by_llm: str, cat) -> str:
    try:
        payload = json.loads(input_by_llm) if input_by_llm else {}
    except Exception:
        payload = {}
    plugin = cat.mad_hatter.get_plugin()
    settings = LifecycleSettings(**(plugin.load_settings() or {}))
    cipher = _cipher(settings)
    store = _store(plugin.path, settings.storage_dir)
    state = _init_state(payload, settings, store, cipher)
    _append_audit(plugin.path, cipher, {"event": "init", "project": state.get("project", {}).get("id")})
    return json.dumps({"message": "initialized", "state_path": _state_path(store, cipher)}, indent=2)


@tool("add_or_update_artifacts", return_direct=False)
def add_or_update_artifacts(input_by_llm: str, cat) -> str:
    try:
        payload = json.loads(input_by_llm) if input_by_llm else {}
    except Exception:
        payload = {}
    plugin = cat.mad_hatter.get_plugin()
    settings = LifecycleSettings(**(plugin.load_settings() or {}))
    cipher = _cipher(settings)
    store = _store(plugin.path, settings.storage_dir)
    state = _load_state(store, cipher) or _init_state({}, settings, store, cipher)
    state = _merge_artifacts(state, payload or {})
    _save_state(store, cipher, state)
    _append_audit(plugin.path, cipher, {"event": "update", "counts": {k: len(v) for k, v in state.get('artifacts',{}).items()}})
    return json.dumps({"message": "updated", "counts": {k: len(v) for k, v in state.get('artifacts',{}).items()}}, indent=2)


@tool("run_compliance_verification", return_direct=False)
def run_compliance_verification(_: str, cat) -> str:
    plugin = cat.mad_hatter.get_plugin()
    settings = LifecycleSettings(**(plugin.load_settings() or {}))
    cipher = _cipher(settings)
    store = _store(plugin.path, settings.storage_dir)
    state = _load_state(store, cipher) or _init_state({}, settings, store, cipher)
    res = _verify_compliance(state, state.get("project", {}).get("standard", settings.default_standard))
    state["compliance"] = {"last_check": res.get("generated_utc"), "issues": res["issues"], "score": res["score"]}
    _save_state(store, cipher, state)
    _append_audit(plugin.path, cipher, {"event": "verify", "score": res.get("score")})
    return json.dumps(res, indent=2)


@tool("compute_traceability_matrix", return_direct=False)
def compute_traceability_matrix(_: str, cat) -> str:
    plugin = cat.mad_hatter.get_plugin()
    settings = LifecycleSettings(**(plugin.load_settings() or {}))
    cipher = _cipher(settings)
    store = _store(plugin.path, settings.storage_dir)
    state = _load_state(store, cipher) or _init_state({}, settings, store, cipher)
    tr = _compute_traceability(state)
    _append_audit(plugin.path, cipher, {"event": "traceability", "requirements": len(tr)})
    return json.dumps(tr, indent=2)


@tool("generate_safety_case", return_direct=False)
def generate_safety_case(_: str, cat) -> str:
    plugin = cat.mad_hatter.get_plugin()
    settings = LifecycleSettings(**(plugin.load_settings() or {}))
    cipher = _cipher(settings)
    store = _store(plugin.path, settings.storage_dir)
    state = _load_state(store, cipher) or _init_state({}, settings, store, cipher)
    tr = _compute_traceability(state)
    check = _verify_compliance(state, state.get("project", {}).get("standard", settings.default_standard))
    md = _safety_case_markdown(state, tr, check)
    ts = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    out_path = os.path.join(store, f"safety_case_{ts}.md" + (".enc" if cipher else ""))
    data = md.encode("utf-8")
    with open(out_path, "wb") as f:
        f.write(cipher.encrypt(data) if cipher else data)
    _append_audit(plugin.path, cipher, {"event": "safety_case", "path": out_path})
    return json.dumps({"message": "safety case generated", "path": out_path}, indent=2)


# ---------------------------
# Endpoints
# ---------------------------
@endpoint.post(
    path="/fusa/lifecycle/init",
    tags=["FuSa Lifecycle"],
    dependencies=[check_permissions(AuthResource.PLUGINS, AuthPermission.WRITE)],
)
def api_init(payload: Dict[str, Any]):
    root = _root()
    from cat.looking_glass.cheshire_cat import CheshireCat
    settings = LifecycleSettings(**(CheshireCat(None).mad_hatter.get_plugin().load_settings() or {}))
    cipher = _cipher(settings)
    store = _store(root, settings.storage_dir)
    state = _init_state(payload or {}, settings, store, cipher)
    _append_audit(root, cipher, {"event": "init", "project": state.get("project", {}).get("id")})
    return {"message": "initialized", "project": state.get("project", {})}


@endpoint.post(
    path="/fusa/lifecycle/update",
    tags=["FuSa Lifecycle"],
    dependencies=[check_permissions(AuthResource.PLUGINS, AuthPermission.WRITE)],
)
def api_update(payload: Dict[str, Any]):
    root = _root()
    from cat.looking_glass.cheshire_cat import CheshireCat
    settings = LifecycleSettings(**(CheshireCat(None).mad_hatter.get_plugin().load_settings() or {}))
    cipher = _cipher(settings)
    store = _store(root, settings.storage_dir)
    state = _load_state(store, cipher) or _init_state({}, settings, store, cipher)
    state = _merge_artifacts(state, payload or {})
    _save_state(store, cipher, state)
    _append_audit(root, cipher, {"event": "update", "counts": {k: len(v) for k, v in state.get('artifacts',{}).items()}})
    return {"message": "updated", "counts": {k: len(v) for k, v in state.get('artifacts',{}).items()}}


@endpoint.get(
    path="/fusa/lifecycle/state",
    tags=["FuSa Lifecycle"],
    dependencies=[check_permissions(AuthResource.PLUGINS, AuthPermission.READ)],
)
def api_state():
    root = _root()
    from cat.looking_glass.cheshire_cat import CheshireCat
    settings = LifecycleSettings(**(CheshireCat(None).mad_hatter.get_plugin().load_settings() or {}))
    cipher = _cipher(settings)
    store = _store(root, settings.storage_dir)
    state = _load_state(store, cipher) or {}
    return {"state": state}


@endpoint.get(
    path="/fusa/lifecycle/traceability",
    tags=["FuSa Lifecycle"],
    dependencies=[check_permissions(AuthResource.PLUGINS, AuthPermission.READ)],
)
def api_traceability():
    root = _root()
    from cat.looking_glass.cheshire_cat import CheshireCat
    settings = LifecycleSettings(**(CheshireCat(None).mad_hatter.get_plugin().load_settings() or {}))
    cipher = _cipher(settings)
    store = _store(root, settings.storage_dir)
    state = _load_state(store, cipher) or {}
    tr = _compute_traceability(state)
    return {"traceability": tr}


@endpoint.get(
    path="/fusa/lifecycle/safety-case",
    tags=["FuSa Lifecycle"],
    dependencies=[check_permissions(AuthResource.PLUGINS, AuthPermission.READ)],
)
def api_safety_case():
    root = _root()
    from cat.looking_glass.cheshire_cat import CheshireCat
    settings = LifecycleSettings(**(CheshireCat(None).mad_hatter.get_plugin().load_settings() or {}))
    cipher = _cipher(settings)
    store = _store(root, settings.storage_dir)
    state = _load_state(store, cipher) or {}
    tr = _compute_traceability(state)
    check = _verify_compliance(state, state.get("project", {}).get("standard", settings.default_standard))
    md = _safety_case_markdown(state, tr, check)
    ts = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    out_path = os.path.join(store, f"safety_case_{ts}.md" + (".enc" if cipher else ""))
    data = md.encode("utf-8")
    with open(out_path, "wb") as f:
        f.write(cipher.encrypt(data) if cipher else data)
    _append_audit(root, cipher, {"event": "safety_case", "path": out_path})
    return {"message": "generated", "path": out_path}