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
    return SessionManager(output_dir=output_dir, checkpoint_dir=checkpoint_dir)

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
    create_test_session(session_manager.output_dir, "session1", now)
    create_test_session(session_manager.output_dir, "orphaned_session", now - timedelta(days=1), create_files=False)
    incomplete_dir = create_test_session(session_manager.output_dir, "incomplete_session", now - timedelta(days=2))
    (incomplete_dir / "incomplete_session_full.txt").unlink()
    stale_checkpoint_dir = create_test_session(session_manager.output_dir, "stale_checkpoint_session", now - timedelta(days=3))
    checkpoint_dir = session_manager.checkpoint_dir / "stale_checkpoint_session"
    checkpoint_dir.mkdir()
    stale_checkpoint_file = checkpoint_dir / "checkpoint.json"
    stale_checkpoint_file.touch()
    stale_time = now - timedelta(days=8)
    import os
    os.utime(stale_checkpoint_file, (stale_time.timestamp(), stale_time.timestamp()))

    report = session_manager.audit_sessions()

    assert len(report.orphaned) == 1
    assert report.orphaned[0].session_id == "orphaned_session"
    assert len(report.incomplete) == 1
    assert report.incomplete[0].session_id == "incomplete_session"
    assert len(report.stale_checkpoints) == 1
    assert report.stale_checkpoints[0].session_id == "stale_checkpoint_session"

def test_cleanup_sessions_dry_run(session_manager, tmp_path):
    now = datetime.now()
    create_test_session(session_manager.output_dir, "orphaned_session", now, create_files=False)
    report = session_manager.audit_sessions()

    actions = session_manager.cleanup_sessions(report, "dry_run")

    assert len(actions["orphaned"]) == 1
    assert not any(actions["deleted_orphaned"])

def test_cleanup_sessions_force(session_manager, tmp_path):
    now = datetime.now()
    create_test_session(session_manager.output_dir, "orphaned_session", now, create_files=False)
    report = session_manager.audit_sessions()

    actions = session_manager.cleanup_sessions(report, "force")

    assert len(actions["deleted_orphaned"]) == 1
    assert not (tmp_path / "output" / f"{now.strftime('%Y%m%d%H%M%S')}_orphaned_session").exists()

@patch('click.confirm', return_value=True)
def test_cleanup_sessions_interactive_yes(mock_confirm, session_manager, tmp_path):
    now = datetime.now()
    create_test_session(session_manager.output_dir, "orphaned_session", now, create_files=False)
    report = session_manager.audit_sessions()

    actions = session_manager.cleanup_sessions(report, "interactive")

    assert len(actions["deleted_orphaned"]) == 1
    assert not (tmp_path / "output" / f"{now.strftime('%Y%m%d%H%M%S')}_orphaned_session").exists()

@patch('click.confirm', return_value=False)
def test_cleanup_sessions_interactive_no(mock_confirm, session_manager, tmp_path):
    now = datetime.now()
    create_test_session(session_manager.output_dir, "orphaned_session", now, create_files=False)
    report = session_manager.audit_sessions()

    actions = session_manager.cleanup_sessions(report, "interactive")

    assert len(actions["deleted_orphaned"]) == 0
    assert (tmp_path / "output" / f"{now.strftime('%Y%m%d%H%M%S')}_orphaned_session").exists()
