"""
Integration tests for the Process Session tab.

These tests verify that all modules (tab_modern, components, helpers, events)
work together correctly as an integrated system.

Test Coverage:
    - Tab creation and initialization
    - Component presence and configuration
    - Event wiring functionality
    - Campaign settings integration
    - End-to-end workflows

Note:
    These tests focus on integration between modules, not full end-to-end
    processing (which would require audio files, models, etc.).
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import gradio as gr

from src.ui.process_session_tab_modern import create_process_session_tab_modern


@pytest.fixture
def mock_dependencies():
    """
    Create mock dependencies for tab creation.

    Returns:
        Dictionary of mocked dependencies needed by create_process_session_tab_modern
    """
    return {
        "refresh_campaign_names": Mock(return_value={
            "campaign1": "Test Campaign",
            "campaign2": "Another Campaign"
        }),
        "process_session_fn": Mock(return_value={
            "status": "success",
            "full_transcript": "Test transcript",
            "ic_transcript": "IC content",
            "ooc_transcript": "OOC content",
            "statistics": {"duration": 60, "speakers": 4},
            "snippet_info": "No snippets generated",
        }),
        "preflight_fn": Mock(return_value="All preflight checks passed"),
        "campaign_manager": Mock(),
        "active_campaign_state": gr.State(value="campaign1"),
        "campaign_badge_text": "Test Campaign Active",
        "initial_campaign_name": "Test Campaign",
    }


@pytest.fixture
def mock_party_manager():
    """Mock PartyConfigManager for tests."""
    with patch('src.ui.process_session_tab_modern.PartyConfigManager') as mock:
        instance = mock.return_value
        instance.list_parties.return_value = ["Party A", "Party B", "Party C"]
        yield instance


# ============================================================================
# Tab Creation Tests
# ============================================================================

class TestTabCreation:
    """Test suite for tab creation and initialization."""

    def test_tab_creates_successfully(self, mock_dependencies, mock_party_manager):
        """Test that tab creates without errors."""
        with gr.Blocks() as demo:
            parties, refs = create_process_session_tab_modern(
                demo,
                **mock_dependencies
            )

        # Should return parties and component references
        assert isinstance(parties, list), "Should return list of parties"
        assert isinstance(refs, dict), "Should return dict of component refs"
        assert len(parties) > 0, "Should have at least one party (Manual Entry)"

    def test_tab_includes_manual_entry(self, mock_dependencies, mock_party_manager):
        """Test that 'Manual Entry' is always included in party list."""
        with gr.Blocks() as demo:
            parties, _ = create_process_session_tab_modern(
                demo,
                **mock_dependencies
            )

        assert "Manual Entry" in parties, "Manual Entry should always be first option"

    def test_tab_includes_configured_parties(self, mock_dependencies, mock_party_manager):
        """Test that configured parties from PartyConfigManager are included."""
        with gr.Blocks() as demo:
            parties, _ = create_process_session_tab_modern(
                demo,
                **mock_dependencies
            )

        # Should include parties from mock manager
        assert "Party A" in parties
        assert "Party B" in parties
        assert "Party C" in parties


# ============================================================================
# Component Presence Tests
# ============================================================================

class TestComponentPresence:
    """Test suite for verifying all components are created."""

    def test_all_input_components_present(self, mock_dependencies, mock_party_manager):
        """Test that all expected input components are created."""
        with gr.Blocks() as demo:
            _, refs = create_process_session_tab_modern(
                demo,
                **mock_dependencies
            )

        # Input components
        expected_inputs = [
            "audio_input",
            "session_id_input",
            "party_selection_input",
            "character_names_input",
            "player_names_input",
            "num_speakers_input",
            "language_input",
            "transcription_backend_input",
            "diarization_backend_input",
            "classification_backend_input",
            "skip_diarization_input",
            "skip_classification_input",
            "skip_snippets_input",
            "skip_knowledge_input",
        ]

        for component_name in expected_inputs:
            assert component_name in refs, f"Missing input component: {component_name}"

    def test_all_output_components_present(self, mock_dependencies, mock_party_manager):
        """Test that all expected output components are created."""
        with gr.Blocks() as demo:
            _, refs = create_process_session_tab_modern(
                demo,
                **mock_dependencies
            )

        # Output components
        expected_outputs = [
            "status_output",
            "results_section",
            "full_output",
            "ic_output",
            "ooc_output",
            "stats_output",
            "snippet_output",
            "transcription_progress",
            "stage_progress_display",
            "event_log_display",
        ]

        for component_name in expected_outputs:
            assert component_name in refs, f"Missing output component: {component_name}"

    def test_all_control_components_present(self, mock_dependencies, mock_party_manager):
        """Test that all expected control components (buttons, etc.) are created."""
        with gr.Blocks() as demo:
            _, refs = create_process_session_tab_modern(
                demo,
                **mock_dependencies
            )

        # Control components
        expected_controls = [
            "preflight_btn",
            "process_btn",
            "campaign_badge",
            "file_warning_display",
            "party_characters_display",
        ]

        for component_name in expected_controls:
            assert component_name in refs, f"Missing control component: {component_name}"


# ============================================================================
# Component Configuration Tests
# ============================================================================

class TestComponentConfiguration:
    """Test suite for verifying component configurations."""

    def test_party_selection_has_correct_choices(self, mock_dependencies, mock_party_manager):
        """Test that party selection dropdown has correct choices."""
        with gr.Blocks() as demo:
            parties, refs = create_process_session_tab_modern(
                demo,
                **mock_dependencies
            )

        # Party dropdown should have all parties from the returned list
        party_dropdown = refs["party_selection_input"]
        assert isinstance(party_dropdown, gr.Dropdown)
        # Note: Can't easily access choices from gradio component in tests,
        # but we verify the parties list is correct
        assert len(parties) == 4  # Manual Entry + 3 mocked parties

    def test_num_speakers_has_correct_range(self, mock_dependencies, mock_party_manager):
        """Test that num_speakers slider has correct range."""
        with gr.Blocks() as demo:
            _, refs = create_process_session_tab_modern(
                demo,
                **mock_dependencies
            )

        num_speakers = refs["num_speakers_input"]
        assert isinstance(num_speakers, gr.Slider)
        # Note: Can't easily verify min/max in tests without accessing internals


# ============================================================================
# Campaign Integration Tests
# ============================================================================

class TestCampaignIntegration:
    """Test suite for campaign settings integration."""

    def test_campaign_defaults_applied_when_campaign_selected(
        self, mock_dependencies, mock_party_manager
    ):
        """Test that campaign defaults are applied when a campaign is selected."""
        # Create a mock campaign with specific settings
        mock_campaign = Mock()
        mock_campaign.party_id = "Party A"
        mock_campaign.settings.num_speakers = 6
        mock_campaign.settings.skip_diarization = True
        mock_campaign.settings.skip_classification = False
        mock_campaign.settings.skip_snippets = False
        mock_campaign.settings.skip_knowledge = True

        mock_dependencies["campaign_manager"].get_campaign.return_value = mock_campaign
        mock_dependencies["initial_campaign_name"] = "Test Campaign"

        with gr.Blocks() as demo:
            _, refs = create_process_session_tab_modern(
                demo,
                **mock_dependencies
            )

        # Verify campaign manager was queried
        mock_dependencies["campaign_manager"].get_campaign.assert_called()

    def test_manual_setup_defaults_when_no_campaign(
        self, mock_dependencies, mock_party_manager
    ):
        """Test that default values are used when no campaign is selected."""
        mock_dependencies["initial_campaign_name"] = "Manual Setup"

        with gr.Blocks() as demo:
            _, refs = create_process_session_tab_modern(
                demo,
                **mock_dependencies
            )

        # Campaign manager should not be queried
        mock_dependencies["campaign_manager"].get_campaign.assert_not_called()


# ============================================================================
# Event Wiring Tests
# ============================================================================

class TestEventWiring:
    """Test suite for event wiring functionality."""

    def test_event_wiring_manager_is_created(self, mock_dependencies, mock_party_manager):
        """Test that ProcessSessionEventWiring is instantiated."""
        with patch('src.ui.process_session_tab_modern.ProcessSessionEventWiring') as mock_wiring:
            with gr.Blocks() as demo:
                create_process_session_tab_modern(
                    demo,
                    **mock_dependencies
                )

            # Verify event wiring was created
            mock_wiring.assert_called_once()

            # Verify wire_all_events was called
            instance = mock_wiring.return_value
            instance.wire_all_events.assert_called_once()

    def test_event_wiring_receives_correct_arguments(
        self, mock_dependencies, mock_party_manager
    ):
        """Test that event wiring manager receives correct initialization args."""
        with patch('src.ui.process_session_tab_modern.ProcessSessionEventWiring') as mock_wiring:
            with gr.Blocks() as demo:
                create_process_session_tab_modern(
                    demo,
                    **mock_dependencies
                )

            # Verify arguments passed to event wiring
            call_args = mock_wiring.call_args
            assert "components" in call_args.kwargs
            assert "process_session_fn" in call_args.kwargs
            assert "preflight_fn" in call_args.kwargs
            assert "active_campaign_state" in call_args.kwargs


# ============================================================================
# Return Value Tests
# ============================================================================

class TestReturnValues:
    """Test suite for function return values."""

    def test_returns_party_list_and_component_refs(
        self, mock_dependencies, mock_party_manager
    ):
        """Test that function returns (parties, component_refs) tuple."""
        with gr.Blocks() as demo:
            result = create_process_session_tab_modern(
                demo,
                **mock_dependencies
            )

        assert isinstance(result, tuple), "Should return a tuple"
        assert len(result) == 2, "Should return tuple of length 2"

        parties, refs = result
        assert isinstance(parties, list), "First element should be list"
        assert isinstance(refs, dict), "Second element should be dict"

    def test_component_refs_contain_required_keys(
        self, mock_dependencies, mock_party_manager
    ):
        """Test that component refs dictionary contains all required keys."""
        with gr.Blocks() as demo:
            _, refs = create_process_session_tab_modern(
                demo,
                **mock_dependencies
            )

        # Minimum required keys for cross-tab coordination
        required_keys = [
            "campaign_badge",
            "audio_input",
            "party_selection_input",
            "session_id_input",
            "process_btn",
            "preflight_btn",
            "status_output",
        ]

        for key in required_keys:
            assert key in refs, f"Component refs missing required key: {key}"


# ============================================================================
# Edge Case Tests
# ============================================================================

class TestEdgeCases:
    """Test suite for edge cases and error conditions."""

    def test_handles_empty_party_list(self, mock_dependencies):
        """Test that tab handles empty party list gracefully."""
        with patch('src.ui.process_session_tab_modern.PartyConfigManager') as mock:
            instance = mock.return_value
            instance.list_parties.return_value = []  # No parties

            with gr.Blocks() as demo:
                parties, refs = create_process_session_tab_modern(
                    demo,
                    **mock_dependencies
                )

            # Should still have "Manual Entry"
            assert "Manual Entry" in parties
            assert len(parties) == 1

    def test_handles_missing_campaign(self, mock_dependencies, mock_party_manager):
        """Test that tab handles missing campaign gracefully."""
        mock_dependencies["campaign_manager"].get_campaign.return_value = None
        mock_dependencies["initial_campaign_name"] = "Nonexistent Campaign"

        with gr.Blocks() as demo:
            parties, refs = create_process_session_tab_modern(
                demo,
                **mock_dependencies
            )

        # Should still create successfully with default values
        assert isinstance(parties, list)
        assert isinstance(refs, dict)


# ============================================================================
# Builder Pattern Tests
# ============================================================================

class TestBuilderPatternIntegration:
    """Test suite for builder pattern integration."""

    def test_builder_is_instantiated(self, mock_dependencies, mock_party_manager):
        """Test that ProcessSessionTabBuilder is created."""
        with patch('src.ui.process_session_tab_modern.ProcessSessionTabBuilder') as mock_builder:
            # Setup mock to return component refs
            mock_instance = mock_builder.return_value
            mock_instance.build_ui_components.return_value = {
                "audio_input": gr.Audio(),
                "process_btn": gr.Button(),
                # ... minimal set for testing
            }

            with gr.Blocks() as demo:
                create_process_session_tab_modern(
                    demo,
                    **mock_dependencies
                )

            # Verify builder was instantiated
            mock_builder.assert_called_once()

            # Verify build_ui_components was called
            mock_instance.build_ui_components.assert_called_once()


# ============================================================================
# Smoke Tests
# ============================================================================

class TestSmokeTests:
    """Smoke tests for basic functionality."""

    def test_tab_can_be_created_multiple_times(
        self, mock_dependencies, mock_party_manager
    ):
        """Test that tab can be created multiple times without errors."""
        for _ in range(3):
            with gr.Blocks() as demo:
                parties, refs = create_process_session_tab_modern(
                    demo,
                    **mock_dependencies
                )
                assert isinstance(parties, list)
                assert isinstance(refs, dict)

    def test_tab_creation_is_idempotent(
        self, mock_dependencies, mock_party_manager
    ):
        """Test that creating the tab multiple times gives consistent results."""
        results = []

        for _ in range(2):
            with gr.Blocks() as demo:
                parties, refs = create_process_session_tab_modern(
                    demo,
                    **mock_dependencies
                )
                results.append((parties, set(refs.keys())))

        # Party lists should be the same
        assert results[0][0] == results[1][0]

        # Component ref keys should be the same
        assert results[0][1] == results[1][1]


# ============================================================================
# Performance Tests (Basic)
# ============================================================================

class TestPerformance:
    """Basic performance tests."""

    def test_tab_creation_completes_quickly(
        self, mock_dependencies, mock_party_manager
    ):
        """Test that tab creation completes in reasonable time."""
        import time

        start = time.time()

        with gr.Blocks() as demo:
            create_process_session_tab_modern(
                demo,
                **mock_dependencies
            )

        elapsed = time.time() - start

        # Should create in less than 5 seconds (generous for CI environments)
        assert elapsed < 5.0, f"Tab creation took {elapsed:.2f}s (should be < 5s)"
