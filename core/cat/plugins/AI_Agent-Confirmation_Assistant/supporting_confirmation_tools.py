from pathlib import Path

from cat.log import log
from cat.mad_hatter.decorators import tool

from cat.plugins.iso26262_core import artifact_store, config, review_workflow, template_renderer, traceability, utils


PHASE = "supporting_confirmation"
WP_ID = "WP-SAFETYCASE"
TITLE = "Safety Case"

REQUIRED_FIELDS = ["item_name", "author"]

UPSTREAM_CASE = [
    {"phase": "management", "wp_id": "WP-SAFETYPLAN", "status": artifact_store.STATUS_APPROVED},
    {"phase": "concept", "wp_id": "WP-FSC", "status": artifact_store.STATUS_APPROVED},
    {"phase": "system", "wp_id": "WP-TSC", "status": artifact_store.STATUS_APPROVED},
    {"phase": "hardware", "wp_id": "WP-HW-SRS", "status": artifact_store.STATUS_APPROVED},
    {"phase": "software", "wp_id": "WP-SW-SRS", "status": artifact_store.STATUS_APPROVED},
    {"phase": "production_operation", "wp_id": "WP-SAFETYMANUAL", "status": artifact_store.STATUS_APPROVED},
]

REVIEW_CHECKLIST = [
    "Safety claims are stated and traceable",
    "Argument strategy is coherent",
    "Evidence summary references approved artifacts",
    "Residual risks and open issues are documented",
    "Compliance summary is included",
]


def _get_value(data, cat, key, default=""):
    value = utils.coalesce(data.get(key), cat.working_memory.get(key))
    if value is None:
        return default
    if cat and value:
        cat.working_memory[key] = value
    return value


def _build_revision_prompt(change_requests, content):
    requests = "\n".join(f"- {item}" for item in change_requests) if change_requests else "- No change requests"
    return (
        "You are a functional safety engineer. Update the Safety Case markdown to apply the change requests. "
        "Preserve structure and headings. Do not quote ISO text.\n\n"
        f"Change requests:\n{requests}\n\n"
        f"Current document:\n{content}\n"
    )


@tool(return_direct=True, examples=["generate safety case"])
def generate_safety_case(tool_input, cat):
    """Generate a Safety Case draft. Input: JSON with item_name, author, and optional sections."""
    data = utils.parse_tool_input(tool_input)
    project_slug = config.get_project_slug(cat, data)

    missing = []
    fields = {}
    for field in REQUIRED_FIELDS:
        value = _get_value(data, cat, field)
        fields[field] = value
        if not value:
            missing.append(field)
    if missing:
        return template_renderer.render_missing_inputs(missing)

    store = artifact_store.ArtifactStore()
    upstream, missing_upstream = store.resolve_upstream(project_slug, UPSTREAM_CASE)
    allow_missing_upstream = bool(data.get("allow_missing_upstream"))
    manual_upstream_summary = data.get("manual_upstream_summary")
    if missing_upstream and not allow_missing_upstream:
        return template_renderer.render_missing_upstream(missing_upstream)
    if missing_upstream:
        upstream = []

    upstream_refs = traceability.make_upstream_refs(upstream)

    metadata = artifact_store.build_metadata(
        project_slug=project_slug,
        phase=PHASE,
        wp_id=WP_ID,
        title=TITLE,
        author=fields["author"],
        reviewer=utils.normalize_text(data.get("reviewer"), ""),
        upstream_refs=upstream_refs,
    )

    template_path = Path(__file__).resolve().parent / "templates" / "safety_case.md"
    body_template = template_renderer.load_template(template_path)

    context = {
        "scope_objectives": utils.normalize_text(data.get("scope_objectives"), f"Item: {fields['item_name']}"),
        "safety_claims": template_renderer.format_bullets(data.get("safety_claims")),
        "argument_strategy": template_renderer.format_bullets(data.get("argument_strategy")),
        "evidence_summary": template_renderer.format_bullets(data.get("evidence_summary")),
        "compliance_summary": template_renderer.format_bullets(data.get("compliance_summary")),
        "residual_risks": template_renderer.format_bullets(data.get("residual_risks")),
        "references": template_renderer.format_bullets(data.get("references")),
    }

    body = template_renderer.render_template(body_template, context)
    assumptions = utils.ensure_list(data.get("assumptions"))
    if missing_upstream:
        assumptions.append("Upstream artifacts were missing; placeholders were used.")
    if manual_upstream_summary:
        assumptions.append(f"Manual upstream summary provided: {manual_upstream_summary}")
    open_questions = utils.ensure_list(data.get("open_questions"))
    trace_section = traceability.build_traceability_section(upstream_refs)

    content = template_renderer.render_document(
        metadata,
        body,
        assumptions,
        open_questions,
        trace_section,
        REVIEW_CHECKLIST,
    )

    md_path, _ = store.save_artifact(metadata, content)

    return (
        f"DRAFT created: {TITLE}\n"
        f"Artifact ID: {metadata['artifact_id']}\n"
        f"Version: v{metadata['version']:02d}\n"
        f"Status: {metadata['status']}\n"
        f"Path: {md_path}"
    )


@tool(return_direct=True, examples=["request review safety case {\"artifact_id\": \"wp_safetycase-...\"}"])
def request_review_safety_case(tool_input, cat):
    """Request review for a Safety Case. Input: {"artifact_id": "...", "reviewer": "..."}."""
    data = utils.parse_tool_input(tool_input)
    artifact_id = data.get("artifact_id") or data.get("text")
    if not artifact_id:
        return template_renderer.render_missing_inputs(["artifact_id"])
    reviewer = data.get("reviewer")
    store = artifact_store.ArtifactStore()
    return review_workflow.request_review(store, artifact_id, reviewer=reviewer, checklist=REVIEW_CHECKLIST)


@tool(return_direct=True, examples=["request changes safety case {\"artifact_id\": \"wp_safetycase-...\", \"change_requests\": [""..."""]}"])
def request_changes_safety_case(tool_input, cat):
    """Record change requests for a Safety Case. Input: {"artifact_id": "...", "change_requests": [...]}"""
    data = utils.parse_tool_input(tool_input)
    artifact_id = data.get("artifact_id") or data.get("text")
    if not artifact_id:
        return template_renderer.render_missing_inputs(["artifact_id", "change_requests"])
    change_requests = data.get("change_requests")
    store = artifact_store.ArtifactStore()
    return review_workflow.request_changes(store, artifact_id, change_requests)


@tool(return_direct=True, examples=["revise safety case {\"artifact_id\": \"wp_safetycase-...\", \"change_requests\": [""..."""]}"])
def revise_safety_case(tool_input, cat):
    """Revise a Safety Case. Input: {"artifact_id": "...", "change_requests": [...], "revised_document": "..."}."""
    data = utils.parse_tool_input(tool_input)
    artifact_id = data.get("artifact_id") or data.get("text")
    if not artifact_id:
        return template_renderer.render_missing_inputs(["artifact_id"])

    store = artifact_store.ArtifactStore()
    previous = store.get_latest_by_id(artifact_id)
    if not previous:
        return f"Artifact not found: {artifact_id}"

    change_requests = utils.ensure_list(data.get("change_requests"))
    revised_document = data.get("revised_document")

    if revised_document:
        new_content = revised_document
    else:
        current_content = store.read_artifact_content(previous)
        if change_requests:
            prompt = _build_revision_prompt(change_requests, current_content)
            try:
                new_content = cat.llm(prompt).strip()
            except Exception as exc:
                log.warning(f"Safety Case revision LLM failed: {exc}")
                new_content = current_content
        else:
            new_content = current_content

    new_meta = review_workflow.revise(
        store,
        artifact_id,
        new_content,
        change_requests,
        author=previous.get("author"),
    )
    if not new_meta:
        return f"Revision failed for {artifact_id}"

    return (
        f"Revision created: {artifact_id} v{new_meta['version']:02d}\n"
        f"Status: {new_meta['status']}"
    )


@tool(return_direct=True, examples=["approve safety case {\"artifact_id\": \"wp_safetycase-...\", \"reviewer\": ""name""}"])
def approve_safety_case(tool_input, cat):
    """Approve a Safety Case. Input: {"artifact_id": "...", "reviewer": "...", "notes": "..."}."""
    data = utils.parse_tool_input(tool_input)
    artifact_id = data.get("artifact_id") or data.get("text")
    if not artifact_id:
        return template_renderer.render_missing_inputs(["artifact_id", "reviewer"])
    reviewer = data.get("reviewer")
    notes = data.get("notes")
    store = artifact_store.ArtifactStore()
    return review_workflow.approve(store, artifact_id, reviewer=reviewer, notes=notes)
