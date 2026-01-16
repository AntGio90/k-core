import re
import uuid
from datetime import datetime, timezone


def slugify(value: str) -> str:
    if value is None:
        return ""
    cleaned = str(value).strip().lower()
    cleaned = re.sub(r"[^a-z0-9]+", "_", cleaned)
    cleaned = cleaned.strip("_")
    return cleaned or "unnamed"


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")


def new_artifact_id(wp_id: str) -> str:
    base = slugify(wp_id)
    stamp = utc_timestamp()
    suffix = uuid.uuid4().hex[:6]
    return f"{base}-{stamp}-{suffix}"


def next_version(versions) -> int:
    if not versions:
        return 1
    return max(versions) + 1


def format_version(version: int) -> str:
    return f"{int(version):02d}"
