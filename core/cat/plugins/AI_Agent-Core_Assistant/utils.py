import json


def parse_tool_input(tool_input):
    if isinstance(tool_input, dict):
        return tool_input
    if isinstance(tool_input, str):
        stripped = tool_input.strip()
        if not stripped:
            return {}
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            return {"text": stripped}
    return {}


def coalesce(*values):
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


def ensure_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        raw = value.replace("\r", "").strip()
        if not raw:
            return []
        if "\n" in raw:
            return [line.strip() for line in raw.split("\n") if line.strip()]
        if ";" in raw:
            return [part.strip() for part in raw.split(";") if part.strip()]
        return [raw]
    return [str(value).strip()]


def normalize_text(value, default=""):
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default
