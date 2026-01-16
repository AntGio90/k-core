# ISO 26262 Core Plugin

Shared services for ISO 26262 work products:
- Artifact persistence and versioning
- Traceability helpers
- HITL review workflow primitives
- Document control header rendering

## Configuration

Defaults live in `settings.json`:

```json
{
  "workspace_root": "work_products",
  "default_project_slug": "default_project"
}
```

Optional environment overrides:
- `ISO26262_WORKSPACE_ROOT`
- `ISO26262_PROJECT_SLUG`

## Workspace Layout

```
work_products/<project_slug>/<phase>/<wp_id>/<artifact_id>_vNN.md
work_products/<project_slug>/<phase>/<wp_id>/<artifact_id>_vNN.json
```

## Core Tools

### Set active project
```
set iso26262 project: demo_platform
```

### List artifacts
```
list iso26262 artifacts
list iso26262 artifacts {"phase": "concept"}
```

### Show artifact metadata
```
show iso26262 artifact {"artifact_id": "wp_fsc-20260101010101-acde12"}
```

### Show traceability
```
show iso26262 traceability {"artifact_id": "wp_fsc-20260101010101-acde12"}
```

## Notes

- This plugin does not generate ISO 26262 content; it provides shared infrastructure used by phase plugins.
- All output is template-driven and editable.
