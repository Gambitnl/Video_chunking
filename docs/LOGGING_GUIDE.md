# Logging & Audit Reference

This guide explains how the VideoChunking project captures runtime logs, how to adjust verbosity, and how to review the new security-focused audit trail.

---

## Runtime Logging

- **Primary logger**: `src/logger.py` provides a shared `SessionLogger` used across the pipeline, CLI, and Gradio UI.
- **Outputs**:
  - Console logs default to `INFO`.
  - Detailed logs stream to `logs/session_processor_YYYYMMDD.log`.
- **Configuration**:
  - `.env` keys `LOG_LEVEL_CONSOLE` and `LOG_LEVEL_FILE` control default verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`).
  - The CLI accepts `--log-level` to override console verbosity for a single invocation.
  - The Gradio UI exposes a “Logging Controls” accordion under *Settings & Tools* so operators can raise or lower console verbosity without restarting.

---

## Audit Logging

- **Why**: Sensitive operations (session cleanup, party/character imports, OAuth flows, UI pipeline runs) now emit immutable JSON-line entries for traceability.
- **Location**: `logs/audit.log` (configurable via `AUDIT_LOG_PATH`).
- **Format**:
  ```json
  {
    "timestamp": "2025-11-06T12:00:00+00:00",
    "action": "cli.sessions.cleanup",
    "actor": "local",
    "source": "cli",
    "status": "success",
    "metadata": {
      "dry_run": false,
      "results": {
        "deleted_empty": 2,
        "freed_mb": 145.3
      }
    }
  }
  ```
- **Configuration**:
  - `AUDIT_LOG_ENABLED` (default `true`) toggles event recording.
  - `AUDIT_LOG_ACTOR` labels entries (useful per environment/user).
  - `AUDIT_LOG_PATH` sets the file path (absolute or relative to project root).
- **CLI controls**:
  - `--audit-actor` overrides the actor label for a single run.
  - `--no-audit` disables audit logging temporarily (local experimentation only).

---

## Reviewed Actions

| Area | Events Captured |
|------|-----------------|
| CLI  | Session processing, session cleanup, party/character import/export, speaker mapping |
| UI   | Gradio session runs, OAuth authentication attempts and outcomes |
| Services | SessionManager deletions, checkpoint cleanup, overall cleanup summaries |

Each event couples structured metadata with the shared `SessionLogger` output so engineers can correlate human-readable logs with machine-readable audit trails.

---

## Quick Checklist

- Set `AUDIT_LOG_ACTOR` in your `.env` to identify your host.
- Use `python cli.py --log-level DEBUG ...` when debugging noisy flows.
- Review `logs/audit.log` before releases or when investigating destructive actions.
- Include audit log snippets in incident reports for authoritative timelines.
