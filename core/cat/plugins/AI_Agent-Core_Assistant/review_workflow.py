from cat.log import log

from .artifact_store import (
    STATUS_APPROVED,
    STATUS_DRAFT,
    STATUS_IN_REVIEW,
    STATUS_SUPERSEDED,
    build_metadata,
    record_status_change,
    utc_now,
)
from .template_renderer import render_review_checklist, render_document_control, replace_document_control
from .utils import ensure_list, normalize_text


def _review_form(metadata: dict, checklist: list[str]) -> str:
    lines = [
        f"## Review Request: {metadata.get('title')}",
        "",
        f"Artifact ID: {metadata.get('artifact_id')}",
        f"Version: v{metadata.get('version'):02d}",
        f"Status: {metadata.get('status')}",
        f"Reviewer: {metadata.get('reviewer')}",
        "",
        "Provide review results and any change requests.",
        "",
        render_review_checklist(checklist),
    ]
    return "\n".join(lines)


def request_review(store, artifact_id: str, reviewer: str | None = None, checklist: list[str] | None = None) -> str:
    metadata = store.get_latest_by_id(artifact_id)
    if not metadata:
        return f"Artifact not found: {artifact_id}"

    if reviewer:
        metadata["reviewer"] = reviewer

    record_status_change(metadata, STATUS_IN_REVIEW, note="review requested")
    store.update_metadata(metadata)
    return _review_form(metadata, checklist or [])


def request_changes(store, artifact_id: str, change_requests) -> str:
    metadata = store.get_latest_by_id(artifact_id)
    if not metadata:
        return f"Artifact not found: {artifact_id}"

    changes = ensure_list(change_requests)
    metadata["change_requests"] = changes
    record_status_change(metadata, STATUS_DRAFT, note="changes requested")
    store.update_metadata(metadata)

    lines = [
        f"Changes recorded for {artifact_id} (v{metadata.get('version'):02d}).",
        "",
        "Change requests:",
    ]
    if changes:
        lines.extend([f"- {item}" for item in changes])
    else:
        lines.append("- None provided")
    return "\n".join(lines)


def approve(store, artifact_id: str, reviewer: str | None = None, notes: str | None = None) -> str:
    metadata = store.get_latest_by_id(artifact_id)
    if not metadata:
        return f"Artifact not found: {artifact_id}"

    if reviewer:
        metadata["reviewer"] = reviewer
    metadata["review_notes"] = normalize_text(notes, "")
    metadata["approved_at"] = utc_now()
    metadata["locked"] = True

    record_status_change(metadata, STATUS_APPROVED, note="approved")
    store.update_metadata(metadata)

    return (
        f"Approved {artifact_id} v{metadata.get('version'):02d} by {metadata.get('reviewer') or 'reviewer'}"
    )


def revise(
    store,
    artifact_id: str,
    new_content: str,
    change_requests,
    author: str | None = None,
) -> dict | None:
    previous = store.get_latest_by_id(artifact_id)
    if not previous:
        return None

    new_version = int(previous.get("version", 0)) + 1
    new_meta = build_metadata(
        project_slug=previous.get("project_slug"),
        phase=previous.get("phase"),
        wp_id=previous.get("wp_id"),
        title=previous.get("title"),
        author=author or previous.get("author", ""),
        reviewer=previous.get("reviewer", ""),
        upstream_refs=previous.get("upstream_refs", []),
        artifact_id=previous.get("artifact_id"),
        version=new_version,
        status=STATUS_DRAFT,
        supersedes={"artifact_id": previous.get("artifact_id"), "version": previous.get("version")},
        change_requests=ensure_list(change_requests),
    )

    doc_control = render_document_control(new_meta, new_meta.get("upstream_refs", []))
    updated_content = replace_document_control(new_content, doc_control)
    store.save_artifact(new_meta, updated_content)

    record_status_change(previous, STATUS_SUPERSEDED, note=f"superseded by v{new_version:02d}")
    previous["superseded_by"] = {
        "artifact_id": new_meta.get("artifact_id"),
        "version": new_version,
    }
    store.update_metadata(previous)

    log.info(f"Revised artifact {artifact_id} to v{new_version:02d}")
    return new_meta
