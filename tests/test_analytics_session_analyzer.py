"""Unit tests for session analyzer."""
import json
import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.analytics.session_analyzer import SessionAnalyzer
from src.analytics.data_models import SessionMetrics


class TestSessionAnalyzer:
    """Test SessionAnalyzer class."""

    @pytest.fixture
    def temp_project_dir(self, tmp_path):
        """Create a temporary project directory structure."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        return tmp_path

    @pytest.fixture
    def sample_session_data(self):
        """Create sample session data."""
        return {
            "metadata": {
                "session_id": "test_session",
                "timestamp": "2025-11-17T12:00:00"
            },
            "segments": [
                {
                    "start_time": 0.0,
                    "end_time": 10.0,
                    "text": "Hello world test message",
                    "speaker_id": "SPEAKER_00",
                    "speaker_name": "Thorin",
                    "classification": "IC",
                    "words": []
                },
                {
                    "start_time": 10.0,
                    "end_time": 20.0,
                    "text": "Another test message here",
                    "speaker_id": "SPEAKER_01",
                    "speaker_name": "Elara",
                    "classification": "OOC",
                    "words": []
                },
                {
                    "start_time": 20.0,
                    "end_time": 30.0,
                    "text": "Third message from Thorin",
                    "speaker_id": "SPEAKER_00",
                    "speaker_name": "Thorin",
                    "classification": "IC",
                    "words": []
                }
            ]
        }

    def test_analyzer_creation(self, temp_project_dir):
        """Test creating a SessionAnalyzer."""
        analyzer = SessionAnalyzer(temp_project_dir)

        assert analyzer.project_root == temp_project_dir
        assert analyzer.output_dir == temp_project_dir / "output"

    def test_list_available_sessions_empty(self, temp_project_dir):
        """Test listing sessions when none exist."""
        analyzer = SessionAnalyzer(temp_project_dir)

        sessions = analyzer.list_available_sessions()

        assert sessions == []

    def test_list_available_sessions_with_sessions(self, temp_project_dir):
        """Test listing sessions when they exist."""
        output_dir = temp_project_dir / "output"

        # Create session directories
        session1_dir = output_dir / "session1"
        session1_dir.mkdir()
        (session1_dir / "session1_data.json").write_text("{}")

        session2_dir = output_dir / "session2"
        session2_dir.mkdir()
        (session2_dir / "session2_data.json").write_text("{}")

        analyzer = SessionAnalyzer(temp_project_dir)
        sessions = analyzer.list_available_sessions()

        assert len(sessions) == 2
        assert "session1" in sessions
        assert "session2" in sessions

    def test_find_session_data_file_exists(self, temp_project_dir):
        """Test finding session data file that exists."""
        output_dir = temp_project_dir / "output"
        session_dir = output_dir / "session1"
        session_dir.mkdir()

        data_file = session_dir / "session1_data.json"
        data_file.write_text("{}")

        analyzer = SessionAnalyzer(temp_project_dir)
        found_file = analyzer.find_session_data_file("session1")

        assert found_file == data_file

    def test_find_session_data_file_not_exists(self, temp_project_dir):
        """Test finding session data file that doesn't exist."""
        analyzer = SessionAnalyzer(temp_project_dir)
        found_file = analyzer.find_session_data_file("nonexistent")

        assert found_file is None

    def test_extract_metrics_basic(self, sample_session_data):
        """Test extracting metrics from session data."""
        analyzer = SessionAnalyzer(Path("/tmp"))
        metrics = analyzer.extract_metrics(sample_session_data, "test_session")

        assert metrics.session_id == "test_session"
        assert metrics.session_name == "test_session"
        assert metrics.message_count == 3
        assert metrics.ic_message_count == 2
        assert metrics.ooc_message_count == 1
        assert metrics.duration == 30.0
        assert metrics.speaker_count == 2

    def test_extract_metrics_character_stats(self, sample_session_data):
        """Test that character stats are extracted correctly."""
        analyzer = SessionAnalyzer(Path("/tmp"))
        metrics = analyzer.extract_metrics(sample_session_data, "test_session")

        assert "Thorin" in metrics.character_stats
        assert "Elara" in metrics.character_stats

        thorin_stats = metrics.character_stats["Thorin"]
        assert thorin_stats.message_count == 2
        assert thorin_stats.ic_messages == 2
        assert thorin_stats.ooc_messages == 0

        elara_stats = metrics.character_stats["Elara"]
        assert elara_stats.message_count == 1
        assert elara_stats.ic_messages == 0
        assert elara_stats.ooc_messages == 1

    def test_extract_metrics_empty_segments(self):
        """Test extracting metrics with empty segments."""
        analyzer = SessionAnalyzer(Path("/tmp"))
        data = {"metadata": {}, "segments": []}

        metrics = analyzer.extract_metrics(data, "empty_session")

        assert metrics.message_count == 0
        assert metrics.duration == 0.0
        assert len(metrics.character_stats) == 0

    def test_load_session_success(self, temp_project_dir, sample_session_data):
        """Test loading a session successfully."""
        output_dir = temp_project_dir / "output"
        session_dir = output_dir / "session1"
        session_dir.mkdir()

        data_file = session_dir / "session1_data.json"
        data_file.write_text(json.dumps(sample_session_data))

        analyzer = SessionAnalyzer(temp_project_dir)
        metrics = analyzer.load_session("session1")

        assert metrics is not None
        assert metrics.session_id == "session1"
        assert metrics.message_count == 3

    def test_load_session_not_found(self, temp_project_dir):
        """Test loading a session that doesn't exist."""
        analyzer = SessionAnalyzer(temp_project_dir)
        metrics = analyzer.load_session("nonexistent")

        assert metrics is None

    def test_load_multiple_sessions(self, temp_project_dir, sample_session_data):
        """Test loading multiple sessions."""
        output_dir = temp_project_dir / "output"

        # Create two sessions
        for i in [1, 2]:
            session_dir = output_dir / f"session{i}"
            session_dir.mkdir()
            data_file = session_dir / f"session{i}_data.json"
            data_file.write_text(json.dumps(sample_session_data))

        analyzer = SessionAnalyzer(temp_project_dir)
        sessions = analyzer.load_multiple_sessions(["session1", "session2"])

        assert len(sessions) == 2

    def test_load_multiple_sessions_partial_failure(
        self, temp_project_dir, sample_session_data
    ):
        """Test loading multiple sessions when some fail."""
        output_dir = temp_project_dir / "output"

        # Create only one session
        session_dir = output_dir / "session1"
        session_dir.mkdir()
        data_file = session_dir / "session1_data.json"
        data_file.write_text(json.dumps(sample_session_data))

        analyzer = SessionAnalyzer(temp_project_dir)
        sessions = analyzer.load_multiple_sessions(
            ["session1", "nonexistent", "session2"]
        )

        # Should load only session1
        assert len(sessions) == 1
        assert sessions[0].session_id == "session1"

    def test_compare_sessions_single(self, sample_session_data):
        """Test comparing a single session."""
        analyzer = SessionAnalyzer(Path("/tmp"))
        metrics = analyzer.extract_metrics(sample_session_data, "test_session")

        comparison = analyzer.compare_sessions([metrics])

        assert comparison.session_count() == 1
        assert len(comparison.insights) > 0

    def test_compare_sessions_multiple(self):
        """Test comparing multiple sessions."""
        analyzer = SessionAnalyzer(Path("/tmp"))

        session1 = SessionMetrics(
            session_id="s1",
            session_name="S1",
            duration=3600.0,
            message_count=100,
            ic_message_count=70,
            ooc_message_count=30
        )
        session2 = SessionMetrics(
            session_id="s2",
            session_name="S2",
            duration=7200.0,
            message_count=150,
            ic_message_count=100,
            ooc_message_count=50
        )

        comparison = analyzer.compare_sessions([session1, session2])

        assert comparison.session_count() == 2
        assert "duration" in comparison.differences
        assert len(comparison.differences["duration"]) == 2

    def test_compare_sessions_empty(self):
        """Test comparing empty session list raises error."""
        analyzer = SessionAnalyzer(Path("/tmp"))

        with pytest.raises(ValueError):
            analyzer.compare_sessions([])

    def test_generate_insights_duration(self):
        """Test that duration insights are generated."""
        analyzer = SessionAnalyzer(Path("/tmp"))

        session1 = SessionMetrics(
            session_id="s1",
            session_name="S1",
            duration=1000.0
        )
        session2 = SessionMetrics(
            session_id="s2",
            session_name="S2",
            duration=5000.0  # Much longer
        )

        differences = {
            "duration": [1000.0, 5000.0],
            "message_count": [100.0, 150.0],
            "speaker_count": [4.0, 4.0],
            "ic_percentage": [70.0, 80.0],
            "ooc_percentage": [30.0, 20.0],
        }

        insights = analyzer.generate_insights([session1, session2], differences)

        # Should mention that S2 is notably long
        long_insights = [i for i in insights if "long" in i.lower()]
        assert len(long_insights) > 0

    def test_generate_insights_ic_ooc(self):
        """Test that IC/OOC insights are generated."""
        analyzer = SessionAnalyzer(Path("/tmp"))

        session1 = SessionMetrics(
            session_id="s1",
            session_name="S1",
            message_count=100,
            ic_message_count=50,
            ooc_message_count=50
        )
        session2 = SessionMetrics(
            session_id="s2",
            session_name="S2",
            message_count=100,
            ic_message_count=95,  # Very high IC
            ooc_message_count=5
        )

        differences = {
            "duration": [1000.0, 1000.0],
            "message_count": [100.0, 100.0],
            "speaker_count": [4.0, 4.0],
            "ic_percentage": [50.0, 95.0],
            "ooc_percentage": [50.0, 5.0],
        }

        insights = analyzer.generate_insights([session1, session2], differences)

        # Should mention high IC content
        ic_insights = [i for i in insights if "IC" in i and "high" in i.lower()]
        assert len(ic_insights) > 0

    def test_generate_timeline(self):
        """Test generating timeline data."""
        analyzer = SessionAnalyzer(Path("/tmp"))

        session1 = SessionMetrics(
            session_id="s1",
            session_name="S1",
            timestamp=datetime(2025, 1, 1),
            message_count=100,
            ic_message_count=70,
            ooc_message_count=30
        )
        session2 = SessionMetrics(
            session_id="s2",
            session_name="S2",
            timestamp=datetime(2025, 1, 2),
            message_count=100,
            ic_message_count=80,
            ooc_message_count=20
        )

        timeline = analyzer.generate_timeline([session1, session2])

        assert len(timeline.sessions) == 2
        assert len(timeline.ic_ooc_ratios) == 2

        # Should be sorted chronologically
        assert timeline.sessions[0].session_id == "s1"
        assert timeline.sessions[1].session_id == "s2"
