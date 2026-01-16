# ISO 26262 Lifecycle Guide

This guide shows how to run the ISO 26262 work product lifecycle using the provided plugins.

## 1) Configure the project
```
set iso26262 project: demo_platform
```

## 2) Management phase
Generate and approve the Safety Plan:
```
generate safety plan {"item_name": "Brake System", "organization": "ACME", "author": "A. Smith", "safety_manager": "B. Jones"}
request review safety plan {"artifact_id": "wp_safetyplan-...", "reviewer": "B. Jones"}
approve safety plan {"artifact_id": "wp_safetyplan-...", "reviewer": "B. Jones"}
```

## 3) Concept phase
Generate HARA (via local HARA plugin), review, and approve:
```
generate hara artifact {"item_name": "Brake System", "author": "A. Smith"}
request review hara {"artifact_id": "wp_hara-...", "reviewer": "B. Jones"}
approve hara {"artifact_id": "wp_hara-...", "reviewer": "B. Jones"}
```

Generate and approve the Functional Safety Concept:
```
generate fsc {"item_name": "Brake System", "author": "A. Smith"}
request review fsc {"artifact_id": "wp_fsc-...", "reviewer": "B. Jones"}
approve fsc {"artifact_id": "wp_fsc-...", "reviewer": "B. Jones"}
```

## 4) System phase
Generate and approve the Technical Safety Concept:
```
generate tsc {"item_name": "Brake System", "author": "A. Smith"}
request review tsc {"artifact_id": "wp_tsc-...", "reviewer": "B. Jones"}
approve tsc {"artifact_id": "wp_tsc-...", "reviewer": "B. Jones"}
```

## 5) Hardware and Software phases
Generate and approve HW/SW Safety Requirements:
```
generate hw srs {"item_name": "Brake ECU", "author": "A. Smith"}
request review hw srs {"artifact_id": "wp_hw_srs-...", "reviewer": "B. Jones"}
approve hw srs {"artifact_id": "wp_hw_srs-...", "reviewer": "B. Jones"}

generate sw srs {"item_name": "Brake ECU", "author": "A. Smith"}
request review sw srs {"artifact_id": "wp_sw_srs-...", "reviewer": "B. Jones"}
approve sw srs {"artifact_id": "wp_sw_srs-...", "reviewer": "B. Jones"}
```

## 6) Production and operation phase
Generate and approve the Safety Manual:
```
generate safety manual {"item_name": "Brake ECU", "author": "A. Smith"}
request review safety manual {"artifact_id": "wp_safetymanual-...", "reviewer": "B. Jones"}
approve safety manual {"artifact_id": "wp_safetymanual-...", "reviewer": "B. Jones"}
```

## 7) Supporting and confirmation processes
Generate and approve the Safety Case:
```
generate safety case {"item_name": "Brake ECU", "author": "A. Smith"}
request review safety case {"artifact_id": "wp_safetycase-...", "reviewer": "B. Jones"}
approve safety case {"artifact_id": "wp_safetycase-...", "reviewer": "B. Jones"}
```

## 8) Traceability and inspection
List and inspect artifacts at any time:
```
list iso26262 artifacts
show iso26262 artifact {"artifact_id": "wp_fsc-..."}
show iso26262 traceability {"artifact_id": "wp_safetycase-..."}
```
