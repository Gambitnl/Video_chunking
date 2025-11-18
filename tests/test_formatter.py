import pytest
from src.formatter import sanitize_filename, TranscriptFormatter
from src.constants import Classification, TranscriptFilter
from src.classifier import ClassificationResult


def test_sanitize_filename_replaces_invalid_characters():
    raw = "Session 10/15: The Return?"
    sanitized = sanitize_filename(raw)
    assert sanitized == "Session_10_15__The_Return"


class TestFormatFiltered:
    """Test suite for format_filtered method."""

    @pytest.fixture
    def formatter(self):
        return TranscriptFormatter()

    @pytest.fixture
    def sample_transcript(self):
        """Sample transcript with mixed IC/OOC content."""
        return [
            {
                "speaker": "DM",
                "text": "You enter the tavern.",
                "start_time": 0.0,
                "end_time": 2.0
            },
            {
                "speaker": "Player1",
                "text": "Wait, do I get advantage on perception?",
                "start_time": 2.5,
                "end_time": 4.0
            },
            {
                "speaker": "Player1",
                "text": "I look around for suspicious characters.",
                "start_time": 4.5,
                "end_time": 6.0
            },
            {
                "speaker": "DM",
                "text": "Let's take a break.",
                "start_time": 6.5,
                "end_time": 7.5
            }
        ]

    @pytest.fixture
    def sample_classifications(self):
        """Sample classifications matching the transcript."""
        return [
            ClassificationResult(
                segment_index=0,
                classification="IC",
                confidence=0.95,
                reasoning="DM narration",
                character="DM"
            ),
            ClassificationResult(
                segment_index=1,
                classification="OOC",
                confidence=0.90,
                reasoning="Rules question",
                character=None
            ),
            ClassificationResult(
                segment_index=2,
                classification="MIXED",  # Changed to MIXED to test backward compat
                confidence=0.92,
                reasoning="Character action with meta-talk",
                character="Thorin"
            ),
            ClassificationResult(
                segment_index=3,
                classification="OOC",
                confidence=0.88,
                reasoning="Break announcement",
                character=None
            )
        ]

    def test_filter_all(self, formatter, sample_transcript, sample_classifications):
        """Test that ALL filter returns complete transcript."""
        result = formatter.format_filtered(
            sample_transcript,
            sample_classifications,
            TranscriptFilter.ALL
        )
        assert "You enter the tavern" in result
        assert "Wait, do I get advantage" in result
        assert "I look around" in result
        assert "Let's take a break" in result
        assert "FILTERED VERSION" in result

    def test_filter_ic_only(self, formatter, sample_transcript, sample_classifications):
        """Test that IC filter excludes OOC but includes IC and MIXED (backward compat)."""
        result = formatter.format_filtered(
            sample_transcript,
            sample_classifications,
            TranscriptFilter.IN_CHARACTER_ONLY
        )
        # Should include IC segments
        assert "You enter the tavern" in result
        # Should include MIXED segments (backward compatibility!)
        assert "I look around" in result
        # Should exclude OOC segments
        assert "Wait, do I get advantage" not in result
        assert "Let's take a break" not in result
        assert "IN-CHARACTER ONLY" in result

    def test_filter_ooc_only(self, formatter, sample_transcript, sample_classifications):
        """Test that OOC filter excludes IC but includes OOC and MIXED (backward compat)."""
        result = formatter.format_filtered(
            sample_transcript,
            sample_classifications,
            TranscriptFilter.OUT_OF_CHARACTER_ONLY
        )
        # Should include OOC segments
        assert "Wait, do I get advantage" in result
        assert "Let's take a break" in result
        # Should include MIXED segments (backward compatibility!)
        assert "I look around" in result
        # Should exclude IC segments
        assert "You enter the tavern" not in result
        assert "OUT-OF-CHARACTER ONLY" in result

    def test_filter_mixed_only(self, formatter, sample_transcript, sample_classifications):
        """Test that MIXED filter returns only mixed segments."""
        result = formatter.format_filtered(
            sample_transcript,
            sample_classifications,
            TranscriptFilter.MIXED_ONLY
        )
        # Should include MIXED segment
        assert "I look around" in result
        # Should exclude IC and OOC segments
        assert "You enter the tavern" not in result
        assert "Wait, do I get advantage" not in result
        assert "Let's take a break" not in result
        assert "MIXED CONTENT ONLY" in result

    def test_filter_mixed_only_with_mixed_content(self, formatter):
        """Test MIXED filter with actual mixed content."""
        segments = [
            {"speaker": "Player1", "text": "I attack! Wait, do I add my strength?", "start_time": 0.0, "end_time": 2.0}
        ]
        classifications = [
            ClassificationResult(0, "MIXED", 0.85, "Both IC and OOC", "Thorin")
        ]
        result = formatter.format_filtered(segments, classifications, TranscriptFilter.MIXED_ONLY)
        assert "I attack" in result
        assert "MIXED CONTENT ONLY" in result

    def test_invalid_filter_type(self, formatter, sample_transcript, sample_classifications):
        """Test that invalid filter type raises ValueError."""
        # Passing a non-enum value should raise ValueError during validation
        with pytest.raises(ValueError, match="filter_type must be a TranscriptFilter enum member"):
            formatter.format_filtered(
                sample_transcript,
                sample_classifications,
                "invalid_filter"
            )

    def test_empty_transcript(self, formatter):
        """Test filtering with empty transcript."""
        result = formatter.format_filtered([], [], TranscriptFilter.ALL)
        assert isinstance(result, str)
        assert "=" * 80 in result  # Headers should still be present

    def test_speaker_profiles_mapping(self, formatter):
        """Test that speaker profiles are applied correctly."""
        segments = [
            {"speaker": "SPEAKER_00", "text": "Hello", "start_time": 0.0, "end_time": 1.0}
        ]
        classifications = [
            ClassificationResult(0, "OOC", 0.9, "Greeting", None)
        ]
        speaker_profiles = {"SPEAKER_00": "Alice"}

        result = formatter.format_filtered(
            segments,
            classifications,
            TranscriptFilter.ALL,
            speaker_profiles
        )
        assert "Alice" in result
        assert "SPEAKER_00" not in result

    def test_character_name_in_ic_only(self, formatter):
        """Test that character names are used in IC-only mode."""
        segments = [
            {"speaker": "Player1", "text": "I draw my sword", "start_time": 0.0, "end_time": 1.0}
        ]
        classifications = [
            ClassificationResult(0, "IC", 0.95, "Character action", "Aragorn")
        ]

        result = formatter.format_filtered(
            segments,
            classifications,
            TranscriptFilter.IN_CHARACTER_ONLY
        )
        assert "Aragorn" in result
        assert "Player1" not in result

    def test_backward_compatibility_ic_only(self, formatter, sample_transcript, sample_classifications):
        """Test that old format_ic_only still works and matches new method."""
        old_result = formatter.format_ic_only(
            sample_transcript,
            sample_classifications
        )
        new_result = formatter.format_filtered(
            sample_transcript,
            sample_classifications,
            TranscriptFilter.IN_CHARACTER_ONLY
        )
        assert old_result == new_result

    def test_backward_compatibility_ooc_only(self, formatter, sample_transcript, sample_classifications):
        """Test that old format_ooc_only still works and matches new method."""
        old_result = formatter.format_ooc_only(
            sample_transcript,
            sample_classifications
        )
        new_result = formatter.format_filtered(
            sample_transcript,
            sample_classifications,
            TranscriptFilter.OUT_OF_CHARACTER_ONLY
        )
        assert old_result == new_result

    def test_timestamps_formatted_correctly(self, formatter):
        """Test that timestamps are formatted in HH:MM:SS format."""
        segments = [
            {"speaker": "DM", "text": "Test", "start_time": 3661.5, "end_time": 3662.0}
        ]
        classifications = [
            ClassificationResult(0, "IC", 0.9, "Test", None)
        ]

        result = formatter.format_filtered(segments, classifications, TranscriptFilter.ALL)
        assert "[01:01:01]" in result

    def test_default_filter_is_all(self, formatter, sample_transcript, sample_classifications):
        """Test that default filter type is ALL."""
        result = formatter.format_filtered(
            sample_transcript,
            sample_classifications
        )
        # Should include both IC and OOC content
        assert "You enter the tavern" in result
        assert "Wait, do I get advantage" in result
