from .id_generation import format_version


def make_upstream_refs(upstream_metadata: list[dict]) -> list[dict]:
    refs = []
    for meta in upstream_metadata:
        refs.append(
            {
                "artifact_id": meta.get("artifact_id", ""),
                "wp_id": meta.get("wp_id", ""),
                "title": meta.get("title", ""),
                "version": meta.get("version", 0),
                "status": meta.get("status", ""),
            }
        )
    return refs


def summarize_upstream(upstream_refs: list[dict]) -> str:
    if not upstream_refs:
        return "None"
    parts = []
    for ref in upstream_refs:
        version = format_version(ref.get("version", 0))
        parts.append(
            f"{ref.get('artifact_id')} ({ref.get('wp_id')}, v{version}, {ref.get('status')})"
        )
    return "; ".join(parts)


def build_traceability_section(upstream_refs: list[dict]) -> str:
    lines = ["## Traceability"]
    if not upstream_refs:
        lines.append("- No upstream artifacts linked.")
        return "\n".join(lines)

    for ref in upstream_refs:
        version = format_version(ref.get("version", 0))
        title = ref.get("title", "")
        lines.append(
            f"- {ref.get('artifact_id')} ({ref.get('wp_id')}, v{version}, {ref.get('status')}) - {title}"
        )
    return "\n".join(lines)
