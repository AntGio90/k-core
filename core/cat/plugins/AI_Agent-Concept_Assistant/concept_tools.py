import importlib
import importlib.util
import sys
from pathlib import Path

from cat.log import log
from cat.mad_hatter.decorators import tool

from cat.plugins.iso26262_core import artifact_store, config, review_workflow, template_renderer, traceability, utils


PHASE = "concept"
WP_ID_MAIN = "WP-FSC"
TITLE_MAIN = "Functional Safety Concept"
WP_ID_HARA = "WP-HARA"
TITLE_HARA = "Hazard Analysis and Risk Assessment"

REQUIRED_FIELDS = ["item_name", "author"]

UPSTREAM_FSC = [
    {"phase": "management", "wp_id": "WP-SAFETYPLAN", "status": artifact_store.STATUS_APPROVED},
    {"phase": "concept", "wp_id": WP_ID_HARA, "status": artifact_store.STATUS_APPROVED},
]

REVIEW_CHECKLIST_FSC = [
    "HARA is referenced and approved",
    "Safety goals are captured",
    "Functional safety requirements are defined",
    "Interfaces and dependencies are documented",
    "Assumptions and open questions are listed",
]

REVIEW_CHECKLIST_HARA = [
    "Item context is documented",
    "Hazard list and classifications are present",
    "ASIL determinations are recorded",
    "Safety goals are derived or referenced",
]


def _get_value(data, cat, key, default=""):
    value = utils.coalesce(data.get(key), cat.working_memory.get(key))
    if value is None:
        return default
    if cat and value:
        cat.working_memory[key] = value
    return value


def _load_hara_module():
    module_name = "cat.plugins.AI_Agent-HARA_Assistant.Hara_Assistant_tool"
    try:
        return importlib.import_module(module_name)
    except Exception as exc:
        log.warning(f"HARA import fallback: {exc}")

    plugin_dir = Path(__file__).resolve().parents[1] / "AI_Agent-HARA_Assistant"
    module_path = plugin_dir / "Hara_Assistant_tool.py"
    if not module_path.exists():
        return None

    spec = importlib.util.spec_from_file_location(
        module_name,
        module_path,
        submodule_search_locations=[str(plugin_dir)],
    )
    if not spec or not spec.loader:
        return None

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _build_revision_prompt(change_requests, content, title):
    requests = "\n".join(f"- {item}" for item in change_requests) if change_requests else "- No change requests"
    return (
        f"You are a functional safety engineer. Update the {title} markdown to apply the change requests. "
        "Preserve structure and headings. Do not quote ISO text.\n\n"
        f"Change requests:\n{requests}\n\n"
        f"Current document:\n{content}\n"
    )


@tool(return_direct=True, examples=["generate hara artifact"])
def generate_hara_artifact(tool_input, cat):
    """Generate a HARA artifact by invoking the local HARA plugin. Input: JSON with item_name, author, and optional hara_tool_input."""
    data = utils.parse_tool_input(tool_input)
    project_slug = config.get_project_slug(cat, data)

    item_name = _get_value(data, cat, "item_name")
    author = _get_value(data, cat, "author")
    if not item_name or not author:
        return template_renderer.render_missing_inputs(["item_name", "author"])

    hara_module = _load_hara_module()
    if not hara_module:
        return "HARA plugin not found. Ensure AI_Agent-HARA_Assistant is installed."

    if "hara_table" not in cat.working_memory:
        hara_tool_input = data.get("hara_tool_input", "")
        result = hara_module.generate_hara_table(hara_tool_input, cat)
        if "hara_table" not in cat.working_memory:
            return result

    hara_table = cat.working_memory.get("hara_table", "")
    safety_goals = cat.working_memory.get("safety_goals", "")

    store = artifact_store.ArtifactStore()
    upstream_refs = []

    metadata = artifact_store.build_metadata(
        project_slug=project_slug,
        phase=PHASE,
        wp_id=WP_ID_HARA,
        title=TITLE_HARA,
        author=author,
        reviewer=utils.normalize_text(data.get("reviewer"), ""),
        upstream_refs=upstream_refs,
    )

    template_path = Path(__file__).resolve().parent / "templates" / "hara.md"
    body_template = template_renderer.load_template(template_path)

    context = {
        "item_context": utils.normalize_text(data.get("item_context"), f"Item: {item_name}"),
        "hara_table": hara_table or "TBD",
        "safety_goals_summary": safety_goals or "TBD",
        "references": template_renderer.format_bullets(data.get("references")),
    }

    body = template_renderer.render_template(body_template, context)
    assumptions = utils.ensure_list(data.get("assumptions"))
    open_questions = utils.ensure_list(data.get("open_questions"))
    trace_section = traceability.build_traceability_section(upstream_refs)

    content = template_renderer.render_document(
        metadata,
        body,
        assumptions,
        open_questions,
        trace_section,
        REVIEW_CHECKLIST_HARA,
    )

    md_path, _ = store.save_artifact(metadata, content)

    return (
        f"DRAFT created: {TITLE_HARA}\n"
        f"Artifact ID: {metadata['artifact_id']}\n"
        f"Version: v{metadata['version']:02d}\n"
        f"Status: {metadata['status']}\n"
        f"Path: {md_path}"
    )


@tool(return_direct=True, examples=["generate fsc"])
def generate_fsc(tool_input, cat):
    """Generate a Functional Safety Concept draft. Input: JSON with item_name, author, and optional sections."""
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
    upstream, missing_upstream = store.resolve_upstream(project_slug, UPSTREAM_FSC)
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
        wp_id=WP_ID_MAIN,
        title=TITLE_MAIN,
        author=fields["author"],
        reviewer=utils.normalize_text(data.get("reviewer"), ""),
        upstream_refs=upstream_refs,
    )

    template_path = Path(__file__).resolve().parent / "templates" / "fsc.md"
    body_template = template_renderer.load_template(template_path)

    hara_ref = "TBD"
    for ref in upstream_refs:
        if ref.get("wp_id") == WP_ID_HARA:
            hara_ref = f"- HARA artifact: {ref.get('artifact_id')} (v{ref.get('version'):02d}, {ref.get('status')})"
            break
    if manual_upstream_summary:
        hara_ref = manual_upstream_summary

    context = {
        "item_overview": utils.normalize_text(data.get("item_overview"), f"Item: {fields['item_name']}"),
        "hara_summary": hara_ref,
        "safety_goals": template_renderer.format_bullets(data.get("safety_goals")),
        "functional_safety_concept": template_renderer.format_bullets(data.get("functional_safety_concept")),
        "functional_safety_requirements": template_renderer.format_bullets(data.get("functional_safety_requirements")),
        "interfaces_and_dependencies": template_renderer.format_bullets(data.get("interfaces_and_dependencies")),
        "verification_strategy": template_renderer.format_bullets(data.get("verification_strategy")),
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
        REVIEW_CHECKLIST_FSC,
    )

    md_path, _ = store.save_artifact(metadata, content)

    return (
        f"DRAFT created: {TITLE_MAIN}\n"
        f"Artifact ID: {metadata['artifact_id']}\n"
        f"Version: v{metadata['version']:02d}\n"
        f"Status: {metadata['status']}\n"
        f"Path: {md_path}"
    )


@tool(return_direct=True, examples=["request review hara {\"artifact_id\": \"wp_hara-...\"}"])
def request_review_hara(tool_input, cat):
    """Request review for a HARA artifact. Input: {"artifact_id": "...", "reviewer": "..."}."""
    data = utils.parse_tool_input(tool_input)
    artifact_id = data.get("artifact_id") or data.get("text")
    if not artifact_id:
        return template_renderer.render_missing_inputs(["artifact_id"])
    reviewer = data.get("reviewer")
    store = artifact_store.ArtifactStore()
    return review_workflow.request_review(store, artifact_id, reviewer=reviewer, checklist=REVIEW_CHECKLIST_HARA)


@tool(return_direct=True, examples=["request changes hara {\"artifact_id\": \"wp_hara-...\", \"change_requests\": [""..."""]}"])
def request_changes_hara(tool_input, cat):
    """Record change requests for a HARA artifact. Input: {"artifact_id": "...", "change_requests": [...]}"""
    data = utils.parse_tool_input(tool_input)
    artifact_id = data.get("artifact_id") or data.get("text")
    if not artifact_id:
        return template_renderer.render_missing_inputs(["artifact_id", "change_requests"])
    change_requests = data.get("change_requests")
    store = artifact_store.ArtifactStore()
    return review_workflow.request_changes(store, artifact_id, change_requests)


@tool(return_direct=True, examples=["revise hara {\"artifact_id\": \"wp_hara-...\", \"change_requests\": [""..."""]}"])
def revise_hara(tool_input, cat):
    """Revise a HARA artifact. Input: {"artifact_id": "...", "change_requests": [...], "revised_document": "..."}."""
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
            prompt = _build_revision_prompt(change_requests, current_content, TITLE_HARA)
            try:
                new_content = cat.llm(prompt).strip()
            except Exception as exc:
                log.warning(f"HARA revision LLM failed: {exc}")
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


@tool(return_direct=True, examples=["approve hara {\"artifact_id\": \"wp_hara-...\", \"reviewer\": ""name""}"])
def approve_hara(tool_input, cat):
    """Approve a HARA artifact. Input: {"artifact_id": "...", "reviewer": "...", "notes": "..."}."""
    data = utils.parse_tool_input(tool_input)
    artifact_id = data.get("artifact_id") or data.get("text")
    if not artifact_id:
        return template_renderer.render_missing_inputs(["artifact_id", "reviewer"])
    reviewer = data.get("reviewer")
    notes = data.get("notes")
    store = artifact_store.ArtifactStore()
    return review_workflow.approve(store, artifact_id, reviewer=reviewer, notes=notes)


@tool(return_direct=True, examples=["request review fsc {\"artifact_id\": \"wp_fsc-...\"}"])
def request_review_fsc(tool_input, cat):
    """Request review for a Functional Safety Concept. Input: {"artifact_id": "...", "reviewer": "..."}."""
    data = utils.parse_tool_input(tool_input)
    artifact_id = data.get("artifact_id") or data.get("text")
    if not artifact_id:
        return template_renderer.render_missing_inputs(["artifact_id"])
    reviewer = data.get("reviewer")
    store = artifact_store.ArtifactStore()
    return review_workflow.request_review(store, artifact_id, reviewer=reviewer, checklist=REVIEW_CHECKLIST_FSC)


@tool(return_direct=True, examples=["request changes fsc {\"artifact_id\": \"wp_fsc-...\", \"change_requests\": [""..."""]}"])
def request_changes_fsc(tool_input, cat):
    """Record change requests for a Functional Safety Concept. Input: {"artifact_id": "...", "change_requests": [...]}"""
    data = utils.parse_tool_input(tool_input)
    artifact_id = data.get("artifact_id") or data.get("text")
    if not artifact_id:
        return template_renderer.render_missing_inputs(["artifact_id", "change_requests"])
    change_requests = data.get("change_requests")
    store = artifact_store.ArtifactStore()
    return review_workflow.request_changes(store, artifact_id, change_requests)


@tool(return_direct=True, examples=["revise fsc {\"artifact_id\": \"wp_fsc-...\", \"change_requests\": [""..."""]}"])
def revise_fsc(tool_input, cat):
    """Revise a Functional Safety Concept. Input: {"artifact_id": "...", "change_requests": [...], "revised_document": "..."}."""
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
            prompt = _build_revision_prompt(change_requests, current_content, TITLE_MAIN)
            try:
                new_content = cat.llm(prompt).strip()
            except Exception as exc:
                log.warning(f"FSC revision LLM failed: {exc}")
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


@tool(return_direct=True, examples=["approve fsc {\"artifact_id\": \"wp_fsc-...\", \"reviewer\": ""name""}"])
def approve_fsc(tool_input, cat):
    """Approve a Functional Safety Concept. Input: {"artifact_id": "...", "reviewer": "...", "notes": "..."}."""
    data = utils.parse_tool_input(tool_input)
    artifact_id = data.get("artifact_id") or data.get("text")
    if not artifact_id:
        return template_renderer.render_missing_inputs(["artifact_id", "reviewer"])
    reviewer = data.get("reviewer")
    notes = data.get("notes")
    store = artifact_store.ArtifactStore()
    return review_workflow.approve(store, artifact_id, reviewer=reviewer, notes=notes)
