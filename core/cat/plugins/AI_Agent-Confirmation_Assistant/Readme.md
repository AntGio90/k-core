# ISO 26262 Supporting and Confirmation Work Products Plugin

Main work product: Safety Case (WP-SAFETYCASE).

## Tools

### Generate Safety Case
```
generate safety case {"item_name": "Brake ECU", "author": "A. Smith"}
```

### Review Flow
```
request review safety case {"artifact_id": "wp_safetycase-...", "reviewer": "B. Jones"}
request changes safety case {"artifact_id": "wp_safetycase-...", "change_requests": ["Add evidence summary"]}
revise safety case {"artifact_id": "wp_safetycase-...", "change_requests": ["Add evidence summary"]}
approve safety case {"artifact_id": "wp_safetycase-...", "reviewer": "B. Jones"}
```

## Output Location

Artifacts are stored under:
`work_products/<project_slug>/supporting_confirmation/WP-SAFETYCASE/`
