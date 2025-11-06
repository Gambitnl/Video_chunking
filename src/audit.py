"""Lightweight audit logging utilities for security-sensitive operations."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from .config import Config


class AuditLogger:
    """Append-only JSON lines audit logger."""

    def __init__(self) -> None:
        self.enabled = Config.AUDIT_LOG_ENABLED
        self.log_file = _resolve_log_path()
        if self.enabled:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def log(
        self,
        action: str,
        *,
        actor: Optional[str] = None,
        source: Optional[str] = None,
        status: str = "info",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Write an audit event if auditing is enabled."""
        if not self.enabled:
            return

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "actor": actor or Config.AUDIT_LOG_ACTOR,
            "source": source or "system",
            "status": status,
            "metadata": metadata or {},
        }

        with self.log_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=True) + "\n")


def _resolve_log_path() -> Path:
    configured = Config.AUDIT_LOG_PATH
    if configured.is_absolute():
        return configured
    return Config.PROJECT_ROOT / configured


_audit_logger = AuditLogger()


def log_audit_event(
    action: str,
    *,
    actor: Optional[str] = None,
    source: Optional[str] = None,
    status: str = "info",
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Public helper to record an audit event."""
    _audit_logger.log(
        action,
        actor=actor,
        source=source,
        status=status,
        metadata=metadata,
    )


def audit_enabled() -> bool:
    """Return True when audit logging is active."""
    return _audit_logger.enabled
