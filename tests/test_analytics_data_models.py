"""Unit tests for analytics data models."""
import pytest
from datetime import datetime

from src.analytics.data_models import (
    CharacterStats,
    SessionMetrics,
    ComparisonResult,
    TimelineData
)


class TestCharacterStats:
    """Test CharacterStats dataclass."""

    def test_character_stats_creation(self):
        """Test creating a CharacterStats object."""
        stats = CharacterStats(
            character_name="Thorin",
            message_count=10,
            word_count=500,
            speaking_duration=300.0
        )

        assert stats.character_name == "Thorin"
        assert stats.message_count == 10
        assert stats.word_count == 500
        assert stats.speaking_duration == 300.0

    def test_character_stats_avg_message_length_calculation(self):
        """Test automatic calculation of average message length."""
        stats = CharacterStats(
            character_name="Thorin",
            message_count=10,
            word_count=500
        )

        # Should auto-calculate in __post_init__
        assert stats.avg_message_length == 50.0

    def test_character_stats_ic_percentage(self):
        """Test IC percentage calculation."""
        stats = CharacterStats(
            character_name="Thorin",
            message_count=10,
            ic_messages=7,
            ooc_messages=3
        )

        assert stats.ic_percentage() == 70.0

    def test_character_stats_ooc_percentage(self):
        """Test OOC percentage calculation."""
        stats = CharacterStats(
            character_name="Thorin",
            message_count=10,
            ic_messages=7,
            ooc_messages=3
        )

        assert stats.ooc_percentage() == 30.0

    def test_character_stats_zero_messages(self):
        """Test percentages with zero messages."""
        stats = CharacterStats(
            character_name="Thorin",
            message_count=0
        )

        assert stats.ic_percentage() == 0.0
        assert stats.ooc_percentage() == 0.0
        assert stats.avg_message_length == 0.0


class TestSessionMetrics:
    """Test SessionMetrics dataclass."""

    def test_session_metrics_creation(self):
        """Test creating a SessionMetrics object."""
        metrics = SessionMetrics(
            session_id="session1",
            session_name="Session 1",
            duration=3600.0,
            message_count=100,
            ic_message_count=70,
            ooc_message_count=30
        )

        assert metrics.session_id == "session1"
        assert metrics.duration == 3600.0
        assert metrics.message_count == 100

    def test_session_metrics_validation_negative_duration(self):
        """Test that negative duration raises assertion error."""
        with pytest.raises(AssertionError):
            SessionMetrics(
                session_id="session1",
                session_name="Session 1",
                duration=-100.0
            )

    def test_session_metrics_validation_ic_ooc_sum(self):
        """Test that IC + OOC must equal total messages."""
        with pytest.raises(AssertionError):
            SessionMetrics(
                session_id="session1",
                session_name="Session 1",
                message_count=100,
                ic_message_count=60,
                ooc_message_count=30  # Only adds to 90, not 100
            )

    def test_session_metrics_ic_percentage(self):
        """Test IC percentage calculation."""
        metrics = SessionMetrics(
            session_id="session1",
            session_name="Session 1",
            message_count=100,
            ic_message_count=75,
            ooc_message_count=25
        )

        assert metrics.ic_percentage() == 75.0

    def test_session_metrics_duration_formatted(self):
        """Test duration formatting."""
        metrics = SessionMetrics(
            session_id="session1",
            session_name="Session 1",
            duration=3665.0  # 1 hour, 1 minute, 5 seconds
        )

        assert metrics.duration_formatted() == "01:01:05"

    def test_session_metrics_get_top_speakers(self):
        """Test getting top speakers by speaking time."""
        char1 = CharacterStats(character_name="Thorin", speaking_duration=500.0)
        char2 = CharacterStats(character_name="Elara", speaking_duration=300.0)
        char3 = CharacterStats(character_name="Zyx", speaking_duration=400.0)

        metrics = SessionMetrics(
            session_id="session1",
            session_name="Session 1",
            character_stats={
                "Thorin": char1,
                "Elara": char2,
                "Zyx": char3
            }
        )

        top_speakers = metrics.get_top_speakers(limit=2)

        assert len(top_speakers) == 2
        assert top_speakers[0][0] == "Thorin"
        assert top_speakers[1][0] == "Zyx"


class TestComparisonResult:
    """Test ComparisonResult dataclass."""

    def test_comparison_result_creation(self):
        """Test creating a ComparisonResult."""
        session1 = SessionMetrics(
            session_id="s1",
            session_name="Session 1",
            duration=3600.0
        )

        comparison = ComparisonResult(
            sessions=[session1],
            insights=["Test insight"]
        )

        assert len(comparison.sessions) == 1
        assert len(comparison.insights) == 1

    def test_comparison_result_validation_empty_sessions(self):
        """Test that empty sessions list raises assertion error."""
        with pytest.raises(AssertionError):
            ComparisonResult(sessions=[])

    def test_comparison_result_session_count(self):
        """Test session_count method."""
        session1 = SessionMetrics(session_id="s1", session_name="S1")
        session2 = SessionMetrics(session_id="s2", session_name="S2")

        comparison = ComparisonResult(sessions=[session1, session2])

        assert comparison.session_count() == 2

    def test_comparison_result_average_duration(self):
        """Test average_duration calculation."""
        session1 = SessionMetrics(
            session_id="s1",
            session_name="S1",
            duration=3600.0
        )
        session2 = SessionMetrics(
            session_id="s2",
            session_name="S2",
            duration=7200.0
        )

        comparison = ComparisonResult(sessions=[session1, session2])

        assert comparison.average_duration() == 5400.0

    def test_comparison_result_get_longest_session(self):
        """Test getting longest session."""
        session1 = SessionMetrics(
            session_id="s1",
            session_name="S1",
            duration=3600.0
        )
        session2 = SessionMetrics(
            session_id="s2",
            session_name="S2",
            duration=7200.0
        )

        comparison = ComparisonResult(sessions=[session1, session2])

        longest = comparison.get_longest_session()

        assert longest.session_id == "s2"
        assert longest.duration == 7200.0

    def test_comparison_result_get_most_ic_session(self):
        """Test getting session with highest IC percentage."""
        session1 = SessionMetrics(
            session_id="s1",
            session_name="S1",
            message_count=100,
            ic_message_count=60,
            ooc_message_count=40
        )
        session2 = SessionMetrics(
            session_id="s2",
            session_name="S2",
            message_count=100,
            ic_message_count=80,
            ooc_message_count=20
        )

        comparison = ComparisonResult(sessions=[session1, session2])

        most_ic = comparison.get_most_ic_session()

        assert most_ic.session_id == "s2"
        assert most_ic.ic_percentage() == 80.0


class TestTimelineData:
    """Test TimelineData dataclass."""

    def test_timeline_data_creation(self):
        """Test creating a TimelineData object."""
        session1 = SessionMetrics(
            session_id="s1",
            session_name="S1",
            timestamp=datetime(2025, 1, 1)
        )
        session2 = SessionMetrics(
            session_id="s2",
            session_name="S2",
            timestamp=datetime(2025, 1, 2)
        )

        timeline = TimelineData(sessions=[session1, session2])

        assert len(timeline.sessions) == 2

    def test_timeline_data_chronological_sorting(self):
        """Test that sessions are sorted chronologically."""
        session1 = SessionMetrics(
            session_id="s1",
            session_name="S1",
            timestamp=datetime(2025, 1, 2)
        )
        session2 = SessionMetrics(
            session_id="s2",
            session_name="S2",
            timestamp=datetime(2025, 1, 1)
        )

        timeline = TimelineData(sessions=[session1, session2])

        # Should be sorted by timestamp in __post_init__
        assert timeline.sessions[0].session_id == "s2"
        assert timeline.sessions[1].session_id == "s1"

    def test_timeline_data_ic_ooc_ratios_population(self):
        """Test that IC/OOC ratios are populated."""
        session1 = SessionMetrics(
            session_id="s1",
            session_name="S1",
            message_count=100,
            ic_message_count=70,
            ooc_message_count=30
        )

        timeline = TimelineData(sessions=[session1])

        assert len(timeline.ic_ooc_ratios) == 1
        assert timeline.ic_ooc_ratios[0] == ("s1", 70.0, 30.0)

    def test_timeline_data_get_ic_trend(self):
        """Test getting IC percentage trend."""
        session1 = SessionMetrics(
            session_id="s1",
            session_name="S1",
            message_count=100,
            ic_message_count=60,
            ooc_message_count=40
        )
        session2 = SessionMetrics(
            session_id="s2",
            session_name="S2",
            message_count=100,
            ic_message_count=80,
            ooc_message_count=20
        )

        timeline = TimelineData(sessions=[session1, session2])

        ic_trend = timeline.get_ic_trend()

        assert ic_trend == [60.0, 80.0]

    def test_timeline_data_get_character_timeline(self):
        """Test getting character timeline."""
        char1 = CharacterStats(character_name="Thorin", speaking_duration=300.0)
        char2 = CharacterStats(character_name="Thorin", speaking_duration=400.0)

        session1 = SessionMetrics(
            session_id="s1",
            session_name="S1",
            character_stats={"Thorin": char1}
        )
        session2 = SessionMetrics(
            session_id="s2",
            session_name="S2",
            character_stats={"Thorin": char2}
        )

        timeline = TimelineData(sessions=[session1, session2])

        thorin_timeline = timeline.get_character_timeline("Thorin")

        assert len(thorin_timeline) == 2
        assert thorin_timeline[0] == ("s1", 300.0)
        assert thorin_timeline[1] == ("s2", 400.0)
