# ISO 26262 Concept Work Products Plugin

Main work product: Functional Safety Concept (WP-FSC).
Additional artifact: HARA (WP-HARA) via local HARA plugin integration.

## Tools

### Generate HARA artifact
```
generate hara artifact {"item_name": "Brake System", "author": "A. Smith"}
```

### Generate Functional Safety Concept
```
generate fsc {"item_name": "Brake System", "author": "A. Smith"}
```

### Review Flow (HARA)
```
request review hara {"artifact_id": "wp_hara-...", "reviewer": "B. Jones"}
request changes hara {"artifact_id": "wp_hara-...", "change_requests": ["Refine scenarios"]}
revise hara {"artifact_id": "wp_hara-...", "change_requests": ["Refine scenarios"]}
approve hara {"artifact_id": "wp_hara-...", "reviewer": "B. Jones"}
```

### Review Flow (FSC)
```
request review fsc {"artifact_id": "wp_fsc-...", "reviewer": "B. Jones"}
request changes fsc {"artifact_id": "wp_fsc-...", "change_requests": ["Clarify safety goals"]}
revise fsc {"artifact_id": "wp_fsc-...", "change_requests": ["Clarify safety goals"]}
approve fsc {"artifact_id": "wp_fsc-...", "reviewer": "B. Jones"}
```

## Output Location

Artifacts are stored under:
`work_products/<project_slug>/concept/`
