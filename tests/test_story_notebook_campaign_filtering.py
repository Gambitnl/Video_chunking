"""Tests for campaign filtering in StoryNotebookManager."""
import pytest
import json
from pathlib import Path

from src.story_notebook import StoryNotebookManager


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create temporary output directory with test sessions."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir


@pytest.fixture
def sample_sessions(temp_output_dir):
    """Create sample session files with different campaign assignments."""
    sessions_data = [
        # Campaign A sessions
        {
            "session_id": "session_a1",
            "campaign_id": "campaign_a",
            "campaign_name": "Campaign A",
        },
        {
            "session_id": "session_a2",
            "campaign_id": "campaign_a",
            "campaign_name": "Campaign A",
        },
        # Campaign B sessions
        {
            "session_id": "session_b1",
            "campaign_id": "campaign_b",
            "campaign_name": "Campaign B",
        },
        # Legacy session (no campaign_id)
        {
            "session_id": "legacy_session",
            "campaign_id": None,
        },
    ]

    for session_data in sessions_data:
        session_id = session_data["session_id"]
        session_dir = temp_output_dir / f"20251102_120000_{session_id}"
        session_dir.mkdir()

        data_file = session_dir / f"{session_id}_data.json"
        file_content = {
            "metadata": session_data,
            "segments": [],
        }
        data_file.write_text(json.dumps(file_content, indent=2), encoding="utf-8")

    return temp_output_dir


def test_list_sessions_no_filter(sample_sessions):
    """Test listing all sessions without campaign filter."""
    manager = StoryNotebookManager(output_dir=sample_sessions)
    sessions = manager.list_sessions(limit=None, campaign_id=None)

    assert len(sessions) == 4
    assert "session_a1" in sessions
    assert "session_a2" in sessions
    assert "session_b1" in sessions
    assert "legacy_session" in sessions


def test_list_sessions_filter_by_campaign(sample_sessions):
    """Test filtering sessions by campaign_id (includes unassigned by default)."""
    manager = StoryNotebookManager(output_dir=sample_sessions)

    # Filter for campaign_a (includes unassigned by default)
    sessions_a = manager.list_sessions(limit=None, campaign_id="campaign_a")
    assert len(sessions_a) == 3  # 2 campaign_a + 1 legacy
    assert "session_a1" in sessions_a
    assert "session_a2" in sessions_a
    assert "legacy_session" in sessions_a  # Included by default
    assert "session_b1" not in sessions_a

    # Filter for campaign_b (includes unassigned by default)
    sessions_b = manager.list_sessions(limit=None, campaign_id="campaign_b")
    assert len(sessions_b) == 2  # 1 campaign_b + 1 legacy
    assert "session_b1" in sessions_b
    assert "legacy_session" in sessions_b  # Included by default
    assert "session_a1" not in sessions_b


def test_list_sessions_include_unassigned(sample_sessions):
    """Test including unassigned sessions when filtering by campaign."""
    manager = StoryNotebookManager(output_dir=sample_sessions)

    # With include_unassigned=True (default)
    sessions_with_unassigned = manager.list_sessions(
        limit=None,
        campaign_id="campaign_a",
        include_unassigned=True
    )
    assert len(sessions_with_unassigned) == 3  # 2 campaign_a + 1 legacy
    assert "session_a1" in sessions_with_unassigned
    assert "session_a2" in sessions_with_unassigned
    assert "legacy_session" in sessions_with_unassigned
    assert "session_b1" not in sessions_with_unassigned


def test_list_sessions_exclude_unassigned(sample_sessions):
    """Test excluding unassigned sessions when filtering by campaign."""
    manager = StoryNotebookManager(output_dir=sample_sessions)

    # With include_unassigned=False
    sessions_without_unassigned = manager.list_sessions(
        limit=None,
        campaign_id="campaign_a",
        include_unassigned=False
    )
    assert len(sessions_without_unassigned) == 2  # Only campaign_a sessions
    assert "session_a1" in sessions_without_unassigned
    assert "session_a2" in sessions_without_unassigned
    assert "legacy_session" not in sessions_without_unassigned
    assert "session_b1" not in sessions_without_unassigned


def test_list_sessions_with_limit(sample_sessions):
    """Test that limit parameter works with campaign filtering."""
    manager = StoryNotebookManager(output_dir=sample_sessions)

    # Limit to 1 session from campaign_a (may include unassigned)
    sessions = manager.list_sessions(
        limit=1,
        campaign_id="campaign_a"
    )
    assert len(sessions) == 1
    # Could be campaign_a session or legacy (unassigned) session
    assert sessions[0] in ["session_a1", "session_a2", "legacy_session"]


def test_list_sessions_nonexistent_campaign(sample_sessions):
    """Test filtering for a campaign that has no sessions (includes unassigned)."""
    manager = StoryNotebookManager(output_dir=sample_sessions)

    # Filter for nonexistent campaign (still includes unassigned by default)
    sessions = manager.list_sessions(
        limit=None,
        campaign_id="nonexistent_campaign"
    )
    assert len(sessions) == 1  # Only legacy (unassigned) session
    assert "legacy_session" in sessions

    # Filter for nonexistent campaign excluding unassigned
    sessions_strict = manager.list_sessions(
        limit=None,
        campaign_id="nonexistent_campaign",
        include_unassigned=False
    )
    assert len(sessions_strict) == 0  # No sessions at all


def test_build_session_info_with_campaign(temp_output_dir):
    """Test that build_session_info displays campaign information."""
    from src.story_notebook import StorySessionData

    # Session with full campaign info
    session = StorySessionData(
        session_id="test_session",
        json_path=temp_output_dir / "test_session_data.json",
        metadata={
            "campaign_id": "test_campaign",
            "campaign_name": "Test Campaign",
            "statistics": {
                "total_duration_seconds": 300,
                "ic_segments": 10,
                "ooc_segments": 2,
                "ic_percentage": 83.3,
            },
        },
        segments=[],
    )

    manager = StoryNotebookManager(output_dir=temp_output_dir)
    info = manager.build_session_info(session)

    assert "Campaign" in info
    assert "Test Campaign" in info
    assert "test_campaign" in info


def test_build_session_info_without_campaign(temp_output_dir):
    """Test that build_session_info handles sessions without campaign info."""
    from src.story_notebook import StorySessionData

    # Legacy session without campaign
    session = StorySessionData(
        session_id="legacy_session",
        json_path=temp_output_dir / "legacy_session_data.json",
        metadata={
            "statistics": {
                "total_duration_seconds": 300,
                "ic_segments": 10,
                "ooc_segments": 2,
                "ic_percentage": 83.3,
            },
        },
        segments=[],
    )

    manager = StoryNotebookManager(output_dir=temp_output_dir)
    info = manager.build_session_info(session)

    assert "Unassigned" in info
    assert "migration tools" in info


def test_list_sessions_empty_directory(temp_output_dir):
    """Test listing sessions from an empty directory."""
    manager = StoryNotebookManager(output_dir=temp_output_dir)
    sessions = manager.list_sessions(limit=None, campaign_id=None)
    assert sessions == []


def test_list_sessions_corrupted_metadata(temp_output_dir):
    """Test handling of sessions with corrupted metadata when filtering."""
    # Create a session with corrupted JSON
    session_dir = temp_output_dir / "20251102_120000_corrupted"
    session_dir.mkdir()
    data_file = session_dir / "corrupted_data.json"
    data_file.write_text("{ invalid json }", encoding="utf-8")

    manager = StoryNotebookManager(output_dir=temp_output_dir)

    # Should not crash, should skip corrupted session when filtering
    sessions = manager.list_sessions(
        limit=None,
        campaign_id="campaign_a",
        include_unassigned=False
    )
    assert "corrupted" not in sessions

    # Corrupted session should be excluded when include_unassigned=False
    sessions_with_unassigned = manager.list_sessions(
        limit=None,
        campaign_id="campaign_a",
        include_unassigned=True
    )
    # Corrupted session may appear if include_unassigned=True since
    # exception handling allows it through, but it shouldn't crash
    assert isinstance(sessions_with_unassigned, list)
