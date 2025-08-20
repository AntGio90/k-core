"""
FuSa Documentation Review Agent Plugin

Features:
- Tools for analyzing provided safety documentation bundles
- Automated ISO 26262 / IEC 61508 checklist validation (heuristic checks)
- Traceability and consistency checks across requirements, FMEA entries, and test cases
- Structured report generation (JSON and Markdown)
- Audit trail with access controls (plaintext at rest)
- Customizable settings via settings.json (auto schema)
- REST endpoints for retrieving last report and uploading docs

Security:
- Records and reports are stored in plaintext at rest (encryption disabled)
- Endpoint access is guarded via core permissions (PLUGINS READ/WRITE)

Usage (tools):
- analyze_safety_documents: Accepts a JSON string with documents and options. Returns a path to the saved report and a short summary.
- get_last_doc_review_report: Returns last generated report preview.

Usage (endpoints):
- GET /custom/fusa/doc-review/report
- POST /custom/fusa/doc-review/analyze
"""
# top-level imports in this file
import os
import json
import base64
import hashlib
import datetime
from typing import Dict, Any, List, Tuple, Optional

from pydantic import BaseModel, Field
from cryptography.fernet import Fernet, InvalidToken

from cat.mad_hatter.decorators import tool, endpoint, plugin, hook
from cat.auth.permissions import check_permissions, AuthResource, AuthPermission
from cat.log import log
import re
from io import BytesIO
import tempfile
import shutil
import subprocess

# Optional imports for simple PDF generation (ReportLab)
try:
    from reportlab.pdfgen import canvas as _rl_canvas
    from reportlab.lib.pagesizes import A4 as _RL_A4
    from reportlab.lib.units import mm as _RL_MM
except Exception:
    _rl_canvas = None
    _RL_A4 = None
    _RL_MM = None


# ---------------------------
# Settings model and helpers
# ---------------------------
class DocReviewSettings(BaseModel):
    # Accepted standards to check references for
    accepted_standards: List[str] = Field(default_factory=lambda: ["ISO 26262", "IEC 61508"])
    # Default output format (json or markdown)
    report_format: str = "json"
    # Enable encryption for stored artifacts and audit log
    encryption_enabled: bool = True
    # Regex-like hints to detect requirement IDs in content
    requirement_id_hints: List[str] = Field(
        default_factory=lambda: ["REQ-", "SR-", "ASIL-", "FSR-"]
    )
    # Traceability fields expected in each section
    expected_mappings: Dict[str, List[str]] = Field(
        default_factory=lambda: {
            "requirements": ["id", "text", "source"],
            "fmea": ["id", "requirement_ids", "severity", "occurrence", "detection"],
            "tests": ["id", "requirement_ids", "status", "results"],
        }
    )
    # Minimum fields for compliance sections
    expected_sections: List[str] = Field(
        default_factory=lambda: ["requirements", "fmea", "tests"]
    )
    # Access “roles” advisory (enforced by API permissions; used here for audit metadata)
    access_roles: List[str] = Field(default_factory=lambda: ["FuSaEngineer", "VnV", "Compliance"])
    # Where to store encrypted reports/audit (relative to plugin folder)
    storage_dir: str = "storage"
    # Retain max N reports
    retention_reports: int = 25
    # Use ISO reference corpus and where to read it from
    use_reference_corpus: bool = True
    reference_dir: str = "ISO26262"
    iso_edition: str = "2018"
    checklist_dir: str = "checklists"


@plugin
def settings_model():
    return DocReviewSettings


# ---------------------------
# Encryption helpers
# ---------------------------
def _derive_fernet_key() -> Optional[bytes]:
    # Encryption explicitly disabled: always return None
    return None


def _get_cipher(settings: DocReviewSettings) -> Optional[Fernet]:
    # Encryption explicitly disabled: always return None
    return None


def _write_encrypted_json(path: str, obj: Any, cipher: Optional[Fernet]):
    data = json.dumps(obj, indent=2).encode("utf-8")
    to_write = cipher.encrypt(data) if cipher else data
    with open(path, "wb") as f:
        f.write(to_write)


def _read_encrypted_json(path: str, cipher: Optional[Fernet]) -> Any:
    with open(path, "rb") as f:
        content = f.read()
    if cipher:
        try:
            content = cipher.decrypt(content)
        except InvalidToken:
            log.error("fusa_doc_review: invalid decryption key for file")
            raise
    return json.loads(content.decode("utf-8"))


def _append_audit(plugin_root: str, event: Dict[str, Any], cipher: Optional[Fernet]):
    audit_path = os.path.join(plugin_root, "audit_log.jsonl" + (".enc" if cipher else ""))
    line = json.dumps(
        {"ts": datetime.datetime.utcnow().isoformat() + "Z", **event},
        separators=(",", ":"),
    ).encode("utf-8")
    if cipher:
        line = cipher.encrypt(line)
    with open(audit_path, "ab") as f:
        f.write(line + b"\n")


# ---------------------------
# Core analysis logic
# ---------------------------
def _ensure_storage(plugin_root: str, folder: str) -> str:
    p = os.path.join(plugin_root, folder)
    os.makedirs(p, exist_ok=True)
    return p


def _normalize_input(docs: Dict[str, Any]) -> Dict[str, Any]:
    # Accept either raw text, JSON arrays, or minimal dicts
    norm = {"requirements": [], "fmea": [], "tests": []}

    if "requirements" in docs:
        for r in docs["requirements"] or []:
            if isinstance(r, str):
                norm["requirements"].append({"id": r, "text": ""})
            elif isinstance(r, dict):
                norm["requirements"].append(r)
            # else ignore unknown types

    if "fmea" in docs:
        for f in docs["fmea"] or []:
            if isinstance(f, str):
                # Coerce to minimal structure; full fields will be flagged by field checks
                norm["fmea"].append({
                    "id": f[:50] or "fmea-item",
                    "text": f,
                    "requirement_ids": []
                })
            elif isinstance(f, dict):
                norm["fmea"].append(f)

    if "tests" in docs:
        for t in docs["tests"] or []:
            if isinstance(t, str):
                norm["tests"].append({
                    "id": t[:50] or "test-item",
                    "text": t,
                    "requirement_ids": [],
                    "status": "unknown",
                    "results": ""
                })
            elif isinstance(t, dict):
                norm["tests"].append(t)

    return norm


def _check_sections(norm: Dict[str, Any], expected_sections: List[str]) -> List[str]:
    missing = []
    for s in expected_sections:
        if s not in norm or not isinstance(norm[s], list) or len(norm[s]) == 0:
            missing.append(s)
    return missing


def _check_required_fields(items: List[Dict[str, Any]], required_fields: List[str]) -> List[Tuple[str, List[str]]]:
    issues = []
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            # Entire set of fields is missing if item is not a dict
            issues.append((f"index:{idx}", required_fields))
            continue
        miss = [f for f in required_fields if f not in item]
        if miss:
            issues.append((f"index:{idx}", miss))
    return issues


def _collect_ids(items: List[Dict[str, Any]]) -> List[str]:
    ids = []
    for it in items:
        if isinstance(it, dict) and "id" in it:
            ids.append(it["id"])
    return ids


def _traceability_issues(norm: Dict[str, Any]) -> Dict[str, List[str]]:
    req_ids = set(_collect_ids(norm["requirements"]))
    fmea_map: Dict[str, List[str]] = {}
    test_map: Dict[str, List[str]] = {}

    for f in norm["fmea"]:
        if not isinstance(f, dict):
            continue
        for rid in f.get("requirement_ids", []):
            fmea_map.setdefault(rid, []).append(f.get("id", "unknown"))

    for t in norm["tests"]:
        if not isinstance(t, dict):
            continue
        for rid in t.get("requirement_ids", []):
            test_map.setdefault(rid, []).append(t.get("id", "unknown"))

    missing_fmea = [r for r in req_ids if r not in fmea_map]
    missing_tests = [r for r in req_ids if r not in test_map]
    orphan_fmea = [rid for rid in fmea_map.keys() if rid not in req_ids]
    orphan_tests = [rid for rid in test_map.keys() if rid not in req_ids]

    return {
        "requirements_without_fmea": missing_fmea,
        "requirements_without_tests": missing_tests,
        "fmea_orphans": orphan_fmea,
        "test_orphans": orphan_tests,
    }


def _compliance_checklists(norm: Dict[str, Any], accepted_standards: List[str], settings: DocReviewSettings, plugin_root: str) -> Dict[str, Any]:
    # Heuristic, extend as necessary
    checks = []
    notes = []
    # ISO 26262: ensure ASIL assignment appears if mentioned
    asil_mentions = any(
        ("asil" in (r.get("text", "") + " " + r.get("id", "")).lower()) for r in norm["requirements"]
    )
    checks.append({"standard": "ISO 26262", "rule": "ASIL presence in safety reqs", "passed": asil_mentions})
    if not asil_mentions:
        notes.append("Some requirements do not include ASIL rationale or classification.")
    # IEC 61508: ensure safety lifecycle references are present (heuristic)
    lifecycle_mentions = any(
        "safety lifecycle" in (r.get("text", "").lower()) for r in norm["requirements"]
    )
    checks.append({"standard": "IEC 61508", "rule": "Safety lifecycle references", "passed": lifecycle_mentions})
    if not lifecycle_mentions:
        notes.append("Consider referencing IEC 61508 lifecycle activities for traceability.")
    # Extendable placeholder for more formal checks
    active = [c for c in checks if c["standard"] in accepted_standards]

    # Load and evaluate ISO 26262 checklist items (edition-aware)
    checklist_info = {"edition": settings.iso_edition, "files_loaded": [], "summary": {"total": 0, "passed": 0, "failed": 0, "manual": 0}, "results": []}
    cl_dir = _resolve_checklist_dir(plugin_root, settings)
    if cl_dir:
        items, files_loaded = _load_checklist_items(cl_dir)
        checklist_info["files_loaded"] = files_loaded
        if items:
            eval_res = _evaluate_checklist_items(norm, items)
            checklist_info["summary"] = eval_res.get("summary", checklist_info["summary"])
            checklist_info["results"] = eval_res.get("results", [])

    return {"active_checks": active, "notes": notes, "checklists": checklist_info}


def _format_report(report: Dict[str, Any], fmt: str) -> str:
    if fmt == "markdown":
        parts = ["# FuSa Documentation Review Report"]
        parts.append(f"- generated_utc: {report['metadata']['generated_utc']}")
        parts.append("## Summary")
        parts.append(f"- requirements: {report['summary']['num_requirements']}")
        parts.append(f"- fmea: {report['summary']['num_fmea']}")
        parts.append(f"- tests: {report['summary']['num_tests']}")
        parts.append("## Compliance")
        for c in report["compliance"]["active_checks"]:
            parts.append(f"- [{c['standard']}] {c['rule']}: {'PASS' if c['passed'] else 'FAIL'}")
        # Add checklist section if present
        comp = report.get("compliance", {})
        cl = comp.get("checklists", {})
        if cl:
            parts.append("## ISO 26262 Checklists")
            parts.append(f"- edition: {report['metadata'].get('iso_edition', 'N/A')}")
            parts.append(f"- files_loaded: {len(cl.get('files_loaded', []))}")
            summ = cl.get("summary", {}) or {}
            parts.append(f"- auto_passed: {summ.get('passed', 0)}")
            parts.append(f"- auto_failed: {summ.get('failed', 0)}")
            parts.append(f"- manual: {summ.get('manual', 0)}")
            # show up to 5 failing items
            fails = [r for r in (cl.get('results') or []) if r.get('requires_manual') is False and r.get('passed') is False]
            if fails:
                parts.append("### Checklist items needing attention (sample)")
                for r in fails[:5]:
                    ident = r.get("id") or "N/A"
                    clause = r.get("clause") or "N/A"
                    title = r.get("title") or "N/A"
                    src = r.get("source_file") or "checklist"
                    parts.append(f"- [{src}] {ident} ({clause}): {title}")
        parts.append("## Traceability Issues")
        for k, v in report["traceability"].items():
            parts.append(f"- {k}: {len(v)}")
        parts.append("## Recommendations")
        for r in report.get("recommendations", []):
            parts.append(f"- {r}")
        return "\n".join(parts)
    # default json string
    return json.dumps(report, indent=2)


def _build_report(norm: Dict[str, Any], settings: DocReviewSettings, plugin_root: str) -> Dict[str, Any]:
    missing_sections = _check_sections(norm, settings.expected_sections)

    field_issues = {}
    for sec, required in settings.expected_mappings.items():
        field_issues[sec] = _check_required_fields(norm.get(sec, []), required)

    trace = _traceability_issues(norm)
    comp = _compliance_checklists(norm, settings.accepted_standards, settings, plugin_root)

    recommendations = []
    if missing_sections:
        recommendations.append(f"Missing sections: {', '.join(missing_sections)}.")
    if trace["requirements_without_fmea"]:
        recommendations.append("Add/verify FMEA entries for all requirements lacking linkage.")
    if trace["requirements_without_tests"]:
        recommendations.append("Create or link test cases for untested requirements.")
    if comp["notes"]:
        recommendations.extend(comp["notes"])

    return {
        "metadata": {
            "generated_utc": datetime.datetime.utcnow().isoformat() + "Z",
            "standards_checked": settings.accepted_standards,
            "encryption_enabled": settings.encryption_enabled,
            "iso_edition": settings.iso_edition,
        },
        "summary": {
            "num_requirements": len(norm["requirements"]),
            "num_fmea": len(norm["fmea"]),
            "num_tests": len(norm["tests"]),
        },
        "missing_sections": missing_sections,
        "field_issues": field_issues,
        "traceability": trace,
        "compliance": comp,
        "recommendations": recommendations,
        "status": "OK" if not (missing_sections or trace["requirements_without_tests"] or trace["requirements_without_fmea"]) else "ATTENTION",
    }


def _plugin_root(cat) -> str:
    return cat.mad_hatter.get_plugin().path


def _load_settings(cat) -> DocReviewSettings:
    raw = cat.mad_hatter.get_plugin().load_settings() or {}
    return DocReviewSettings(**raw)


def _resolve_reference_dir(plugin_root: str, settings: DocReviewSettings) -> Optional[str]:
    candidates = [
        os.path.join(plugin_root, settings.reference_dir),
        os.path.join(plugin_root, "reference", "ISO_26262", settings.iso_edition),
        os.path.join(plugin_root, "ISO_26262"),
        os.path.join(plugin_root, "ISO26262"),
    ]
    for p in candidates:
        if os.path.isdir(p):
            return p
    return None


def _resolve_checklist_dir(plugin_root: str, settings: DocReviewSettings) -> Optional[str]:
    """
    Resolve the directory containing ISO 26262 checklist JSON files for the configured edition.
    Looks for variations under: <plugin_root>/checklists/ISO_26262/<edition> and similar.
    """
    candidates = [
        os.path.join(plugin_root, settings.checklist_dir, "ISO_26262", settings.iso_edition),
        os.path.join(plugin_root, settings.checklist_dir, settings.iso_edition),
        os.path.join(plugin_root, settings.checklist_dir, "ISO_26262"),
        os.path.join(plugin_root, "ISO26262", "checklists", settings.iso_edition),
    ]
    for p in candidates:
        if os.path.isdir(p):
            return p
    return None


def _load_checklist_items(folder: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Load checklist items from all *.json files under the given folder.
    Supports root being either:
      - {"checks": [ ... ]}  OR  a plain array [ ... ]
    Each item is augmented with "source_file" for provenance.
    """
    items: List[Dict[str, Any]] = []
    files_loaded: List[str] = []
    if not folder or not os.path.isdir(folder):
        return items, files_loaded

    for fname in sorted(os.listdir(folder)):
        if not fname.lower().endswith(".json"):
            continue
        fpath = os.path.join(folder, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and isinstance(data.get("checks"), list):
                for it in data["checks"]:
                    if isinstance(it, dict):
                        it2 = dict(it)
                        it2["source_file"] = fname
                        items.append(it2)
                files_loaded.append(fname)
            elif isinstance(data, list):
                for it in data:
                    if isinstance(it, dict):
                        it2 = dict(it)
                        it2["source_file"] = fname
                        items.append(it2)
                files_loaded.append(fname)
            else:
                # Skip unknown shapes
                continue
        except Exception:
            # Ignore malformed files to avoid blocking the whole review
            continue
    return items, files_loaded


def _evaluate_checklist_items(norm: Dict[str, Any], items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Minimal evaluator:
      - If a checklist item has "patterns" or "keywords", try to find them in the relevant text (case-insensitive).
      - If "section" is set to one of ["requirements","fmea","tests"], only search within that section; else search globally.
      - If no patterns/keywords are present, mark as manual_check=True and do not auto-pass/fail.
    Returns summary counts and per-item results.
    """
    # Build concatenated text corpora for quick scanning
    def concat_section(sec_items: List[Any]) -> str:
        bucket: List[str] = []
        for it in sec_items:
            if isinstance(it, dict):
                txt = (it.get("text") or "") + " " + (it.get("id") or "")
                bucket.append(txt)
            elif isinstance(it, str):
                bucket.append(it)
        return "\n".join(bucket).lower()

    corpora = {
        "requirements": concat_section(norm.get("requirements", [])),
        "fmea": concat_section(norm.get("fmea", [])),
        "tests": concat_section(norm.get("tests", [])),
    }
    corpora["all"] = "\n".join([corpora["requirements"], corpora["fmea"], corpora["tests"]])

    results: List[Dict[str, Any]] = []
    passed = failed = manual = 0

    for item in items:
        section = (item.get("section") or "all").lower()
        haystack = corpora.get(section, corpora["all"])
        pats = item.get("patterns") or item.get("keywords") or []

        requires_manual = not isinstance(pats, list) or len(pats) == 0
        auto_pass = None

        if not requires_manual:
            ok_all = True
            for p in pats:
                try:
                    # Prefer regex if it compiles, else fallback to substring
                    if re.search(p, haystack, flags=re.IGNORECASE):
                        continue
                    # If regex didn't find, try a plain substring check
                    if str(p).lower() in haystack:
                        continue
                    ok_all = False
                    break
                except re.error:
                    # Invalid regex; fallback to substring
                    if str(p).lower() not in haystack:
                        ok_all = False
                        break
            auto_pass = ok_all
            if ok_all:
                passed += 1
            else:
                failed += 1
        else:
            manual += 1

        results.append({
            "id": item.get("id"),
            "title": item.get("title") or item.get("name"),
            "clause": item.get("clause"),
            "section": section,
            "source_file": item.get("source_file"),
            "requires_manual": requires_manual,
            "passed": auto_pass,  # True/False for auto-assessed, None for manual
        })

    return {
        "summary": {"total": len(items), "passed": passed, "failed": failed, "manual": manual},
        "results": results,
    }


# module-scope helpers
def _housekeep_reports(folder: str, keep: int):
    files = sorted(
        [os.path.join(folder, f) for f in os.listdir(folder) if f.startswith("report_")],
        key=lambda x: os.path.getmtime(x),
        reverse=True,
    )
    for f in files[keep:]:
        try:
            os.remove(f)
        except Exception:
            pass


def _gather_uploaded_texts(
    cat,
    files: Optional[List[str]] = None,
    metadata_filter: Optional[Dict[str, Any]] = None,
    limit_sources: Optional[int] = None,
    max_chars_per_source: int = 100000,
) -> List[Dict[str, str]]:
    """
    Gather uploaded document chunks from declarative memory, grouped and concatenated by source filename.
    - files: exact filenames to include (match against metadata['source'])
    - metadata_filter: dict of key/value pairs to match inside metadata
    - limit_sources: limit number of distinct sources returned (most recent first by 'when')
    Returns: List of { "source": <filename>, "text": <joined_text> }
    """
    ALLOWED_EXTS = {".pdf", ".docx", ".txt", ".md", ".rtf", ".html", ".htm"}
    try:
        points, next_offset = cat.memory.vectors.declarative.get_all_points(limit=10000, offset=None)
    except Exception:
        return []

    all_points = list(points) if points else []
    visited_offsets = 0
    while next_offset and visited_offsets < 50:
        visited_offsets += 1
        chunk, next_offset = cat.memory.vectors.declarative.get_all_points(limit=10000, offset=next_offset)
        if not chunk:
            break
        all_points.extend(chunk)

    grouped: Dict[str, List[Any]] = {}
    for p in all_points:
        payload = getattr(p, "payload", {}) or {}
        meta = payload.get("metadata") or {}
        source = meta.get("source")
        if not source or not isinstance(source, str):
            continue
        lower = source.lower()
        if not any(lower.endswith(ext) for ext in ALLOWED_EXTS):
            continue
        if files:
            base = os.path.basename(source)
            if base not in files:
                continue
        if metadata_filter:
            ok = True
            for k, v in metadata_filter.items():
                if meta.get(k) != v:
                    ok = False
                    break
            if not ok:
                continue
        grouped.setdefault(source, []).append(p)

    if not grouped:
        return []

    def source_recency_key(points_list):
        return max((getattr(pt, "payload", {}).get("metadata", {}).get("when", 0)) for pt in points_list)

    sources_sorted = sorted(grouped.items(), key=lambda kv: source_recency_key(kv[1]), reverse=True)
    if limit_sources is not None:
        sources_sorted = sources_sorted[: max(1, limit_sources)]

    def sort_key(point):
        payload = getattr(point, "payload", {}) or {}
        meta = payload.get("metadata") or {}
        return meta.get("when", 0)

    result = []
    for source, points_list in sources_sorted:
        points_list.sort(key=sort_key)
        chunks = []
        current_chars = 0
        for pt in points_list:
            payload = getattr(pt, "payload", {}) or {}
            text = payload.get("page_content") or ""
            if not text:
                continue
            if current_chars + len(text) > max_chars_per_source:
                remaining = max_chars_per_source - current_chars
                if remaining > 0:
                    chunks.append(text[:remaining])
                    current_chars += remaining
                break
            chunks.append(text)
            current_chars += len(text)
        result.append({"source": os.path.basename(source), "text": "\n".join(chunks)})
    return result


def _extract_structured_from_texts(docs: List[Dict[str, str]]) -> Dict[str, List[Any]]:
    """
    Heuristically extract requirements, FMEA-like entries, and tests from raw text.
    Output format compatible with _normalize_input (each list can contain strings or dicts).
    """
    reqs: List[Any] = []
    fmea: List[Any] = []
    tests: List[Any] = []

    req_patterns = [
        r"\bREQ[\-_ ]?\d+[:\s\-]",
        r"\b[Ss]ystem\s+shall\b",
        r"\b[Ss]hall\s+[a-zA-Z]",
        r"\b[Mm]ust\s+[a-zA-Z]",
        r"\b[Ss]hould\s+[a-zA-Z]",
        r"\b[Ss]afety\s+goal\b",
    ]
    req_re = re.compile("|".join(req_patterns))

    fmea_keywords = [
        "failure mode", "effect", "cause", "severity", "occurrence", "detection", "rpn",
        "mitigation", "control", "action", "recommended action",
    ]
    test_patterns = [
        r"\b[Tt]est\s*[Cc]ase\b",
        r"\bTC[\-_ ]?\d+\b",
        r"\b[Gg]iven\b.*\b[Ww]hen\b.*\b[Tt]hen\b",
        r"\bverification\b", r"\bvalidation\b", r"\bunit\s+test\b", r"\bintegration\s+test\b",
    ]
    test_re = re.compile("|".join(test_patterns))

    for d in docs:
        text = d.get("text", "") or ""
        for line in text.splitlines():
            line_stripped = line.strip()
            if not line_stripped:
                continue
            if req_re.search(line_stripped):
                reqs.append(line_stripped)

        for para in re.split(r"\n\s*\n", text):
            lc = para.lower()
            hits = sum(1 for k in fmea_keywords if k in lc)
            if hits >= 2:
                snippet = para.strip()
                if len(snippet) > 2000:
                    snippet = snippet[:2000] + " ..."
                fmea.append(snippet)

        for line in text.splitlines():
            line_stripped = line.strip()
            if not line_stripped:
                continue
            if test_re.search(line_stripped):
                tests.append(line_stripped)

    return {"requirements": reqs, "fmea": fmea, "tests": tests}


@tool("analyze_safety_documents", return_direct=False, examples=[
    "Analyze a documentation bundle in JSON containing requirements, FMEA, and tests. Return a compliance report.",
    "Analyze uploaded PDFs by filenames: {\"files\":[\"SafetyPlan.pdf\",\"HARA.pdf\"], \"options\":{\"format\":\"markdown\"}}",
    "Analyze most recent uploaded documents in memory: {\"use_memory\": true, \"options\": {\"format\":\"json\"}}",
    "Review my Safety Plan PDF and produce an ISO 26262 compliance and traceability report.",
    "Analyze the safety plan I just uploaded and generate a compliance report in markdown.",
    "Generate the report in DOCX or PDF format."
])
def analyze_safety_documents(input_by_llm: str, cat) -> str:
    """
    Analyze safety documentation for compliance and traceability.

    Input options:
      1) Structured JSON with keys 'requirements', 'fmea', 'tests' (each list of dicts or strings), and optional 'options'.
      2) JSON specifying uploaded files to analyze:
         {
           "files": ["SafetyPlan.pdf", "HARA.pdf"],
           "filters": {"project": "ABC"},
           "options": {"format": "markdown"}  # "json" | "markdown" (default: settings.report_format)
         }
      3) JSON to use most recent uploaded documents in memory:
         { "use_memory": true, "limit_sources": 3, "options": { "format": "json" } }

    Output: Path to stored report and summarized status.
    """
    settings = _load_settings(cat)
    cipher = _get_cipher(settings)
    plugin_root = _plugin_root(cat)
    storage = _ensure_storage(plugin_root, settings.storage_dir)

    parsed: Dict[str, Any] = {}
    try:
        parsed = json.loads(input_by_llm) if input_by_llm else {}
        if not isinstance(parsed, dict):
            parsed = {}
    except Exception:
        parsed = {}

    if any(k in parsed for k in ("requirements", "fmea", "tests")):
        options = parsed.get("options", {}) if isinstance(parsed.get("options", {}), dict) else {}
        fmt = options.get("format", settings.report_format)
        norm = _normalize_input(parsed)
        report = _build_report(norm, settings, plugin_root)

        # Always build a markdown rendering for rich export
        md_rendered = _format_report(report, "markdown")
        ts = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        base = f"report_{ts}"
        saved_path = None
        alt_paths: List[str] = []

        if fmt == "markdown":
            report_path = os.path.join(storage, f"{base}.md")
            payload = md_rendered.encode("utf-8")
            payload = cipher.encrypt(payload) if cipher else payload
            with open(report_path + (".enc" if cipher else ""), "wb") as f:
                f.write(payload)
            saved_path = report_path + (".enc" if cipher else "")
        elif fmt == "json":
            report_path = os.path.join(storage, f"{base}.json")
            _write_encrypted_json(report_path + (".enc" if cipher else ""), report, cipher)
            saved_path = report_path + (".enc" if cipher else "")
        elif fmt in ("docx", "pdf"):
            docx_bytes = _markdown_to_docx_bytes(md_rendered)
            if docx_bytes:
                docx_path = os.path.join(storage, f"{base}.docx")
                _write_encrypted_bytes(docx_path + (".enc" if cipher else ""), docx_bytes, cipher)
                if fmt == "docx":
                    saved_path = docx_path + (".enc" if cipher else "")
                alt_paths.append(docx_path + (".enc" if cipher else ""))
                # Try to get a PDF via docx->pdf, else simple markdown->pdf
                pdf_bytes = _docx_bytes_to_pdf_bytes(docx_bytes) or _markdown_to_simple_pdf_bytes(md_rendered)
                if pdf_bytes:
                    pdf_path = os.path.join(storage, f"{base}.pdf")
                    _write_encrypted_bytes(pdf_path + (".enc" if cipher else ""), pdf_bytes, cipher)
                    if fmt == "pdf":
                        saved_path = pdf_path + (".enc" if cipher else "")
                    alt_paths.append(pdf_path + (".enc" if cipher else ""))
                elif fmt == "pdf" and not saved_path:
                    saved_path = docx_path + (".enc" if cipher else "")
            else:
                report_path = os.path.join(storage, f"{base}.md")
                payload = md_rendered.encode("utf-8")
                payload = cipher.encrypt(payload) if cipher else payload
                with open(report_path + (".enc" if cipher else ""), "wb") as f:
                    f.write(payload)
                saved_path = report_path + (".enc" if cipher else "")
        else:
            # Unknown format -> default to settings
            fmt2 = settings.report_format
            rendered2 = _format_report(report, fmt2)
            report_base = f"{base}.{('md' if fmt2=='markdown' else 'json')}"
            report_path = os.path.join(storage, report_base)
            if fmt2 == "markdown":
                payload = rendered2.encode("utf-8")
                payload = cipher.encrypt(payload) if cipher else payload
                with open(report_path + (".enc" if cipher else ""), "wb") as f:
                    f.write(payload)
                saved_path = report_path + (".enc" if cipher else "")
            else:
                _write_encrypted_json(report_path + (".enc" if cipher else ""), report, cipher)
                saved_path = report_path + (".enc" if cipher else "")

        _append_audit(plugin_root, {"event": "analyze", "mode": "structured", "report_path": saved_path, "summary": report.get("summary")}, cipher)
        _housekeep_reports(storage, settings.retention_reports)

        return json.dumps({
            "message": "Documentation analyzed (structured input).",
            "report_path": saved_path,
            "alternatives": alt_paths,
            "status": report.get("status"),
            "summary": report.get("summary"),
        })

    files = parsed.get("files") if isinstance(parsed.get("files"), list) else None
    use_memory = bool(parsed.get("use_memory")) if "use_memory" in parsed else False
    filters = parsed.get("filters") if isinstance(parsed.get("filters"), dict) else None
    limit_sources = parsed.get("limit_sources")
    try:
        limit_sources = int(limit_sources) if limit_sources is not None else None
    except Exception:
        limit_sources = None

    options = parsed.get("options", {}) if isinstance(parsed.get("options", {}), dict) else {}
    fmt = options.get("format", settings.report_format)

    docs = []
    if files or use_memory:
        docs = _gather_uploaded_texts(
            cat=cat,
            files=files,
            metadata_filter=filters,
            limit_sources=limit_sources,
            max_chars_per_source=100000,
        )
    else:
        docs = _gather_uploaded_texts(cat=cat, files=None, metadata_filter=None, limit_sources=3, max_chars_per_source=100000)

    if not docs:
        auto_norm = {"requirements": [], "fmea": [], "tests": []}
    else:
        extracted = _extract_structured_from_texts(docs)
        auto_norm = _normalize_input(extracted)

    report = _build_report(auto_norm, settings, plugin_root)
    meta = report.get("metadata", {})
    meta["sources"] = [d.get("source") for d in (docs or [])]
    report["metadata"] = meta

    # Always produce markdown for rich exports
    md_rendered = _format_report(report, "markdown")
    ts = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    base = f"report_{ts}"
    saved_path = None
    alt_paths: List[str] = []

    if fmt == "markdown":
        report_path = os.path.join(storage, f"{base}.md")
        payload = md_rendered.encode("utf-8")
        payload = cipher.encrypt(payload) if cipher else payload
        with open(report_path + (".enc" if cipher else ""), "wb") as f:
            f.write(payload)
        saved_path = report_path + (".enc" if cipher else "")
    elif fmt == "json":
        report_path = os.path.join(storage, f"{base}.json")
        _write_encrypted_json(report_path + (".enc" if cipher else ""), report, cipher)
        saved_path = report_path + (".enc" if cipher else "")
    elif fmt in ("docx", "pdf"):
        docx_bytes = _markdown_to_docx_bytes(md_rendered)
        if docx_bytes:
            docx_path = os.path.join(storage, f"{base}.docx")
            _write_encrypted_bytes(docx_path + (".enc" if cipher else ""), docx_bytes, cipher)
            if fmt == "docx":
                saved_path = docx_path + (".enc" if cipher else "")
            alt_paths.append(docx_path + (".enc" if cipher else ""))
            # Try to get a PDF via docx->pdf, else simple markdown->pdf
            pdf_bytes = _docx_bytes_to_pdf_bytes(docx_bytes) or _markdown_to_simple_pdf_bytes(md_rendered)
            if pdf_bytes:
                pdf_path = os.path.join(storage, f"{base}.pdf")
                _write_encrypted_bytes(pdf_path + (".enc" if cipher else ""), pdf_bytes, cipher)
                if fmt == "pdf":
                    saved_path = pdf_path + (".enc" if cipher else "")
                alt_paths.append(pdf_path + (".enc" if cipher else ""))
            elif fmt == "pdf" and not saved_path:
                saved_path = docx_path + (".enc" if cipher else "")
        else:
            report_path = os.path.join(storage, f"{base}.md")
            payload = md_rendered.encode("utf-8")
            payload = cipher.encrypt(payload) if cipher else payload
            with open(report_path + (".enc" if cipher else ""), "wb") as f:
                f.write(payload)
            saved_path = report_path + (".enc" if cipher else "")
    else:
        # Unknown format -> default to settings
        fmt2 = settings.report_format
        rendered2 = _format_report(report, fmt2)
        report_base = f"{base}.{('md' if fmt2=='markdown' else 'json')}"
        report_path = os.path.join(storage, report_base)
        if fmt2 == "markdown":
            payload = rendered2.encode("utf-8")
            payload = cipher.encrypt(payload) if cipher else payload
            with open(report_path + (".enc" if cipher else ""), "wb") as f:
                f.write(payload)
            saved_path = report_path + (".enc" if cipher else "")
        else:
            _write_encrypted_json(report_path + (".enc" if cipher else ""), report, cipher)
            saved_path = report_path + (".enc" if cipher else "")

    _append_audit(
        plugin_root,
        {
            "event": "analyze",
            "mode": "memory" if (files or use_memory) else "auto-default",
            "report_path": saved_path,
            "sources": [d.get("source") for d in (docs or [])],
            "summary": report.get("summary"),
        },
        cipher
    )
    _housekeep_reports(storage, settings.retention_reports)

    return json.dumps({
        "message": "Documentation analyzed (memory).",
        "report_path": saved_path,
        "alternatives": alt_paths,
        "status": report.get("status"),
        "summary": report.get("summary"),
    })


@tool("get_last_doc_review_report", return_direct=False)
def get_last_doc_review_report(_: str, cat) -> str:
    """
    Return a quick preview of the latest stored report (metadata only).
    Output: JSON with last file path and top-level fields; no decryption is performed by this tool.
    """
    settings = _load_settings(cat)
    cipher = _get_cipher(settings)
    plugin_root = _plugin_root(cat)
    storage = _ensure_storage(plugin_root, settings.storage_dir)

    candidates = sorted(
        [os.path.join(storage, f) for f in os.listdir(storage)],
        key=lambda x: os.path.getmtime(x),
        reverse=True,
    )
    if not candidates:
        return json.dumps({"message": "No reports available."})

    last_path = candidates[0]
    # Only open JSON reports for preview if not markdown
    if last_path.endswith(".json") or last_path.endswith(".json.enc"):
        try:
            obj = _read_encrypted_json(last_path, cipher)
            preview = {
                "report_path": last_path,
                "metadata": obj.get("metadata", {}),
                "summary": obj.get("summary", {}),
                "status": obj.get("status", "UNKNOWN"),
            }
            return json.dumps(preview, indent=2)
        except Exception:
            pass

    return json.dumps({"report_path": last_path})


@endpoint.get(
    path="/fusa/doc-review/report",
    tags=["FuSa Doc Review"],
    dependencies=[check_permissions(AuthResource.PLUGINS, AuthPermission.READ)],
)
def http_get_last_report():
    """
    Returns the latest report path (and quick metadata if JSON).
    Note: Reports are stored in plaintext (encryption disabled). Only JSON metadata may be returned.
    """
    # This endpoint runs without 'cat' context. Use environment only.
    # Lightweight: search in plugin folder
    try:
        from cat.looking_glass.cheshire_cat import CheshireCat
        cat = CheshireCat(None)
        settings = _load_settings(cat)
        cipher = _get_cipher(settings)
        plugin_root = _plugin_root(cat)
        storage = _ensure_storage(plugin_root, settings.storage_dir)

        candidates = sorted(
            [os.path.join(storage, f) for f in os.listdir(storage)],
            key=lambda x: os.path.getmtime(x),
            reverse=True,
        )
        if not candidates:
            return {"message": "No reports available."}

        last_path = candidates[0]
        if last_path.endswith(".json") or last_path.endswith(".json.enc"):
            try:
                obj = _read_encrypted_json(last_path, cipher)
                return {
                    "report_path": last_path,
                    "metadata": obj.get("metadata", {}),
                    "summary": obj.get("summary", {}),
                    "status": obj.get("status", "UNKNOWN"),
                }
            except Exception:
                return {"report_path": last_path}
        return {"report_path": last_path}
    except Exception as e:
        log.error(f"fusa_doc_review: error {e}")
        return {"error": "Unable to load last report"}


@endpoint.post(
    path="/fusa/doc-review/analyze",
    tags=["FuSa Doc Review"],
    dependencies=[check_permissions(AuthResource.PLUGINS, AuthPermission.WRITE)],
)
def http_post_analyze(payload: Dict[str, Any]):
    """
    HTTP API to trigger document analysis. Body matches the tool input shape.
    Returns report metadata and path.
    """
    try:
        from cat.looking_glass.cheshire_cat import CheshireCat
        cat = CheshireCat(None)
        out = analyze_safety_documents.run(json.dumps(payload), cat)
        return json.loads(out)
    except Exception as e:
        log.error(f"fusa_doc_review: analyze endpoint error {e}")
        return {"error": "Failed to analyze input"}


@endpoint.get(
    path="/fusa/doc-review/references",
    tags=["FuSa Doc Review"],
    dependencies=[check_permissions(AuthResource.PLUGINS, AuthPermission.READ)],
)
def http_list_references():
    """
    Lists available ISO 26262 PDFs detected for the configured edition.
    Returns: {"edition": "2018", "directory": "<path>", "files": [...], "parts_detected": [1..12]}
    """
    try:
        from cat.looking_glass.cheshire_cat import CheshireCat
        cat = CheshireCat(None)
        settings = _load_settings(cat)
        plugin_root = _plugin_root(cat)
        ref_dir = _resolve_reference_dir(plugin_root, settings)
        if not ref_dir:
            return {"edition": settings.iso_edition, "directory": None, "files": [], "parts_detected": []}

        files = [f for f in os.listdir(ref_dir) if f.lower().endswith(".pdf")]
        parts = []
        for f in files:
            m = re.search(r"26262-(\d+)", f)
            if m:
                try:
                    parts.append(int(m.group(1)))
                except Exception:
                    pass
        parts = sorted(list(set(parts)))
        return {"edition": settings.iso_edition, "directory": ref_dir, "files": files, "parts_detected": parts}
    except Exception as e:
        log.error(f"fusa_doc_review references error: {e}")
        return {"error": "Unable to read references"}

@endpoint.get(
    path="/fusa/doc-review/checklists",
    tags=["FuSa Doc Review"],
    dependencies=[check_permissions(AuthResource.PLUGINS, AuthPermission.READ)],
)
def http_list_checklists():
    """
    Lists available ISO 26262 checklist JSON files detected for the configured edition.
    Returns: {"edition": "2018", "directory": "<path>", "files": [...], "total_items": N}
    """
    try:
        from cat.looking_glass.cheshire_cat import CheshireCat
        cat = CheshireCat(None)
        settings = _load_settings(cat)
        plugin_root = _plugin_root(cat)
        cl_dir = _resolve_checklist_dir(plugin_root, settings)
        if not cl_dir:
            return {"edition": settings.iso_edition, "directory": None, "files": [], "total_items": 0}
        items, files = _load_checklist_items(cl_dir)
        return {"edition": settings.iso_edition, "directory": cl_dir, "files": files, "total_items": len(items)}
    except Exception as e:
        log.error(f"fusa_doc_review checklists error: {e}")
        return {"error": "Unable to read checklists"}


# Hook: auto-trigger analysis tool from natural language prompts
@hook(priority=5)
def agent_fast_reply(agent_fast_reply: dict, cat) -> None | dict:
    try:
        msg = (cat.working_memory.user_message_json.text or "")
    except Exception:
        msg = ""

    if not msg:
        return None

    msg_lc = msg.lower()

    # Minimal keyword match to detect intent
    trigger_hits = any(w in msg_lc for w in [
        "review", "analyze", "audit", "assess", "produce", "generate"
    ])
    domain_hits = any(w in msg_lc for w in [
        "safety plan", "iso 26262", "compliance", "traceability", "safety documentation", "fusa", "hara", "fmea"
    ])

    if not (trigger_hits and domain_hits):
        return None

    # Try to extract filenames mentioned in the message
    file_matches = re.findall(r'([A-Za-z0-9_. -]+\.(?:pdf|docx|txt|md|html))', msg, flags=re.IGNORECASE)
    files = [f.strip() for f in file_matches] if file_matches else []

    payload = {}
    if files:
        # Deduplicate while preserving order
        seen = set()
        deduped = []
        for f in files:
            key = f.lower()
            if key not in seen:
                seen.add(key)
                deduped.append(f)
        payload["files"] = deduped
    else:
        # Fall back to most recent uploaded documents
        payload["use_memory"] = True
        payload["limit_sources"] = 3

    # Detect preferred output format (prioritize PDF/DOCX/Word)
    if "pdf" in msg_lc and ("docx" in msg_lc or "word" in msg_lc):
        payload.setdefault("options", {})["format"] = "pdf"
    elif "pdf" in msg_lc:
        payload.setdefault("options", {})["format"] = "pdf"
    elif "docx" in msg_lc or "word" in msg_lc:
        payload.setdefault("options", {})["format"] = "docx"
    elif "markdown" in msg_lc or "mark down" in msg_lc or "md" in msg_lc:
        payload.setdefault("options", {})["format"] = "markdown"
    elif "json" in msg_lc:
        payload.setdefault("options", {})["format"] = "json"

    try:
        result = analyze_safety_documents.run(json.dumps(payload), cat)
        # Return the tool output directly to the chat, bypassing default agent flow
        return {"output": result}
    except Exception as e:
        return {"output": f"Failed to run FuSa Doc Review: {e}"}


# Optional imports for DOCX/PDF
try:
    from docx import Document as DocxDocument  # python-docx
except Exception:
    DocxDocument = None

try:
    from docx2pdf import convert as docx2pdf_convert  # requires MS Word on Windows
except Exception:
    docx2pdf_convert = None

def _write_encrypted_bytes(path: str, data: bytes, cipher: Optional[Fernet]):
    to_write = cipher.encrypt(data) if cipher else data
    with open(path, "wb") as f:
        f.write(to_write)

def _markdown_to_docx_bytes(md_text: str) -> Optional[bytes]:
    """
    Convert basic Markdown to a .docx document.
    Returns bytes or None if python-docx is unavailable.
    """
    if DocxDocument is None:
        return None

    doc = DocxDocument()
    lines = md_text.splitlines()
    in_code = False

    for raw in lines:
        line = raw.rstrip("\n")

        # Code block fence
        if line.strip().startswith("```"):
            in_code = not in_code
            continue

        if in_code:
            doc.add_paragraph(line)
            continue

        # Headings
        if line.startswith("### "):
            doc.add_heading(line[4:].strip(), level=3)
        elif line.startswith("## "):
            doc.add_heading(line[3:].strip(), level=2)
        elif line.startswith("# "):
            doc.add_heading(line[2:].strip(), level=1)
        # Bullets and numbered lists (basic)
        elif line.strip().startswith(("- ", "* ")):
            p = doc.add_paragraph(line.strip()[2:])
            p.style = doc.styles["List Bullet"] if "List Bullet" in doc.styles else p.style
        elif re.match(r"^\s*\d+\.\s+", line):
            text = re.sub(r"^\s*\d+\.\s+", "", line).strip()
            p = doc.add_paragraph(text)
            p.style = doc.styles["List Number"] if "List Number" in doc.styles else p.style
        # Horizontal rule
        elif line.strip() in ("---", "***"):
            doc.add_paragraph()  # simple spacer
        # Paragraph
        else:
            if line.strip():
                doc.add_paragraph(line)
            else:
                doc.add_paragraph("")

    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()

def _markdown_to_simple_pdf_bytes(md_text: str) -> Optional[bytes]:
    """
    Very basic PDF generation from markdown text (no styling), used as a last resort.
    Requires reportlab if available. Returns bytes or None.
    """
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
    except Exception:
        return None

    from io import BytesIO
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    left = 20 * mm
    top = height - 20 * mm
    line_height = 6 * mm

    y = top
    for raw in md_text.splitlines():
        text = raw.replace("\t", "    ")
        if not text.strip():
            y -= line_height
            if y <= 20 * mm:
                c.showPage()
                y = top
            continue
        max_chars = 100
        while text:
            line = text[:max_chars]
            text = text[max_chars:]
            c.drawString(left, y, line)
            y -= line_height
            if y <= 20 * mm:
                c.showPage()
                y = top
    c.showPage()
    c.save()
    return buf.getvalue()

def _docx_bytes_to_pdf_bytes(docx_bytes: bytes) -> Optional[bytes]:
    """
    Convert DOCX bytes to PDF bytes using docx2pdf if available (Windows + MS Word).
    Fallback to LibreOffice (soffice) if available, else return None.
    """
    # Try docx2pdf first (if available)
    if docx2pdf_convert is not None:
        with tempfile.TemporaryDirectory() as tmpdir:
            docx_path = os.path.join(tmpdir, "report.docx")
            pdf_path = os.path.join(tmpdir, "report.pdf")
            with open(docx_path, "wb") as f:
                f.write(docx_bytes)
            try:
                docx2pdf_convert(docx_path, pdf_path)
                with open(pdf_path, "rb") as f:
                    return f.read()
            except Exception:
                # Try LibreOffice as fallback within same temp dir
                soffice = shutil.which("soffice") or shutil.which("libreoffice")
                if not soffice:
                    return None
                try:
                    subprocess.run(
                        [soffice, "--headless", "--convert-to", "pdf", "--outdir", tmpdir, docx_path],
                        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
                    )
                    with open(pdf_path, "rb") as f:
                        return f.read()
                except Exception:
                    return None

    # If docx2pdf is not available, try LibreOffice directly
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        return None
    with tempfile.TemporaryDirectory() as tmpdir:
        docx_path = os.path.join(tmpdir, "report.docx")
        pdf_path = os.path.join(tmpdir, "report.pdf")
        with open(docx_path, "wb") as f:
            f.write(docx_bytes)
        try:
            subprocess.run(
                [soffice, "--headless", "--convert-to", "pdf", "--outdir", tmpdir, docx_path],
                check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            with open(pdf_path, "rb") as f:
                return f.read()
        except Exception:
            return None