"""
Test suite for src/session_manager.py
"""
import pytest
from pathlib import Path
from datetime import datetime, timedelta

from unittest.mock import patch

from src.session_manager import SessionManager, Session

@pytest.fixture
def session_manager(tmp_path):
    output_dir = tmp_path / "output"
    checkpoint_dir = output_dir / "_checkpoints"
    output_dir.mkdir()
    checkpoint_dir.mkdir()
    # Note: checkpoint_dir is automatically created as output_dir/_checkpoints
    return SessionManager(output_dir=output_dir, checkpoint_age_threshold_days=7)

def create_test_session(output_dir: Path, session_id: str, timestamp: datetime, create_files: bool = True):
    session_dir_name = f"{timestamp.strftime('%Y%m%d%H%M%S')}_{session_id}"
    session_dir = output_dir / session_dir_name
    session_dir.mkdir()
    if create_files:
        (session_dir / f"{session_id}_full.txt").touch()
        (session_dir / f"{session_id}_data.json").touch()
    return session_dir

def test_discover_sessions(session_manager, tmp_path):
    now = datetime.now()
    create_test_session(session_manager.output_dir, "session2", now - timedelta(days=1))
    create_test_session(session_manager.output_dir, "session1", now)

    sessions = session_manager._discover_sessions()
    assert len(sessions) == 2
    assert sessions[0].session_id == "session2"
    assert sessions[1].session_id == "session1"

def test_is_orphaned(session_manager, tmp_path):
    now = datetime.now()
    session_dir = create_test_session(session_manager.output_dir, "orphaned_session", now, create_files=False)
    session = Session(session_dir, "orphaned_session", now)

    assert session_manager._is_orphaned(session) is True

def test_is_incomplete(session_manager, tmp_path):
    now = datetime.now()
    session_dir = create_test_session(session_manager.output_dir, "incomplete_session", now)
    (session_dir / f"incomplete_session_full.txt").unlink()
    session = Session(session_dir, "incomplete_session", now)

    assert session_manager._is_incomplete(session) is True

def test_has_stale_checkpoint(session_manager, tmp_path):
    now = datetime.now()
    stale_time = now - timedelta(days=8)
    session_dir = create_test_session(session_manager.output_dir, "stale_checkpoint_session", now)
    checkpoint_dir = session_manager.checkpoint_dir / "stale_checkpoint_session"
    checkpoint_dir.mkdir()
    stale_checkpoint_file = checkpoint_dir / "checkpoint.json"
    stale_checkpoint_file.touch()
    import os
    os.utime(stale_checkpoint_file, (stale_time.timestamp(), stale_time.timestamp()))

    session = Session(session_dir, "stale_checkpoint_session", now)

    assert session_manager._has_stale_checkpoint(session) is True

def test_audit_sessions(session_manager, tmp_path):
    now = datetime.now()
    # Create a complete session
    complete_dir = create_test_session(session_manager.output_dir, "session1", now)
    transcripts_dir = complete_dir / "transcripts"
    transcripts_dir.mkdir()
    (transcripts_dir / "transcript.json").write_text("{}")
    (transcripts_dir / "diarized_transcript.json").write_text("{}")
    (transcripts_dir / "classified_transcript.json").write_text("{}")

    # Create empty session
    create_test_session(session_manager.output_dir, "empty_session", now - timedelta(days=1), create_files=False)

    # Create incomplete session
    incomplete_dir = create_test_session(session_manager.output_dir, "incomplete_session", now - timedelta(days=2))
    incomplete_transcripts = incomplete_dir / "transcripts"
    incomplete_transcripts.mkdir()
    (incomplete_transcripts / "transcript.json").write_text("{}")
    (incomplete_transcripts / "diarized_transcript.json").write_text("{}")
    # Missing classified_transcript.json

    # Create stale checkpoint
    stale_checkpoint_dir = create_test_session(session_manager.output_dir, "stale_checkpoint_session", now - timedelta(days=3))
    stale_transcripts = stale_checkpoint_dir / "transcripts"
    stale_transcripts.mkdir()
    (stale_transcripts / "transcript.json").write_text("{}")
    (stale_transcripts / "diarized_transcript.json").write_text("{}")
    (stale_transcripts / "classified_transcript.json").write_text("{}")

    checkpoint_name = f"{now.strftime('%Y%m%d%H%M%S')}_stale_checkpoint_session".replace(now.strftime('%Y%m%d%H%M%S'), (now - timedelta(days=3)).strftime('%Y%m%d%H%M%S'))
    checkpoint_dir = session_manager.checkpoint_dir / checkpoint_name
    checkpoint_dir.mkdir()
    stale_checkpoint_file = checkpoint_dir / "checkpoint.json"
    stale_checkpoint_file.touch()
    stale_time = now - timedelta(days=8)
    import os
    os.utime(stale_checkpoint_file, (stale_time.timestamp(), stale_time.timestamp()))

    report = session_manager.audit_sessions()

    # New API uses empty_sessions, incomplete_sessions, valid_sessions
    # Note: Files with very small sizes (<1KB) are treated as empty
    assert report.total_sessions == 4
    assert len(report.empty_sessions) + len(report.incomplete_sessions) + len(report.valid_sessions) == 4
    # At least one empty session should be identified
    assert len([s for s in report.empty_sessions if s.session_id.endswith('empty_session')]) >= 1

def test_cleanup_dry_run(session_manager, tmp_path):
    """Test cleanup in dry-run mode (should not delete files)."""
    now = datetime.now()
    empty_session = create_test_session(session_manager.output_dir, "empty_session", now, create_files=False)

    report = session_manager.cleanup(
        delete_empty=True,
        delete_incomplete=False,
        delete_stale_checkpoints=False,
        dry_run=True,
        interactive=False
    )

    assert report.deleted_empty == 1
    assert empty_session.exists()  # Still exists in dry-run

def test_cleanup_force(session_manager, tmp_path):
    """Test cleanup actually deletes empty sessions."""
    now = datetime.now()
    empty_session = create_test_session(session_manager.output_dir, "empty_session", now, create_files=False)

    report = session_manager.cleanup(
        delete_empty=True,
        delete_incomplete=False,
        delete_stale_checkpoints=False,
        dry_run=False,
        interactive=False
    )

    assert report.deleted_empty == 1
    assert not empty_session.exists()  # Actually deleted

@patch('builtins.input', return_value='y')
def test_cleanup_interactive_yes(mock_input, session_manager, tmp_path):
    """Test interactive cleanup when user confirms deletion."""
    now = datetime.now()
    empty_session = create_test_session(session_manager.output_dir, "empty_session", now, create_files=False)

    report = session_manager.cleanup(
        delete_empty=True,
        delete_incomplete=False,
        delete_stale_checkpoints=False,
        dry_run=False,
        interactive=True
    )

    assert report.deleted_empty == 1
    assert not empty_session.exists()  # Deleted after confirmation

@patch('builtins.input', return_value='n')
def test_cleanup_interactive_no(mock_input, session_manager, tmp_path):
    """Test interactive cleanup when user declines deletion."""
    now = datetime.now()
    empty_session = create_test_session(session_manager.output_dir, "empty_session", now, create_files=False)

    report = session_manager.cleanup(
        delete_empty=True,
        delete_incomplete=False,
        delete_stale_checkpoints=False,
        dry_run=False,
        interactive=True
    )

    assert report.deleted_empty == 0
    assert len(report.skipped_sessions) >= 1
    assert empty_session.exists()  # Not deleted when user declines
