# ISO 26262 Production and Operation Work Products Plugin

Main work product: Safety Manual (WP-SAFETYMANUAL).

## Tools

### Generate Safety Manual
```
generate safety manual {"item_name": "Brake ECU", "author": "A. Smith"}
```

### Review Flow
```
request review safety manual {"artifact_id": "wp_safetymanual-...", "reviewer": "B. Jones"}
request changes safety manual {"artifact_id": "wp_safetymanual-...", "change_requests": ["Clarify warnings"]}
revise safety manual {"artifact_id": "wp_safetymanual-...", "change_requests": ["Clarify warnings"]}
approve safety manual {"artifact_id": "wp_safetymanual-...", "reviewer": "B. Jones"}
```

## Output Location

Artifacts are stored under:
`work_products/<project_slug>/production_operation/WP-SAFETYMANUAL/`
