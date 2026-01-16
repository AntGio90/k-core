import json
import os
from pathlib import Path

from cat.log import log

from .id_generation import slugify


DEFAULT_WORKSPACE_ROOT = "work_products"
DEFAULT_PROJECT_SLUG = "default_project"
ENV_WORKSPACE_ROOT = "ISO26262_WORKSPACE_ROOT"
ENV_PROJECT_SLUG = "ISO26262_PROJECT_SLUG"


def _find_repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        plugins_path = parent / "core" / "cat" / "plugins"
        if plugins_path.exists():
            return parent
    return Path.cwd()


def _resolve_path(path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return _find_repo_root() / path


def plugin_dir() -> Path:
    return Path(__file__).resolve().parent


def settings_path() -> Path:
    return plugin_dir() / "settings.json"


def load_settings() -> dict:
    path = settings_path()
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        return {}
    except Exception as exc:
        log.warning(f"iso26262_core settings load failed: {exc}")
        return {}


def save_settings(settings: dict) -> bool:
    path = settings_path()
    try:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(settings, handle, indent=4)
        return True
    except Exception as exc:
        log.warning(f"iso26262_core settings save failed: {exc}")
        return False


def get_workspace_root() -> Path:
    env_root = os.getenv(ENV_WORKSPACE_ROOT)
    if env_root:
        return _resolve_path(env_root)

    settings = load_settings()
    settings_root = settings.get("workspace_root")
    if settings_root:
        return _resolve_path(settings_root)

    return _resolve_path(DEFAULT_WORKSPACE_ROOT)


def normalize_project_slug(value: str) -> str:
    if not value:
        return DEFAULT_PROJECT_SLUG
    return slugify(value)


def get_project_slug(cat=None, tool_input=None) -> str:
    tool_input = tool_input or {}
    if isinstance(tool_input, dict):
        provided = tool_input.get("project_slug") or tool_input.get("project")
        if provided:
            slug = normalize_project_slug(provided)
            if cat:
                cat.working_memory["iso26262_project_slug"] = slug
            return slug

    if cat:
        existing = cat.working_memory.get("iso26262_project_slug")
        if existing:
            return normalize_project_slug(existing)

    env_slug = os.getenv(ENV_PROJECT_SLUG)
    if env_slug:
        return normalize_project_slug(env_slug)

    settings = load_settings()
    settings_slug = settings.get("default_project_slug")
    if settings_slug:
        return normalize_project_slug(settings_slug)

    return DEFAULT_PROJECT_SLUG


def set_project_slug(cat, project_slug: str, persist: bool = False) -> str:
    slug = normalize_project_slug(project_slug)
    if cat:
        cat.working_memory["iso26262_project_slug"] = slug
    if persist:
        settings = load_settings()
        settings["default_project_slug"] = slug
        save_settings(settings)
    return slug
