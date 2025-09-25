# ISO 26262 FSC Generator (FSC_generator)

Plugin per supportare la derivazione del Functional Safety Concept (FSC) secondo ISO 26262: normalizzazione Item Definition, generazione ipotesi di malfunzionamento, HARA, sintesi Safety Goals, derivazione FSR, suggerimenti di allocazione, tracciabilità ed export degli artefatti (inclusi DOCX/PDF).

## Contenuti principali
- plugin.json — metadati del plugin
- iso26262_fsc.py — logica principale e strumenti (tools)
- settings.json — impostazioni del plugin (attualmente vuoto)
- requirements.txt — dipendenze Python del plugin

## Requisiti
- Python 3.10+
- Dipendenze minime:
  - pydantic>=2.0.0
  - typing-extensions>=4.0.0
  - json5>=0.9.14
- Per l’esportazione in DOCX/PDF (opzionali ma consigliate):
  - python-docx>=0.8.11 (DOCX)
  - reportlab>=3.6.12 (PDF)

Installazione (Windows):
- Installa le dipendenze del plugin con il tuo flusso standard (ad es. script del progetto) oppure con pip nella tua venv.

## Flusso di lavoro consigliato
1) Ingest e normalizzazione Item Definition
   - id_ingest_normalize (accetta JSON o testo libero)
2) Estrazione funzioni, interfacce e modalità
   - id_extract_functions_interfaces
3) Generazione ipotesi di malfunzionamento
   - malfunction_hypotheses_generate
4) HARA (derivazione o validazione dei parametri S/E/C, calcolo ASIL)
   - hara_derive_or_validate
5) Sintesi Safety Goals
   - safety_goals_synthesize
6) Derivazione Functional Safety Requirements (FSR) e coerenza
   - fsc_derive
7) Suggerimenti di allocazione logica (indipendenza, FFI)
   - allocation_hints_propose
8) Tracciabilità end-to-end (Item Definition → HE → SG → FSR)
   - traceability_build
9) Esportazione artefatti (Markdown/CSV/JSON)
   - fsc_export
10) Salvataggio su disco + conversione DOCX/PDF
   - fsc_save_exports

## Elenco strumenti (tools)

- id_ingest_normalize
  - Input: JSON (o testo) Item Definition
  - Output: Item Definition normalizzata in memoria di lavoro
- id_extract_functions_interfaces
  - Output: catene funzionali, interfacce (I/O, comunicazioni, power, HMI), modalità operative/degradate
- malfunction_hypotheses_generate
  - Output: lista ipotesi di malfunzionamento (omission, commission, out-of-range, stuck, timing/latency/sequence)
- hara_derive_or_validate
  - Input: hazardous events con S/E/C (o parametri grezzi)
  - Output: HARA con calcolo ASIL e persistenza in memoria
- safety_goals_synthesize
  - Output: Safety Goals con ASIL massimo per evento, safe states, FTTI, assunzioni e misure esterne
- fsc_derive
  - Output: FSR per ciascun Safety Goal (detection, reaction, HMI alerts, degraded operation) + validazione coerenza
- allocation_hints_propose
  - Output: suggerimenti allocazione (detection/reaction), indipendenza e freedom-from-interference
- traceability_build
  - Output: tabella tracciabilità (CSV o JSON) tra ID, HE, SG, FSR
- fsc_export
  - Output: artefatti in memoria:
    - fsc_document.md (documento completo FSC in Markdown)
    - compliance_checklist.md (checklist di conformità)
    - traceability_matrix.csv (matrice di tracciabilità)
    - fsc_data.json (dati di analisi)
- fsc_save_exports (nuovo)
  - Scopo: salva su disco gli artefatti da fsc_export e converte il documento FSC in DOCX e/o PDF
  - Parametri (stringa “chiave=valore” separati da virgole):
    - format=docx|pdf|both (default: both)
    - dir=<cartella_output> (default: cartella “exports” del plugin)
  - Comportamento:
    - Se gli artefatti non sono già presenti in memoria (iso26262_exports), il tool rigenera on-the-fly il documento FSC e la checklist a partire dai dati correnti (iso26262_data), se presenti
    - Salva sempre i file testuali (md/json/csv); genera DOCX e/o PDF se le dipendenze opzionali sono installate

Nota: esistono anche due hook opzionali in iso26262_fsc.py:
- before_cat_sends_message: aggiunge un banner di conformità quando il contenuto riguarda l’FSC
- agent_allowed_tools: limita gli strumenti disponibili al contesto ISO 26262 quando rilevato

## Esempi d’uso

- Workflow tipico:
  - id_ingest_normalize -> “{...JSON Item Definition...}”
  - id_extract_functions_interfaces
  - malfunction_hypotheses_generate
  - hara_derive_or_validate -> “mode=derive”
  - safety_goals_synthesize
  - fsc_derive
  - allocation_hints_propose
  - traceability_build -> “format=csv”
  - fsc_export

- Salvataggio su disco e conversione:
  - fsc_save_exports -> “format=both”
    - Salva nella cartella default: d:\Documents\k-core\core\cat\plugins\FSC_generator\exports\
    - Genera FSC_<timestamp>.docx e FSC_<timestamp>.pdf (se le dipendenze sono installate)
  - fsc_save_exports -> “format=docx,dir=D:\\Exports\\FSC”
    - Crea solo DOCX nella cartella specificata
  - fsc_save_exports -> “format=pdf”
    - Crea solo PDF nella cartella default del plugin

## File generati
- fsc_document.md — documento FSC completo (Markdown)
- compliance_checklist.md — checklist di conformità ISO 26262
- traceability_matrix.csv — matrice di tracciabilità end-to-end
- fsc_data.json — dati strutturati (analisi, SG, FSR, ecc.)
- FSC_<timestamp>.docx — documento DOCX generato da fsc_document.md
- FSC_<timestamp>.pdf — documento PDF generato da fsc_document.md

## Note e limitazioni
- La conversione Markdown→DOCX/PDF è semplificata:
  - Heading e bullet list supportati; tabelle e immagini non sono convertite in modo avanzato
  - Il PDF usa una resa testuale “plain” (reportlab) con wrapping semplice
- Verifica di avere installato le dipendenze opzionali per generare DOCX/PDF
- Per esportazioni ufficiali, considera una revisione manuale del documento generato


## Quick Start

This quick start shows a minimal end-to-end flow from Item Definition to exported artifacts.

1) Prepare a minimal Item Definition (example)

```json
{
  "item_name": "ADAS Perception",
  "functions": [
    { "id": "F1", "name": "Object Detection" }
  ],
  "interfaces": [
    { "id": "I1", "name": "Front Camera Input", "type": "I/O" }
  ],
  "modes": ["Nominal", "Degraded"]
}
```

2) Normalize and extract structures
- id_ingest_normalize -> paste the JSON above
- id_extract_functions_interfaces

3) Generate malfunction hypotheses
- malfunction_hypotheses_generate

4) HARA (derive ASIL from S/E/C)
- hara_derive_or_validate -> "mode=derive"

5) Synthesize Safety Goals
- safety_goals_synthesize

6) Derive FSRs and validate consistency
- fsc_derive

7) Build traceability
- traceability_build -> "format=csv"

8) Export artifacts (kept in working memory)
- fsc_export
  - Produces: fsc_document.md, compliance_checklist.md, traceability_matrix.csv, fsc_data.json

9) Save to disk and optionally convert to DOCX/PDF (if supported in your build)
- If a save/convert tool is available:
  - Default folder, DOCX+PDF: format=both
  - Custom folder, DOCX only: format=docx, dir=D:\\Exports\\FSC
  - Default folder, PDF only: format=pdf

Tips
- Many tools accept simple key=value parameter strings separated by commas (e.g., "mode=derive", "format=csv").
- Re-run traceability_build and fsc_export after changes to Safety Goals or FSRs.

Expected outcomes:
- A normalized Item Definition, HARA with ASIL values, synthesized Safety Goals, derived FSRs, allocation hints, and an end-to-end traceability matrix.
- Exported artifacts ready for review (Markdown/CSV/JSON), and optionally DOCX/PDF if your build supports conversion.

---

### Scenario 2 — Validate existing HARA and Safety Goals
Goal: You already have initial hazardous events (with S/E/C) and preliminary Safety Goals; validate and complete the FSC.

Steps:
1) Normalize Item Definition and extract structures (if not already done)
   - id_ingest_normalize -> "<your Item Definition JSON or text>"
   - id_extract_functions_interfaces

2) Validate HARA
   - hara_derive_or_validate -> "mode=validate"
   - Provide your hazardous events; the tool will compute/confirm ASIL values.

3) Re-synthesize/refine Safety Goals (if events changed)
   - safety_goals_synthesize

4) Derive FSRs and validate consistency
   - fsc_derive

5) Traceability and export
   - traceability_build -> "format=json"
   - fsc_export
   - Optionally save/convert to DOCX/PDF if supported.

Expected outcomes:
- Confirmed ASIL assignments, refined Safety Goals, and consistent FSRs with full traceability and exports.

---

### Scenario 3 — Iterative update after design change
Goal: Interfaces or modes changed (e.g., new sensor or degraded mode); update artifacts incrementally.

Steps:
1) Update Item Definition and re-extract
   - id_ingest_normalize -> "<updated Item Definition JSON>"
   - id_extract_functions_interfaces

2) Regenerate malfunction hypotheses
   - malfunction_hypotheses_generate

3) Update HARA only where impacted
   - hara_derive_or_validate -> "mode=derive"
   - Focus on changed functions/interfaces/modes.

4) Re-run downstream synthesis/derivation
   - safety_goals_synthesize
   - fsc_derive
   - allocation_hints_propose

5) Refresh traceability and export
   - traceability_build -> "format=csv"
   - fsc_export

Expected outcomes:
- Up-to-date HARA, Safety Goals, FSRs, and traceability reflecting the latest design.

---

### Scenario 4 — Prepare a compliance review package
Goal: Produce a review packet for stakeholders with key artifacts.

Steps:
1) Ensure the workflow has been executed up through fsc_derive
2) Build traceability and export
   - traceability_build -> "format=csv"
   - fsc_export
3) Save and optionally convert documents (if supported)
   - See “Saving to disk and DOCX/PDF”:
     - DOCX+PDF in default folder: format=both
     - Only DOCX to a custom folder: format=docx, dir=D:\Exports\FSC
     - Only PDF: format=pdf

Expected outcomes:
- A set of review-ready artifacts (Markdown/CSV/JSON), plus optional DOCX/PDF documents.

---

### Notes on tool input format
- Many tools accept a simple "key=value" parameter string, e.g.:
  - "mode=derive"
  - "format=csv"
  - "format=docx, dir=D:\Exports\FSC"
- Separate multiple parameters with commas, and avoid surrounding quotes unless needed for spaces.