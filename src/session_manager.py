"""Session management utilities for auditing and cleaning up session data."""
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, NamedTuple, Optional
from dataclasses import dataclass, field
import shutil
import click

from .config import Config
from .logger import get_logger


@dataclass
class SessionInfo:
    """Detailed information about a session output directory."""

    session_id: str
    path: Path
    created_time: datetime
    size_bytes: int
    has_transcript: bool = False
    has_diarized_transcript: bool = False
    has_classified_transcript: bool = False
    has_snippets: bool = False
    has_story: bool = False
    has_knowledge: bool = False
    checkpoint_exists: bool = False
    checkpoint_age_days: Optional[float] = None

    @property
    def size_mb(self) -> float:
        """Return size in megabytes."""
        return self.size_bytes / (1024 * 1024)

    @property
    def is_complete(self) -> bool:
        """Check if session has all expected outputs."""
        return (
            self.has_transcript and
            self.has_diarized_transcript and
            self.has_classified_transcript
        )

    @property
    def is_empty(self) -> bool:
        """Check if session directory is empty or nearly empty."""
        return self.size_bytes < 1024  # Less than 1KB


@dataclass
class AuditReport:
    """Detailed audit report with statistics."""

    total_sessions: int = 0
    valid_sessions: List[SessionInfo] = field(default_factory=list)
    incomplete_sessions: List[SessionInfo] = field(default_factory=list)
    empty_sessions: List[SessionInfo] = field(default_factory=list)
    stale_checkpoints: List[str] = field(default_factory=list)

    total_size_bytes: int = 0
    incomplete_size_bytes: int = 0
    empty_size_bytes: int = 0
    stale_checkpoint_size_bytes: int = 0

    @property
    def total_size_mb(self) -> float:
        return self.total_size_bytes / (1024 * 1024)

    @property
    def incomplete_size_mb(self) -> float:
        return self.incomplete_size_bytes / (1024 * 1024)

    @property
    def empty_size_mb(self) -> float:
        return self.empty_size_bytes / (1024 * 1024)

    @property
    def stale_checkpoint_size_mb(self) -> float:
        return self.stale_checkpoint_size_bytes / (1024 * 1024)

    @property
    def potential_cleanup_mb(self) -> float:
        """Total space that could be freed."""
        return self.empty_size_mb + self.incomplete_size_mb + self.stale_checkpoint_size_mb


@dataclass
class CleanupReport:
    """Report of cleanup actions taken."""

    deleted_empty: int = 0
    deleted_incomplete: int = 0
    deleted_checkpoints: int = 0

    freed_empty_bytes: int = 0
    freed_incomplete_bytes: int = 0
    freed_checkpoint_bytes: int = 0

    skipped_sessions: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def total_deleted(self) -> int:
        return self.deleted_empty + self.deleted_incomplete + self.deleted_checkpoints

    @property
    def total_freed_mb(self) -> float:
        total_bytes = self.freed_empty_bytes + self.freed_incomplete_bytes + self.freed_checkpoint_bytes
        return total_bytes / (1024 * 1024)


# Legacy types for backward compatibility
class Session(NamedTuple):
    path: Path
    session_id: str
    timestamp: datetime

class SessionManager:
    """Manage session lifecycle and cleanup."""

    def __init__(
        self,
        output_dir: Optional[Path] = None,
        checkpoint_age_threshold_days: int = 7
    ):
        """Initialize session manager.

        Args:
            output_dir: Base output directory (defaults to Config.OUTPUT_DIR)
            checkpoint_age_threshold_days: Age threshold for stale checkpoints
        """
        self.output_dir = Path(output_dir) if output_dir else Config.OUTPUT_DIR
        self.checkpoint_dir = self.output_dir / "_checkpoints"
        self.checkpoint_age_threshold = timedelta(days=checkpoint_age_threshold_days)
        self.logger = get_logger('session_manager')

    def _get_directory_size(self, path: Path) -> int:
        """Recursively calculate directory size in bytes."""
        total = 0
        try:
            for item in path.rglob('*'):
                if item.is_file():
                    try:
                        total += item.stat().st_size
                    except (OSError, PermissionError):
                        pass
        except (OSError, PermissionError):
            pass
        return total

    def _get_creation_time(self, path: Path) -> datetime:
        """Get directory creation time."""
        try:
            stat_info = path.stat()
            # Use modification time as a proxy for creation time
            return datetime.fromtimestamp(stat_info.st_mtime)
        except (OSError, PermissionError):
            return datetime.now()

    def _analyze_session(self, session_path: Path) -> SessionInfo:
        """Analyze a session directory and return detailed metadata.

        Args:
            session_path: Path to session directory

        Returns:
            SessionInfo object with session metadata
        """
        session_id = session_path.name
        created_time = self._get_creation_time(session_path)
        size_bytes = self._get_directory_size(session_path)

        # Check for expected output files
        transcripts_dir = session_path / "transcripts"
        has_transcript = (transcripts_dir / "transcript.json").exists()
        has_diarized = (transcripts_dir / "diarized_transcript.json").exists()
        has_classified = (transcripts_dir / "classified_transcript.json").exists()

        # Check for snippets
        segments_dir = self.output_dir / "segments" / session_id
        has_snippets = (segments_dir / "manifest.json").exists() if segments_dir.exists() else False

        # Check for story and knowledge outputs
        stories_dir = session_path / "stories"
        has_story = (stories_dir / "story_notebook.md").exists() if stories_dir.exists() else False

        knowledge_dir = session_path / "knowledge"
        has_knowledge = knowledge_dir.exists() and any(knowledge_dir.glob("*.json"))

        # Check for checkpoint
        checkpoint_path = self.checkpoint_dir / session_id
        checkpoint_exists = checkpoint_path.exists()
        checkpoint_age_days = None

        if checkpoint_exists:
            checkpoint_time = self._get_creation_time(checkpoint_path)
            checkpoint_age = datetime.now() - checkpoint_time
            checkpoint_age_days = checkpoint_age.total_seconds() / 86400

        return SessionInfo(
            session_id=session_id,
            path=session_path,
            created_time=created_time,
            size_bytes=size_bytes,
            has_transcript=has_transcript,
            has_diarized_transcript=has_diarized,
            has_classified_transcript=has_classified,
            has_snippets=has_snippets,
            has_story=has_story,
            has_knowledge=has_knowledge,
            checkpoint_exists=checkpoint_exists,
            checkpoint_age_days=checkpoint_age_days
        )

    def discover_sessions(self) -> List[SessionInfo]:
        """Discover all sessions in output directory.

        Returns:
            List of SessionInfo objects for all discovered sessions
        """
        sessions = []

        if not self.output_dir.exists():
            self.logger.warning(f"Output directory does not exist: {self.output_dir}")
            return sessions

        # Scan output directory for session directories
        # Skip special directories like _checkpoints and segments
        skip_dirs = {"_checkpoints", "segments"}

        for item in self.output_dir.iterdir():
            if item.is_dir() and item.name not in skip_dirs:
                try:
                    session_info = self._analyze_session(item)
                    sessions.append(session_info)
                except Exception as e:
                    self.logger.error(f"Error analyzing session {item.name}: {e}")

        return sorted(sessions, key=lambda s: s.created_time, reverse=True)

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
        """Audit all sessions and identify issues.

        Returns:
            AuditReport with detailed findings and statistics
        """
        self.logger.info("Starting session audit...")

        sessions = self.discover_sessions()
        report = AuditReport(total_sessions=len(sessions))

        for session in sessions:
            report.total_size_bytes += session.size_bytes

            if session.is_empty:
                report.empty_sessions.append(session)
                report.empty_size_bytes += session.size_bytes
            elif not session.is_complete:
                report.incomplete_sessions.append(session)
                report.incomplete_size_bytes += session.size_bytes
            else:
                report.valid_sessions.append(session)

        # Check for stale checkpoints
        if self.checkpoint_dir.exists():
            for checkpoint in self.checkpoint_dir.iterdir():
                if checkpoint.is_dir():
                    checkpoint_time = self._get_creation_time(checkpoint)
                    checkpoint_age = datetime.now() - checkpoint_time

                    if checkpoint_age > self.checkpoint_age_threshold:
                        report.stale_checkpoints.append(checkpoint.name)
                        checkpoint_size = self._get_directory_size(checkpoint)
                        report.stale_checkpoint_size_bytes += checkpoint_size

        self.logger.info(
            f"Audit complete: {report.total_sessions} sessions, "
            f"{len(report.empty_sessions)} empty, "
            f"{len(report.incomplete_sessions)} incomplete, "
            f"{len(report.stale_checkpoints)} stale checkpoints"
        )

        return report

    def cleanup_session(self, session_info: SessionInfo, dry_run: bool = False) -> int:
        """Delete a session directory and associated files.

        Args:
            session_info: Session to delete
            dry_run: If True, don't actually delete (just report)

        Returns:
            Number of bytes that would be freed (or were freed)
        """
        if dry_run:
            self.logger.info(f"[DRY RUN] Would delete session: {session_info.session_id} ({session_info.size_mb:.2f} MB)")
            return session_info.size_bytes

        try:
            # Delete session directory
            shutil.rmtree(session_info.path)
            self.logger.info(f"Deleted session: {session_info.session_id} ({session_info.size_mb:.2f} MB)")

            # Delete associated snippets if they exist
            segments_dir = self.output_dir / "segments" / session_info.session_id
            if segments_dir.exists():
                shutil.rmtree(segments_dir)
                self.logger.info(f"Deleted snippets for: {session_info.session_id}")

            # Delete checkpoint if it exists
            checkpoint_path = self.checkpoint_dir / session_info.session_id
            if checkpoint_path.exists():
                shutil.rmtree(checkpoint_path)
                self.logger.info(f"Deleted checkpoint for: {session_info.session_id}")

            return session_info.size_bytes

        except Exception as e:
            self.logger.error(f"Error deleting session {session_info.session_id}: {e}")
            raise

    def cleanup_checkpoint(self, checkpoint_name: str, dry_run: bool = False) -> int:
        """Delete a stale checkpoint.

        Args:
            checkpoint_name: Name of checkpoint to delete
            dry_run: If True, don't actually delete (just report)

        Returns:
            Number of bytes that would be freed (or were freed)
        """
        checkpoint_path = self.checkpoint_dir / checkpoint_name

        if not checkpoint_path.exists():
            self.logger.warning(f"Checkpoint not found: {checkpoint_name}")
            return 0

        size = self._get_directory_size(checkpoint_path)

        if dry_run:
            self.logger.info(f"[DRY RUN] Would delete checkpoint: {checkpoint_name} ({size / (1024 * 1024):.2f} MB)")
            return size

        try:
            shutil.rmtree(checkpoint_path)
            self.logger.info(f"Deleted checkpoint: {checkpoint_name} ({size / (1024 * 1024):.2f} MB)")
            return size
        except Exception as e:
            self.logger.error(f"Error deleting checkpoint {checkpoint_name}: {e}")
            raise

    def cleanup(
        self,
        delete_empty: bool = True,
        delete_incomplete: bool = False,
        delete_stale_checkpoints: bool = True,
        dry_run: bool = False,
        interactive: bool = True
    ) -> CleanupReport:
        """Clean up sessions based on criteria.

        Args:
            delete_empty: Delete empty session directories
            delete_incomplete: Delete incomplete sessions
            delete_stale_checkpoints: Delete checkpoints older than threshold
            dry_run: Don't actually delete, just report what would be deleted
            interactive: Prompt user before deleting each category

        Returns:
            CleanupReport with cleanup results
        """
        self.logger.info("Starting cleanup...")
        if dry_run:
            self.logger.info("DRY RUN MODE - no files will be deleted")

        report = CleanupReport()
        audit = self.audit_sessions()

        # Handle empty sessions
        if delete_empty and audit.empty_sessions:
            if interactive and not dry_run:
                self.logger.info(
                    "Found %s empty sessions (%.2f MB):",
                    len(audit.empty_sessions),
                    audit.empty_size_mb
                )
                for session in audit.empty_sessions[:5]:  # Show first 5
                    self.logger.info("  - %s (%.2f MB)", session.session_id, session.size_mb)
                if len(audit.empty_sessions) > 5:
                    self.logger.info("  ... and %s more", len(audit.empty_sessions) - 5)

                response = input("\nDelete empty sessions? [y/N]: ")
                if response.lower() != 'y':
                    report.skipped_sessions.extend([s.session_id for s in audit.empty_sessions])
                    delete_empty = False

            if delete_empty:
                for session in audit.empty_sessions:
                    try:
                        freed = self.cleanup_session(session, dry_run=dry_run)
                        report.deleted_empty += 1
                        report.freed_empty_bytes += freed
                    except Exception as e:
                        report.errors.append(f"Failed to delete {session.session_id}: {e}")

        # Handle incomplete sessions
        if delete_incomplete and audit.incomplete_sessions:
            if interactive and not dry_run:
                self.logger.info(
                    "Found %s incomplete sessions (%.2f MB):",
                    len(audit.incomplete_sessions),
                    audit.incomplete_size_mb
                )
                for session in audit.incomplete_sessions[:5]:
                    self.logger.info("  - %s (%.2f MB)", session.session_id, session.size_mb)
                if len(audit.incomplete_sessions) > 5:
                    self.logger.info("  ... and %s more", len(audit.incomplete_sessions) - 5)

                response = input("\nDelete incomplete sessions? [y/N]: ")
                if response.lower() != 'y':
                    report.skipped_sessions.extend([s.session_id for s in audit.incomplete_sessions])
                    delete_incomplete = False

            if delete_incomplete:
                for session in audit.incomplete_sessions:
                    try:
                        freed = self.cleanup_session(session, dry_run=dry_run)
                        report.deleted_incomplete += 1
                        report.freed_incomplete_bytes += freed
                    except Exception as e:
                        report.errors.append(f"Failed to delete {session.session_id}: {e}")

        # Handle stale checkpoints
        if delete_stale_checkpoints and audit.stale_checkpoints:
            if interactive and not dry_run:
                self.logger.info(
                    "Found %s stale checkpoints (%.2f MB):",
                    len(audit.stale_checkpoints),
                    audit.stale_checkpoint_size_mb
                )
                for checkpoint in audit.stale_checkpoints[:5]:
                    self.logger.info("  - %s", checkpoint)
                if len(audit.stale_checkpoints) > 5:
                    self.logger.info("  ... and %s more", len(audit.stale_checkpoints) - 5)

                response = input("\nDelete stale checkpoints? [y/N]: ")
                if response.lower() != 'y':
                    delete_stale_checkpoints = False

            if delete_stale_checkpoints:
                for checkpoint in audit.stale_checkpoints:
                    try:
                        freed = self.cleanup_checkpoint(checkpoint, dry_run=dry_run)
                        report.deleted_checkpoints += 1
                        report.freed_checkpoint_bytes += freed
                    except Exception as e:
                        report.errors.append(f"Failed to delete checkpoint {checkpoint}: {e}")

        self.logger.info(
            f"Cleanup complete: deleted {report.total_deleted} items, "
            f"freed {report.total_freed_mb:.2f} MB"
        )

        return report

    def generate_audit_report_markdown(self, audit: AuditReport) -> str:
        """Generate a markdown audit report.

        Args:
            audit: AuditReport to format

        Returns:
            Markdown-formatted report
        """
        lines = [
            "# Session Audit Report",
            f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Summary",
            f"- **Total Sessions**: {audit.total_sessions}",
            f"- **Valid Sessions**: {len(audit.valid_sessions)}",
            f"- **Empty Sessions**: {len(audit.empty_sessions)} ({audit.empty_size_mb:.2f} MB)",
            f"- **Incomplete Sessions**: {len(audit.incomplete_sessions)} ({audit.incomplete_size_mb:.2f} MB)",
            f"- **Stale Checkpoints**: {len(audit.stale_checkpoints)} ({audit.stale_checkpoint_size_mb:.2f} MB)",
            f"- **Total Storage Used**: {audit.total_size_mb:.2f} MB",
            f"- **Potential Cleanup**: {audit.potential_cleanup_mb:.2f} MB",
            ""
        ]

        if audit.empty_sessions:
            lines.extend([
                "## Empty Sessions",
                ""
            ])
            for session in audit.empty_sessions:
                lines.append(f"- `{session.session_id}` ({session.size_mb:.2f} MB, created {session.created_time.strftime('%Y-%m-%d')})")
            lines.append("")

        if audit.incomplete_sessions:
            lines.extend([
                "## Incomplete Sessions",
                ""
            ])
            for session in audit.incomplete_sessions:
                missing = []
                if not session.has_transcript:
                    missing.append("transcript")
                if not session.has_diarized_transcript:
                    missing.append("diarized")
                if not session.has_classified_transcript:
                    missing.append("classified")

                lines.append(
                    f"- `{session.session_id}` ({session.size_mb:.2f} MB, missing: {', '.join(missing)})"
                )
            lines.append("")

        if audit.stale_checkpoints:
            lines.extend([
                "## Stale Checkpoints (>7 days)",
                ""
            ])
            for checkpoint in audit.stale_checkpoints:
                lines.append(f"- `{checkpoint}`")
            lines.append("")

        return "\n".join(lines)

    def generate_cleanup_report_markdown(self, cleanup: CleanupReport) -> str:
        """Generate a markdown cleanup report.

        Args:
            cleanup: CleanupReport to format

        Returns:
            Markdown-formatted report
        """
        lines = [
            "# Session Cleanup Report",
            f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Summary",
            f"- **Empty Sessions Deleted**: {cleanup.deleted_empty} ({cleanup.freed_empty_bytes / (1024 * 1024):.2f} MB)",
            f"- **Incomplete Sessions Deleted**: {cleanup.deleted_incomplete} ({cleanup.freed_incomplete_bytes / (1024 * 1024):.2f} MB)",
            f"- **Stale Checkpoints Deleted**: {cleanup.deleted_checkpoints} ({cleanup.freed_checkpoint_bytes / (1024 * 1024):.2f} MB)",
            f"- **Total Items Deleted**: {cleanup.total_deleted}",
            f"- **Total Space Freed**: {cleanup.total_freed_mb:.2f} MB",
            ""
        ]

        if cleanup.skipped_sessions:
            lines.extend([
                "## Skipped Sessions",
                ""
            ])
            for session_id in cleanup.skipped_sessions:
                lines.append(f"- `{session_id}`")
            lines.append("")

        if cleanup.errors:
            lines.extend([
                "## Errors",
                ""
            ])
            for error in cleanup.errors:
                lines.append(f"- {error}")
            lines.append("")

        return "\n".join(lines)

    # Legacy methods for backward compatibility
    def cleanup_sessions(self, report: AuditReport, mode: str) -> Dict:
        """DEPRECATED: Use cleanup() method instead.

        Clean up sessions based on the audit report and cleanup mode.
        This method is kept for backward compatibility.
        """
        self.logger.warning("cleanup_sessions() is deprecated. Use cleanup() instead.")

        actions = {
            "deleted_orphaned": [],
            "deleted_incomplete": [],
            "deleted_stale_checkpoints": [],
        }

        if mode == "dry_run":
            return {
                "orphaned": [s.path for s in getattr(report, 'orphaned', [])],
                "incomplete": [s.path for s in getattr(report, 'incomplete', [])],
                "stale_checkpoints": [s.path for s in getattr(report, 'stale_checkpoints', [])],
                "deleted_orphaned": [],
                "deleted_incomplete": [],
                "deleted_stale_checkpoints": [],
            }

        # This is a simplified version; use cleanup() for full functionality
        return actions
