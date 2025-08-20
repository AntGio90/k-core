FuSa Documentation Review Agent

Overview
- Analyzes requirements, FMEA, and test case content to detect traceability gaps and basic ISO 26262 / IEC 61508 checklist coverage.
- Produces JSON or Markdown reports and stores an encrypted audit trail.

Install/Activate
- Place this folder in core/cat/plugins/.
- Start the Cat; activate the plugin from /admin -> Plugins, or via API.

Configuration
- Edit settings.json in the plugin folder or via the Plugins Settings API.
- Set CCAT_FUSA_SECRET or CCAT_JWT_SECRET for encryption. When encryption_enabled:true, both reports and audit logs are encrypted.

Tools
- analyze_safety_documents(JSON): returns report path and summary.
- get_last_doc_review_report(): quick preview of last report.

Endpoints
- GET /custom/fusa/doc-review/report
- POST /custom/fusa/doc-review/analyze

Input shape example
{
  "requirements": [{"id": "REQ-SYS-001", "text": "Brake shall ...", "source": "SRS"}],
  "fmea": [{"id": "FMEA-01", "requirement_ids": ["REQ-SYS-001"], "severity": 8, "occurrence": 2, "detection": 6}],
  "tests": [{"id": "TC-001", "requirement_ids": ["REQ-SYS-001"], "status": "passed"}],
  "options": {"format":"json"}
}

Output
- Files saved under storage/ with encryption when enabled.
+ Encryption disabled by default: reports and audit logs are stored in cleartext (no secret required).