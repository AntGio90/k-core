# ISO 26262 Hardware Work Products Plugin

Main work product: HW Safety Requirements Specification (WP-HW-SRS).

## Tools

### Generate HW SRS
```
generate hw srs {"item_name": "Brake ECU", "author": "A. Smith"}
```

### Review Flow
```
request review hw srs {"artifact_id": "wp_hw_srs-...", "reviewer": "B. Jones"}
request changes hw srs {"artifact_id": "wp_hw_srs-...", "change_requests": ["Add diagnostic coverage"]}
revise hw srs {"artifact_id": "wp_hw_srs-...", "change_requests": ["Add diagnostic coverage"]}
approve hw srs {"artifact_id": "wp_hw_srs-...", "reviewer": "B. Jones"}
```

## Output Location

Artifacts are stored under:
`work_products/<project_slug>/hardware/WP-HW-SRS/`
