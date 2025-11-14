"""
UI Component builders for the Process Session tab.

This module provides builder classes for creating Gradio UI components
in a modular, testable way.
"""

from typing import Any, Dict, List
import gradio as gr

from src.ui.helpers import InfoText, Placeholders, StatusMessages, UIComponents
from src.ui.constants import StatusIndicators as SI


# ============================================================================
# Workflow Header
# ============================================================================

class WorkflowHeaderBuilder:
    """Builder for the visual workflow stepper."""

    @staticmethod
    def build() -> gr.HTML:
        """Create workflow stepper HTML component."""
        return gr.HTML(
            """
            <div class="stepper">
                <div class="step active">
                    <div class="step-number">1</div>
                    <div class="step-label">Upload</div>
                    <div class="step-connector"></div>
                </div>
                <div class="step">
                    <div class="step-number">2</div>
                    <div class="step-label">Configure</div>
                    <div class="step-connector"></div>
                </div>
                <div class="step">
                    <div class="step-number">3</div>
                    <div class="step-label">Process</div>
                    <div class="step-connector"></div>
                </div>
                <div class="step">
                    <div class="step-number">4</div>
                    <div class="step-label">Review</div>
                </div>
            </div>
            """
        )


# ============================================================================
# Upload Section (Step 1)
# ============================================================================

class UploadSectionBuilder:
    """Builder for the audio upload section."""

    ALLOWED_AUDIO_EXTENSIONS = [".m4a", ".mp3", ".wav", ".flac"]

    def build(self) -> Dict[str, gr.Component]:
        """
        Build Step 1: Upload Audio section.

        Returns:
            Dictionary with component references:
            - audio_input: File upload component
            - file_warning_display: Warning markdown for duplicate files
        """
        components = {}

        with gr.Group():
            gr.Markdown("### Step 1: Upload Audio")

            components["audio_input"] = gr.File(
                label="Session Audio File",
                file_types=self.ALLOWED_AUDIO_EXTENSIONS,
            )

            components["file_warning_display"] = gr.Markdown(
                value="",
                visible=False,
            )

        return components


# ============================================================================
# Configuration Section (Step 2)
# ============================================================================

class ConfigurationSectionBuilder:
    """Builder for the session configuration section."""

    def __init__(
        self,
        available_parties: List[str],
        initial_defaults: Dict[str, Any],
    ):
        """
        Initialize configuration builder.

        Args:
            available_parties: List of party IDs to populate dropdown
            initial_defaults: Default values for all configuration fields
        """
        self.available_parties = available_parties
        self.initial_defaults = initial_defaults

    def build(self) -> Dict[str, gr.Component]:
        """
        Build Step 2: Configure Session section.

        Returns:
            Dictionary with component references:
            - session_id_input
            - party_selection_input
            - party_characters_display
            - num_speakers_input
            - language_input
            - character_names_input
            - player_names_input
            - transcription_backend_input
            - diarization_backend_input
            - classification_backend_input
            - skip_diarization_input
            - skip_classification_input
            - skip_snippets_input
            - skip_knowledge_input
        """
        components = {}

        with gr.Group():
            gr.Markdown("### Step 2: Configure Session")

            # Session ID
            components["session_id_input"] = gr.Textbox(
                label="Session ID",
                placeholder=Placeholders.SESSION_ID,
                info=InfoText.SESSION_ID,
            )

            # Party Selection
            with gr.Row():
                components["party_selection_input"] = gr.Dropdown(
                    label="Party Configuration",
                    choices=self.available_parties,
                    value=self.initial_defaults.get("party_selection") or "Manual Entry",
                    info="Select an existing party profile or choose Manual Entry.",
                )

            components["party_characters_display"] = gr.Markdown(
                value="",
                visible=False,
            )

            # Speaker and Language Settings
            with gr.Row():
                components["num_speakers_input"] = gr.Slider(
                    minimum=2,
                    maximum=10,
                    value=self.initial_defaults.get("num_speakers", 4),
                    step=1,
                    label="Expected Speakers",
                    info="Helps diarization accuracy. Typical table is 3 players + 1 DM.",
                )

                components["language_input"] = gr.Dropdown(
                    label="Language",
                    choices=["en", "nl"],
                    value="nl",
                    info="Select the language spoken in the session.",
                )

                components["character_names_input"] = gr.Textbox(
                    label="Character Names (comma-separated)",
                    placeholder=Placeholders.CHARACTER_NAME,
                    info="Used when Manual Entry is selected.",
                )

                components["player_names_input"] = gr.Textbox(
                    label="Player Names (comma-separated)",
                    placeholder=Placeholders.PLAYER_NAME,
                    info="Optional player name mapping for manual entry.",
                )

            # Backend Settings (Advanced)
            with gr.Accordion("Advanced Backend Settings", open=False):
                components["transcription_backend_input"] = gr.Dropdown(
                    label="Transcription Backend",
                    choices=["whisper", "groq"],
                    value="whisper",
                    info="Use local Whisper or cloud Groq API.",
                )
                components["diarization_backend_input"] = gr.Dropdown(
                    label="Diarization Backend",
                    choices=["pyannote", "hf_api"],
                    value="pyannote",
                    info="Use local PyAnnote or cloud Hugging Face API.",
                )
                components["classification_backend_input"] = gr.Dropdown(
                    label="Classification Backend",
                    choices=["ollama", "groq", "colab"],
                    value="colab",
                    info="Use local Ollama, cloud Groq API, or Google Colab GPU.",
                )

            # Skip Options
            with gr.Row():
                components["skip_diarization_input"] = gr.Checkbox(
                    label="Skip Speaker Identification",
                    value=self.initial_defaults.get("skip_diarization", False),
                    info="Saves time but all segments will be UNKNOWN.",
                )
                components["skip_classification_input"] = gr.Checkbox(
                    label="Skip IC/OOC Classification",
                    value=self.initial_defaults.get("skip_classification", False),
                    info="Disables in-character versus out-of-character separation.",
                )
                components["skip_snippets_input"] = gr.Checkbox(
                    label="Skip Snippet Export",
                    value=self.initial_defaults.get("skip_snippets", True),
                    info="Skip exporting WAV snippets to save disk space.",
                )
                components["skip_knowledge_input"] = gr.Checkbox(
                    label="Skip Knowledge Extraction",
                    value=self.initial_defaults.get("skip_knowledge", False),
                    info="Disable automatic quest/NPC extraction.",
                )

        return components


# ============================================================================
# Processing Controls Section (Step 3)
# ============================================================================

class ProcessingControlsBuilder:
    """Builder for processing controls and status displays."""

    def build(self) -> Dict[str, gr.Component]:
        """
        Build Step 3: Process section with controls and status displays.

        Returns:
            Dictionary with component references:
            - preflight_btn
            - process_btn
            - status_output
            - transcription_progress
            - runtime_accordion
            - stage_progress_display
            - event_log_display
            - transcription_timer
            - should_process_state
        """
        components = {}

        with gr.Group():
            gr.Markdown("### Step 3: Process")

            components["preflight_btn"] = UIComponents.create_action_button(
                "Run Preflight Checks",
                variant="secondary",
                size="md",
                full_width=True,
            )

            components["process_btn"] = UIComponents.create_action_button(
                "Start Processing",
                variant="primary",
                size="lg",
                full_width=True,
            )

            components["status_output"] = gr.Markdown(
                value=StatusMessages.info(
                    "Ready",
                    "Provide a session ID and audio file, then click Start Processing."
                )
            )

            components["transcription_progress"] = gr.Markdown(
                value="",
                visible=False,
            )

            # Enhanced Runtime Updates Section
            with gr.Accordion("Runtime Updates & Event Log", open=False) as runtime_accordion:
                gr.Markdown("**Live processing status, stage progress, and detailed event log**")

                # Stage Progress Overview
                components["stage_progress_display"] = gr.Markdown(
                    value="",
                    visible=False,
                )

                # Persistent Event Log
                components["event_log_display"] = gr.Textbox(
                    label="Event Log",
                    lines=15,
                    max_lines=30,
                    value="",
                    interactive=False,
                    show_copy_button=True,
                    elem_classes=["event-log-textbox"],
                )

            components["runtime_accordion"] = runtime_accordion
            components["transcription_timer"] = gr.Timer(every=2.0, active=True)

        # State for processing flow control
        components["should_process_state"] = gr.State(value=False)

        return components


# ============================================================================
# Results Section (Step 4)
# ============================================================================

class ResultsSectionBuilder:
    """Builder for the results display section."""

    def build(self) -> Dict[str, gr.Component]:
        """
        Build Step 4: Review Results section.

        Returns:
            Dictionary with component references:
            - results_section (Group)
            - full_output
            - ic_output
            - ooc_output
            - stats_output
            - snippet_output
            - scroll_trigger
        """
        components = {}

        with gr.Group(visible=False, elem_id="process-results-section") as results_section:
            gr.Markdown("### Step 4: Review Results")
            components["full_output"] = gr.Textbox(label="Full Transcript", lines=10)
            components["ic_output"] = gr.Textbox(label="In-Character Transcript", lines=10)
            components["ooc_output"] = gr.Textbox(label="Out-of-Character Transcript", lines=10)
            components["stats_output"] = gr.Markdown()
            components["snippet_output"] = gr.Markdown()

        components["results_section"] = results_section

        # Auto-scroll JavaScript component (hidden, triggers when results appear)
        components["scroll_trigger"] = gr.HTML(visible=False)

        return components


# ============================================================================
# Main Tab Builder
# ============================================================================

class ProcessSessionTabBuilder:
    """
    Main builder that orchestrates all section builders.

    This class coordinates the creation of all UI components for the
    Process Session tab using the individual section builders.
    """

    def __init__(
        self,
        available_parties: List[str],
        initial_defaults: Dict[str, Any],
        campaign_badge_text: str,
    ):
        """
        Initialize the main tab builder.

        Args:
            available_parties: List of party IDs
            initial_defaults: Default values for configuration
            campaign_badge_text: Initial campaign badge markdown
        """
        self.available_parties = available_parties
        self.initial_defaults = initial_defaults
        self.campaign_badge_text = campaign_badge_text

    def build_ui_components(self) -> Dict[str, gr.Component]:
        """
        Build all UI components for the Process Session tab.

        Returns:
            Dictionary containing all component references organized by section.
        """
        all_components = {}

        # Create workflow header
        WorkflowHeaderBuilder.build()

        # Tab header
        gr.Markdown(
            """
            # Process Session Recording

            Upload an audio file, apply campaign defaults, and run the pipeline.
            """
        )

        # Campaign badge
        badge_value = self.campaign_badge_text or StatusMessages.info(
            "Campaign",
            "No campaign selected. Use the Campaign Launcher above to choose one."
        )
        all_components["campaign_badge"] = gr.Markdown(value=badge_value)

        # Build each section
        upload_builder = UploadSectionBuilder()
        all_components.update(upload_builder.build())

        config_builder = ConfigurationSectionBuilder(
            self.available_parties,
            self.initial_defaults
        )
        all_components.update(config_builder.build())

        controls_builder = ProcessingControlsBuilder()
        all_components.update(controls_builder.build())

        results_builder = ResultsSectionBuilder()
        all_components.update(results_builder.build())

        return all_components
