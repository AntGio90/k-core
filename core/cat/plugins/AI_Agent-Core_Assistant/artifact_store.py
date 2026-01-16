import json
from datetime import datetime, timezone
from pathlib import Path

from cat.log import log

from . import config
from . import id_generation


STATUS_DRAFT = "DRAFT"
STATUS_IN_REVIEW = "IN_REVIEW"
STATUS_APPROVED = "APPROVED"
STATUS_SUPERSEDED = "SUPERSEDED"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class ArtifactStore:
    def __init__(self, root: Path | None = None):
        self.root = Path(root) if root else config.get_workspace_root()
        self.root.mkdir(parents=True, exist_ok=True)

    def project_root(self, project_slug: str) -> Path:
        return self.root / config.normalize_project_slug(project_slug)

    def artifact_dir(self, project_slug: str, phase: str, wp_id: str) -> Path:
        return self.project_root(project_slug) / phase / wp_id

    def build_paths(self, project_slug: str, phase: str, wp_id: str, artifact_id: str, version: int):
        version_tag = id_generation.format_version(version)
        base_dir = self.artifact_dir(project_slug, phase, wp_id)
        base_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{artifact_id}_v{version_tag}"
        return base_dir / f"{filename}.md", base_dir / f"{filename}.json"

    def save_artifact(self, metadata: dict, content: str):
        md_path, json_path = self.build_paths(
            metadata["project_slug"],
            metadata["phase"],
            metadata["wp_id"],
            metadata["artifact_id"],
            metadata["version"],
        )
        metadata["artifact_path"] = str(md_path)
        metadata["metadata_path"] = str(json_path)

        with open(md_path, "w", encoding="utf-8") as handle:
            handle.write(content)
        with open(json_path, "w", encoding="utf-8") as handle:
            json.dump(metadata, handle, indent=2)
        return md_path, json_path

    def load_metadata(self, path: Path) -> dict | None:
        try:
            with open(path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except Exception as exc:
            log.warning(f"Failed to load metadata {path}: {exc}")
            return None

    def list_metadata(self, project_slug: str | None = None, phase: str | None = None, wp_id: str | None = None):
        base = self.root
        if project_slug:
            base = self.project_root(project_slug)
        if phase:
            base = base / phase
        if wp_id:
            base = base / wp_id
        if not base.exists():
            return []
        results = []
        for path in base.glob("**/*_v*.json"):
            meta = self.load_metadata(path)
            if meta:
                results.append(meta)
        return results

    def get_latest_by_id(self, artifact_id: str, project_slug: str | None = None):
        metas = self.list_metadata(project_slug=project_slug)
        matches = [m for m in metas if m.get("artifact_id") == artifact_id]
        if not matches:
            return None
        return max(matches, key=lambda m: m.get("version", 0))

    def get_latest_by_wp(self, project_slug: str, phase: str, wp_id: str, status: str | None = None):
        metas = self.list_metadata(project_slug=project_slug, phase=phase, wp_id=wp_id)
        if status:
            metas = [m for m in metas if m.get("status") == status]
        if not metas:
            return None
        return max(metas, key=lambda m: m.get("version", 0))

    def resolve_upstream(self, project_slug: str, requirements: list[dict]):
        upstream = []
        missing = []
        for req in requirements:
            phase = req.get("phase")
            wp_id = req.get("wp_id")
            status = req.get("status", STATUS_APPROVED)
            meta = self.get_latest_by_wp(project_slug, phase, wp_id, status=status)
            if meta:
                upstream.append(meta)
            else:
                missing.append(req)
        return upstream, missing

    def update_metadata(self, metadata: dict):
        path = metadata.get("metadata_path")
        if not path:
            md_path, json_path = self.build_paths(
                metadata["project_slug"],
                metadata["phase"],
                metadata["wp_id"],
                metadata["artifact_id"],
                metadata["version"],
            )
            path = json_path
            metadata["metadata_path"] = str(json_path)
            metadata["artifact_path"] = str(md_path)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(metadata, handle, indent=2)
        return Path(path)

    def read_artifact_content(self, metadata: dict) -> str:
        md_path = metadata.get("artifact_path")
        if not md_path:
            md_path, _ = self.build_paths(
                metadata["project_slug"],
                metadata["phase"],
                metadata["wp_id"],
                metadata["artifact_id"],
                metadata["version"],
            )
            md_path = str(md_path)
        try:
            with open(md_path, "r", encoding="utf-8") as handle:
                return handle.read()
        except Exception as exc:
            log.warning(f"Failed to read artifact {md_path}: {exc}")
            return ""


def build_metadata(
    project_slug: str,
    phase: str,
    wp_id: str,
    title: str,
    author: str,
    reviewer: str | None = None,
    upstream_refs: list | None = None,
    artifact_id: str | None = None,
    version: int = 1,
    status: str = STATUS_DRAFT,
    supersedes: dict | None = None,
    change_requests: list | None = None,
):
    now = utc_now()
    metadata = {
        "artifact_id": artifact_id or id_generation.new_artifact_id(wp_id),
        "wp_id": wp_id,
        "title": title,
        "phase": phase,
        "project_slug": config.normalize_project_slug(project_slug),
        "version": version,
        "status": status,
        "created_at": now,
        "updated_at": now,
        "author": author,
        "reviewer": reviewer or "",
        "review_notes": "",
        "approved_at": "",
        "locked": False,
        "supersedes": supersedes or {},
        "change_requests": change_requests or [],
        "upstream_refs": upstream_refs or [],
        "status_history": [
            {"status": status, "date": now, "note": "created"}
        ],
    }
    return metadata


def record_status_change(metadata: dict, status: str, note: str = "") -> dict:
    metadata["status"] = status
    metadata["updated_at"] = utc_now()
    if "status_history" not in metadata:
        metadata["status_history"] = []
    metadata["status_history"].append(
        {"status": status, "date": metadata["updated_at"], "note": note}
    )
    return metadata
