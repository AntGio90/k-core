from cat.log import log

from . import config


def setup_workspace():
    root = config.get_workspace_root()
    try:
        root.mkdir(parents=True, exist_ok=True)
        readme_path = root / "README.txt"
        if not readme_path.exists():
            with open(readme_path, "w", encoding="utf-8") as handle:
                handle.write(
                    """ISO 26262 Work Products Workspace

Artifacts are stored as:
work_products/<project_slug>/<phase>/<wp_id>/<artifact_id>_vNN.md

Each markdown has a JSON sidecar with metadata.
"""
                )
        log.info(f"iso26262_core workspace ready at {root}")
    except Exception as exc:
        log.warning(f"iso26262_core workspace setup failed: {exc}")


try:
    setup_workspace()
except Exception as exc:
    log.warning(f"iso26262_core workspace setup error: {exc}")
