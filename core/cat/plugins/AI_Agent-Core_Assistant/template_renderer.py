from pathlib import Path
from . import traceability
from .utils import ensure_list


class _SafeDict(dict):
    def __missing__(self, key):
        return ""


def load_template(path: Path) -> str:
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def render_template(template_str: str, context: dict) -> str:
    return template_str.format_map(_SafeDict(context))


def format_bullets(items: list[str], default: str = "- TBD") -> str:
    items = ensure_list(items)
    if not items:
        return default
    return "\n".join(f"- {item}" for item in items)


def render_document_control(metadata: dict, upstream_refs: list[dict]) -> str:
    template_path = Path(__file__).resolve().parent / "templates" / "document_control.md"
    template_str = load_template(template_path)
    context = {
        "title": metadata.get("title", ""),
        "wp_id": metadata.get("wp_id", ""),
        "artifact_id": metadata.get("artifact_id", ""),
        "version": metadata.get("version", ""),
        "status": metadata.get("status", ""),
        "project_slug": metadata.get("project_slug", ""),
        "phase": metadata.get("phase", ""),
        "author": metadata.get("author", ""),
        "reviewer": metadata.get("reviewer", ""),
        "created_at": metadata.get("created_at", ""),
        "updated_at": metadata.get("updated_at", ""),
        "supersedes": metadata.get("supersedes", {}).get("artifact_id", ""),
        "upstream_refs": traceability.summarize_upstream(upstream_refs),
    }
    return render_template(template_str, context)


def render_assumptions(assumptions: list[str]) -> str:
    section = ["## Assumptions", format_bullets(assumptions)]
    return "\n".join(section)


def render_open_questions(open_questions: list[str]) -> str:
    section = ["## Open Questions", format_bullets(open_questions)]
    return "\n".join(section)


def render_review_checklist(checklist: list[str]) -> str:
    section = ["## Review Checklist", format_bullets(checklist)]
    return "\n".join(section)


def render_document(
    metadata: dict,
    body: str,
    assumptions: list[str],
    open_questions: list[str],
    traceability_section: str,
    review_checklist: list[str],
) -> str:
    title = f"# {metadata.get('title', '')}"
    doc_control = render_document_control(metadata, metadata.get("upstream_refs", []))
    parts = [
        title,
        doc_control,
        body,
        render_assumptions(assumptions),
        render_open_questions(open_questions),
        traceability_section,
        render_review_checklist(review_checklist),
    ]
    return "\n\n".join(part for part in parts if part)


def render_missing_inputs(missing_fields: list[str]) -> str:
    lines = [
        "## Missing Inputs",
        "Provide the following fields to continue:",
    ]
    for field in missing_fields:
        lines.append(f"- {field}")
    lines.append("")
    lines.append("Reply with JSON, for example:")
    lines.append("```json")
    lines.append("{")
    for idx, field in enumerate(missing_fields):
        comma = "," if idx < len(missing_fields) - 1 else ""
        lines.append(f"  \"{field}\": \"...\"{comma}")
    lines.append("}")
    lines.append("```")
    return "\n".join(lines)


def render_missing_upstream(missing_requirements: list[dict]) -> str:
    lines = ["## Missing Upstream Artifacts", "Generate and approve these artifacts:"]
    for req in missing_requirements:
        lines.append(
            f"- {req.get('wp_id')} (phase: {req.get('phase')}, status: {req.get('status', 'APPROVED')})"
        )
    lines.append("")
    lines.append("Once available, re-run this generator.")
    lines.append("")
    lines.append("If you must proceed with placeholders, reply with JSON:")
    lines.append("```json")
    lines.append("{")
    lines.append("  \"allow_missing_upstream\": true,")
    lines.append("  \"manual_upstream_summary\": \"Summarize missing inputs here\"")
    lines.append("}")
    lines.append("```")
    return "\n".join(lines)


def replace_document_control(content: str, new_doc_control: str) -> str:
    marker = "## Document Control"
    start = content.find(marker)
    if start == -1:
        return f"{new_doc_control}\n\n{content}"
    next_header = content.find("\n## ", start + len(marker))
    if next_header == -1:
        return content[:start] + new_doc_control
    return content[:start] + new_doc_control + content[next_header:]
