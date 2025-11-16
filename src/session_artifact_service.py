"""Service layer for browsing and exporting processed session artifacts."""
from __future__ import annotations

import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Union

from .config import Config
from .logger import get_logger

__all__ = [
    "ArtifactMetadata",
    "ArtifactPreview",
    "SessionArtifactService",
    "SessionArtifactServiceError",
    "SessionDirectorySummary",
]

# Text artifacts that are eligible for inline previews.
DEFAULT_TEXT_PREVIEW_EXTENSIONS: Sequence[str] = (
    ".txt",
    ".md",
    ".markdown",
    ".json",
    ".log",
    ".srt",
    ".vtt",
    ".csv",
    ".tsv",
    ".yaml",
    ".yml",
)


class SessionArtifactServiceError(Exception):
    """Raised when the SessionArtifactService encounters invalid input or IO failures."""


@dataclass(frozen=True)
class SessionDirectorySummary:
    """Aggregate metadata describing a processed session directory.

    Attributes:
        name: Terminal directory name (typically the session identifier).
        relative_path: Path to the session relative to the configured output directory.
        file_count: Count of files inside the directory (recursive).
        total_size_bytes: Total byte size of the directory contents (recursive).
        created: Creation timestamp (UTC) reported by the filesystem.
        modified: Last modification timestamp (UTC) reported by the filesystem.
    """

    name: str
    relative_path: str
    file_count: int
    total_size_bytes: int
    created: datetime
    modified: datetime


@dataclass(frozen=True)
class ArtifactMetadata:
    """Metadata that describes an individual file or directory within a session.

    Attributes:
        name: Basename of the artifact.
        relative_path: Artifact path relative to the output directory root, using '/' separators.
        artifact_type: File extension (without dot) or 'directory'/'file' for generic entries.
        size_bytes: Reported byte size (files) or directory entry size reported by the OS.
        created: Creation timestamp (UTC) reported by the filesystem.
        modified: Last modification timestamp (UTC) reported by the filesystem.
        is_directory: Indicator for directories so callers can decide whether to expand it.
    """

    name: str
    relative_path: str
    artifact_type: str
    size_bytes: int
    created: datetime
    modified: datetime
    is_directory: bool


@dataclass(frozen=True)
class ArtifactPreview:
    """Represents the preview snippet generated for a text artifact.

    Attributes:
        relative_path: Artifact path relative to the output directory root.
        content: UTF-8 (or configured) decoded text snippet.
        truncated: Indicates whether the returned content is shorter than the file.
        encoding: Name of the codec used to decode the bytes.
        byte_length: Number of raw bytes captured in the preview.
    """

    relative_path: str
    content: str
    truncated: bool
    encoding: str
    byte_length: int


RelativePath = Union[str, Path]


class SessionArtifactService:
    """Provides filesystem-backed queries for session artifacts and bundles."""

    def __init__(
        self,
        output_dir: Optional[Path] = None,
        temp_dir: Optional[Path] = None,
        preview_byte_limit: int = 10_240,
        text_preview_extensions: Optional[Sequence[str]] = None,
    ) -> None:
        self.output_dir = (output_dir or Config.OUTPUT_DIR).resolve()
        self.temp_dir = (temp_dir or Config.TEMP_DIR).resolve()
        self.preview_byte_limit = max(preview_byte_limit, 1)
        self.text_preview_extensions = {
            ext.lower() for ext in (text_preview_extensions or DEFAULT_TEXT_PREVIEW_EXTENSIONS)
        }
        self.logger = get_logger("session_artifacts")

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def list_sessions(self) -> List[SessionDirectorySummary]:
        """Return metadata for every session directory under output/ sorted by modified time."""
        summaries: List[SessionDirectorySummary] = []
        for entry in self.output_dir.iterdir():
            if not entry.is_dir():
                continue
            try:
                summaries.append(self._build_session_summary(entry))
            except OSError as exc:
                self.logger.warning("Failed to inspect session directory %s: %s", entry, exc)
        summaries.sort(key=lambda summary: summary.modified, reverse=True)
        return summaries

    def list_directory(self, relative_path: RelativePath) -> List[ArtifactMetadata]:
        """Return metadata for direct children of the provided directory."""
        directory = self._resolve_relative_path(relative_path)
        if not directory.is_dir():
            raise SessionArtifactServiceError(f"{directory} is not a directory")

        artifacts: List[ArtifactMetadata] = []
        for child in directory.iterdir():
            try:
                artifacts.append(self._build_artifact_metadata(child))
            except OSError as exc:
                self.logger.warning("Failed to inspect artifact %s: %s", child, exc)
        artifacts.sort(key=lambda artifact: artifact.name.lower())
        return artifacts

    def get_artifact_metadata(self, relative_path: RelativePath) -> ArtifactMetadata:
        """Return metadata for a single artifact located inside the output directory."""
        artifact_path = self._resolve_relative_path(relative_path)
        if not artifact_path.exists():
            raise SessionArtifactServiceError(f"Artifact {relative_path!r} does not exist")
        return self._build_artifact_metadata(artifact_path)

    def get_text_preview(
        self,
        relative_path: RelativePath,
        max_bytes: Optional[int] = None,
        encoding: str = "utf-8",
    ) -> ArtifactPreview:
        """Return a truncated preview snippet for supported text artifacts."""
        artifact_path = self._resolve_relative_path(relative_path)
        if not artifact_path.is_file():
            raise SessionArtifactServiceError(f"{artifact_path} is not a file")

        suffix = artifact_path.suffix.lower()
        if suffix not in self.text_preview_extensions:
            raise SessionArtifactServiceError(
                f"Preview is only available for text files ({suffix} is unsupported)"
            )

        limit = max_bytes or self.preview_byte_limit
        if limit <= 0:
            raise SessionArtifactServiceError("Preview byte limit must be positive")

        preview_bytes = self._read_preview_bytes(artifact_path, limit)
        truncated = preview_bytes["truncated"]
        content_bytes = preview_bytes["data"]
        decoded = content_bytes.decode(encoding, errors="replace")

        return ArtifactPreview(
            relative_path=self._to_relative_str(artifact_path),
            content=decoded,
            truncated=truncated,
            encoding=encoding,
            byte_length=len(content_bytes),
        )

    def create_session_zip(
        self,
        relative_path: RelativePath,
        destination: Optional[Path] = None,
        compression: int = zipfile.ZIP_DEFLATED,
    ) -> Path:
        """Bundle an entire session directory into a zip archive stored under temp/."""
        session_dir = self._resolve_relative_path(relative_path)
        if not session_dir.is_dir():
            raise SessionArtifactServiceError(f"{session_dir} is not a directory")

        archive_path = self._resolve_archive_destination(session_dir, destination)
        with zipfile.ZipFile(archive_path, "w", compression=compression) as archive:
            for file_path in sorted(self._iter_files(session_dir)):
                arcname = file_path.relative_to(session_dir).as_posix()
                archive.write(file_path, arcname=arcname)
        self.logger.info("Created session bundle at %s", archive_path)
        return archive_path

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _build_session_summary(self, path: Path) -> SessionDirectorySummary:
        stats = path.stat()
        total_size = self._directory_size(path)
        file_count = self._file_count(path)
        return SessionDirectorySummary(
            name=path.name,
            relative_path=self._to_relative_str(path),
            file_count=file_count,
            total_size_bytes=total_size,
            created=self._timestamp(stats.st_ctime),
            modified=self._timestamp(stats.st_mtime),
        )

    def _build_artifact_metadata(self, path: Path) -> ArtifactMetadata:
        stats = path.stat()
        artifact_type = self._artifact_type(path)
        return ArtifactMetadata(
            name=path.name,
            relative_path=self._to_relative_str(path),
            artifact_type=artifact_type,
            size_bytes=stats.st_size,
            created=self._timestamp(stats.st_ctime),
            modified=self._timestamp(stats.st_mtime),
            is_directory=path.is_dir(),
        )

    def _artifact_type(self, path: Path) -> str:
        if path.is_dir():
            return "directory"
        suffix = path.suffix.lower().lstrip(".")
        return suffix or "file"

    def _resolve_relative_path(self, relative_path: RelativePath) -> Path:
        relative = Path(relative_path)
        if relative.is_absolute():
            raise SessionArtifactServiceError("Absolute paths are not allowed")
        joined = (self.output_dir / relative).resolve()
        try:
            joined.relative_to(self.output_dir)
        except ValueError as exc:
            raise SessionArtifactServiceError("Path escapes output directory") from exc
        return joined

    def _to_relative_str(self, path: Path) -> str:
        return path.relative_to(self.output_dir).as_posix()

    def _directory_size(self, path: Path) -> int:
        total = 0
        for file_path in self._iter_files(path):
            try:
                total += file_path.stat().st_size
            except OSError:
                self.logger.warning("Failed to compute size for %s", file_path)
        return total

    def _file_count(self, path: Path) -> int:
        return sum(1 for _ in self._iter_files(path))

    def _iter_files(self, path: Path) -> Iterable[Path]:
        for child in path.rglob("*"):
            if child.is_file():
                yield child

    def _read_preview_bytes(self, artifact_path: Path, limit: int) -> dict:
        with artifact_path.open("rb") as handle:
            buffer = handle.read(limit + 1)
        truncated = len(buffer) > limit
        data = buffer[:limit]
        return {"data": data, "truncated": truncated}

    def _resolve_archive_destination(self, session_dir: Path, destination: Optional[Path]) -> Path:
        if destination is not None:
            destination = destination.resolve()
            destination.parent.mkdir(parents=True, exist_ok=True)
            return destination

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        safe_name = session_dir.name or "session"
        archive_name = f"{safe_name}_{timestamp}.zip"
        return (self.temp_dir / archive_name).resolve()

    def _timestamp(self, value: float) -> datetime:
        return datetime.fromtimestamp(value, tz=timezone.utc)
