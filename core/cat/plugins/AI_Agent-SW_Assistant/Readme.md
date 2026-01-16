# ISO 26262 Software Work Products Plugin

Main work product: SW Safety Requirements Specification (WP-SW-SRS).

## Tools

### Generate SW SRS
```
generate sw srs {"item_name": "Brake ECU", "author": "A. Smith"}
```

### Review Flow
```
request review sw srs {"artifact_id": "wp_sw_srs-...", "reviewer": "B. Jones"}
request changes sw srs {"artifact_id": "wp_sw_srs-...", "change_requests": ["Clarify interfaces"]}
revise sw srs {"artifact_id": "wp_sw_srs-...", "change_requests": ["Clarify interfaces"]}
approve sw srs {"artifact_id": "wp_sw_srs-...", "reviewer": "B. Jones"}
```

## Output Location

Artifacts are stored under:
`work_products/<project_slug>/software/WP-SW-SRS/`
