import json
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime
import re
from pathlib import Path
import glob
import hashlib

from cat.mad_hatter.decorators import tool, hook
from cat.log import log

# DOCX support
from docx import Document  # pip install python-docx

PLUGIN_VERSION = "2.0.0"

# --------- Enums ---------
class ASIL(str, Enum):
    QM = "QM"
    A = "A"
    B = "B"
    C = "C"
    D = "D"

class SeverityLevel(str, Enum):
    S0 = "S0"; S1 = "S1"; S2 = "S2"; S3 = "S3"

class ExposureLevel(str, Enum):
    E0 = "E0"; E1 = "E1"; E2 = "E2"; E3 = "E3"; E4 = "E4"

class ControllabilityLevel(str, Enum):
    C0 = "C0"; C1 = "C1"; C2 = "C2"; C3 = "C3"

# --------- Data classes ---------
@dataclass
class HARAEntry:
    hara_id: str
    hazardous_event: str
    operational_situation: str
    severity: SeverityLevel
    exposure: ExposureLevel
    controllability: ControllabilityLevel
    asil: ASIL
    linked_safety_goal_id: str

@dataclass
class SafetyGoal:
    sg_id: str
    text: str
    severity: SeverityLevel
    exposure: ExposureLevel
    controllability: ControllabilityLevel
    asil: ASIL
    rationale: str

@dataclass
class FSR:
    fsr_id: str
    text: str
    asil: ASIL
    detection: str
    reaction: str
    timing_ms: int
    safe_state: str
    assumptions: List[str]
    linked_safety_goal_id: str
    allocation_hint: str
    verification_strategy: str

# --------- Config & utils ---------
def _plugin_dir() -> Path:
    return Path(__file__).parent

def _load_json_or_default(path: Path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log.warning(f"Config fallback for {path.name}: {e}")
        return default

def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def _sanitize_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "_", name) or "Item"

# Defaults if config is missing
_DEFAULT_ASIL_MATRIX = {
    "S3|E4|C3": "D", "S3|E4|C2": "C", "S3|E3|C3": "C", "S2|E4|C3": "C",
    "S3|E4|C1": "B", "S3|E3|C2": "B", "S2|E4|C2": "B", "S3|E2|C3": "B",
    "S3|E3|C1": "B", "S2|E3|C3": "B"
}

_DEFAULT_DOMAIN_POLICY = {
    "keywords": {
        "critical": ["brake", "steer", "accelerat", "power", "control"],
        "safety": ["monitor", "detect", "warning", "alert"]
    },
    "timings_ms": {
        "critical_detect": 300, "critical_react": 700,
        "safety_detect": 500, "safety_react": 1000,
        "generic_detect": 1000, "generic_react": 2000
    },
    "safe_states": {
        "critical": "Fail-safe with controlled shutdown",
        "safety": "Maintain state with degraded functionality",
        "generic": "Continue with reduced performance"
    },
    "allocation_hints": {
        "critical": "HW+SW", "safety": "SW", "generic": "SW"
    },
    "verification": {
        "A": "Review + Unit test", "B": "Unit + Integration + Analysis",
        "C": "Integration + Fault Injection + Analysis",
        "D": "System test + Fault Injection + Formal/Analysis"
    }
}

# --------- Core helper ---------
class ISO26262Helper:
    def __init__(self, asil_matrix: Dict[str, str], policy: Dict):
        self.asil_matrix = asil_matrix
        self.policy = policy

    def determine_asil(self, s: SeverityLevel, e: ExposureLevel, c: ControllabilityLevel) -> ASIL:
        key = f"{s.value}|{e.value}|{c.value}"
        if int(s.value[1]) + int(e.value[1]) + int(c.value[1]) < 7:
            return ASIL.QM
        level = self.asil_matrix.get(key, "A")
        return ASIL(level)

    def _get_classification(self, func_name: str, func_desc: str) -> tuple[str, SeverityLevel, ExposureLevel, ControllabilityLevel]:
        kw = self.policy.get("keywords", {})
        joined = (func_name + " " + func_desc).lower()
        is_critical = any(k in joined for k in kw.get("critical", []))
        is_safety = any(k in joined for k in kw.get("safety", []))
        if is_critical:
            return "critical", SeverityLevel.S3, ExposureLevel.E4, ControllabilityLevel.C3
        elif is_safety:
            return "safety", SeverityLevel.S2, ExposureLevel.E3, ControllabilityLevel.C2
        else:
            return "generic", SeverityLevel.S1, ExposureLevel.E2, ControllabilityLevel.C1

    def _create_safety_goal_hardcoded(self, func_name: str, func_desc: str, idx: int) -> SafetyGoal:
        """Deterministic, hardcoded version for Safety Goal generation (used as fallback)."""
        classification, s, e, c = self._get_classification(func_name, func_desc)
        rationale = f"Hardcoded classification based on keywords: {classification}"
        asil = self.determine_asil(s, e, c)
        return SafetyGoal(
            sg_id=f"SG_{idx:03d}",
            text=f"Prevent unreasonable risk from malfunctions of '{func_name}'",
            severity=s, exposure=e, controllability=c,
            asil=asil, rationale=rationale
        )

    def create_safety_goal(self, func_name: str, func_desc: str, idx: int, cat) -> SafetyGoal:
        """Derives a Safety Goal using an LLM for S, E, C analysis, with a hardcoded fallback."""
        prompt = f"""
You are an expert in Functional Safety Engineering (ISO 26262) for the automotive industry.
Your task is to perform a hazard analysis for a given system function to determine its risk classification (Severity, Exposure, Controllability) and formulate a Safety Goal.

**Context:**
- **System Function Name:** "{func_name}"
- **Function Description:** "{func_desc}"

**Instructions:**
1.  Analyze the function and its potential hazards if it malfunctions.
2.  Determine the **Severity (S)**: S0 (No injuries), S1 (Light/moderate), S2 (Severe/life-threatening, survival probable), S3 (Life-threatening/fatal).
3.  Determine the **Exposure (E)**: E0 (Incredibly unlikely), E1 (Very low probability), E2 (Low), E3 (Medium), E4 (High).
4.  Determine the **Controllability (C)**: C0 (Controllable), C1 (Simply controllable), C2 (Normally controllable), C3 (Difficult/uncontrollable).
5.  Formulate a concise safety goal text and provide a brief rationale for your S, E, and C choices.

**Output Format:**
Respond ONLY with a single, valid JSON object in a code block. The object must have the following keys: `text`, `severity`, `exposure`, `controllability`, `rationale`.

Example:
{{
    "text": "Prevent unintended steering lock during driving.",
    "severity": "S3",
    "exposure": "E4",
    "controllability": "C3",
    "rationale": "An unintended steering lock at high speed can be catastrophic (S3), occurs during normal driving (E4), and is nearly impossible for the driver to control (C3)."
}}

Now, generate the JSON for the given function.
"""
        try:
            log.info(f"Generating Safety Goal for '{func_name}' using LLM.")
            llm_response = cat.llm(prompt)
            json_match = re.search(r"```json\s*([\s\S]+?)\s*```", llm_response, re.MULTILINE)
            json_str = json_match.group(1) if json_match else llm_response
            data = json.loads(json_str)
            s, e, c = SeverityLevel(data["severity"]), ExposureLevel(data["exposure"]), ControllabilityLevel(data["controllability"])
            asil = self.determine_asil(s, e, c)
            log.info(f"Successfully generated SG for '{func_name}' via LLM with S={s.value}, E={e.value}, C={c.value} -> ASIL {asil.value}")
            return SafetyGoal(
                sg_id=f"SG_{idx:03d}",
                text=data.get("text", f"Prevent unreasonable risk from malfunctions of '{func_name}'"),
                severity=s, exposure=e, controllability=c,
                asil=asil, rationale=data.get("rationale", "Rationale not provided by LLM.")
            )
        except Exception as e:
            log.warning(f"LLM Safety Goal generation failed for '{func_name}': {e}. Falling back to hardcoded method.")
            return self._create_safety_goal_hardcoded(func_name, func_desc, idx)

    def create_hara_entry(self, func_name: str, func_desc: str, sg: SafetyGoal, idx: int) -> HARAEntry:
        """Deterministically creates a HARA entry linked to a Safety Goal."""
        classification, _, _, _ = self._get_classification(func_name, func_desc)
        hazardous_event = f"Unintended or loss of function '{func_name}'"
        if classification == "critical": op_situation = "Driving at high speed in traffic"
        elif classification == "safety": op_situation = "Normal driving conditions with potential system faults"
        else: op_situation = "Various driving scenarios"
        return HARAEntry(
            hara_id=f"HARA_{idx:03d}", hazardous_event=hazardous_event, operational_situation=op_situation,
            severity=sg.severity, exposure=sg.exposure, controllability=sg.controllability,
            asil=sg.asil, linked_safety_goal_id=sg.sg_id
        )

    def _derive_fsrs_from_sg_hardcoded(self, sg: SafetyGoal, func_name: str, func_desc: str) -> List[FSR]:
        """Deterministic, hardcoded version for FSR generation (used as fallback)."""
        if sg.asil == ASIL.QM: return []
        pol, classification, _, _, _ = self.policy, *self._get_classification(func_name, func_desc)
        detect_ms = pol["timings_ms"].get(f"{classification}_detect", 1000)
        react_ms = pol["timings_ms"].get(f"{classification}_react", 2000)
        safe_state = pol["safe_states"].get(classification, "Maintain safe state")
        alloc = pol["allocation_hints"].get(classification, "SW")
        ver = pol.get("verification", {}).get(sg.asil.value, "Review + Test")
        func_id = re.sub(r"[^A-Za-z0-9]", "_", func_name).upper()[:12] or "FUNC"
        fsrs = [
            FSR(fsr_id=f"{func_id}_DET", text=f"The system shall detect malfunctions of '{func_name}' within {detect_ms} ms.", asil=sg.asil, detection=f"Plausibility checks for '{func_name}' I/O.", reaction="Raise internal fault.", timing_ms=detect_ms, safe_state=safe_state, assumptions=["Inputs are available for monitoring."], linked_safety_goal_id=sg.sg_id, allocation_hint=alloc, verification_strategy=ver),
            FSR(fsr_id=f"{func_id}_REACT", text=f"The system shall react to faults in '{func_name}' within {react_ms} ms.", asil=sg.asil, detection=f"Confirmed fault from {func_id}_DET.", reaction=f"Transition to safe state.", timing_ms=react_ms, safe_state=safe_state, assumptions=["Safe state is reachable."], linked_safety_goal_id=sg.sg_id, allocation_hint=alloc, verification_strategy=ver)
        ]
        if classification == "critical":
            fsrs.append(FSR(fsr_id=f"{func_id}_WARN", text="The system shall warn the driver of the malfunction within 500 ms.", asil=ASIL.A, detection=f"Safety-relevant fault in '{func_name}'.", reaction="Activate HMI warning.", timing_ms=500, safe_state="Driver is informed.", assumptions=["Driver is attentive."], linked_safety_goal_id=sg.sg_id, allocation_hint="SW", verification_strategy="HMI Test"))
        return fsrs

    def derive_fsrs_from_sg(self, sg: SafetyGoal, func_name: str, func_desc: str, cat) -> List[FSR]:
        """Derives FSRs using an LLM for contextual generation, with a hardcoded fallback."""
        if sg.asil == ASIL.QM:
            log.info(f"Skipping FSR generation for QM Safety Goal: {sg.sg_id}")
            return []
        prompt = f"""
You are an expert in Functional Safety Engineering (ISO 26262).
Your task is to derive a set of Functional Safety Requirements (FSRs) from a given Safety Goal and system function.

**Context:**
- **System Function Name:** "{func_name}"
- **Function Description:** "{func_desc}"
- **Safety Goal (SG) ID:** "{sg.sg_id}"
- **Safety Goal Text:** "{sg.text}"
- **ASIL Level:** {sg.asil.value}

**Instructions:**
1.  Derive at least two FSRs: one for fault **detection** and one for **reaction**.
2.  If the function is critical, add a third FSR for **warning the driver**.
3.  FSRs must be specific, measurable, and verifiable.
4.  Provide realistic text for `detection`, `reaction`, `safe_state`, and `assumptions`.
5.  `timing_ms` must be a reasonable integer.

**Output Format:**
Respond ONLY with a valid JSON object in a code block. The object should be a list of FSR dictionaries with keys: `fsr_id`, `text`, `detection`, `reaction`, `timing_ms`, `safe_state`, `assumptions`, `allocation_hint`, `verification_strategy`.

Now, generate the JSON for the given context.
"""
        try:
            log.info(f"Generating FSRs for '{func_name}' using LLM.")
            llm_response = cat.llm(prompt)
            json_match = re.search(r"```json\s*([\s\S]+?)\s*```", llm_response, re.MULTILINE)
            json_str = json_match.group(1) if json_match else llm_response
            parsed_fsrs = json.loads(json_str)
            fsrs = [FSR(
                fsr_id=f.get("fsr_id", "FSR_ID_MISSING"), text=f.get("text", "Requirement text missing."),
                asil=sg.asil, detection=f.get("detection", "N/A"), reaction=f.get("reaction", "N/A"),
                timing_ms=int(f.get("timing_ms", 500)), safe_state=f.get("safe_state", "N/A"),
                assumptions=f.get("assumptions", []), linked_safety_goal_id=sg.sg_id,
                allocation_hint=f.get("allocation_hint", "SW"),
                verification_strategy=f.get("verification_strategy", "Review + Test")
            ) for f in parsed_fsrs]
            if not fsrs: raise ValueError("LLM returned an empty list of FSRs.")
            log.info(f"Successfully generated {len(fsrs)} FSRs via LLM.")
            return fsrs
        except Exception as e:
            log.warning(f"LLM FSR generation failed for '{func_name}': {e}. Falling back to hardcoded method.")
            return self._derive_fsrs_from_sg_hardcoded(sg, func_name, func_desc)

    @staticmethod
    def asil_distribution(fsrs: List[FSR]) -> Dict[str, int]:
        d = {}
        for f in fsrs: d[f.asil.value] = d.get(f.asil.value, 0) + 1
        return d

# --------- Input parsing ---------
def _read_item_definition(plugin_dir: Path):
    item_dir = plugin_dir / "item_definition"
    if not item_dir.exists(): raise FileNotFoundError(f"item_definition directory not found at {item_dir}")
    supported = ["*.json", "*.md", "*.txt", "*.docx"]
    candidates = [p for pat in supported for p in glob.glob(str(item_dir / pat))]
    if not candidates: raise FileNotFoundError("No supported files in item_definition")
    file_path = Path(sorted(candidates)[0])
    ext = file_path.suffix.lower()
    if ext == ".json":
        with open(file_path, "r", encoding="utf-8") as f: data = json.load(f)
        data.setdefault("item_name", file_path.stem)
        return data, file_path
    elif ext in (".md", ".txt"):
        with open(file_path, "r", encoding="utf-8") as f: content = f.read()
        return {"item_name": file_path.stem, "purpose": content[:400]}, file_path
    elif ext == ".docx":
        doc = Document(str(file_path))
        text = "\n".join(p.text for p in doc.paragraphs)
        return {"item_name": file_path.stem, "purpose": text[:400]}, file_path
    raise ValueError(f"Unsupported extension: {ext}")

# --------- DOCX report ---------
def _save_docx_report(path: Path, item_name: str, src_name: str, generated_iso: str,
                      summary: Dict, hara: List[HARAEntry], sgs: List[SafetyGoal], fsrs: List[FSR]):
    doc = Document()
    doc.add_heading(f"Safety Analysis Report - {item_name}", 1)
    p = doc.add_paragraph(); p.add_run("Plugin version: ").bold = True; p.add_run(PLUGIN_VERSION)
    doc.add_paragraph(f"Source: {src_name}\nGenerated: {generated_iso}")
    doc.add_heading("Summary", 2)
    doc.add_paragraph(json.dumps(summary, indent=2))

    doc.add_heading("HARA (Hazard Analysis and Risk Assessment)", 2)
    tbl_h = doc.add_table(1, 6); tbl_h.style = "Light Grid"
    hdr_h = tbl_h.rows[0].cells
    hdr_h[0].text = "ID"; hdr_h[1].text = "Hazardous Event"; hdr_h[2].text = "Op. Situation";
    hdr_h[3].text = "S/E/C"; hdr_h[4].text = "ASIL"; hdr_h[5].text = "Linked SG"
    for h in hara:
        row = tbl_h.add_row().cells
        row[0].text = h.hara_id; row[1].text = h.hazardous_event; row[2].text = h.operational_situation
        row[3].text = f"{h.severity.value}/{h.exposure.value}/{h.controllability.value}"
        row[4].text = h.asil.value; row[5].text = h.linked_safety_goal_id

    doc.add_heading("Safety Goals", 2)
    tbl_sg = doc.add_table(1, 5); tbl_sg.style = "Light Grid"
    hdr_sg = tbl_sg.rows[0].cells
    hdr_sg[0].text = "ID"; hdr_sg[1].text = "Text"; hdr_sg[2].text = "S/E/C";
    hdr_sg[3].text = "ASIL"; hdr_sg[4].text = "Rationale"
    for sg in sgs:
        row = tbl_sg.add_row().cells
        row[0].text = sg.sg_id; row[1].text = sg.text
        row[2].text = f"{sg.severity.value}/{sg.exposure.value}/{sg.controllability.value}"
        row[3].text = sg.asil.value; row[4].text = sg.rationale

    doc.add_heading("Functional Safety Requirements (FSRs)", 2)
    tbl_f = doc.add_table(1, 6); tbl_f.style = "Light Grid"
    hdr_f = tbl_f.rows[0].cells
    hdr_f[0].text = "ID"; hdr_f[1].text = "ASIL"; hdr_f[2].text = "Requirement";
    hdr_f[3].text = "Timing"; hdr_f[4].text = "Safe State"; hdr_f[5].text = "Linked SG"
    for f in fsrs:
        row = tbl_f.add_row().cells
        row[0].text = f.fsr_id; row[1].text = f.asil.value; row[2].text = f.text
        row[3].text = f"{f.timing_ms} ms"; row[4].text = f.safe_state; row[5].text = f.linked_safety_goal_id
    doc.save(str(path))

# --------- Manifest handling ---------
def _update_manifest(fsr_dir: Path, artifacts: List[Path], src_file: Path, item_name: str):
    manifest_path = fsr_dir / "manifest.json"
    entry = {"timestamp": datetime.now().isoformat(), "plugin_version": PLUGIN_VERSION,
             "item_name": item_name, "source_file": src_file.name,
             "artifacts": [{"name": a.name, "sha256": _sha256_file(a)} for a in artifacts]}
    try:
        with open(manifest_path, "r", encoding="utf-8") as f: manifest = json.load(f)
    except Exception: manifest = {"runs": []}
    manifest["runs"].append(entry)
    with open(manifest_path, "w", encoding="utf-8") as f: json.dump(manifest, f, indent=2)

# --------- Hooks ---------
@hook
def after_cat_bootstrap(cat):
    pdir = Path(__file__).parent
    for d in ["config", "schemas", "fsrs", "item_definition"]: (pdir / d).mkdir(exist_ok=True)
    if not (pdir / "config/asil_matrix.json").exists():
        with open(pdir / "config/asil_matrix.json", "w") as f: json.dump(_DEFAULT_ASIL_MATRIX, f, indent=2)
    if not (pdir / "config/domain_policy.json").exists():
        with open(pdir / "config/domain_policy.json", "w") as f: json.dump(_DEFAULT_DOMAIN_POLICY, f, indent=2)
    log.info("ISO 26262 Helper Plugin bootstrap complete.")

# --------- Tool ---------
@tool(return_direct=True)
def generate_safety_artifacts(tool_input: Optional[dict | str], cat) -> str:
    """
    Generates HARA, Safety Goals, and FSRs from an Item Definition.
    This tool leverages an LLM for analysis with deterministic fallbacks.

    Input options:
      - "auto" or empty: use the first file in item_definition.
      - "file": save to files only.
      - "chat": show a preview in the chat only.
      - "both" (default): save to files and show a chat preview.
    """
    pdir = _plugin_dir()
    save_mode = "both"
    if isinstance(tool_input, str):
        t = tool_input.strip().lower()
        if t == "file": save_mode = "file"
        elif t == "chat": save_mode = "chat"
    elif isinstance(tool_input, dict): save_mode = str(tool_input.get("output", save_mode))

    helper = ISO26262Helper(
        _load_json_or_default(pdir / "config/asil_matrix.json", _DEFAULT_ASIL_MATRIX),
        _load_json_or_default(pdir / "config/domain_policy.json", _DEFAULT_DOMAIN_POLICY)
    )
    try:
        item_data, src_path = _read_item_definition(pdir)
    except Exception as e:
        log.error(f"Input error: {e}"); return f"❌ Input error: {e}"

    item_name = item_data.get("item_name", "Unknown Item")
    text_content = item_data.get("purpose", "")
    if "functions" not in item_data and text_content:
        # Simplified function extraction for brevity
        functions = [{"name": "Primary Function", "description": text_content}]
    else:
        functions = item_data.get("functions", [{"name": "Primary Function", "description": "Main system function"}])

    hara, safety_goals, all_fsrs = [], [], []
    for idx, func in enumerate(functions, start=1):
        fname, fdesc = func.get("name", f"Func {idx}"), func.get("description", "")
        sg = helper.create_safety_goal(fname, fdesc, idx, cat)
        safety_goals.append(sg)
        hara.append(helper.create_hara_entry(fname, fdesc, sg, idx))
        all_fsrs.extend(helper.derive_fsrs_from_sg(sg, fname, fdesc, cat))

    summary = {
        "item": item_name, "functions_analyzed": len(functions),
        "hazardous_events": len(hara), "safety_goals": len(safety_goals),
        "fsrs_generated": len(all_fsrs),
        "asil_distribution": helper.asil_distribution(all_fsrs),
        "plugin_version": PLUGIN_VERSION
    }
    output_data = {
        "generation_info": {"item_name": item_name, "source_file": src_path.name, "timestamp": datetime.now().isoformat()},
        "summary": summary, "hara_analysis": [asdict(h) for h in hara],
        "safety_goals": [asdict(sg) for sg in safety_goals],
        "functional_safety_requirements": [asdict(f) for f in all_fsrs]
    }

    if save_mode in ("file", "both"):
        fsr_dir = pdir / "fsrs"
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"{_sanitize_name(item_name)}_report_{ts}"
        json_path = fsr_dir / f"{base_name}.json"
        docx_path = fsr_dir / f"{base_name}.docx"
        try:
            with open(json_path, "w", encoding="utf-8") as f: json.dump(output_data, f, indent=2)
            _save_docx_report(docx_path, item_name, src_path.name, output_data["generation_info"]["timestamp"], summary, hara, safety_goals, all_fsrs)
            _update_manifest(fsr_dir, [json_path, docx_path], src_path, item_name)
            file_list = f"📄 JSON: {json_path.name}\n📘 Word: {docx_path.name}"
        except Exception as e:
            log.error(f"Saving error: {e}"); return f"❌ Save error: {e}"

    if save_mode == "file": return f"✅ Safety analysis artifacts saved to '{fsr_dir.name}' folder.\n{file_list}"
    
    preview = [f"✅ Safety Analysis Complete for **{item_name}**",
               f"- **{summary['hazardous_events']}** Hazardous Events Identified",
               f"- **{summary['safety_goals']}** Safety Goals Derived",
               f"- **{summary['fsrs_generated']}** FSRs Generated"]
    if summary['asil_distribution']:
        dist_str = ", ".join([f"ASIL {k}: {v}" for k, v in sorted(summary['asil_distribution'].items())])
        preview.append(f"- **ASIL Distribution**: {dist_str}")

    if save_mode == "both": return f"{' '.join(preview)}\n\nFiles saved to '{fsr_dir.name}' folder:\n{file_list}"
    return "\n".join(preview)