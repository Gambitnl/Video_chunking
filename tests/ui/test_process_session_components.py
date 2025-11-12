"""Tests for process session UI component builders."""

import pytest
import gradio as gr
from unittest.mock import Mock, patch

from src.ui.process_session_components import (
    WorkflowHeaderBuilder,
    UploadSectionBuilder,
    ConfigurationSectionBuilder,
    ProcessingControlsBuilder,
    ResultsSectionBuilder,
    ProcessSessionTabBuilder,
)


class TestWorkflowHeaderBuilder:
    """Test workflow header builder."""

    def test_build_returns_html(self):
        """Test that build returns HTML component."""
        with gr.Blocks():
            result = WorkflowHeaderBuilder.build()
            assert isinstance(result, gr.HTML)
            assert "stepper" in result.value.lower()

    def test_build_contains_all_steps(self):
        """Test that all workflow steps are present."""
        with gr.Blocks():
            result = WorkflowHeaderBuilder.build()
            value = result.value.lower()
            assert "upload" in value
            assert "configure" in value
            assert "process" in value
            assert "review" in value


class TestUploadSectionBuilder:
    """Test upload section builder."""

    def test_build_returns_components(self):
        """Test that build returns expected components."""
        builder = UploadSectionBuilder()

        with gr.Blocks():
            components = builder.build()

        assert "audio_input" in components
        assert "file_warning_display" in components
        assert isinstance(components["audio_input"], gr.File)
        assert isinstance(components["file_warning_display"], gr.Markdown)

    def test_audio_input_has_correct_file_types(self):
        """Test that audio input accepts correct file types."""
        builder = UploadSectionBuilder()

        with gr.Blocks():
            components = builder.build()

        audio_input = components["audio_input"]
        # Check that file_types includes audio extensions
        assert ".wav" in UploadSectionBuilder.ALLOWED_AUDIO_EXTENSIONS
        assert ".mp3" in UploadSectionBuilder.ALLOWED_AUDIO_EXTENSIONS
        assert ".m4a" in UploadSectionBuilder.ALLOWED_AUDIO_EXTENSIONS
        assert ".flac" in UploadSectionBuilder.ALLOWED_AUDIO_EXTENSIONS

    def test_file_warning_initially_hidden(self):
        """Test that file warning starts hidden."""
        builder = UploadSectionBuilder()

        with gr.Blocks():
            components = builder.build()

        assert components["file_warning_display"].visible is False


class TestConfigurationSectionBuilder:
    """Test configuration section builder."""

    def test_build_with_defaults(self):
        """Test building with default values."""
        parties = ["Manual Entry", "Party1", "Party2"]
        defaults = {
            "party_selection": "Party1",
            "num_speakers": 5,
            "skip_diarization": True,
            "skip_classification": False,
            "skip_snippets": False,
            "skip_knowledge": True,
        }

        builder = ConfigurationSectionBuilder(parties, defaults)

        with gr.Blocks():
            components = builder.build()

        # Verify all expected components exist
        assert "session_id_input" in components
        assert "party_selection_input" in components
        assert "party_characters_display" in components
        assert "num_speakers_input" in components
        assert "language_input" in components
        assert "character_names_input" in components
        assert "player_names_input" in components
        assert "transcription_backend_input" in components
        assert "diarization_backend_input" in components
        assert "classification_backend_input" in components
        assert "skip_diarization_input" in components
        assert "skip_classification_input" in components
        assert "skip_snippets_input" in components
        assert "skip_knowledge_input" in components

        # Verify defaults are applied
        assert components["party_selection_input"].value == "Party1"
        assert components["num_speakers_input"].value == 5
        assert components["skip_diarization_input"].value is True
        assert components["skip_classification_input"].value is False
        assert components["skip_snippets_input"].value is False
        assert components["skip_knowledge_input"].value is True

    def test_build_with_empty_defaults(self):
        """Test building with empty defaults."""
        parties = ["Manual Entry"]
        defaults = {}

        builder = ConfigurationSectionBuilder(parties, defaults)

        with gr.Blocks():
            components = builder.build()

        # Should still create all components with fallback defaults
        assert components["party_selection_input"].value == "Manual Entry"
        assert components["num_speakers_input"].value == 4  # Default

    def test_party_characters_display_initially_hidden(self):
        """Test that party characters display starts hidden."""
        parties = ["Manual Entry", "Party1"]
        defaults = {}

        builder = ConfigurationSectionBuilder(parties, defaults)

        with gr.Blocks():
            components = builder.build()

        assert components["party_characters_display"].visible is False

    def test_backend_defaults_are_correct(self):
        """Test that backend dropdowns have correct defaults."""
        parties = ["Manual Entry"]
        defaults = {}

        builder = ConfigurationSectionBuilder(parties, defaults)

        with gr.Blocks():
            components = builder.build()

        assert components["transcription_backend_input"].value == "whisper"
        assert components["diarization_backend_input"].value == "pyannote"
        assert components["classification_backend_input"].value == "ollama"


class TestProcessingControlsBuilder:
    """Test processing controls builder."""

    def test_build_returns_all_components(self):
        """Test that all expected components are created."""
        builder = ProcessingControlsBuilder()

        with gr.Blocks():
            components = builder.build()

        expected_keys = [
            "preflight_btn",
            "process_btn",
            "status_output",
            "transcription_progress",
            "runtime_accordion",
            "stage_progress_display",
            "event_log_display",
            "transcription_timer",
            "should_process_state",
        ]

        for key in expected_keys:
            assert key in components, f"Missing component: {key}"

    def test_buttons_exist(self):
        """Test that buttons are created correctly."""
        builder = ProcessingControlsBuilder()

        with gr.Blocks():
            components = builder.build()

        assert components["preflight_btn"] is not None
        assert components["process_btn"] is not None
        assert isinstance(components["preflight_btn"], gr.Button)
        assert isinstance(components["process_btn"], gr.Button)

    def test_status_output_has_initial_value(self):
        """Test that status output has an initial ready message."""
        builder = ProcessingControlsBuilder()

        with gr.Blocks():
            components = builder.build()

        status_value = components["status_output"].value
        assert status_value is not None
        assert len(status_value) > 0
        assert "Ready" in status_value or "ready" in status_value.lower()

    def test_transcription_progress_initially_hidden(self):
        """Test that transcription progress starts hidden."""
        builder = ProcessingControlsBuilder()

        with gr.Blocks():
            components = builder.build()

        assert components["transcription_progress"].visible is False

    def test_stage_progress_initially_hidden(self):
        """Test that stage progress starts hidden."""
        builder = ProcessingControlsBuilder()

        with gr.Blocks():
            components = builder.build()

        assert components["stage_progress_display"].visible is False

    def test_event_log_is_textbox(self):
        """Test that event log is a textbox with correct properties."""
        builder = ProcessingControlsBuilder()

        with gr.Blocks():
            components = builder.build()

        event_log = components["event_log_display"]
        assert isinstance(event_log, gr.Textbox)
        assert event_log.interactive is False
        assert event_log.show_copy_button is True

    def test_timer_is_active(self):
        """Test that transcription timer is created and active."""
        builder = ProcessingControlsBuilder()

        with gr.Blocks():
            components = builder.build()

        timer = components["transcription_timer"]
        assert isinstance(timer, gr.Timer)
        assert timer.active is True

    def test_should_process_state_initial_value(self):
        """Test that should_process_state starts as False."""
        builder = ProcessingControlsBuilder()

        with gr.Blocks():
            components = builder.build()

        assert components["should_process_state"].value is False


class TestResultsSectionBuilder:
    """Test results section builder."""

    def test_build_creates_results_section(self):
        """Test that results section is created."""
        builder = ResultsSectionBuilder()

        with gr.Blocks():
            components = builder.build()

        assert "results_section" in components
        assert "full_output" in components
        assert "ic_output" in components
        assert "ooc_output" in components
        assert "stats_output" in components
        assert "snippet_output" in components
        assert "scroll_trigger" in components

    def test_results_section_initially_hidden(self):
        """Test that results section starts hidden."""
        builder = ResultsSectionBuilder()

        with gr.Blocks():
            components = builder.build()

        # Results section should be invisible initially
        assert components["results_section"].visible is False

    def test_transcript_outputs_are_textboxes(self):
        """Test that transcript outputs are textboxes."""
        builder = ResultsSectionBuilder()

        with gr.Blocks():
            components = builder.build()

        assert isinstance(components["full_output"], gr.Textbox)
        assert isinstance(components["ic_output"], gr.Textbox)
        assert isinstance(components["ooc_output"], gr.Textbox)

    def test_stats_and_snippet_outputs_are_markdown(self):
        """Test that stats and snippet outputs are markdown."""
        builder = ResultsSectionBuilder()

        with gr.Blocks():
            components = builder.build()

        assert isinstance(components["stats_output"], gr.Markdown)
        assert isinstance(components["snippet_output"], gr.Markdown)

    def test_scroll_trigger_is_html(self):
        """Test that scroll trigger is HTML component."""
        builder = ResultsSectionBuilder()

        with gr.Blocks():
            components = builder.build()

        assert isinstance(components["scroll_trigger"], gr.HTML)
        assert components["scroll_trigger"].visible is False


class TestProcessSessionTabBuilder:
    """Test main tab builder."""

    def test_build_creates_all_sections(self):
        """Test that main builder creates all section components."""
        parties = ["Manual Entry", "TestParty"]
        defaults = {"num_speakers": 4}
        badge_text = "Test Campaign"

        builder = ProcessSessionTabBuilder(parties, defaults, badge_text)

        with gr.Blocks():
            components = builder.build_ui_components()

        # Verify components from each section
        assert "campaign_badge" in components
        assert "audio_input" in components  # From upload section
        assert "session_id_input" in components  # From config section
        assert "process_btn" in components  # From controls section
        assert "results_section" in components  # From results section

    def test_build_applies_initial_defaults(self):
        """Test that initial defaults are applied."""
        parties = ["Manual Entry", "TestParty"]
        defaults = {
            "party_selection": "TestParty",
            "num_speakers": 6,
            "skip_diarization": True,
        }
        badge_text = "Test Campaign"

        builder = ProcessSessionTabBuilder(parties, defaults, badge_text)

        with gr.Blocks():
            components = builder.build_ui_components()

        assert components["party_selection_input"].value == "TestParty"
        assert components["num_speakers_input"].value == 6
        assert components["skip_diarization_input"].value is True

    def test_campaign_badge_uses_provided_text(self):
        """Test that campaign badge displays provided text."""
        parties = ["Manual Entry"]
        defaults = {}
        badge_text = "### Test Campaign Badge"

        builder = ProcessSessionTabBuilder(parties, defaults, badge_text)

        with gr.Blocks():
            components = builder.build_ui_components()

        assert components["campaign_badge"].value == badge_text

    def test_campaign_badge_fallback_when_empty(self):
        """Test that campaign badge has fallback when text is empty."""
        parties = ["Manual Entry"]
        defaults = {}
        badge_text = ""

        builder = ProcessSessionTabBuilder(parties, defaults, badge_text)

        with gr.Blocks():
            components = builder.build_ui_components()

        # Should have fallback message
        assert components["campaign_badge"].value is not None
        assert len(components["campaign_badge"].value) > 0
        assert "Campaign" in components["campaign_badge"].value

    def test_all_component_types_are_correct(self):
        """Test that all components have correct types."""
        parties = ["Manual Entry"]
        defaults = {}
        badge_text = "Test"

        builder = ProcessSessionTabBuilder(parties, defaults, badge_text)

        with gr.Blocks():
            components = builder.build_ui_components()

        # Type checks for critical components
        assert isinstance(components["campaign_badge"], gr.Markdown)
        assert isinstance(components["audio_input"], gr.File)
        assert isinstance(components["session_id_input"], gr.Textbox)
        assert isinstance(components["party_selection_input"], gr.Dropdown)
        assert isinstance(components["num_speakers_input"], gr.Slider)
        assert isinstance(components["process_btn"], gr.Button)
        assert isinstance(components["preflight_btn"], gr.Button)
        assert isinstance(components["status_output"], gr.Markdown)
        assert isinstance(components["results_section"], gr.Group)

    def test_integration_all_builders_work_together(self):
        """Test that all builders integrate correctly."""
        parties = ["Manual Entry", "Party1", "Party2"]
        defaults = {
            "party_selection": "Party1",
            "num_speakers": 5,
            "skip_diarization": False,
            "skip_classification": True,
            "skip_snippets": False,
            "skip_knowledge": False,
        }
        badge_text = "### Integration Test Campaign"

        builder = ProcessSessionTabBuilder(parties, defaults, badge_text)

        with gr.Blocks():
            components = builder.build_ui_components()

        # Verify comprehensive component list
        expected_components = [
            # Campaign badge
            "campaign_badge",
            # Upload section
            "audio_input",
            "file_warning_display",
            # Configuration section
            "session_id_input",
            "party_selection_input",
            "party_characters_display",
            "num_speakers_input",
            "language_input",
            "character_names_input",
            "player_names_input",
            "transcription_backend_input",
            "diarization_backend_input",
            "classification_backend_input",
            "skip_diarization_input",
            "skip_classification_input",
            "skip_snippets_input",
            "skip_knowledge_input",
            # Processing controls section
            "preflight_btn",
            "process_btn",
            "status_output",
            "transcription_progress",
            "runtime_accordion",
            "stage_progress_display",
            "event_log_display",
            "transcription_timer",
            "should_process_state",
            # Results section
            "results_section",
            "full_output",
            "ic_output",
            "ooc_output",
            "stats_output",
            "snippet_output",
            "scroll_trigger",
        ]

        for component_name in expected_components:
            assert component_name in components, f"Missing component: {component_name}"

        # Verify all defaults were applied
        assert components["party_selection_input"].value == "Party1"
        assert components["num_speakers_input"].value == 5
        assert components["skip_diarization_input"].value is False
        assert components["skip_classification_input"].value is True
        assert components["skip_snippets_input"].value is False
        assert components["skip_knowledge_input"].value is False
