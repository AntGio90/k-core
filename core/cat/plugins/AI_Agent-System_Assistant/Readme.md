# ISO 26262 System Work Products Plugin

Main work product: Technical Safety Concept (WP-TSC).

## Tools

### Generate Technical Safety Concept
```
generate tsc {"item_name": "Brake System", "author": "A. Smith"}
```

### Review Flow
```
request review tsc {"artifact_id": "wp_tsc-...", "reviewer": "B. Jones"}
request changes tsc {"artifact_id": "wp_tsc-...", "change_requests": ["Clarify allocations"]}
revise tsc {"artifact_id": "wp_tsc-...", "change_requests": ["Clarify allocations"]}
approve tsc {"artifact_id": "wp_tsc-...", "reviewer": "B. Jones"}
```

## Output Location

Artifacts are stored under:
`work_products/<project_slug>/system/WP-TSC/`
