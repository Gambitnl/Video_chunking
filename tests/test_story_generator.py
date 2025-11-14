"""
Comprehensive test suite for story_generator.py

Tests cover:
- Narrator perspective generation
- Character POV generation
- Google Docs integration (notebook_context)
- Error handling scenarios
- Prompt building
- Log suppression
- Empty/invalid inputs
"""
import pytest
import json
import logging
import sys
from unittest.mock import Mock, patch, MagicMock
from io import StringIO

from src.story_generator import StoryGenerator
from src.config import Config


# ============================================================================
# Mock LLM Client
# ============================================================================

class MockOllamaClient:
    """Mock Ollama client for testing."""

    def __init__(self, response_text="Generated story text", should_fail=False):
        self.response_text = response_text
        self.should_fail = should_fail
        self.calls = []

    def generate(self, model, prompt, options):
        """Mock generate method."""
        self.calls.append({
            'model': model,
            'prompt': prompt,
            'options': options
        })

        if self.should_fail:
            raise Exception("LLM generation failed")

        return {"response": self.response_text}


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_segments():
    """Sample transcript segments for testing."""
    return [
        {
            "start_time": 0.0,
            "end_time": 5.0,
            "text": "I ready my sword and approach the dragon.",
            "speaker_name": "Aragorn",
            "character": "Aragorn",
            "classification": "IC"
        },
        {
            "start_time": 5.5,
            "end_time": 10.0,
            "text": "The dragon roars and breathes fire!",
            "speaker_name": "DM",
            "character": "DM",
            "classification": "IC"
        },
        {
            "start_time": 10.5,
            "end_time": 15.0,
            "text": "I cast Shield to protect myself.",
            "speaker_name": "Gandalf",
            "character": "Gandalf",
            "classification": "IC"
        },
        {
            "start_time": 15.5,
            "end_time": 20.0,
            "text": "Should we order pizza?",
            "speaker_name": "Player1",
            "character": "Player1",
            "classification": "OOC"
        }
    ]


@pytest.fixture
def character_names():
    """Sample character names."""
    return ["Aragorn", "Gandalf", "Legolas"]


@pytest.fixture
def notebook_context():
    """Sample Google Docs notebook context."""
    return """
    Campaign: The Quest for the Ring
    Session 5 Notes:
    - Party encountered ancient dragon in mountain cave
    - Dragon guards magical artifact
    - Previous session: Party scaled mountain, fought goblins
    """


# ============================================================================
# Initialization Tests
# ============================================================================

class TestStoryGeneratorInit:
    """Test StoryGenerator initialization."""

    def test_init_creates_ollama_client(self):
        """Test that initialization creates Ollama client."""
        generator = StoryGenerator()
        assert generator.client is not None

    def test_init_uses_config_url(self, monkeypatch):
        """Test that initialization uses configured Ollama URL."""
        test_url = "http://test-ollama:11434"
        monkeypatch.setattr(Config, "OLLAMA_BASE_URL", test_url)

        with patch('ollama.Client') as mock_client:
            generator = StoryGenerator()
            mock_client.assert_called_with(host=test_url)


# ============================================================================
# Log Suppression Tests
# ============================================================================

class TestLogSuppression:
    """Test log suppression context manager."""

    def test_suppress_llm_logs_context_manager(self, capsys, caplog):
        """Test that suppress_llm_logs suppresses stdout/stderr and lower-level logs."""
        generator = StoryGenerator()

        with caplog.at_level(logging.DEBUG, logger="ollama"):
            with generator.suppress_llm_logs():
                # stdout and stderr should be suppressed
                print("This should not appear in stdout")
                sys.stderr.write("This should not appear in stderr")
                # Lower-level logs should be suppressed
                logging.getLogger("ollama").info("This info should not appear")
                logging.getLogger("ollama").warning("This warning should not appear")
                # Note: CRITICAL logs are NOT suppressed by the current implementation
                # (setLevel(CRITICAL) allows CRITICAL messages through)

        captured = capsys.readouterr()
        assert captured.out == "", "stdout should be empty after suppression"
        assert captured.err == "", "stderr should be empty after suppression"
        assert "This info should not appear" not in caplog.text, "Info logs should be suppressed"
        assert "This warning should not appear" not in caplog.text, "Warning logs should be suppressed"

    def test_suppress_llm_logs_restores_streams(self):
        """Test that suppress_llm_logs restores stdout/stderr after context."""
        generator = StoryGenerator()

        original_stdout = sys.stdout
        original_stderr = sys.stderr

        with generator.suppress_llm_logs():
            pass

        # Streams should be restored
        assert sys.stdout == original_stdout
        assert sys.stderr == original_stderr

    def test_suppress_llm_logs_restores_on_exception(self):
        """Test that suppress_llm_logs restores streams even on exception."""
        generator = StoryGenerator()

        original_stdout = sys.stdout
        original_stderr = sys.stderr

        try:
            with generator.suppress_llm_logs():
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Streams should be restored
        assert sys.stdout == original_stdout
        assert sys.stderr == original_stderr


# ============================================================================
# Prompt Building Tests
# ============================================================================

class TestPromptBuilding:
    """Test prompt construction for different perspectives."""

    def test_build_prompt_narrator_perspective(self, sample_segments, character_names, notebook_context):
        """Test prompt building for narrator perspective."""
        generator = StoryGenerator()

        prompt = generator._build_prompt(
            perspective_name="Narrator",
            segments=sample_segments,
            character_names=character_names,
            narrator=True,
            notebook_context=notebook_context
        )

        # Check narrator-specific content
        assert "omniscient narrator" in prompt.lower()
        assert "balanced overview" in prompt.lower()
        assert "neutral and descriptive" in prompt.lower()
        assert "Campaign notebook excerpt:" in prompt
        assert "Campaign: The Quest for the Ring" in prompt

    def test_build_prompt_character_pov(self, sample_segments, character_names, notebook_context):
        """Test prompt building for character POV."""
        generator = StoryGenerator()

        prompt = generator._build_prompt(
            perspective_name="Aragorn",
            segments=sample_segments,
            character_names=character_names,
            narrator=False,
            notebook_context=notebook_context
        )

        # Check character-specific content
        assert "You are the character Aragorn" in prompt
        assert "main protagonists" in prompt
        assert "character's voice" in prompt.lower()
        assert "emotions" in prompt.lower()

    def test_build_prompt_filters_ic_only(self, character_names, notebook_context):
        """Test that prompt only includes IC (in-character) segments."""
        generator = StoryGenerator()

        segments = [
            {"text": "IC speech", "classification": "IC", "speaker_name": "Test", "start_time": 0.0},
            {"text": "OOC speech", "classification": "OOC", "speaker_name": "Test", "start_time": 5.0}
        ]

        prompt = generator._build_prompt(
            perspective_name="Narrator",
            segments=segments,
            character_names=character_names,
            narrator=True,
            notebook_context=notebook_context
        )

        # IC speech should be included
        assert "IC speech" in prompt
        # OOC speech should NOT be included
        assert "OOC speech" not in prompt

    def test_build_prompt_includes_timestamps(self, sample_segments, character_names, notebook_context):
        """Test that prompt includes segment timestamps."""
        generator = StoryGenerator()

        prompt = generator._build_prompt(
            perspective_name="Narrator",
            segments=sample_segments,
            character_names=character_names,
            narrator=True,
            notebook_context=notebook_context
        )

        # Check for timestamp format [XX.XX]
        assert "[000.00]" in prompt or "[00.00]" in prompt

    def test_build_prompt_limits_segments(self, character_names, notebook_context):
        """Test that prompt limits segments to 60."""
        generator = StoryGenerator()

        # Create 100 segments
        many_segments = [
            {
                "text": f"Segment {i}",
                "classification": "IC",
                "speaker_name": "Test",
                "start_time": float(i)
            }
            for i in range(100)
        ]

        prompt = generator._build_prompt(
            perspective_name="Narrator",
            segments=many_segments,
            character_names=character_names,
            narrator=True,
            notebook_context=notebook_context
        )

        # Should only include first 60 segments
        assert "Segment 0" in prompt
        assert "Segment 59" in prompt
        # Segment 60+ should not be included
        assert "Segment 60" not in prompt

    def test_build_prompt_handles_empty_notebook_context(self, sample_segments, character_names):
        """Test prompt building with empty notebook context."""
        generator = StoryGenerator()

        prompt = generator._build_prompt(
            perspective_name="Narrator",
            segments=sample_segments,
            character_names=character_names,
            narrator=True,
            notebook_context=""
        )

        assert "no additional notes provided" in prompt.lower()

    def test_build_prompt_handles_none_notebook_context(self, sample_segments, character_names):
        """Test prompt building with None notebook context."""
        generator = StoryGenerator()

        prompt = generator._build_prompt(
            perspective_name="Narrator",
            segments=sample_segments,
            character_names=character_names,
            narrator=True,
            notebook_context=None
        )

        assert "no additional notes provided" in prompt.lower()

    def test_build_prompt_handles_empty_segments(self, character_names, notebook_context):
        """Test prompt building with empty segments list."""
        generator = StoryGenerator()

        prompt = generator._build_prompt(
            perspective_name="Narrator",
            segments=[],
            character_names=character_names,
            narrator=True,
            notebook_context=notebook_context
        )

        assert "Transcript excerpts unavailable" in prompt

    def test_build_prompt_handles_segments_with_missing_fields(self, character_names, notebook_context):
        """Test prompt building with segments missing optional fields."""
        generator = StoryGenerator()

        segments = [
            {
                "text": "Valid segment",
                "classification": "IC",
                "start_time": 0.0
                # Missing speaker_name and character
            }
        ]

        prompt = generator._build_prompt(
            perspective_name="Narrator",
            segments=segments,
            character_names=character_names,
            narrator=True,
            notebook_context=notebook_context
        )

        # Should not crash, should include the text
        assert "Valid segment" in prompt

    def test_build_prompt_truncates_long_notebook_context(self, sample_segments, character_names):
        """Test that long notebook context is truncated to 3000 chars."""
        generator = StoryGenerator()

        # Create very long notebook context (5000 chars)
        long_context = "A" * 5000

        prompt = generator._build_prompt(
            perspective_name="Narrator",
            segments=sample_segments,
            character_names=character_names,
            narrator=True,
            notebook_context=long_context
        )

        # Check that the long context was truncated to exactly 3000 characters.
        assert ("A" * 3000) in prompt
        assert ("A" * 3001) not in prompt


# ============================================================================
# Story Generation Tests
# ============================================================================

class TestStoryGeneration:
    """Test actual story generation with mocked LLM."""

    def test_generate_story_calls_ollama(self):
        """Test that _generate_story calls Ollama client."""
        generator = StoryGenerator()
        mock_client = MockOllamaClient(response_text="Test story")
        generator.client = mock_client

        result = generator._generate_story("Test prompt", temperature=0.5)

        assert len(mock_client.calls) == 1
        assert mock_client.calls[0]['model'] == Config.OLLAMA_MODEL
        assert mock_client.calls[0]['prompt'] == "Test prompt"
        assert mock_client.calls[0]['options']['temperature'] == 0.5
        assert result == "Test story"

    def test_generate_story_uses_custom_temperature(self):
        """Test that _generate_story uses custom temperature."""
        generator = StoryGenerator()
        mock_client = MockOllamaClient()
        generator.client = mock_client

        generator._generate_story("Test", temperature=0.9)

        assert mock_client.calls[0]['options']['temperature'] == 0.9

    def test_generate_story_sets_num_predict(self):
        """Test that _generate_story sets num_predict option."""
        generator = StoryGenerator()
        mock_client = MockOllamaClient()
        generator.client = mock_client

        generator._generate_story("Test")

        assert mock_client.calls[0]['options']['num_predict'] == 800

    def test_generate_story_handles_empty_response(self):
        """Test handling of empty LLM response."""
        generator = StoryGenerator()
        mock_client = MockOllamaClient()
        generator.client = mock_client

        # Mock response with missing 'response' key
        mock_client.generate = lambda **kwargs: {}

        result = generator._generate_story("Test")

        assert result == "(LLM returned no text)"

    def test_generate_story_handles_llm_exception(self):
        """Test handling of LLM generation exception."""
        generator = StoryGenerator()
        mock_client = MockOllamaClient(should_fail=True)
        generator.client = mock_client

        # Should raise the exception
        with pytest.raises(Exception, match="LLM generation failed"):
            generator._generate_story("Test")


# ============================================================================
# Narrator Summary Tests
# ============================================================================

class TestNarratorSummary:
    """Test narrator perspective story generation."""

    def test_generate_narrator_summary_basic(self, sample_segments, character_names, notebook_context):
        """Test basic narrator summary generation."""
        generator = StoryGenerator()
        mock_client = MockOllamaClient(response_text="Narrator summary of the dragon encounter.")
        generator.client = mock_client

        result = generator.generate_narrator_summary(
            segments=sample_segments,
            character_names=character_names,
            notebook_context=notebook_context,
            temperature=0.5
        )

        assert result == "Narrator summary of the dragon encounter."
        assert len(mock_client.calls) == 1

    def test_generate_narrator_summary_builds_correct_prompt(self, sample_segments, character_names, notebook_context):
        """Test that narrator summary builds narrator-style prompt."""
        generator = StoryGenerator()
        mock_client = MockOllamaClient()
        generator.client = mock_client

        generator.generate_narrator_summary(
            segments=sample_segments,
            character_names=character_names,
            notebook_context=notebook_context
        )

        prompt = mock_client.calls[0]['prompt']
        assert "omniscient narrator" in prompt.lower()

    def test_generate_narrator_summary_with_empty_segments(self, character_names, notebook_context):
        """Test narrator summary with empty segments."""
        generator = StoryGenerator()
        mock_client = MockOllamaClient(response_text="No events to summarize.")
        generator.client = mock_client

        result = generator.generate_narrator_summary(
            segments=[],
            character_names=character_names,
            notebook_context=notebook_context
        )

        assert result == "No events to summarize."

    def test_generate_narrator_summary_custom_temperature(self, sample_segments, character_names, notebook_context):
        """Test narrator summary with custom temperature."""
        generator = StoryGenerator()
        mock_client = MockOllamaClient()
        generator.client = mock_client

        generator.generate_narrator_summary(
            segments=sample_segments,
            character_names=character_names,
            notebook_context=notebook_context,
            temperature=0.9
        )

        assert mock_client.calls[0]['options']['temperature'] == 0.9


# ============================================================================
# Character POV Tests
# ============================================================================

class TestCharacterPOV:
    """Test character POV story generation."""

    def test_generate_character_pov_basic(self, sample_segments, character_names, notebook_context):
        """Test basic character POV generation."""
        generator = StoryGenerator()
        mock_client = MockOllamaClient(response_text="I faced the dragon with courage.")
        generator.client = mock_client

        result = generator.generate_character_pov(
            segments=sample_segments,
            character_name="Aragorn",
            character_names=character_names,
            notebook_context=notebook_context,
            temperature=0.5
        )

        assert result == "I faced the dragon with courage."
        assert len(mock_client.calls) == 1

    def test_generate_character_pov_builds_correct_prompt(self, sample_segments, character_names, notebook_context):
        """Test that character POV builds character-style prompt."""
        generator = StoryGenerator()
        mock_client = MockOllamaClient()
        generator.client = mock_client

        generator.generate_character_pov(
            segments=sample_segments,
            character_name="Aragorn",
            character_names=character_names,
            notebook_context=notebook_context
        )

        prompt = mock_client.calls[0]['prompt']
        assert "You are the character Aragorn" in prompt
        assert "main protagonists" in prompt

    def test_generate_character_pov_different_character(self, sample_segments, character_names, notebook_context):
        """Test character POV for different character."""
        generator = StoryGenerator()
        mock_client = MockOllamaClient()
        generator.client = mock_client

        generator.generate_character_pov(
            segments=sample_segments,
            character_name="Gandalf",
            character_names=character_names,
            notebook_context=notebook_context
        )

        prompt = mock_client.calls[0]['prompt']
        assert "You are the character Gandalf" in prompt

    def test_generate_character_pov_with_empty_segments(self, character_names, notebook_context):
        """Test character POV with empty segments."""
        generator = StoryGenerator()
        mock_client = MockOllamaClient(response_text="Nothing happened today.")
        generator.client = mock_client

        result = generator.generate_character_pov(
            segments=[],
            character_name="Aragorn",
            character_names=character_names,
            notebook_context=notebook_context
        )

        assert result == "Nothing happened today."

    def test_generate_character_pov_custom_temperature(self, sample_segments, character_names, notebook_context):
        """Test character POV with custom temperature."""
        generator = StoryGenerator()
        mock_client = MockOllamaClient()
        generator.client = mock_client

        generator.generate_character_pov(
            segments=sample_segments,
            character_name="Aragorn",
            character_names=character_names,
            notebook_context=notebook_context,
            temperature=0.8
        )

        assert mock_client.calls[0]['options']['temperature'] == 0.8


# ============================================================================
# Google Docs Integration Tests
# ============================================================================

class TestGoogleDocsIntegration:
    """Test Google Docs notebook context integration."""

    def test_notebook_context_included_in_prompt(self, sample_segments, character_names):
        """Test that notebook context is included in generated prompt."""
        generator = StoryGenerator()

        notebook_context = "Important campaign notes about the dragon."

        prompt = generator._build_prompt(
            perspective_name="Narrator",
            segments=sample_segments,
            character_names=character_names,
            narrator=True,
            notebook_context=notebook_context
        )

        assert "Important campaign notes about the dragon" in prompt

    def test_missing_notebook_context_handled(self, sample_segments, character_names):
        """Test that missing notebook context is handled gracefully."""
        generator = StoryGenerator()
        mock_client = MockOllamaClient()
        generator.client = mock_client

        # Should not crash with None or empty context
        result1 = generator.generate_narrator_summary(
            segments=sample_segments,
            character_names=character_names,
            notebook_context=None
        )

        result2 = generator.generate_narrator_summary(
            segments=sample_segments,
            character_names=character_names,
            notebook_context=""
        )

        assert result1 is not None
        assert result2 is not None

    def test_notebook_context_supports_multiline(self, sample_segments, character_names):
        """Test that multiline notebook context is preserved."""
        generator = StoryGenerator()

        multiline_context = """Line 1: Dragon information
Line 2: Party composition
Line 3: Quest objectives"""

        prompt = generator._build_prompt(
            perspective_name="Narrator",
            segments=sample_segments,
            character_names=character_names,
            narrator=True,
            notebook_context=multiline_context
        )

        assert "Line 1: Dragon information" in prompt
        assert "Line 2: Party composition" in prompt
        assert "Line 3: Quest objectives" in prompt

    def test_notebook_context_with_special_characters(self, sample_segments, character_names):
        """Test that special characters in notebook context are handled."""
        generator = StoryGenerator()

        special_context = "Notes with 'quotes', \"double quotes\", and symbols: @#$%"

        prompt = generator._build_prompt(
            perspective_name="Narrator",
            segments=sample_segments,
            character_names=character_names,
            narrator=True,
            notebook_context=special_context
        )

        # Should not crash and should include the content
        assert "quotes" in prompt
        assert "@#$%" in prompt


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestErrorHandling:
    """Test error handling scenarios."""

    def test_handles_none_segments(self, character_names, notebook_context):
        """Test handling of None segments list raises TypeError."""
        generator = StoryGenerator()

        # None segments should raise TypeError (invalid input)
        with pytest.raises(TypeError):
            generator._build_prompt(
                perspective_name="Narrator",
                segments=None,
                character_names=character_names,
                narrator=True,
                notebook_context=notebook_context
            )

    def test_handles_segments_with_none_text(self, character_names, notebook_context):
        """Test handling of segments with None text."""
        generator = StoryGenerator()

        segments = [
            {"text": None, "classification": "IC", "start_time": 0.0},
            {"text": "Valid text", "classification": "IC", "start_time": 5.0}
        ]

        prompt = generator._build_prompt(
            perspective_name="Narrator",
            segments=segments,
            character_names=character_names,
            narrator=True,
            notebook_context=notebook_context
        )

        # Should skip None text, include valid text
        assert "Valid text" in prompt

    def test_handles_segments_with_invalid_timestamp(self, character_names, notebook_context):
        """Test handling of segments with invalid timestamp."""
        generator = StoryGenerator()

        segments = [
            {"text": "Text 1", "classification": "IC", "start_time": "invalid"},
            {"text": "Text 2", "classification": "IC", "start_time": None},
            {"text": "Text 3", "classification": "IC", "start_time": 5.0}
        ]

        prompt = generator._build_prompt(
            perspective_name="Narrator",
            segments=segments,
            character_names=character_names,
            narrator=True,
            notebook_context=notebook_context
        )

        # Should handle invalid timestamps gracefully
        assert "Text 1" in prompt
        assert "Text 2" in prompt
        assert "Text 3" in prompt

    def test_handles_empty_character_names(self, sample_segments, notebook_context):
        """Test handling of empty character names list."""
        generator = StoryGenerator()
        mock_client = MockOllamaClient()
        generator.client = mock_client

        # Should not crash with empty character names
        result = generator.generate_narrator_summary(
            segments=sample_segments,
            character_names=[],
            notebook_context=notebook_context
        )

        assert result is not None

    def test_handles_llm_connection_error(self, sample_segments, character_names, notebook_context):
        """Test handling of LLM connection error."""
        generator = StoryGenerator()

        def raise_connection_error(**kwargs):
            raise ConnectionError("Cannot connect to Ollama")

        generator.client.generate = raise_connection_error

        # Should propagate the error (caller should handle)
        with pytest.raises(ConnectionError, match="Cannot connect to Ollama"):
            generator.generate_narrator_summary(
                segments=sample_segments,
                character_names=character_names,
                notebook_context=notebook_context
            )

    def test_handles_malformed_llm_response(self, sample_segments, character_names, notebook_context):
        """Test handling of malformed LLM response."""
        generator = StoryGenerator()

        # LLM returns response without 'response' key
        generator.client.generate = lambda **kwargs: {"error": "Something went wrong"}

        result = generator.generate_narrator_summary(
            segments=sample_segments,
            character_names=character_names,
            notebook_context=notebook_context
        )

        # Should return fallback message
        assert result == "(LLM returned no text)"
