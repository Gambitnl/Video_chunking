"""Tests for SessionArtifactService."""
from datetime import datetime, timezone
import os
from pathlib import Path
import zipfile

import pytest

from src.session_artifact_service import (
    ArtifactPreview,
    SessionArtifactService,
    SessionArtifactServiceError,
)


@pytest.fixture()
def service_env(tmp_path):
    """Create an isolated output/temp directory pair for the service under test."""
    output_dir = tmp_path / "output"
    temp_dir = tmp_path / "temp"
    output_dir.mkdir()
    temp_dir.mkdir()
    service = SessionArtifactService(
        output_dir=output_dir,
        temp_dir=temp_dir,
        preview_byte_limit=8,
    )
    return service, output_dir, temp_dir


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_binary(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def test_list_sessions_sorted_by_modified(service_env):
    """Session directories should be returned newest-first with accurate metadata."""
    service, output_dir, _ = service_env
    older = output_dir / "session_old"
    newer = output_dir / "session_new"
    older.mkdir()
    newer.mkdir()
    _write_text(older / "story.txt", "old session")
    _write_text(newer / "story.txt", "new session text")

    old_timestamp = datetime(2024, 1, 1, tzinfo=timezone.utc).timestamp()
    new_timestamp = datetime(2024, 1, 2, tzinfo=timezone.utc).timestamp()
    os.utime(older, (old_timestamp, old_timestamp))
    os.utime(newer, (new_timestamp, new_timestamp))

    summaries = service.list_sessions()
    assert [summary.name for summary in summaries] == ["session_new", "session_old"]

    latest = summaries[0]
    assert latest.relative_path == "session_new"
    assert latest.file_count == 1
    assert latest.total_size_bytes == len("new session text")
    assert latest.created.tzinfo == timezone.utc
    assert latest.modified == datetime(2024, 1, 2, tzinfo=timezone.utc)


def test_list_directory_returns_files_and_directories(service_env):
    """Listing a directory should return metadata for each child entry."""
    service, output_dir, _ = service_env
    session = output_dir / "session_alpha"
    segments = session / "segments"
    session.mkdir()
    segments.mkdir()

    _write_text(session / "transcript.json", '{"status": "complete"}')
    _write_text(segments / "chunk01.txt", "chunk content")

    rows = service.list_directory("session_alpha")
    assert [row.name for row in rows] == ["segments", "transcript.json"]

    directory_row = rows[0]
    assert directory_row.is_directory is True
    assert directory_row.artifact_type == "directory"
    assert directory_row.relative_path == "session_alpha/segments"

    file_row = rows[1]
    assert file_row.is_directory is False
    assert file_row.artifact_type == "json"
    assert file_row.size_bytes == len('{"status": "complete"}')
    assert file_row.relative_path == "session_alpha/transcript.json"


def test_list_directory_with_subpath(service_env):
    """The service should support listing nested directories via relative paths."""
    service, output_dir, _ = service_env
    session = output_dir / "session_bravo"
    nested = session / "narratives"
    nested.mkdir(parents=True)
    _write_text(nested / "ic_only.md", "## Narrative")

    entries = service.list_directory("session_bravo/narratives")
    assert len(entries) == 1
    assert entries[0].name == "ic_only.md"
    assert entries[0].relative_path == "session_bravo/narratives/ic_only.md"


def test_list_directory_blocks_path_traversal(service_env):
    """Relative paths that escape the output directory should raise an error."""
    service, _, _ = service_env
    with pytest.raises(SessionArtifactServiceError):
        service.list_directory("../temp")


def test_get_text_preview_truncates_long_files(service_env):
    """Preview should return truncated UTF-8 content and metadata."""
    service, output_dir, _ = service_env
    session = output_dir / "session_charlie"
    session.mkdir()
    _write_text(session / "summary.txt", "ABCDEFGHIJK")

    preview = service.get_text_preview("session_charlie/summary.txt")
    assert isinstance(preview, ArtifactPreview)
    assert preview.content == "ABCDEFGH"
    assert preview.truncated is True
    assert preview.encoding == "utf-8"
    assert preview.byte_length == 8


def test_get_text_preview_rejects_binary_files(service_env):
    """Binary artifacts should not be eligible for previews."""
    service, output_dir, _ = service_env
    session = output_dir / "session_delta"
    session.mkdir()
    binary_path = session / "audio.bin"
    _write_binary(binary_path, b"\x00\x01\x02")

    with pytest.raises(SessionArtifactServiceError):
        service.get_text_preview("session_delta/audio.bin")


def test_create_session_zip_includes_all_files(service_env):
    """The bundle helper should write an archive with every file preserved."""
    service, output_dir, temp_dir = service_env
    session = output_dir / "session_echo"
    session.mkdir()
    _write_text(session / "summary.txt", "summary text")
    _write_binary(session / "segments" / "chunk01.bin", b"chunk")

    archive_path = service.create_session_zip("session_echo")
    assert archive_path.exists()
    assert archive_path.parent == temp_dir

    with zipfile.ZipFile(archive_path, "r") as archive:
        names = sorted(archive.namelist())
        assert names == ["segments/chunk01.bin", "summary.txt"]


def test_get_artifact_metadata_for_file(service_env):
    """Single artifact metadata lookups should include relative paths and sizes."""
    service, output_dir, _ = service_env
    session = output_dir / "session_foxtrot"
    session.mkdir()
    target = session / "report.json"
    _write_text(target, '{"key": "value"}')

    metadata = service.get_artifact_metadata("session_foxtrot/report.json")
    assert metadata.name == "report.json"
    assert metadata.relative_path == "session_foxtrot/report.json"
    assert metadata.size_bytes == len('{"key": "value"}')
    assert metadata.artifact_type == "json"


def test_zip_requires_directory(service_env):
    """Attempting to zip a file path should raise a descriptive error."""
    service, output_dir, _ = service_env
    session = output_dir / "session_golf"
    session.mkdir()
    _write_text(session / "note.txt", "note")

    with pytest.raises(SessionArtifactServiceError):
        service.create_session_zip("session_golf/note.txt")


def test_delete_file_removes_artifact(service_env):
    """Deleting a file should remove it from disk and return metadata."""
    service, output_dir, _ = service_env
    session = output_dir / "session_hotel"
    session.mkdir()
    target = session / "obsolete.txt"
    _write_text(target, "obsolete")

    metadata = service.delete_artifact("session_hotel/obsolete.txt")
    assert metadata.name == "obsolete.txt"
    assert not target.exists()


def test_delete_directory_requires_recursive_flag(service_env):
    """Non-empty directories require recursive deletion."""
    service, output_dir, _ = service_env
    session = output_dir / "session_india"
    nested = session / "intermediates"
    nested.mkdir(parents=True)
    _write_text(nested / "stage.json", "{}")

    with pytest.raises(SessionArtifactServiceError):
        service.delete_artifact("session_india/intermediates", recursive=False)


def test_delete_directory_recursive(service_env):
    """Recursive deletion should remove directories and their contents."""
    service, output_dir, _ = service_env
    session = output_dir / "session_juliet"
    nested = session / "segments"
    nested.mkdir(parents=True)
    _write_text(nested / "chunk.txt", "chunk")

    metadata = service.delete_artifact("session_juliet/segments", recursive=True)
    assert metadata.is_directory is True
    assert not nested.exists()
