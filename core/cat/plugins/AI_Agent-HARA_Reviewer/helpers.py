import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import PyPDF2
from cat.looking_glass.cheshire_cat import CatMessage

# ---------------------------------------------------------------------------
# Costanti di percorso
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).parent
HARA_DEF_PATH = BASE_DIR / "checklists" / "hara_definitions_schema.json"
ASIL_LOOKUP_PATH = BASE_DIR / "checklists" / "asil_lookup.json"
ITEM_DEFINITIONS_DIR = BASE_DIR / "item_definitions"

# ---------------------------------------------------------------------------
# Chiavi accettate per estrarre l’identificativo dell’item
# ---------------------------------------------------------------------------

_VALID_ITEM_KEYS: tuple[str, ...] = (
    "ITEM_ID_PATH",
    "id",  # originali
    "ITEM_ID",
    "item_id_path",
    "item_id",
    "name",
    "path",  # varianti comuni
)

def _extract_item_id(d: Dict[str, Any]) -> Optional[str]:
    """Ritorna la prima chiave valida presente nel dict, senza spazi."""
    for key in _VALID_ITEM_KEYS:
        value = d.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None

# ---------------------------------------------------------------------------
# Caricamento file statici (ASIL lookup e definizioni HARA)
# ---------------------------------------------------------------------------

try:
    with open(ASIL_LOOKUP_PATH, "r", encoding="utf-8") as f:
        ASIL_LOOKUP: Dict[str, Dict[str, Dict[str, str]]] = json.load(f)
except FileNotFoundError as exc:
    raise FileNotFoundError(f"ASIL lookup file not found at {ASIL_LOOKUP_PATH}") from exc

try:
    with open(HARA_DEF_PATH, "r", encoding="utf-8") as f:
        HARA_DEF = json.load(f)
except FileNotFoundError as exc:
    raise FileNotFoundError(f"HARA definitions file not found at {HARA_DEF_PATH}") from exc

# ---------------------------------------------------------------------------
# Helper: lettura testi item (.txt o .pdf)
# ---------------------------------------------------------------------------

def _read_txt(path: Path) -> str:
    return path.read_text(encoding="utf-8")

def _read_pdf(path: Path) -> str:
    reader = PyPDF2.PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)

def load_item_text(item_id_path: str) -> str:
    """
    Restituisce il contenuto testuale dell’item (percorso flessibile).
    """
    if not item_id_path or not isinstance(item_id_path, str):
        raise ValueError(f"Invalid ITEM_ID_PATH: {item_id_path}")

    given = Path(item_id_path)

    # 1) Percorso già completo
    if given.is_file():
        if given.suffix.lower() == ".txt":
            return _read_txt(given)
        if given.suffix.lower() == ".pdf":
            return _read_pdf(given)
        raise ValueError(f"Unsupported file type for {given}")

    # 2) Nome file con estensione, cerca dentro item_definitions/
    if given.suffix.lower() in (".txt", ".pdf"):
        candidate = ITEM_DEFINITIONS_DIR / given.name
        if candidate.is_file():
            return _read_txt(candidate) if candidate.suffix.lower() == ".txt" else _read_pdf(candidate)

    # 3) Solo stem, comportamento legacy
    stem = given.stem if given.suffix else item_id_path
    txt_file = ITEM_DEFINITIONS_DIR / f"{stem}.txt"
    pdf_file = ITEM_DEFINITIONS_DIR / f"{stem}.pdf"

    if txt_file.exists():
        return _read_txt(txt_file)
    if pdf_file.exists():
        return _read_pdf(pdf_file)

    raise FileNotFoundError(
        f"No definition found for ITEM_ID_PATH '{item_id_path}' "
        f"(looked for {txt_file.name} / {pdf_file.name})"
    )

# ---------------------------------------------------------------------------
# Caricamento checklist — ricerca tollerante + hint diagnostico
# ---------------------------------------------------------------------------

# Chiavi alternative accettate come "descrizione" di un punto
_DESC_KEYS: tuple[str, ...] = (
    "description", "desc", "text", "requirement", "requirement_text",
    "details", "detail", "name", "title", "label", "rule",
    "criterion", "criteria", "content", "summary",
)

def _schema_debug_hint(obj: Any) -> str:
    if isinstance(obj, dict):
        keys = list(obj.keys())[:12]
        return f"top-level dict keys: {keys}"
    if isinstance(obj, list):
        types = sorted({type(x).__name__ for x in obj})
        return f"top-level list ({len(obj)} items), element types: {types}"
    return f"top-level type: {type(obj).__name__}"

def _find_checklist(obj: Any) -> Optional[List[Any]]:
    """
    Ricerca ricorsiva. Priorità:
      1) lista di dict con almeno una delle _DESC_KEYS
      2) lista di dict
      3) lista di stringhe
    """
    # Caso lista
    if isinstance(obj, list):
        # 1) lista di dict con chiavi descrittive
        if obj and all(isinstance(el, dict) for el in obj):
            if any(any(k in el for k in _DESC_KEYS) for el in obj):
                return obj
        # 2) lista di dict (senza chiavi note)
        if obj and all(isinstance(el, dict) for el in obj):
            return obj
        # 3) lista di stringhe
        if obj and all(isinstance(el, str) for el in obj):
            return obj
        # Ricerca nei sotto-elementi
        for el in obj:
            res = _find_checklist(el)
            if res is not None:
                return res
        return None

    # Caso dizionario
    if isinstance(obj, dict):
        # Prova chiavi comuni
        for key in ("checklist", "points", "requirements", "items", "rules", "questions", "entries", "list"):
            if key in obj:
                res = _find_checklist(obj[key])
                if res is not None:
                    return res
        # Ricerca ricorsiva nei valori
        for val in obj.values():
            res = _find_checklist(val)
            if res is not None:
                return res
        return None

    # Altri tipi: niente
    return None

def load_checklist() -> List[Any]:
    """
    Estrae una lista plausibile di punti checklist da HARA_DEF.
    Restituisce la lista (elementi dict o stringhe). Alza ValueError con hint se non trovata.
    """
    checklist = _find_checklist(HARA_DEF)
    if not checklist:
        raise ValueError(
            "Unexpected format for HARA definitions schema: impossibile trovare "
            "una lista di punti. " + _schema_debug_hint(HARA_DEF)
        )
    return checklist

# ---------------------------------------------------------------------------
# Review checklist
# ---------------------------------------------------------------------------

def _extract_point_description(point: Any) -> str:
    """
    Estrae una descrizione leggibile dal punto checklist.
    - Se è stringa → ritorna la stringa
    - Se è dict → cerca nelle _DESC_KEYS, altrimenti prova il primo valore stringa
    - Fallback → JSON compatto del dict
    """
    if isinstance(point, str):
        return point.strip()
    if isinstance(point, dict):
        for k in _DESC_KEYS:
            v = point.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
        # prima stringa disponibile
        for v in point.values():
            if isinstance(v, str) and v.strip():
                return v.strip()
        # fallback: rappresentazione compatta
        try:
            return json.dumps(point, ensure_ascii=False)
        except Exception:
            return str(point)
    return str(point)

def run_checklist(item_input: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Esegue la checklist sull’item."""
    if isinstance(item_input, dict):
        ITEM_ID_PATH = _extract_item_id(item_input)
    else:
        ITEM_ID_PATH = str(item_input).strip()

    if not ITEM_ID_PATH:
        raise ValueError(
            "ITEM_ID_PATH missing – expected one of "
            f"{', '.join(_VALID_ITEM_KEYS)} in the input."
        )

    item_text = load_item_text(ITEM_ID_PATH)
    raw_checklist = load_checklist()

    results: List[Dict[str, Any]] = []
    # Accetta sia dict che stringhe; ignora altri tipi
    for idx, point in enumerate(raw_checklist):
        if not isinstance(point, (dict, str)):
            continue
        desc = _extract_point_description(point)
        pt_id = point.get("id", idx) if isinstance(point, dict) else idx

        prompt = (
            "You are reviewing an item definition. Check if it covers this "
            f"requirement:\n- {desc}\nProvide 'pass' or 'fail' with a brief "
            "comment.\nItem definition:\n" + item_text
        )
        
        verdict: str = CatMessage(prompt)
        results.append(
            {"point_id": pt_id, "description": desc, "verdict": verdict}
        )

    def extract_section(text: str, heading: str) -> str:
        pattern = rf"{re.escape(heading)}[:\n](.*?)(?=\n[A-Z][a-z]+[:\n]|$)"
        match = re.search(pattern, text, re.DOTALL)
        return match.group(1).strip() if match else ""

    return {
        "ITEM_ID_PATH": ITEM_ID_PATH,
        "results": results,
        "description": extract_section(item_text, "Description"),
        "functions": extract_section(item_text, "Functions"),
        "operating_scenarios": extract_section(item_text, "Operating Scenarios"),
        "safety_goals": extract_section(item_text, "Safety Goals"),
    }

# ---------------------------------------------------------------------------
# HARA helpers
# ---------------------------------------------------------------------------

def format_review_context(review_result: Dict[str, Any]) -> str:
    parts: List[str] = []
    for key in ("description", "functions", "operating_scenarios", "safety_goals"):
        txt = review_result.get(key)
        if txt:
            parts.append(f"== {key.replace('_', ' ').title()} ==\n{txt}\n")
    return "\n".join(parts)

def extract_hazards_from_text(item_text: str) -> List[Dict[str, Any]]:
    system_prompt = (
        "You are a functional safety engineer. Given the item context, "
        "identify hazards and assign Severity (S0–S3), Exposure (E0–E4), "
        "Controllability (C0–C3). Return JSON array with fields: hazard_id, "
        "description, severity, exposure, controllability, rationale."
    )
    response: str = CatMessage(system_prompt + "\nContext:\n" + item_text)
    return json.loads(response)

def compute_asil(hazards: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    for h in hazards:
        s, e, c = map(str, (h.get("severity"), h.get("exposure"), h.get("controllability")))
        h["ASIL"] = ASIL_LOOKUP.get(s, {}).get(e, {}).get(c, "QM")
    return hazards

def run_hara(review_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    context = format_review_context(review_result)
    hazards_raw = extract_hazards_from_text(context)
    return compute_asil(hazards_raw)

# ---------------------------------------------------------------------------
# Wrapper high‑level
# ---------------------------------------------------------------------------

def run_hara_and_review(item_input: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
    review = run_checklist(item_input)
    hazards = run_hara(review)
    return {
        "ITEM_ID_PATH": review["ITEM_ID_PATH"],
        "review": review["results"],
        "sections": {
            "description": review["description"],
            "functions": review["functions"],
            "operating_scenarios": review["operating_scenarios"],
            "safety_goals": review["safety_goals"],
        },
        "hazards": hazards,
    }

def run_full_review(tool_input: Any, cat=None) -> Dict[str, Any]:
    """
    Entry‑point primario (tool Cheshire‑Cat).
    """
    if isinstance(tool_input, dict):
        ITEM_ID_PATH = _extract_item_id(tool_input)
    elif isinstance(tool_input, str):
        ITEM_ID_PATH = tool_input.strip()
    else:
        raise ValueError(
            "tool_input must be a string or dict containing one of: "
            + ", ".join(_VALID_ITEM_KEYS)
        )

    if not ITEM_ID_PATH:
        raise ValueError(
            "ITEM_ID_PATH could not be determined from input; "
            f"accepted keys: {', '.join(_VALID_ITEM_KEYS)}"
        )

    return run_hara_and_review(ITEM_ID_PATH)
