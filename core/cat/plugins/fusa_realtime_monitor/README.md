FuSa Real-time Safety Monitoring Agent

Overview
- Ingest metrics via REST, periodically evaluate against thresholds, raise alerts, and keep encrypted audit logs.

Endpoints
- POST /custom/fusa/monitor/ingest  (body: {"metrics": {"cpu_temp": 72.0}})
- GET  /custom/fusa/monitor/audit   (returns last entries)

Tools
- current_safety_state()
- set_thresholds(JSON)
- export_monitor_audit_trail()

Scheduler
- The evaluator is started after bootstrap using the after_cat_bootstrap hook and runs every evaluation_period_seconds.

Security
- Set CCAT_FUSA_SECRET or CCAT_JWT_SECRET for encryption; endpoints require PLUGINS permissions.
+ Encryption disabled by default: audit and state are stored in cleartext; endpoints still require PLUGINS permissions.