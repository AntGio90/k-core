import json
import json5
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime
import re
import os

from cat.mad_hatter.decorators import tool, hook
from cat.log import log


# Utilities to load ISO 26262 data from disk (ISO26262 folder in plugin)

def _get_iso26262_folder_path() -> str:
    return os.path.join(os.path.dirname(__file__), "ISO26262")


def _load_iso26262_data_from_folder() -> Optional[Dict[str, Any]]:
    folder = _get_iso26262_folder_path()
    if not os.path.isdir(folder):
        return None
    data: Dict[str, Any] = {}

    # 1) Prefer combined export if present
    combined_path = os.path.join(folder, "fsc_data.json")
    try:
        if os.path.isfile(combined_path):
            with open(combined_path, "r", encoding="utf-8") as f:
                text = f.read()
            try:
                obj = json5.loads(text)
            except Exception:
                obj = json.loads(text)
            if isinstance(obj, dict):
                data.update(obj)
    except Exception as e:
        log.error(f"Error reading combined fsc_data.json: {e}")

    # 2) Merge individual JSON files
    known_keys = {
        "item_definition",
        "extracted_functions_interfaces",
        "malfunctions",
        "hara",
        "safety_goals",
        "fsc",
        "allocation_hints",
        "traceability"
    }
    try:
        for name in os.listdir(folder):
            if not name.lower().endswith(".json"):
                continue
            path = os.path.join(folder, name)
            if os.path.abspath(path) == os.path.abspath(combined_path):
                continue
            try:
                with open(path, "r", encoding="utf-8") as f:
                    text = f.read()
                try:
                    obj = json5.loads(text)
                except Exception:
                    obj = json.loads(text)
                if not isinstance(obj, dict):
                    continue
                # If file contains known top-level keys, merge
                if any(k in obj for k in known_keys):
                    for k in known_keys:
                        if k in obj and obj[k] is not None:
                            data[k] = obj[k]
                else:
                    base = os.path.splitext(name)[0]
                    if base in known_keys:
                        data[base] = obj
            except Exception as e:
                log.error(f"Error reading {name}: {e}")
    except Exception as e:
        log.error(f"Error scanning ISO26262 folder: {e}")

    return data or None


def _ensure_iso26262_data(cat) -> bool:
    try:
        current = getattr(cat.working_memory, 'iso26262_data', None)
        if current:
            return True
        loaded = _load_iso26262_data_from_folder()
        if loaded:
            if not hasattr(cat.working_memory, 'iso26262_data'):
                cat.working_memory.iso26262_data = {}
            cat.working_memory.iso26262_data.update(loaded)
            log.info(f"Loaded ISO 26262 data from folder: {_get_iso26262_folder_path()}")
            return True
        return False
    except Exception as e:
        log.error(f"Error ensuring ISO 26262 data: {e}")
        return False


class ASIL(str, Enum):
    """Automotive Safety Integrity Level enumeration"""
    QM = "QM"
    A = "A"
    B = "B" 
    C = "C"
    D = "D"


class SeverityLevel(str, Enum):
    """Severity levels for HARA"""
    S0 = "S0"
    S1 = "S1"
    S2 = "S2"
    S3 = "S3"


class ExposureLevel(str, Enum):
    """Exposure levels for HARA"""
    E0 = "E0"
    E1 = "E1"
    E2 = "E2"
    E3 = "E3"
    E4 = "E4"


class ControllabilityLevel(str, Enum):
    """Controllability levels for HARA"""
    C0 = "C0"
    C1 = "C1"
    C2 = "C2"
    C3 = "C3"


class MalfunctionType(str, Enum):
    """Types of malfunctions for analysis"""
    OMISSION = "omission"
    COMMISSION = "commission"
    OUT_OF_RANGE = "out_of_range"
    STUCK = "stuck"
    TIMING = "timing"
    LATENCY = "latency"
    SEQUENCE = "sequence"


@dataclass
class ItemDefinition:
    """Normalized Item Definition structure"""
    item_name: str
    purpose: str
    boundaries: str
    functions: List[Dict[str, Any]]
    modes: List[Dict[str, Any]]
    interfaces: List[Dict[str, Any]]
    environment: List[str]
    assumptions: List[str]
    constraints: List[str]


@dataclass
class Malfunction:
    """Malfunction representation"""
    malfunction_id: str
    function_id: str
    malfunction_type: MalfunctionType
    description: str
    conditions: List[str]


@dataclass
class HazardousEvent:
    """Hazardous Event from HARA"""
    event_id: str
    hazard: str
    operational_situation: str
    severity: SeverityLevel
    exposure: ExposureLevel
    controllability: ControllabilityLevel
    asil: ASIL
    rationale: str


@dataclass
class SafetyGoal:
    """Safety Goal definition"""
    sg_id: str
    text: str
    asil: ASIL
    safe_state: str
    ftti_ms: int
    assumptions: List[str]
    external_measures: List[str]


@dataclass
class FSR:
    """Functional Safety Requirement"""
    fsr_id: str
    text: str
    asil: ASIL
    detection: str
    reaction: str
    timing_ms: int
    interfaces: List[str]
    assumptions: List[str]
    independence: str


@dataclass
class FSCElement:
    """Functional Safety Concept Element"""
    safety_goal_id: str
    text: str
    asil: ASIL
    safe_state: str
    ftti_ms: int
    fsrs: List[FSR]


class ISO26262FSCHelper:
    """Helper class for ISO 26262 FSC operations"""

    @staticmethod
    def determine_asil(severity: SeverityLevel, exposure: ExposureLevel, controllability: ControllabilityLevel) -> ASIL:
        """Determine ASIL based on S, E, C parameters according to ISO 26262"""
        # ASIL determination matrix according to ISO 26262-3
        asil_matrix = {
            ("S0", "E0", "C0"): ASIL.QM, ("S0", "E0", "C1"): ASIL.QM, ("S0", "E0", "C2"): ASIL.QM, ("S0", "E0", "C3"): ASIL.QM,
            ("S0", "E1", "C0"): ASIL.QM, ("S0", "E1", "C1"): ASIL.QM, ("S0", "E1", "C2"): ASIL.QM, ("S0", "E1", "C3"): ASIL.QM,
            ("S0", "E2", "C0"): ASIL.QM, ("S0", "E2", "C1"): ASIL.QM, ("S0", "E2", "C2"): ASIL.QM, ("S0", "E2", "C3"): ASIL.QM,
            ("S0", "E3", "C0"): ASIL.QM, ("S0", "E3", "C1"): ASIL.QM, ("S0", "E3", "C2"): ASIL.QM, ("S0", "E3", "C3"): ASIL.QM,
            ("S0", "E4", "C0"): ASIL.QM, ("S0", "E4", "C1"): ASIL.QM, ("S0", "E4", "C2"): ASIL.QM, ("S0", "E4", "C3"): ASIL.QM,

            ("S1", "E0", "C0"): ASIL.QM, ("S1", "E0", "C1"): ASIL.QM, ("S1", "E0", "C2"): ASIL.QM, ("S1", "E0", "C3"): ASIL.QM,
            ("S1", "E1", "C0"): ASIL.QM, ("S1", "E1", "C1"): ASIL.QM, ("S1", "E1", "C2"): ASIL.QM, ("S1", "E1", "C3"): ASIL.A,
            ("S1", "E2", "C0"): ASIL.QM, ("S1", "E2", "C1"): ASIL.QM, ("S1", "E2", "C2"): ASIL.A, ("S1", "E2", "C3"): ASIL.A,
            ("S1", "E3", "C0"): ASIL.QM, ("S1", "E3", "C1"): ASIL.A, ("S1", "E3", "C2"): ASIL.A, ("S1", "E3", "C3"): ASIL.B,
            ("S1", "E4", "C0"): ASIL.QM, ("S1", "E4", "C1"): ASIL.A, ("S1", "E4", "C2"): ASIL.B, ("S1", "E4", "C3"): ASIL.B,

            ("S2", "E0", "C0"): ASIL.QM, ("S2", "E0", "C1"): ASIL.QM, ("S2", "E0", "C2"): ASIL.QM, ("S2", "E0", "C3"): ASIL.QM,
            ("S2", "E1", "C0"): ASIL.QM, ("S2", "E1", "C1"): ASIL.QM, ("S2", "E1", "C2"): ASIL.A, ("S2", "E1", "C3"): ASIL.A,
            ("S2", "E2", "C0"): ASIL.QM, ("S2", "E2", "C1"): ASIL.A, ("S2", "E2", "C2"): ASIL.A, ("S2", "E2", "C3"): ASIL.B,
            ("S2", "E3", "C0"): ASIL.A, ("S2", "E3", "C1"): ASIL.A, ("S2", "E3", "C2"): ASIL.B, ("S2", "E3", "C3"): ASIL.B,
            ("S2", "E4", "C0"): ASIL.A, ("S2", "E4", "C1"): ASIL.B, ("S2", "E4", "C2"): ASIL.B, ("S2", "E4", "C3"): ASIL.C,

            ("S3", "E0", "C0"): ASIL.QM, ("S3", "E0", "C1"): ASIL.QM, ("S3", "E0", "C2"): ASIL.QM, ("S3", "E0", "C3"): ASIL.QM,
            ("S3", "E1", "C0"): ASIL.QM, ("S3", "E1", "C1"): ASIL.A, ("S3", "E1", "C2"): ASIL.A, ("S3", "E1", "C3"): ASIL.B,
            ("S3", "E2", "C0"): ASIL.A, ("S3", "E2", "C1"): ASIL.A, ("S3", "E2", "C2"): ASIL.B, ("S3", "E2", "C3"): ASIL.B,
            ("S3", "E3", "C0"): ASIL.A, ("S3", "E3", "C1"): ASIL.B, ("S3", "E3", "C2"): ASIL.B, ("S3", "E3", "C3"): ASIL.C,
            ("S3", "E4", "C0"): ASIL.B, ("S3", "E4", "C1"): ASIL.B, ("S3", "E4", "C2"): ASIL.C, ("S3", "E4", "C3"): ASIL.D,
        }

        key = (severity.value, exposure.value, controllability.value)
        return asil_matrix.get(key, ASIL.QM)

    @staticmethod
    def validate_fsr_consistency(fsr: FSR, safety_goal: SafetyGoal) -> List[str]:
        """Validate FSR consistency with safety goal"""
        issues = []

        # Check ASIL consistency
        if ASIL(fsr.asil).name > ASIL(safety_goal.asil).name:
            issues.append(f"FSR {fsr.fsr_id} ASIL ({fsr.asil}) cannot be higher than Safety Goal ASIL ({safety_goal.asil})")

        # Check timing consistency
        if fsr.timing_ms > safety_goal.ftti_ms:
            issues.append(f"FSR {fsr.fsr_id} timing ({fsr.timing_ms}ms) exceeds Safety Goal FTTI ({safety_goal.ftti_ms}ms)")

        return issues


@tool
def id_ingest_normalize(tool_input: str, cat) -> str:
    """Parse and normalize an Item Definition (PDF/DOCX/Markdown/JSON).
    Input: Path to file or JSON payload containing item definition data.
    Normalizes into internal schema with functions, operational scenarios, interfaces, modes, assumptions, constraints.
    """
    try:
        log.info(f"Processing Item Definition input: {tool_input[:100]}...")

        # Try to parse as JSON first
        try:
            if tool_input.strip().startswith('{'):
                data = json5.loads(tool_input)
            else:
                # Assume it's a file path or description - create a basic structure
                data = {
                    "item_name": "Extracted from input",
                    "purpose": tool_input[:200] + "..." if len(tool_input) > 200 else tool_input,
                    "boundaries": "To be defined based on analysis",
                    "functions": [],
                    "modes": [],
                    "interfaces": [],
                    "environment": [],
                    "assumptions": [],
                    "constraints": []
                }
        except Exception:
            # Create structure from text input
            data = {
                "item_name": "Item extracted from text",
                "purpose": tool_input[:200] + "..." if len(tool_input) > 200 else tool_input,
                "boundaries": "System boundaries to be analyzed",
                "functions": [{"function_id": "F001", "name": "Primary Function", "description": "Main system function"}],
                "modes": [{"mode_id": "M001", "name": "Normal Operation", "description": "Standard operating mode"}],
                "interfaces": [{"interface_id": "I001", "type": "input", "description": "System inputs"}],
                "environment": ["Standard automotive environment"],
                "assumptions": ["Standard operational assumptions"],
                "constraints": ["Automotive safety constraints"]
            }

        # Create ItemDefinition object
        item_def = ItemDefinition(**data)

        # Store in working memory
        if not hasattr(cat.working_memory, 'iso26262_data'):
            cat.working_memory.iso26262_data = {}

        cat.working_memory.iso26262_data['item_definition'] = asdict(item_def)

        log.info("Item Definition successfully normalized and stored")

        return f"✓ Item Definition normalized and stored: '{item_def.item_name}' with {len(item_def.functions)} functions, {len(item_def.modes)} modes, {len(item_def.interfaces)} interfaces"

    except Exception as e:
        log.error(f"Error in id_ingest_normalize: {str(e)}")
        return f"❌ Error normalizing Item Definition: {str(e)}"


# Helper to gather uploaded texts from declarative memory (Rabbit Hole)
def _gather_uploaded_texts(cat,
                           files: Optional[List[str]] = None,
                           metadata_filter: Optional[Dict[str, Any]] = None,
                           limit_sources: Optional[int] = None,
                           max_chars_per_source: int = 100000) -> List[Dict[str, str]]:
    ALLOWED_EXTS = {".pdf", ".docx", ".txt", ".md", ".rtf", ".html", ".htm"}
    try:
        points, next_offset = cat.memory.vectors.declarative.get_all_points(limit=10000, offset=None)
    except Exception:
        return []

    all_points = list(points) if points else []
    hops = 0
    while next_offset and hops < 50:
        hops += 1
        chunk, next_offset = cat.memory.vectors.declarative.get_all_points(limit=10000, offset=next_offset)
        if not chunk:
            break
        all_points.extend(chunk)

    grouped: Dict[str, List[Any]] = {}
    for p in all_points:
        payload = getattr(p, 'payload', {}) or {}
        meta = payload.get('metadata') or {}
        src = meta.get('source')
        if not isinstance(src, str):
            continue
        if not any(src.lower().endswith(ext) for ext in ALLOWED_EXTS):
            continue
        if files:
            if os.path.basename(src) not in files:
                continue
        if metadata_filter:
            ok = True
            for k, v in metadata_filter.items():
                if meta.get(k) != v:
                    ok = False
                    break
            if not ok:
                continue
        grouped.setdefault(src, []).append(p)

    if not grouped:
        return []

    def _recency(points_list):
        return max((getattr(pt, 'payload', {}).get('metadata', {}).get('when', 0)) for pt in points_list)

    items = sorted(grouped.items(), key=lambda kv: _recency(kv[1]), reverse=True)
    if limit_sources is not None:
        items = items[: max(1, limit_sources)]

    def _sort_key(pt):
        return getattr(pt, 'payload', {}).get('metadata', {}).get('when', 0)

    result: List[Dict[str, str]] = []
    for src, pts in items:
        pts.sort(key=_sort_key)
        out = []
        used = 0
        for pt in pts:
            text = (getattr(pt, 'payload', {}) or {}).get('page_content') or ''
            if not text:
                continue
            if used + len(text) > max_chars_per_source:
                remain = max_chars_per_source - used
                if remain > 0:
                    out.append(text[:remain])
                    used += remain
                break
            out.append(text)
            used += len(text)
        result.append({"source": os.path.basename(src), "text": "\n".join(out)})
    return result


@tool
def id_ingest_from_rabbithole(tool_input: str, cat) -> str:
    """Ingest Item Definition from documents previously uploaded via Rabbit Hole (DOCX/PDF/TXT/MD/HTML).
    Optional JSON input supports: {files: [basenames], metadata: {...}, limit_sources: N, max_chars_per_source: M}.
    If no JSON provided, the most recent eligible sources are used. The text is forwarded to id_ingest_normalize.
    """
    try:
        files = None
        metadata = None
        limit_sources = None
        max_chars = 100000
        payload = None
        try:
            if tool_input and tool_input.strip().startswith('{'):
                payload = json5.loads(tool_input)
        except Exception:
            payload = None
        if isinstance(payload, dict):
            files = payload.get('files')
            metadata = payload.get('metadata')
            limit_sources = payload.get('limit_sources')
            max_chars = int(payload.get('max_chars_per_source', max_chars))

        docs = _gather_uploaded_texts(cat,
                                      files=files,
                                      metadata_filter=metadata,
                                      limit_sources=limit_sources,
                                      max_chars_per_source=max_chars)
        if not docs:
            return "❌ No suitable documents found in memory. Upload DOCX/PDF/TXT/MD/HTML via Rabbit Hole or adjust filters."

        combined = "\n\n".join([f"### Source: {d['source']}\n{d['text']}" for d in docs])
        result = id_ingest_normalize(combined, cat)
        used_sources = ", ".join(d['source'] for d in docs)
        return f"{result}\nSources ingested: {used_sources}"

    except Exception as e:
        log.error(f"Error in id_ingest_from_rabbithole: {str(e)}")
        return f"❌ Error ingesting from Rabbit Hole: {str(e)}"


@tool
def id_extract_functions_interfaces(tool_input: str, cat) -> str:
    """Extract functional chains, interfaces (I/O, comms, power, HMI), operating/degradation modes.
    Input: 'use last' to read from working memory or fresh JSON with function/interface data.
    """
    try:
        if tool_input.strip().lower() == "use last":
            # Use data from working memory
            if not hasattr(cat.working_memory, 'iso26262_data') or 'item_definition' not in cat.working_memory.iso26262_data:
                return "❌ No Item Definition found in working memory. Please run id_ingest_normalize first."

            item_data = cat.working_memory.iso26262_data['item_definition']
        else:
            # Parse fresh JSON
            item_data = json5.loads(tool_input)

        # Extract and categorize interfaces
        interfaces = {
            'input': [],
            'output': [], 
            'communication': [],
            'power': [],
            'hmi': []
        }

        for interface in item_data.get('interfaces', []):
            iface_type = interface.get('type', 'input').lower()
            if iface_type in interfaces:
                interfaces[iface_type].append(interface)
            else:
                interfaces['input'].append(interface)

        # Extract functional chains
        functional_chains = []
        for func in item_data.get('functions', []):
            chain = {
                'function_id': func.get('function_id', f"F{len(functional_chains)+1:03d}"),
                'name': func.get('name', 'Unnamed Function'),
                'inputs': func.get('inputs', []),
                'outputs': func.get('outputs', []),
                'dependencies': func.get('dependencies', [])
            }
            functional_chains.append(chain)

        # Extract modes (operating and degradation)
        operating_modes = []
        degradation_modes = []

        for mode in item_data.get('modes', []):
            mode_type = mode.get('type', 'operating').lower()
            if 'degrad' in mode_type or 'fail' in mode_type:
                degradation_modes.append(mode)
            else:
                operating_modes.append(mode)

        # Store extracted data
        extracted_data = {
            'functional_chains': functional_chains,
            'interfaces': interfaces,
            'operating_modes': operating_modes,
            'degradation_modes': degradation_modes
        }

        cat.working_memory.iso26262_data['extracted_functions_interfaces'] = extracted_data

        summary = f"✓ Extracted {len(functional_chains)} functional chains, {len(operating_modes)} operating modes, {len(degradation_modes)} degradation modes"
        summary += f"\n- I/O Interfaces: {len(interfaces['input'])} inputs, {len(interfaces['output'])} outputs"
        summary += f"\n- Communication: {len(interfaces['communication'])}, Power: {len(interfaces['power'])}, HMI: {len(interfaces['hmi'])}"

        return summary

    except Exception as e:
        log.error(f"Error in id_extract_functions_interfaces: {str(e)}")
        return f"❌ Error extracting functions/interfaces: {str(e)}"


@tool
def malfunction_hypotheses_generate(tool_input: str, cat) -> str:
    """Generate malfunction lists by function/mode/interface covering omission, commission, out-of-range, stuck, timing, latency, sequence.
    Input: Optional filter criteria or empty for full analysis.
    """
    try:
        if not hasattr(cat.working_memory, 'iso26262_data') or 'extracted_functions_interfaces' not in cat.working_memory.iso26262_data:
            return "❌ No extracted functions/interfaces found. Please run id_extract_functions_interfaces first."

        extracted_data = cat.working_memory.iso26262_data['extracted_functions_interfaces']
        malfunctions = []

        # Generate malfunctions for each function
        for func in extracted_data['functional_chains']:
            func_id = func['function_id']

            for mal_type in MalfunctionType:
                malfunction = Malfunction(
                    malfunction_id=f"{func_id}_{mal_type.value.upper()}",
                    function_id=func_id,
                    malfunction_type=mal_type,
                    description=f"{func['name']} - {mal_type.value.replace('_', ' ').title()}",
                    conditions=ISO26262FSCHelper._generate_malfunction_conditions(mal_type, func)
                )
                malfunctions.append(malfunction)

        # Generate interface-specific malfunctions
        for iface_type, interfaces in extracted_data['interfaces'].items():
            for interface in interfaces:
                iface_id = interface.get('interface_id', f"I_{iface_type}_{len(malfunctions)}")

                # Focus on critical malfunction types for interfaces
                critical_types = [MalfunctionType.OMISSION, MalfunctionType.OUT_OF_RANGE, 
                                 MalfunctionType.TIMING, MalfunctionType.STUCK]

                for mal_type in critical_types:
                    malfunction = Malfunction(
                        malfunction_id=f"{iface_id}_{mal_type.value.upper()}",
                        function_id=iface_id,
                        malfunction_type=mal_type,
                        description=f"{iface_type.title()} Interface - {mal_type.value.replace('_', ' ').title()}",
                        conditions=ISO26262FSCHelper._generate_interface_malfunction_conditions(mal_type, interface)
                    )
                    malfunctions.append(malfunction)

        # Store malfunctions
        cat.working_memory.iso26262_data['malfunctions'] = [asdict(m) for m in malfunctions]

        summary = f"✓ Generated {len(malfunctions)} malfunction hypotheses:"
        for mal_type in MalfunctionType:
            count = sum(1 for m in malfunctions if m.malfunction_type == mal_type)
            summary += f"\n- {mal_type.value.replace('_', ' ').title()}: {count}"

        return summary

    except Exception as e:
        log.error(f"Error in malfunction_hypotheses_generate: {str(e)}")
        return f"❌ Error generating malfunction hypotheses: {str(e)}"


@staticmethod
def _generate_malfunction_conditions(mal_type: MalfunctionType, func: Dict) -> List[str]:
    """Generate conditions for function malfunctions"""
    base_conditions = [
        "System operating in normal mode",
        "Environmental conditions within specification",
        "No external interference"
    ]

    type_specific = {
        MalfunctionType.OMISSION: ["Function not executed when required"],
        MalfunctionType.COMMISSION: ["Function executed when not required"],
        MalfunctionType.OUT_OF_RANGE: ["Function output exceeds acceptable range"],
        MalfunctionType.STUCK: ["Function output stuck at previous value"],
        MalfunctionType.TIMING: ["Function execution timing violation"],
        MalfunctionType.LATENCY: ["Function response time exceeds threshold"],
        MalfunctionType.SEQUENCE: ["Function executed in wrong sequence"]
    }

    return base_conditions + type_specific.get(mal_type, [])


@staticmethod  
def _generate_interface_malfunction_conditions(mal_type: MalfunctionType, interface: Dict) -> List[str]:
    """Generate conditions for interface malfunctions"""
    base_conditions = [
        "Interface connection established",
        "Communication protocol active",
        "Power supply within specification"
    ]

    type_specific = {
        MalfunctionType.OMISSION: ["Signal not transmitted"],
        MalfunctionType.OUT_OF_RANGE: ["Signal amplitude outside limits"],
        MalfunctionType.TIMING: ["Signal timing violation"],
        MalfunctionType.STUCK: ["Signal stuck at constant value"]
    }

    return base_conditions + type_specific.get(mal_type, [])


# Add the static methods to the helper class
ISO26262FSCHelper._generate_malfunction_conditions = _generate_malfunction_conditions
ISO26262FSCHelper._generate_interface_malfunction_conditions = _generate_interface_malfunction_conditions


@tool
def hara_derive_or_validate(tool_input: str, cat) -> str:
    """If HARA is supplied, validate consistency; else derive hazards, hazardous events, assign S/E/C, compute ASIL, record rationale/assumptions.
    Input: 'derive' for new HARA or JSON with existing HARA data for validation.
    """
    try:
        if tool_input.strip().lower() == "derive":
            # Derive new HARA
            if not hasattr(cat.working_memory, 'iso26262_data') or 'malfunctions' not in cat.working_memory.iso26262_data:
                return "❌ No malfunctions found. Please run malfunction_hypotheses_generate first."

            malfunctions = cat.working_memory.iso26262_data['malfunctions']
            hazardous_events = []

            # Derive hazardous events from malfunctions
            for mal_data in malfunctions:
                # Create hazardous events for significant malfunctions
                if mal_data['malfunction_type'] in ['omission', 'commission', 'out_of_range']:
                    event = HazardousEvent(
                        event_id=f"HE_{len(hazardous_events)+1:03d}",
                        hazard=f"Hazard from {mal_data['description']}",
                        operational_situation="Vehicle in motion during normal operation",
                        severity=ISO26262FSCHelper._derive_severity(mal_data),
                        exposure=ISO26262FSCHelper._derive_exposure(mal_data),
                        controllability=ISO26262FSCHelper._derive_controllability(mal_data),
                        asil=ASIL.QM,  # Will be calculated
                        rationale=f"Derived from malfunction: {mal_data['malfunction_id']}"
                    )

                    # Calculate ASIL
                    event.asil = ISO26262FSCHelper.determine_asil(
                        event.severity, event.exposure, event.controllability
                    )

                    hazardous_events.append(event)

            hara_data = {
                'hazardous_events': [asdict(he) for he in hazardous_events],
                'analysis_date': datetime.now().isoformat(),
                'assumptions': [
                    "Driver is alert and able to respond",
                    "Vehicle systems are maintained properly",
                    "Environmental conditions are within normal range"
                ]
            }

        else:
            # Validate existing HARA
            hara_data = json5.loads(tool_input)
            validation_issues = ISO26262FSCHelper._validate_hara_consistency(hara_data)

            if validation_issues:
                return f"❌ HARA validation failed:\n" + "\n".join(validation_issues)

        # Store HARA data
        cat.working_memory.iso26262_data['hara'] = hara_data

        events_count = len(hara_data['hazardous_events'])
        asil_counts = {}
        for event in hara_data['hazardous_events']:
            asil = event.get('asil', 'QM')
            asil_counts[asil] = asil_counts.get(asil, 0) + 1

        summary = f"✓ HARA completed with {events_count} hazardous events:\n"
        for asil, count in sorted(asil_counts.items()):
            summary += f"- ASIL {asil}: {count} events\n"

        return summary.strip()

    except Exception as e:
        log.error(f"Error in hara_derive_or_validate: {str(e)}")
        return f"❌ Error in HARA: {str(e)}"


@staticmethod
def _derive_severity(mal_data: Dict) -> SeverityLevel:
    """Derive severity level from malfunction data"""
    # Simplified severity derivation - in practice would be more sophisticated
    critical_functions = ['brake', 'steer', 'accelerat', 'power']

    if any(keyword in mal_data['description'].lower() for keyword in critical_functions):
        return SeverityLevel.S3
    elif 'communication' in mal_data['description'].lower():
        return SeverityLevel.S2
    else:
        return SeverityLevel.S1


@staticmethod  
def _derive_exposure(mal_data: Dict) -> ExposureLevel:
    """Derive exposure level from malfunction data"""
    # Simplified exposure derivation
    if 'normal operation' in str(mal_data.get('conditions', [])).lower():
        return ExposureLevel.E4
    else:
        return ExposureLevel.E3


@staticmethod
def _derive_controllability(mal_data: Dict) -> ControllabilityLevel:
    """Derive controllability level from malfunction data"""
    # Simplified controllability derivation
    if mal_data['malfunction_type'] in ['timing', 'latency']:
        return ControllabilityLevel.C3  # Difficult to control
    elif mal_data['malfunction_type'] in ['omission', 'commission']:
        return ControllabilityLevel.C2  # Moderately controllable
    else:
        return ControllabilityLevel.C1  # Usually controllable


@staticmethod
def _validate_hara_consistency(hara_data: Dict) -> List[str]:
    """Validate HARA data consistency"""
    issues = []

    for event in hara_data.get('hazardous_events', []):
        expected_asil = ISO26262FSCHelper.determine_asil(
            SeverityLevel(event['severity']),
            ExposureLevel(event['exposure']),
            ControllabilityLevel(event['controllability'])
        )

        if ASIL(event['asil']) != expected_asil:
            issues.append(f"Event {event['event_id']}: ASIL mismatch - expected {expected_asil}, got {event['asil']}")

    return issues


# Add static methods to helper class  
ISO26262FSCHelper._derive_severity = _derive_severity
ISO26262FSCHelper._derive_exposure = _derive_exposure
ISO26262FSCHelper._derive_controllability = _derive_controllability
ISO26262FSCHelper._validate_hara_consistency = _validate_hara_consistency


@tool
def safety_goals_synthesize(tool_input: str, cat) -> str:
    """From hazardous events, synthesize Safety Goals with Safe State, FTTI, ASIL, assumptions/residual risk notes; deduplicate/merge.
    Input: Optional parameters for FTTI calculation or empty for default derivation.
    """
    try:
        if not hasattr(cat.working_memory, 'iso26262_data') or 'hara' not in cat.working_memory.iso26262_data:
            return "❌ No HARA data found. Please run hara_derive_or_validate first."

        hara_data = cat.working_memory.iso26262_data['hara']
        safety_goals = []

        # Group hazardous events by similar characteristics for consolidation
        event_groups = ISO26262FSCHelper._group_hazardous_events(hara_data['hazardous_events'])

        for group_id, events in event_groups.items():
            # Find highest ASIL in group
            max_asil = max([ASIL(event['asil']) for event in events], key=lambda x: ['QM', 'A', 'B', 'C', 'D'].index(x.value))

            # Generate safety goal
            representative_event = events[0]

            safety_goal = SafetyGoal(
                sg_id=f"SG_{len(safety_goals)+1:03d}",
                text=ISO26262FSCHelper._generate_safety_goal_text(representative_event, events),
                asil=max_asil,
                safe_state=ISO26262FSCHelper._derive_safe_state(representative_event),
                ftti_ms=ISO26262FSCHelper._calculate_ftti(representative_event, max_asil),
                assumptions=[
                    "Driver maintains situational awareness",
                    "Vehicle sensors operate within specification",
                    "Communication links remain functional"
                ],
                external_measures=ISO26262FSCHelper._derive_external_measures(representative_event)
            )

            safety_goals.append(safety_goal)

        # Store safety goals
        cat.working_memory.iso26262_data['safety_goals'] = [asdict(sg) for sg in safety_goals]

        summary = f"✓ Synthesized {len(safety_goals)} Safety Goals from {len(hara_data['hazardous_events'])} hazardous events:\n"
        for sg in safety_goals:
            summary += f"- {sg.sg_id} (ASIL {sg.asil}): FTTI {sg.ftti_ms}ms\n"

        return summary.strip()

    except Exception as e:
        log.error(f"Error in safety_goals_synthesize: {str(e)}")
        return f"❌ Error synthesizing safety goals: {str(e)}"


@staticmethod
def _group_hazardous_events(events: List[Dict]) -> Dict[str, List[Dict]]:
    """Group similar hazardous events for consolidation"""
    groups = {}

    for event in events:
        # Simple grouping by severity level
        group_key = f"severity_{event['severity']}"
        if group_key not in groups:
            groups[group_key] = []
        groups[group_key].append(event)

    return groups


@staticmethod
def _generate_safety_goal_text(representative_event: Dict, events: List[Dict]) -> str:
    """Generate safety goal text from hazardous events"""
    if len(events) == 1:
        return f"Prevent or mitigate {representative_event['hazard'].lower()}"
    else:
        return f"Prevent or mitigate hazards of severity {representative_event['severity']} level"


@staticmethod
def _derive_safe_state(event: Dict) -> str:
    """Derive appropriate safe state for hazardous event"""
    hazard_lower = event['hazard'].lower()

    if 'brake' in hazard_lower:
        return "Vehicle brought to controlled stop with hazard warnings active"
    elif 'steer' in hazard_lower:
        return "Vehicle maintains lane position with reduced speed and driver alert"
    elif 'accelerat' in hazard_lower:
        return "Engine power limited, vehicle coasts to safe speed"
    else:
        return "System enters fail-safe mode with driver notification"


@staticmethod  
def _calculate_ftti(event: Dict, asil: ASIL) -> int:
    """Calculate Fault Tolerant Time Interval based on event and ASIL"""
    base_ftti = {
        ASIL.QM: 5000,  # 5 seconds
        ASIL.A: 3000,   # 3 seconds  
        ASIL.B: 1500,   # 1.5 seconds
        ASIL.C: 1000,   # 1 second
        ASIL.D: 500     # 0.5 seconds
    }

    return base_ftti.get(asil, 2000)


@staticmethod
def _derive_external_measures(event: Dict) -> List[str]:
    """Derive external measures for hazardous event"""
    measures = ["Driver training and awareness"]

    if 'brake' in event['hazard'].lower():
        measures.append("Regular brake system maintenance")
    elif 'steer' in event['hazard'].lower():
        measures.append("Steering system inspection")

    return measures


# Add static methods to helper class
ISO26262FSCHelper._group_hazardous_events = _group_hazardous_events  
ISO26262FSCHelper._generate_safety_goal_text = _generate_safety_goal_text
ISO26262FSCHelper._derive_safe_state = _derive_safe_state
ISO26262FSCHelper._calculate_ftti = _calculate_ftti
ISO26262FSCHelper._derive_external_measures = _derive_external_measures


@tool(return_direct=False)  
def fsc_derive(tool_input: str, cat) -> str:
    """Derive Functional Safety Requirements (FSRs) per Safety Goal, covering detection/monitoring, reaction to safe state, degradation/limp-home, HMI alerts, external measures/independence, expected diagnostic coverage, environmental constraints.
    Input: Optional specification of FSR derivation parameters.
    """
    try:
        if not hasattr(cat.working_memory, 'iso26262_data') or 'safety_goals' not in cat.working_memory.iso26262_data:
            return "❌ No safety goals found. Please run safety_goals_synthesize first."

        safety_goals = cat.working_memory.iso26262_data['safety_goals']
        fsc_elements = []

        for sg_data in safety_goals:
            safety_goal = SafetyGoal(**sg_data)

            # Derive FSRs for this safety goal
            fsrs = []

            # FSR for fault detection
            detection_fsr = FSR(
                fsr_id=f"{safety_goal.sg_id}_FSR_DET",
                text=f"System shall detect faults that could lead to violation of {safety_goal.sg_id} within {safety_goal.ftti_ms//3}ms",
                asil=safety_goal.asil,
                detection=ISO26262FSCHelper._derive_detection_mechanism(safety_goal),
                reaction="Alert system monitoring component",
                timing_ms=safety_goal.ftti_ms//3,
                interfaces=["monitoring_interface", "diagnostic_interface"],
                assumptions=["Monitoring system operational"],
                independence="Detection independent from main function execution"
            )
            fsrs.append(detection_fsr)

            # FSR for fault reaction
            reaction_fsr = FSR(
                fsr_id=f"{safety_goal.sg_id}_FSR_REACT",
                text=f"System shall transition to safe state within {safety_goal.ftti_ms*2//3}ms upon fault confirmation",
                asil=safety_goal.asil,
                detection="Fault confirmed by detection mechanism",
                reaction=f"Execute transition to: {safety_goal.safe_state}",
                timing_ms=safety_goal.ftti_ms*2//3,
                interfaces=["actuator_interface", "safety_mechanism_interface"],
                assumptions=["Safe state achievable within timing constraints"],
                independence="Reaction path independent from normal operation path"
            )
            fsrs.append(reaction_fsr)

            # FSR for HMI warning
            hmi_fsr = FSR(
                fsr_id=f"{safety_goal.sg_id}_FSR_HMI",
                text=f"System shall alert driver of safety-relevant fault within 500ms",
                asil=safety_goal.asil if safety_goal.asil != ASIL.QM else ASIL.A,
                detection="Safety-relevant fault detected",
                reaction="Display visual/auditory warning to driver",
                timing_ms=500,
                interfaces=["hmi_interface", "warning_system_interface"],
                assumptions=["Driver able to perceive and respond to warnings"],
                independence="Warning system independent from main function"
            )
            fsrs.append(hmi_fsr)

            # FSR for degraded operation
            if safety_goal.asil in [ASIL.C, ASIL.D]:
                degrade_fsr = FSR(
                    fsr_id=f"{safety_goal.sg_id}_FSR_DEGRADE", 
                    text=f"System shall maintain degraded functionality after non-critical fault detection",
                    asil=safety_goal.asil,
                    detection="Non-critical fault affecting performance",
                    reaction="Reduce performance while maintaining safety",
                    timing_ms=safety_goal.ftti_ms,
                    interfaces=["control_interface", "performance_interface"],
                    assumptions=["Degraded operation provides acceptable safety margin"],
                    independence="Degraded mode uses separate control paths"
                )
                fsrs.append(degrade_fsr)

            # Create FSC element
            fsc_element = FSCElement(
                safety_goal_id=safety_goal.sg_id,
                text=safety_goal.text,
                asil=safety_goal.asil,
                safe_state=safety_goal.safe_state,
                ftti_ms=safety_goal.ftti_ms,
                fsrs=fsrs
            )

            fsc_elements.append(fsc_element)

        # Store FSC
        cat.working_memory.iso26262_data['fsc'] = [asdict(fsc) for fsc in fsc_elements]

        # Validate consistency
        consistency_issues = []
        for fsc in fsc_elements:
            for fsr in fsc.fsrs:
                issues = ISO26262FSCHelper.validate_fsr_consistency(fsr, SafetyGoal(**[sg for sg in safety_goals if sg['sg_id'] == fsc.safety_goal_id][0]))
                consistency_issues.extend(issues)

        total_fsrs = sum(len(fsc.fsrs) for fsc in fsc_elements)
        summary = f"✓ Derived Functional Safety Concept with {total_fsrs} FSRs across {len(fsc_elements)} Safety Goals"

        if consistency_issues:
            summary += f"\n⚠️ {len(consistency_issues)} consistency issues detected"

        return summary

    except Exception as e:
        log.error(f"Error in fsc_derive: {str(e)}")
        return f"❌ Error deriving FSC: {str(e)}"


@staticmethod
def _derive_detection_mechanism(safety_goal: SafetyGoal) -> str:
    """Derive appropriate detection mechanism for safety goal"""
    if safety_goal.asil == ASIL.D:
        return "Dual-channel monitoring with voter logic"
    elif safety_goal.asil == ASIL.C:
        return "Plausibility checking with timeout monitoring"  
    elif safety_goal.asil in [ASIL.A, ASIL.B]:
        return "Range checking and reasonableness validation"
    else:
        return "Basic parameter validation"


# Add static method to helper class
ISO26262FSCHelper._derive_detection_mechanism = _derive_detection_mechanism


@tool
def allocation_hints_propose(tool_input: str, cat) -> str:
    """Provide logical allocation hints (no hardware specifics), independence & freedom-from-interference notes.
    Input: Optional allocation constraints or preferences.
    """
    try:
        if not hasattr(cat.working_memory, 'iso26262_data') or 'fsc' not in cat.working_memory.iso26262_data:
            return "❌ No FSC found. Please run fsc_derive first."

        fsc_data = cat.working_memory.iso26262_data['fsc']
        allocation_hints = []

        for fsc_element in fsc_data:
            element_hints = {
                'safety_goal_id': fsc_element['safety_goal_id'],
                'asil': fsc_element['asil'],
                'allocations': [],
                'independence_requirements': [],
                'interference_prevention': []
            }

            for fsr in fsc_element['fsrs']:
                # Determine logical allocation based on FSR type and ASIL
                if 'DET' in fsr['fsr_id']:  # Detection FSR
                    allocation = {
                        'fsr_id': fsr['fsr_id'],
                        'logical_allocation': ISO26262FSCHelper._get_detection_allocation_hint(fsr['asil']),
                        'independence_level': ISO26262FSCHelper._get_independence_requirement(fsr['asil']),
                        'timing_constraint': f"Detection time ≤ {fsr['timing_ms']}ms"
                    }
                elif 'REACT' in fsr['fsr_id']:  # Reaction FSR  
                    allocation = {
                        'fsr_id': fsr['fsr_id'],
                        'logical_allocation': ISO26262FSCHelper._get_reaction_allocation_hint(fsr['asil']),
                        'independence_level': "Separate execution path from normal operation",
                        'timing_constraint': f"Reaction time ≤ {fsr['timing_ms']}ms"
                    }
                elif 'HMI' in fsr['fsr_id']:  # HMI FSR
                    allocation = {
                        'fsr_id': fsr['fsr_id'], 
                        'logical_allocation': "Dedicated warning/display subsystem",
                        'independence_level': "Independent communication path to driver",
                        'timing_constraint': f"Warning time ≤ {fsr['timing_ms']}ms"
                    }
                else:  # Other FSRs
                    allocation = {
                        'fsr_id': fsr['fsr_id'],
                        'logical_allocation': "Application-specific subsystem",
                        'independence_level': fsr.get('independence', 'Standard separation'),
                        'timing_constraint': f"Response time ≤ {fsr['timing_ms']}ms"
                    }

                element_hints['allocations'].append(allocation)

            # Add ASIL-specific independence requirements
            if fsc_element['asil'] == 'D':
                element_hints['independence_requirements'] = [
                    "Dual-channel architecture with independent processing paths",
                    "Separate memory spaces for safety-critical functions", 
                    "Independent power supply monitoring",
                    "Hardware-enforced separation between channels"
                ]
                element_hints['interference_prevention'] = [
                    "Memory protection units to prevent cross-interference",
                    "Temporal isolation via time-triggered scheduling",
                    "Independent communication channels for safety functions",
                    "Hardware barriers between safety and non-safety functions"
                ]
            elif fsc_element['asil'] == 'C':
                element_hints['independence_requirements'] = [
                    "Separate execution contexts for safety functions",
                    "Independent monitoring of critical parameters",
                    "Isolated communication paths for safety data"
                ]
                element_hints['interference_prevention'] = [
                    "Software-based memory protection",
                    "Priority-based scheduling with safety function precedence", 
                    "Message authentication for safety-critical communications"
                ]
            elif fsc_element['asil'] in ['A', 'B']:
                element_hints['independence_requirements'] = [
                    "Logical separation of safety and non-safety functions",
                    "Independent validation of critical inputs"
                ]
                element_hints['interference_prevention'] = [
                    "Resource management to prevent resource starvation",
                    "Input validation to prevent malformed data interference"
                ]

            allocation_hints.append(element_hints)

        # Store allocation hints
        cat.working_memory.iso26262_data['allocation_hints'] = allocation_hints

        total_allocations = sum(len(hints['allocations']) for hints in allocation_hints)
        summary = f"✓ Generated allocation hints for {total_allocations} FSRs across {len(allocation_hints)} Safety Goals\n"

        asil_breakdown = {}
        for hints in allocation_hints:
            asil = hints['asil']
            asil_breakdown[asil] = asil_breakdown.get(asil, 0) + len(hints['allocations'])

        for asil, count in sorted(asil_breakdown.items()):
            summary += f"- ASIL {asil}: {count} allocations\n"

        return summary.strip()

    except Exception as e:
        log.error(f"Error in allocation_hints_propose: {str(e)}")
        return f"❌ Error proposing allocation hints: {str(e)}"


@staticmethod
def _get_detection_allocation_hint(asil: str) -> str:
    """Get detection allocation hint based on ASIL"""
    hints = {
        'D': "Dedicated safety monitoring processor with diverse technology",
        'C': "Separate safety monitoring task with independent timer", 
        'B': "Dedicated monitoring function with priority scheduling",
        'A': "Monitoring integrated with main control loop",
        'QM': "Basic parameter range checking"
    }
    return hints.get(asil, "Standard monitoring approach")


@staticmethod  
def _get_reaction_allocation_hint(asil: str) -> str:
    """Get reaction allocation hint based on ASIL"""
    hints = {
        'D': "Independent safety reaction controller with direct actuator access",
        'C': "Separate safety task with dedicated communication channel",
        'B': "Priority safety function with preemptive execution",
        'A': "Safety function integrated with normal control flow", 
        'QM': "Standard error handling mechanism"
    }
    return hints.get(asil, "Standard reaction mechanism")


@staticmethod
def _get_independence_requirement(asil: str) -> str:
    """Get independence requirement based on ASIL"""
    requirements = {
        'D': "Complete hardware and software independence",
        'C': "Software independence with shared hardware monitoring",
        'B': "Logical independence with resource protection", 
        'A': "Functional independence with data validation",
        'QM': "Basic separation of concerns"
    }
    return requirements.get(asil, "Standard separation")


# Add static methods to helper class
ISO26262FSCHelper._get_detection_allocation_hint = _get_detection_allocation_hint
ISO26262FSCHelper._get_reaction_allocation_hint = _get_reaction_allocation_hint  
ISO26262FSCHelper._get_independence_requirement = _get_independence_requirement


@tool(return_direct=True)
def traceability_build(tool_input: str, cat) -> str:
    """Build and return end-to-end traceability table (CSV format):
    Item Def → Malfunctions → Hazards/Op.Situations → HARA (S/E/C/ASIL) → Safety Goals → FSRs (with FTTI & Safe State).
    Input: Output format preference (csv/json).
    """
    try:
        if not hasattr(cat.working_memory, 'iso26262_data'):
            return "❌ No ISO 26262 data found. Please complete the analysis workflow first."

        data = cat.working_memory.iso26262_data
        format_type = tool_input.strip().lower() if tool_input.strip() else 'csv'

        # Build traceability data
        traceability_records = []

        # Get base data
        item_def = data.get('item_definition', {})
        malfunctions = data.get('malfunctions', [])
        hara = data.get('hara', {})
        safety_goals = data.get('safety_goals', [])
        fsc = data.get('fsc', [])

        # Build comprehensive traceability
        for fsc_element in fsc:
            # Find corresponding safety goal
            safety_goal = next((sg for sg in safety_goals if sg['sg_id'] == fsc_element['safety_goal_id']), None)
            if not safety_goal:
                continue

            # Find related hazardous events (simplified - in practice would need better mapping)
            related_events = [he for he in hara.get('hazardous_events', []) if he['asil'] == safety_goal['asil']]

            for fsr in fsc_element['fsrs']:
                for event in related_events:
                    # Find related malfunctions (simplified mapping)
                    related_mals = [m for m in malfunctions if m['malfunction_type'] in ['omission', 'commission']][:1]

                    for malfunction in related_mals:
                        record = {
                            'Item_Name': item_def.get('item_name', 'N/A'),
                            'Function_ID': malfunction.get('function_id', 'N/A'),
                            'Malfunction_ID': malfunction.get('malfunction_id', 'N/A'),
                            'Malfunction_Type': malfunction.get('malfunction_type', 'N/A'),
                            'Hazardous_Event_ID': event.get('event_id', 'N/A'),
                            'Hazard': event.get('hazard', 'N/A'),
                            'Operational_Situation': event.get('operational_situation', 'N/A'),
                            'Severity': event.get('severity', 'N/A'),
                            'Exposure': event.get('exposure', 'N/A'),
                            'Controllability': event.get('controllability', 'N/A'),
                            'ASIL': event.get('asil', 'N/A'),
                            'Safety_Goal_ID': safety_goal.get('sg_id', 'N/A'),
                            'Safety_Goal_Text': safety_goal.get('text', 'N/A'),
                            'Safe_State': safety_goal.get('safe_state', 'N/A'),
                            'FTTI_ms': safety_goal.get('ftti_ms', 'N/A'),
                            'FSR_ID': fsr.get('fsr_id', 'N/A'),
                            'FSR_Text': fsr.get('text', 'N/A'),
                            'FSR_ASIL': fsr.get('asil', 'N/A'),
                            'FSR_Timing_ms': fsr.get('timing_ms', 'N/A'),
                            'Detection_Method': fsr.get('detection', 'N/A'),
                            'Reaction_Method': fsr.get('reaction', 'N/A')
                        }
                        traceability_records.append(record)

        # Generate output based on format
        if format_type == 'json':
            output = json.dumps({
                'traceability_matrix': traceability_records,
                'summary': {
                    'total_records': len(traceability_records),
                    'item_name': item_def.get('item_name', 'N/A'),
                    'analysis_date': datetime.now().isoformat(),
                    'safety_goals_count': len(safety_goals),
                    'fsrs_count': sum(len(fsc_el['fsrs']) for fsc_el in fsc)
                }
            }, indent=2)
        else:  # CSV format
            if not traceability_records:
                return "❌ No traceability records generated. Please ensure complete analysis workflow."

            # Build CSV
            headers = list(traceability_records[0].keys())
            csv_lines = [','.join(headers)]

            for record in traceability_records:
                csv_line = ','.join([f'"{str(record.get(header, ""))}"' for header in headers])
                csv_lines.append(csv_line)

            output = '\n'.join(csv_lines)

        # Store traceability data
        cat.working_memory.iso26262_data['traceability'] = traceability_records

        return f"✓ Traceability Matrix Generated ({format_type.upper()}):\n{len(traceability_records)} traceability records\n\n{output}"

    except Exception as e:
        log.error(f"Error in traceability_build: {str(e)}")
        return f"❌ Error building traceability: {str(e)}"


@tool(return_direct=True)
def fsc_export(tool_input: str, cat) -> str:
    """Export artifacts: FSC document (Markdown) with Item overview, HARA summary, Safety Goals, Safe States & FTTIs, FSRs, allocation hints, assumptions/external measures, independence, open issues, compliance checklist.
    Input: format=md|pdf,json=pretty|raw for export options.
    """
    try:
        if not hasattr(cat.working_memory, 'iso26262_data'):
            return "❌ No ISO 26262 data found. Please complete the analysis workflow first."

        data = cat.working_memory.iso26262_data

        # Parse export parameters
        params = {}
        if tool_input.strip():
            for param in tool_input.split(','):
                if '=' in param:
                    key, value = param.split('=', 1)
                    params[key.strip()] = value.strip()

        format_type = params.get('format', 'md')
        json_format = params.get('json', 'pretty')

        # Generate FSC document
        fsc_doc = ISO26262FSCHelper._generate_fsc_document(data)

        # Generate compliance checklist
        checklist = ISO26262FSCHelper._generate_compliance_checklist(data)

        # Prepare exports
        exports = {}

        if format_type == 'md':
            exports['fsc_document.md'] = fsc_doc

        exports['compliance_checklist.md'] = checklist

        # Add JSON exports if requested
        if json_format == 'pretty':
            exports['fsc_data.json'] = json.dumps(data, indent=2, default=str)
        elif json_format == 'raw': 
            exports['fsc_data.json'] = json.dumps(data, separators=(',', ':'), default=str)

        # Add traceability CSV
        if 'traceability' in data:
            traceability_records = data['traceability']
            if traceability_records:
                headers = list(traceability_records[0].keys())
                csv_lines = [','.join(headers)]
                for record in traceability_records:
                    csv_line = ','.join([f'"{str(record.get(header, ""))}"' for header in headers])
                    csv_lines.append(csv_line)
                exports['traceability_matrix.csv'] = '\n'.join(csv_lines)

        # Create export summary
        item_name = data.get('item_definition', {}).get('item_name', 'Unknown Item')
        safety_goals_count = len(data.get('safety_goals', []))
        fsrs_count = sum(len(fsc_el['fsrs']) for fsc_el in data.get('fsc', []))

        export_summary = f"""
✓ ISO 26262 FSC Export Complete for: {item_name}

Generated Artifacts:
• FSC Document ({format_type.upper()})
• Compliance Checklist
• Traceability Matrix (CSV)
• Analysis Data (JSON)

Analysis Summary:
• Safety Goals: {safety_goals_count}
• Functional Safety Requirements: {fsrs_count}
• Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

⚠️ IMPORTANT COMPLIANCE NOTE:
This is a DRAFT document generated by AI analysis. 
Human safety review and validation are REQUIRED before use in any safety-critical application.
ISO 26262 compliance requires qualified safety engineer review.

Export Files Ready:
"""

        for filename in exports.keys():
            export_summary += f"• {filename}\n"

        # Store export data (in real implementation would save files)
        cat.working_memory.iso26262_exports = exports

        return export_summary + "\n" + fsc_doc[:500] + "\n[Document truncated for preview...]"

    except Exception as e:
        log.error(f"Error in fsc_export: {str(e)}")
        return f"❌ Error exporting FSC: {str(e)}"


@staticmethod
def _generate_fsc_document(data: Dict) -> str:
    """Generate comprehensive FSC document in Markdown format"""

    item_def = data.get('item_definition', {})
    hara = data.get('hara', {})
    safety_goals = data.get('safety_goals', [])
    fsc = data.get('fsc', [])
    allocation_hints = data.get('allocation_hints', [])

    doc = f"""# Functional Safety Concept (FSC)
## ISO 26262 Compliance Document

**Item:** {item_def.get('item_name', 'N/A')}  
**Document Version:** 1.0  
**Date:** {datetime.now().strftime('%Y-%m-%d')}  
**Status:** DRAFT - Human Review Required

---

## 1. Item Overview

### 1.1 Item Definition
**Purpose:** {item_def.get('purpose', 'Not specified')}

**Boundaries:** {item_def.get('boundaries', 'Not specified')}

### 1.2 Functions
"""

    for i, func in enumerate(item_def.get('functions', []), 1):
        doc += f"{i}. **{func.get('name', 'Unnamed Function')}**: {func.get('description', 'No description')}\n"

    doc += f"""
### 1.3 Operating Modes
"""
    for i, mode in enumerate(item_def.get('modes', []), 1):
        doc += f"{i}. **{mode.get('name', 'Unnamed Mode')}**: {mode.get('description', 'No description')}\n"

    doc += f"""
---

## 2. Hazard Analysis and Risk Assessment (HARA) Summary

**Total Hazardous Events:** {len(hara.get('hazardous_events', []))}

### 2.1 ASIL Distribution
"""

    # Calculate ASIL distribution
    asil_counts = {}
    for event in hara.get('hazardous_events', []):
        asil = event.get('asil', 'QM')
        asil_counts[asil] = asil_counts.get(asil, 0) + 1

    for asil in ['D', 'C', 'B', 'A', 'QM']:
        if asil in asil_counts:
            doc += f"- **ASIL {asil}:** {asil_counts[asil]} events\n"

    doc += f"""
### 2.2 Key Hazardous Events
"""

    for event in hara.get('hazardous_events', [])[:5]:  # Show top 5
        doc += f"""
**{event.get('event_id', 'N/A')}** (ASIL {event.get('asil', 'N/A')})  
- Hazard: {event.get('hazard', 'N/A')}  
- Situation: {event.get('operational_situation', 'N/A')}  
- S={event.get('severity', 'N/A')}, E={event.get('exposure', 'N/A')}, C={event.get('controllability', 'N/A')}
"""

    doc += f"""
---

## 3. Safety Goals

**Total Safety Goals:** {len(safety_goals)}
"""

    for sg in safety_goals:
        doc += f"""
### 3.{sg.get('sg_id', 'N/A').split('_')[-1]} {sg.get('sg_id', 'N/A')} (ASIL {sg.get('asil', 'N/A')})

**Goal:** {sg.get('text', 'N/A')}

**Safe State:** {sg.get('safe_state', 'N/A')}

**FTTI:** {sg.get('ftti_ms', 'N/A')} ms

**Assumptions:**
"""
        for assumption in sg.get('assumptions', []):
            doc += f"- {assumption}\n"

        doc += f"""
**External Measures:**
"""
        for measure in sg.get('external_measures', []):
            doc += f"- {measure}\n"

    doc += f"""
---

## 4. Functional Safety Requirements (FSRs)

**Total FSRs:** {sum(len(fsc_el['fsrs']) for fsc_el in fsc)}
"""

    for fsc_element in fsc:
        doc += f"""
### 4.{fsc_element.get('safety_goal_id', 'N/A').split('_')[-1]} Safety Goal {fsc_element.get('safety_goal_id', 'N/A')}
"""

        for fsr in fsc_element.get('fsrs', []):
            doc += f"""
#### {fsr.get('fsr_id', 'N/A')} (ASIL {fsr.get('asil', 'N/A')})

**Requirement:** {fsr.get('text', 'N/A')}

**Detection:** {fsr.get('detection', 'N/A')}

**Reaction:** {fsr.get('reaction', 'N/A')}

**Timing Constraint:** {fsr.get('timing_ms', 'N/A')} ms

**Independence:** {fsr.get('independence', 'N/A')}
"""

    doc += f"""
---

## 5. Allocation Hints

### 5.1 Logical Architecture Allocation
"""

    for hints in allocation_hints:
        doc += f"""
#### {hints.get('safety_goal_id', 'N/A')} (ASIL {hints.get('asil', 'N/A')})

**Independence Requirements:**
"""
        for req in hints.get('independence_requirements', []):
            doc += f"- {req}\n"

        doc += f"""
**Freedom from Interference:**
"""
        for measure in hints.get('interference_prevention', []):
            doc += f"- {measure}\n"

    doc += f"""
---

## 6. Assumptions and External Measures

### 6.1 System Assumptions
"""

    all_assumptions = set()
    for sg in safety_goals:
        all_assumptions.update(sg.get('assumptions', []))

    for assumption in sorted(all_assumptions):
        doc += f"- {assumption}\n"

    doc += f"""
### 6.2 External Measures
"""

    all_external_measures = set()
    for sg in safety_goals:
        all_external_measures.update(sg.get('external_measures', []))

    for measure in sorted(all_external_measures):
        doc += f"- {measure}\n"

    doc += f"""
---

## 7. Open Issues and Recommendations

### 7.1 Items Requiring Human Review
1. **ASIL Assignments:** All ASIL determinations require validation by qualified safety engineer
2. **FTTI Values:** Fault Tolerant Time Intervals need validation against system performance
3. **Safe States:** Safe state definitions require verification against system capabilities  
4. **Independence:** Independence requirements need validation against target architecture

### 7.2 Next Steps
1. Human safety engineer review and validation
2. Technical safety concept development
3. System architecture definition
4. Hardware/software safety requirements derivation

---

## 8. Document Control

**Prepared by:** ISO 26262 FSC Plugin (AI-generated)  
**Review Status:** DRAFT - Not Reviewed  
**Approval Status:** Not Approved

**⚠️ SAFETY NOTICE:** This document is AI-generated and requires human safety engineer review and approval before use in safety-critical applications.
"""

    return doc


@staticmethod
def _generate_compliance_checklist(data: Dict) -> str:
    """Generate ISO 26262 compliance checklist"""

    checklist = f"""# ISO 26262 Compliance Checklist

**Item:** {data.get('item_definition', {}).get('item_name', 'N/A')}  
**Date:** {datetime.now().strftime('%Y-%m-%d')}

## Part 3 - Concept Phase Compliance

### 3.5 - Item Definition
- [x] Item purpose and functionality defined
- [x] Item boundaries specified  
- [x] Functions identified
- [x] Operating modes documented
- [x] Interfaces specified
- [⚠️] Environmental conditions specified (Review Required)
- [⚠️] Assumptions documented (Review Required)

### 3.6 - Hazard Analysis and Risk Assessment  
- [x] Hazards identified
- [x] Operating situations defined
- [x] Hazardous events formulated
- [x] Severity classified
- [x] Exposure probability estimated
- [x] Controllability assessed  
- [x] ASIL determined
- [⚠️] HARA completeness verified (Review Required)

### 3.7 - Functional Safety Concept
- [x] Safety goals specified
- [x] Safe states defined
- [x] FTTI specified
- [x] Functional safety requirements derived
- [x] Allocation to architectural elements
- [⚠️] FSC completeness verified (Review Required)
- [⚠️] Independence requirements validated (Review Required)

## Verification Requirements (ISO 26262-8)

### 8.4 - Verification
- [ ] Independent review performed
- [ ] Completeness verified
- [ ] Correctness verified  
- [ ] Consistency verified
- [ ] ASIL-appropriate methods applied

## Outstanding Items Requiring Human Review

1. **Technical Validation**
   - [ ] ASIL assignments verified by safety engineer
   - [ ] FTTI values validated against system performance
   - [ ] Safe state achievability confirmed
   - [ ] Detection/reaction mechanisms feasibility assessed

2. **Completeness Review**  
   - [ ] All hazards identified and assessed
   - [ ] All safety goals address identified hazards
   - [ ] All FSRs derived from safety goals
   - [ ] Traceability established and verified

3. **Consistency Review**
   - [ ] ASIL consistency maintained through derivation
   - [ ] Timing constraints achievable  
   - [ ] Independence requirements realizable
   - [ ] Allocation feasible with target architecture

## Sign-off Requirements

**Safety Manager:** _________________________ Date: _________

**Chief Safety Engineer:** __________________ Date: _________

**Project Manager:** ______________________ Date: _________

---

**Status:** DRAFT - Human Review and Sign-off Required
"""

    return checklist


# Add static methods to helper class
ISO26262FSCHelper._generate_fsc_document = _generate_fsc_document
ISO26262FSCHelper._generate_compliance_checklist = _generate_compliance_checklist


# Optional Hooks

@hook(priority=1)
def before_cat_sends_message(message, cat):
    """Add compliance banner to outputs containing FSC artifacts"""

    # Check if message contains FSC-related content
    fsc_keywords = ['fsc', 'safety goal', 'asil', 'fsr', 'hazard analysis', 'iso 26262', 'functional safety']

    if any(keyword in message.get('content', '').lower() for keyword in fsc_keywords):
        compliance_banner = "\n\n📋 **COMPLIANCE NOTICE:** This is a DRAFT generated by AI analysis. Human safety engineer review is required before use in safety-critical applications per ISO 26262 requirements."

        if 'content' in message:
            message['content'] += compliance_banner

    return message


@hook(priority=2)
def agent_allowed_tools(allowed_tools, cat):
    """Restrict tools when in ISO 26262 context"""

    # Check if we're in ISO 26262 context
    user_message = getattr(cat.working_memory, 'user_message_json', {})
    message_text = user_message.get('text', '').lower() if user_message else ''

    iso_keywords = ['iso 26262', 'item definition', 'fsc', 'functional safety', 'hara', 'safety goal']

    if any(keyword in message_text for keyword in iso_keywords):
        # Only allow ISO 26262 related tools
        iso26262_tools = [
            'id_ingest_from_rabbithole',
            'id_ingest_normalize',
            'id_extract_functions_interfaces', 
            'malfunction_hypotheses_generate',
            'hara_derive_or_validate',
            'safety_goals_synthesize',
            'fsc_derive',
            'allocation_hints_propose', 
            'traceability_build',
            'fsc_export'
        ]

        # Filter to only ISO 26262 tools
        allowed_tools = [tool for tool in allowed_tools if any(iso_tool in tool for iso_tool in iso26262_tools)]

    return allowed_tools
