# ISO 26262 Management Work Products Plugin

Main work product: Safety Plan (WP-SAFETYPLAN).

## Tools

### Generate Safety Plan
```
generate safety plan {"item_name": "Brake System", "organization": "ACME", "author": "A. Smith", "safety_manager": "B. Jones"}
```

### Review Flow
```
request review safety plan {"artifact_id": "wp_safetyplan-...", "reviewer": "B. Jones"}
request changes safety plan {"artifact_id": "wp_safetyplan-...", "change_requests": ["Update schedule"]}
revise safety plan {"artifact_id": "wp_safetyplan-...", "change_requests": ["Update schedule"]}
approve safety plan {"artifact_id": "wp_safetyplan-...", "reviewer": "B. Jones"}
```

## Output Location

Artifacts are stored under:
`work_products/<project_slug>/management/WP-SAFETYPLAN/`
