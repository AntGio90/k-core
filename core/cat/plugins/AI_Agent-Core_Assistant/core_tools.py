from cat.mad_hatter.decorators import tool

from . import config
from .artifact_store import ArtifactStore
from .id_generation import format_version
from .traceability import build_traceability_section
from .utils import parse_tool_input


@tool(return_direct=True, examples=["set iso26262 project: demo_platform"])
def set_iso26262_project(tool_input, cat):
    """Set the active ISO 26262 project slug. Input: {"project_slug": "name", "persist": false}."""
    data = parse_tool_input(tool_input)
    project_slug = data.get("project_slug") or data.get("project") or data.get("text")
    if not project_slug:
        return "Missing project_slug. Provide {\"project_slug\": \"...\"}."
    persist = bool(data.get("persist", False))
    slug = config.set_project_slug(cat, project_slug, persist=persist)
    return f"Active project set to: {slug}"


@tool(return_direct=True, examples=["list iso26262 artifacts", "list iso26262 artifacts for management"])
def list_iso26262_artifacts(tool_input, cat):
    """List ISO 26262 artifacts. Input: {"project_slug": "...", "phase": "...", "wp_id": "...", "status": "..."}."""
    data = parse_tool_input(tool_input)
    project_slug = config.get_project_slug(cat, data)
    phase = data.get("phase")
    wp_id = data.get("wp_id")
    status = data.get("status")

    store = ArtifactStore()
    metas = store.list_metadata(project_slug=project_slug, phase=phase, wp_id=wp_id)
    if status:
        metas = [m for m in metas if m.get("status") == status]
    if not metas:
        return f"No artifacts found for project '{project_slug}'."

    latest = {}
    for meta in metas:
        artifact_id = meta.get("artifact_id")
        if not artifact_id:
            continue
        if artifact_id not in latest or meta.get("version", 0) > latest[artifact_id].get("version", 0):
            latest[artifact_id] = meta

    lines = [f"Artifacts for project '{project_slug}':"]
    for artifact_id, meta in sorted(latest.items()):
        version = format_version(meta.get("version", 0))
        lines.append(
            f"- {artifact_id} ({meta.get('wp_id')}, v{version}, {meta.get('status')}) - {meta.get('title')}"
        )
    return "\n".join(lines)


@tool(return_direct=True, examples=["show iso26262 artifact {\"artifact_id\": \"wp_fsc-...\"}"])
def show_iso26262_artifact(tool_input, cat):
    """Show artifact metadata. Input: {"artifact_id": "...", "include_content": false}."""
    data = parse_tool_input(tool_input)
    artifact_id = data.get("artifact_id") or data.get("text")
    if not artifact_id:
        return "Missing artifact_id. Provide {\"artifact_id\": \"...\"}."

    store = ArtifactStore()
    meta = store.get_latest_by_id(artifact_id)
    if not meta:
        return f"Artifact not found: {artifact_id}"

    version = format_version(meta.get("version", 0))
    lines = [
        f"Artifact ID: {meta.get('artifact_id')}",
        f"Title: {meta.get('title')}",
        f"WP ID: {meta.get('wp_id')}",
        f"Phase: {meta.get('phase')}",
        f"Project: {meta.get('project_slug')}",
        f"Version: v{version}",
        f"Status: {meta.get('status')}",
        f"Author: {meta.get('author')}",
        f"Reviewer: {meta.get('reviewer')}",
        f"Artifact Path: {meta.get('artifact_path')}",
    ]

    if data.get("include_content"):
        content = store.read_artifact_content(meta)
        lines.append("\n---\n")
        lines.append(content)
    return "\n".join(lines)


@tool(return_direct=True, examples=["show iso26262 traceability {\"artifact_id\": \"wp_fsc-...\"}"])
def show_iso26262_traceability(tool_input, cat):
    """Show traceability for an artifact. Input: {"artifact_id": "..."}."""
    data = parse_tool_input(tool_input)
    artifact_id = data.get("artifact_id") or data.get("text")
    if not artifact_id:
        return "Missing artifact_id. Provide {\"artifact_id\": \"...\"}."

    store = ArtifactStore()
    meta = store.get_latest_by_id(artifact_id)
    if not meta:
        return f"Artifact not found: {artifact_id}"

    upstream_refs = meta.get("upstream_refs", [])
    return build_traceability_section(upstream_refs)
