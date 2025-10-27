"""Session management utilities for auditing and cleaning up session data."""
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, NamedTuple
import shutil
import click

from src.config import Config

class Session(NamedTuple):
    path: Path
    session_id: str
    timestamp: datetime

class AuditReport(NamedTuple):
    orphaned: List[Session]
    incomplete: List[Session]
    stale_checkpoints: List[Session]

class SessionManager:
    """Manage session lifecycle and cleanup."""

    def __init__(self, output_dir: Path = None, checkpoint_dir: Path = None):
        self.output_dir = output_dir or Config.OUTPUT_DIR
        self.checkpoint_dir = checkpoint_dir or Config.OUTPUT_DIR / "_checkpoints"

    def _discover_sessions(self) -> List[Session]:
        """Discover all sessions in the output directory."""
        sessions = []
        for session_dir in self.output_dir.iterdir():
            if not session_dir.is_dir() or session_dir.name == "_checkpoints":
                continue
            try:
                timestamp_str, session_id = session_dir.name.split("_", 1)
                timestamp = datetime.strptime(timestamp_str, "%Y%m%d%H%M%S")
                sessions.append(Session(session_dir, session_id, timestamp))
            except ValueError:
                # Ignore directories that don't match the expected format
                continue
        return sorted(sessions, key=lambda s: s.timestamp)

    def _is_orphaned(self, session: Session) -> bool:
        """Check if a session is orphaned (no files in directory)."""
        return not any(session.path.iterdir())

    def _is_incomplete(self, session: Session) -> bool:
        """Check if a session has all expected outputs."""
        if self._is_orphaned(session):
            return False
        required_files = [
            f"{session.session_id}_full.txt",
            f"{session.session_id}_data.json",
        ]
        return not all((session.path / f).exists() for f in required_files)

    def _has_stale_checkpoint(self, session: Session) -> bool:
        """Check if a session has a stale checkpoint."""
        checkpoint_path = self.checkpoint_dir / session.session_id
        if not checkpoint_path.exists():
            return False
        
        stale_time = datetime.now() - timedelta(days=7)
        for checkpoint_file in checkpoint_path.iterdir():
            if datetime.fromtimestamp(checkpoint_file.stat().st_mtime) < stale_time:
                return True
        return False

    def audit_sessions(self) -> AuditReport:
        """Scan all sessions and identify issues."""
        sessions = self._discover_sessions()
        report = AuditReport([], [], [])
        for session in sessions:
            if self._is_orphaned(session):
                report.orphaned.append(session)
            elif self._is_incomplete(session):
                report.incomplete.append(session)
            if self._has_stale_checkpoint(session):
                report.stale_checkpoints.append(session)
        return report

    def cleanup_sessions(self, report: AuditReport, mode: str) -> Dict:
        """Clean up sessions based on the audit report and cleanup mode."""
        actions = {
            "deleted_orphaned": [],
            "deleted_incomplete": [],
            "deleted_stale_checkpoints": [],
        }

        if mode == "dry_run":
            return {
                "orphaned": [s.path for s in report.orphaned],
                "incomplete": [s.path for s in report.incomplete],
                "stale_checkpoints": [s.path for s in report.stale_checkpoints],
                "deleted_orphaned": [],
                "deleted_incomplete": [],
                "deleted_stale_checkpoints": [],
            }

        for session in report.orphaned:
            if mode == "force" or click.confirm(f"Delete orphaned session {session.session_id}?", default=False):
                shutil.rmtree(session.path)
                actions["deleted_orphaned"].append(session.path)

        for session in report.incomplete:
            if mode == "force" or click.confirm(f"Delete incomplete session {session.session_id}?", default=False):
                shutil.rmtree(session.path)
                actions["deleted_incomplete"].append(session.path)

        for session in report.stale_checkpoints:
            if mode == "force" or click.confirm(f"Delete stale checkpoint for session {session.session_id}?", default=False):
                shutil.rmtree(self.checkpoint_dir / session.session_id)
                actions["deleted_stale_checkpoints"].append(self.checkpoint_dir / session.session_id)

        return actions
