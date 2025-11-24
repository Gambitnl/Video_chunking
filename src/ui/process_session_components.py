"""
UI Component builders for the Process Session tab.

This module provides builder classes for creating Gradio UI components in a modular,
testable way. Each builder class is responsible for creating a specific section of
the Process Session tab UI.

Builder Classes:
    - **WorkflowHeaderBuilder**: Visual workflow stepper (Upload → Configure → Process → Review)
    - **CampaignBadgeBuilder**: Campaign selection badge display
    - **AudioUploadSectionBuilder**: File upload with history warnings
    - **PartySelectionSectionBuilder**: Party config dropdown with character display
    - **ConfigurationSectionBuilder**: Session config (speakers, language, backends, toggles)
    - **ProcessingControlsBuilder**: Action buttons and status displays
    - **ResultsSectionBuilder**: Transcript displays (full, IC, OOC, stats, snippets)
    - **ProcessSessionTabBuilder**: Main orchestrator that combines all sections

Design Pattern:
    - **Builder Pattern**: Each section is built by a dedicated builder class
    - **Static Methods**: Builders use @staticmethod for stateless construction
    - **Component References**: Returns dictionary of component refs for event wiring
    - **Separation of Concerns**: UI structure separated from behavior (events)

Architecture Flow:
    1. ProcessSessionTabBuilder receives configuration (parties, defaults, badge text)
    2. Each section builder creates its Gradio components
    3. Components are collected into a reference dictionary
    4. Main module wires events using ProcessSessionEventWiring
    5. Tab is ready for user interaction

Example:
    >>> tab_builder = ProcessSessionTabBuilder(
    ...     available_parties=["Manual Entry", "Party A", "Party B"],
    ...     initial_defaults={"num_speakers": 4, "party_selection": "Party A"},
    ...     campaign_badge_text="My Campaign Active"
    ... )
    >>> component_refs = tab_builder.build_ui_components()
    >>> # component_refs contains all UI elements keyed by name

Benefits:
    - Testable: Each builder can be tested in isolation
    - Maintainable: Easy to modify individual sections
    - Reusable: Builders can be composed in different ways
    - Readable: Clear separation of UI sections

See Also:
    - `src.ui.process_session_tab_modern`: Main orchestration
    - `src.ui.process_session_helpers`: Business logic and validation
    - `src.ui.process_session_events`: Event handler wiring
    - `src.ui.helpers`: Shared UI utilities and constants
"""

from typing import Any, Dict, List
import gradio as gr

from src.ui.helpers import AccessibilityAttributes, InfoText, Placeholders, StatusMessages, UIComponents
from src.ui.constants import StatusIndicators as SI


def _a11y(
    component: gr.components.Component,
    *,
    label: str,
    described_by: str | None = None,
    role: str | None = None,
    live: str | None = None,
    elem_id: str | None = None,
) -> gr.components.Component:
    """Attach accessibility metadata to a component and return it."""

    return AccessibilityAttributes.apply(
        component,
        label=label,
        described_by=described_by,
        role=role,
        live=live,
        elem_id=elem_id,
    )


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
            _a11y(
                gr.Markdown("### Step 1: Upload Audio", elem_id="process-upload-heading"),
                label="Upload audio heading",
                role="heading",
            )

            components["audio_input"] = _a11y(
                gr.File(
                    label="Session Audio File",
                    file_types=self.ALLOWED_AUDIO_EXTENSIONS,
                    elem_id="process-audio-input",
                ),
                label="Session audio file",
                described_by="process-audio-info",
                role="button",
            )

            components["file_info_display"] = _a11y(
                gr.Markdown(
                    value="",
                    elem_id="process-audio-info",
                ),
                label="File upload guidance",
                role="status",
                live="polite",
            )

            components["file_warning_display"] = _a11y(
                gr.Markdown(
                    value="",
                    visible=False,
                    elem_id="process-audio-warning",
                ),
                label="File warning",
                role="alert",
                live="assertive",
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
            _a11y(
                gr.Markdown("### Step 2: Configure Session", elem_id="process-configure-heading"),
                label="Configure session heading",
                role="heading",
            )

            # Session ID
            components["session_id_input"] = _a11y(
                gr.Textbox(
                    label="Session ID",
                    placeholder=Placeholders.SESSION_ID,
                    info=InfoText.SESSION_ID,
                    elem_id="process-session-id",
                ),
                label="Session ID",
                described_by="process-session-id-help",
            )

            # Session ID validation status (real-time feedback)
            components["session_id_validation"] = _a11y(
                gr.Markdown(
                    value="",
                    visible=True,
                    elem_id="process-session-id-help",
                ),
                label="Session ID guidance",
                role="status",
                live="polite",
            )

            # Party Selection
            with gr.Row():
                components["party_selection_input"] = _a11y(
                    gr.Dropdown(
                        label="Party Configuration",
                        choices=self.available_parties,
                        value=self.initial_defaults.get("party_selection") or "Manual Entry",
                        info="Select an existing party profile or choose Manual Entry.",
                        elem_id="process-party-selection",
                    ),
                    label="Party configuration",
                    described_by="process-party-details",
                )

            components["party_characters_display"] = _a11y(
                gr.Markdown(
                    value="",
                    visible=False,
                    elem_id="process-party-details",
                ),
                label="Party character details",
                role="status",
                live="polite",
            )

            # Speaker and Language Settings
            with gr.Row():
                components["num_speakers_input"] = _a11y(
                    gr.Slider(
                        minimum=2,
                        maximum=10,
                        value=self.initial_defaults.get("num_speakers", 4),
                        step=1,
                        label="Expected Speakers",
                        info="Helps diarization accuracy. Typical table is 3 players + 1 DM.",
                        elem_id="process-expected-speakers",
                    ),
                    label="Expected speakers",
                )

                components["language_input"] = _a11y(
                    gr.Dropdown(
                        label="Language",
                        choices=["en", "nl"],
                        value="nl",
                        info="Select the language spoken in the session.",
                        elem_id="process-language",
                    ),
                    label="Session language",
                )

                components["character_names_input"] = _a11y(
                    gr.Textbox(
                        label="Character Names (comma-separated)",
                        placeholder=Placeholders.CHARACTER_NAME,
                        info="Used when Manual Entry is selected.",
                        elem_id="process-character-names",
                    ),
                    label="Character names",
                )

                components["player_names_input"] = _a11y(
                    gr.Textbox(
                        label="Player Names (comma-separated)",
                        placeholder=Placeholders.PLAYER_NAME,
                        info="Optional player name mapping for manual entry.",
                        elem_id="process-player-names",
                    ),
                    label="Player names",
                )

            # Backend Settings (Advanced)
            with gr.Accordion("Advanced Backend Settings", open=False, elem_id="process-backend-settings") as backend_accordion:
                _a11y(backend_accordion, label="Advanced backend settings", role="group")
                components["transcription_backend_input"] = _a11y(
                    gr.Dropdown(
                        label="Transcription Backend",
                        choices=["whisper", "groq"],
                        value="whisper",
                        info="Use local Whisper or cloud Groq API.",
                        elem_id="process-transcription-backend",
                    ),
                    label="Transcription backend",
                )
                components["diarization_backend_input"] = _a11y(
                    gr.Dropdown(
                        label="Diarization Backend",
                        choices=["pyannote", "hf_api"],
                        value="pyannote",
                        info="Use local PyAnnote or cloud Hugging Face API.",
                        elem_id="process-diarization-backend",
                    ),
                    label="Diarization backend",
                )
                components["classification_backend_input"] = _a11y(
                    gr.Dropdown(
                        label="Classification Backend",
                        choices=["ollama", "groq", "colab"],
                        value="colab",
                        info="Use local Ollama, cloud Groq API, or Google Colab GPU.",
                        elem_id="process-classification-backend",
                    ),
                    label="Classification backend",
                )

            # Pipeline Control
            components["run_until_stage_input"] = _a11y(
                gr.Dropdown(
                    label="Run Pipeline Until",
                    choices=[
                        ("Full Pipeline (All Stages)", "full"),
                        ("Stage 4: Transcription Only", "stage_4"),
                        ("Stage 5: Through Diarization", "stage_5"),
                        ("Stage 6: Through Classification", "stage_6"),
                        ("Stage 7: Through Output Generation (Skip Snippets & Knowledge)", "stage_7"),
                    ],
                    value="full",
                    info="Control which stages of the pipeline to execute",
                    elem_id="process-run-until",
                ),
                label="Run pipeline until",
            )

            # Skip Options (Advanced)
            with gr.Accordion("Advanced Skip Options", open=False, elem_id="process-skip-options") as skip_accordion:
                _a11y(skip_accordion, label="Advanced skip options", role="group")
                _a11y(
                    gr.Markdown("*These options are auto-set by 'Run Pipeline Until' but can be manually overridden*", elem_id="process-skip-helper"),
                    label="Skip options helper",
                    role="note",
                )
                with gr.Row():
                    components["skip_diarization_input"] = _a11y(
                        gr.Checkbox(
                            label="Skip Speaker Identification",
                            value=self.initial_defaults.get("skip_diarization", False),
                            info="Saves time but all segments will be UNKNOWN.",
                            elem_id="process-skip-diarization",
                        ),
                        label="Skip speaker identification",
                        described_by="process-skip-helper",
                    )
                    components["skip_classification_input"] = _a11y(
                        gr.Checkbox(
                            label="Skip IC/OOC Classification",
                            value=self.initial_defaults.get("skip_classification", False),
                            info="Disables in-character versus out-of-character separation.",
                            elem_id="process-skip-classification",
                        ),
                        label="Skip IC or OOC classification",
                        described_by="process-skip-helper",
                    )
                    components["skip_snippets_input"] = _a11y(
                        gr.Checkbox(
                            label="Skip Snippet Export",
                            value=self.initial_defaults.get("skip_snippets", True),
                            info="Skip exporting WAV snippets to save disk space.",
                            elem_id="process-skip-snippets",
                        ),
                        label="Skip snippet export",
                        described_by="process-skip-helper",
                    )
                    components["skip_knowledge_input"] = _a11y(
                        gr.Checkbox(
                            label="Skip Knowledge Extraction",
                            value=self.initial_defaults.get("skip_knowledge", False),
                            info="Disable automatic quest/NPC extraction.",
                            elem_id="process-skip-knowledge",
                        ),
                        label="Skip knowledge extraction",
                        described_by="process-skip-helper",
                    )

                with gr.Accordion("Advanced Processing Options", open=False, elem_id="process-processing-options") as processing_accordion:
                    _a11y(processing_accordion, label="Advanced processing options", role="group")
                    with gr.Row():
                        components["enable_audit_mode_input"] = _a11y(
                            gr.Checkbox(
                                label="Enable Audit Mode",
                                value=False,
                                info="Save detailed classification prompts and responses for reproducibility. Increases disk usage but enables debugging.",
                                elem_id="process-enable-audit",
                            ),
                            label="Enable audit mode",
                        )
                        components["redact_prompts_input"] = _a11y(
                            gr.Checkbox(
                                label="Redact Prompts in Logs",
                                value=False,
                                info="When audit mode is enabled, redact full dialogue text from audit logs.",
                                elem_id="process-redact-prompts",
                            ),
                            label="Redact prompts in logs",
                        )

                    with gr.Row():
                        components["generate_scenes_input"] = _a11y(
                            gr.Checkbox(
                                label="Generate Scene Bundles",
                                value=True,
                                info="Automatically detect and bundle segments into narrative scenes.",
                                elem_id="process-generate-scenes",
                            ),
                            label="Generate scene bundles",
                        )
                        components["scene_summary_mode_input"] = _a11y(
                            gr.Dropdown(
                                choices=["template", "llm", "none"],
                                value="template",
                                label="Scene Summary Mode",
                                info="How to generate scene summaries (template=fast, llm=detailed, none=skip)",
                                elem_id="process-scene-summary-mode",
                            ),
                            label="Scene summary mode",
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
            - overall_progress_display
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
            _a11y(
                gr.Markdown("### Step 3: Process", elem_id="process-step-heading"),
                label="Process heading",
                role="heading",
            )

            # Processing readiness checklist
            components["readiness_checklist"] = _a11y(
                gr.Markdown(
                    value="### ⚠️ Configuration Incomplete\n\n- ✗ Audio file not uploaded\n- ✗ Session ID required\n- ✗ Party selection required\n- ✓ Expected speakers: 4",
                    visible=True,
                    elem_id="process-readiness",
                ),
                label="Processing readiness checklist",
                role="status",
                live="polite",
            )

            components["preflight_btn"] = UIComponents.create_action_button(
                "Run Preflight Checks",
                variant="secondary",
                size="md",
                full_width=True,
                accessible_label="Run preflight checks",
                aria_describedby="process-readiness",
                elem_id="process-preflight-btn",
            )

            components["process_btn"] = UIComponents.create_action_button(
                "Start Processing",
                variant="primary",
                size="lg",
                full_width=True,
                accessible_label="Start session processing",
                aria_describedby="process-readiness",
                elem_id="process-start-btn",
            )

            components["cancel_btn"] = UIComponents.create_action_button(
                "Cancel Processing",
                variant="stop",
                size="md",
                full_width=True,
                visible=False,
                accessible_label="Cancel processing",
                elem_id="process-cancel-btn",
            )

            # Overall Progress Indicator (prominent, visible during processing)
            components["overall_progress_display"] = _a11y(
                gr.HTML(
                    value="",
                    visible=False,
                    elem_id="process-overall-progress",
                ),
                label="Overall progress",
                role="status",
                live="polite",
            )

            components["status_output"] = _a11y(
                gr.Markdown(
                    value=StatusMessages.info(
                        "Ready",
                        "Provide a session ID and audio file, then click Start Processing."
                    ),
                    elem_id="process-status-output",
                ),
                label="Processing status",
                role="status",
                live="polite",
            )

            components["transcription_progress"] = _a11y(
                gr.Markdown(
                    value="",
                    visible=False,
                    elem_id="process-transcription-progress",
                ),
                label="Transcription progress",
                role="status",
                live="polite",
            )

            # Enhanced Runtime Updates Section
            with gr.Accordion("Runtime Updates & Event Log", open=False) as runtime_accordion:
                _a11y(runtime_accordion, label="Runtime updates and event log", role="group", elem_id="process-runtime-updates")
                _a11y(
                    gr.Markdown("**Live processing status, stage progress, and detailed event log**", elem_id="process-runtime-helper"),
                    label="Runtime helper",
                    role="note",
                )

                # Stage Progress Overview
                components["stage_progress_display"] = _a11y(
                    gr.Markdown(
                        value="",
                        visible=False,
                        elem_id="process-stage-progress",
                    ),
                    label="Stage progress",
                    role="status",
                    live="polite",
                )

                # Persistent Event Log
                components["event_log_display"] = _a11y(
                    gr.Textbox(
                        label="Event Log",
                        lines=15,
                        max_lines=30,
                        value="",
                        interactive=False,
                        # show_copy_button=False, # Deprecated in newer Gradio
                        elem_classes=["event-log-textbox"],
                        elem_id="process-event-log",
                    ),
                    label="Event log",
                    described_by="process-runtime-helper",
                    role="log",
                )

            components["runtime_accordion"] = runtime_accordion
            components["transcription_timer"] = gr.Timer(value=2.0)

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
            - full_output (HighlightedText)
            - ic_output
            - ooc_output
            - stats_output
            - snippet_output
            - scroll_trigger
        """
        components = {}

        with gr.Group(visible=False, elem_id="process-results-section") as results_section:
            _a11y(
                gr.Markdown("### Step 4: Review Results", elem_id="process-review-heading"),
                label="Review results heading",
                role="heading",
            )
            
            # IMPROVEMENT: Use HighlightedText for a richer, color-coded transcript view.
            # UX-15: Syntax Highlighting for Transcript Output
            # Note: We use CSS classes defined in theme.py for specific styling
            # .transcript-timestamp, .transcript-speaker-dm, etc.
            # Gradio's HighlightedText is limited to background color.
            # We will use HTML for fine-grained control if possible, or stick to HighlightedText for now
            # as replacing it with HTML requires significant logic changes in app.py which are restricted.
            # However, we can improve the color map to match the theme.
            color_map = {
                "CHARACTER": "blue",     # Maps to Player
                "DM_NARRATION": "cyan",  # Maps to DM
                "NPC_DIALOGUE": "purple",# Maps to NPC
                "OOC_OTHER": "gray",     # Maps to OOC (gray instead of red)
            }
            components["full_output"] = _a11y(
                gr.HighlightedText(
                    label="Full Transcript (Color-Coded by Classification)",
                    color_map=color_map,
                    interactive=False,
                    show_legend=True,
                    elem_id="process-full-output",
                ),
                label="Full transcript with classifications",
                role="article",
            )

            # Plain text version with copy button for easy copying
            components["full_output_text"] = _a11y(
                gr.Textbox(
                    label="Full Transcript (Plain Text)",
                    lines=10,
                    info="Click the copy button to copy the entire transcript",
                    elem_id="process-full-output-text",
                ),
                label="Full transcript plain text",
            )

            components["ic_output"] = _a11y(
                gr.Textbox(
                    label="In-Character Transcript",
                    lines=10,
                    info="IC-only dialogue - click copy button to extract",
                    elem_id="process-ic-output",
                ),
                label="In-character transcript",
            )
            components["ooc_output"] = _a11y(
                gr.Textbox(
                    label="Out-of-Character Transcript",
                    lines=10,
                    info="OOC-only content - click copy button to extract",
                    elem_id="process-ooc-output",
                ),
                label="Out-of-character transcript",
            )
            components["stats_output"] = _a11y(
                gr.Markdown(elem_id="process-stats-output"),
                label="Processing statistics",
                role="status",
                live="polite",
            )
            components["snippet_output"] = _a11y(
                gr.Markdown(elem_id="process-snippet-output"),
                label="Snippet output",
                role="status",
                live="polite",
            )

        components["results_section"] = results_section

        # Auto-scroll JavaScript component (hidden, triggers when results appear)
        components["scroll_trigger"] = gr.HTML(visible=False)

        return components


# ============================================================================
# Resume from Intermediate Section
# ============================================================================

class ResumeFromIntermediateBuilder:
    """Builder for resume from intermediate outputs section."""

    def build(self) -> Dict[str, gr.Component]:
        """
        Build Resume from Intermediate section.

        Allows users to resume processing from saved intermediate outputs.
        """
        from src.ui.intermediate_resume_helper import discover_sessions_with_intermediates

        components = {}

        with gr.Accordion("🔄 Resume from Intermediate Outputs", open=False) as resume_accordion:
            _a11y(resume_accordion, label="Resume from intermediate outputs", role="group", elem_id="process-resume-accordion")
            _a11y(
                gr.Markdown(
                    """
                    Resume processing from a previously saved intermediate stage. This allows you to:
                    - Edit intermediate outputs manually and reprocess
                    - Test different backends on the same data
                    - Skip expensive stages that are already complete
                    """,
                    elem_id="process-resume-helper",
                ),
                label="Resume helper",
                role="note",
            )

            # Discover sessions button and dropdown
            with gr.Row():
                components["resume_refresh_btn"] = UIComponents.create_action_button(
                    "🔍 Find Sessions",
                    variant="secondary",
                    size="sm",
                    accessible_label="Find sessions with intermediate outputs",
                    aria_describedby="process-resume-helper",
                    elem_id="process-resume-refresh",
                )

            components["resume_session_dropdown"] = _a11y(
                gr.Dropdown(
                    label="Session to Resume",
                    choices=[],
                    value=None,
                    interactive=True,
                    info="Select a session with intermediate outputs",
                    elem_id="process-resume-session",
                ),
                label="Session to resume",
                described_by="process-resume-helper",
            )

            components["resume_stage_dropdown"] = _a11y(
                gr.Dropdown(
                    label="Resume from Stage",
                    choices=[
                        ("Stage 4: Merged Transcript → Run Diarization, Classification, Outputs", 4),
                        ("Stage 5: Diarization → Run Classification, Outputs", 5),
                        ("Stage 6: Classification → Regenerate Outputs Only", 6),
                    ],
                    value=5,
                    interactive=True,
                    info="Which stage to resume from",
                    elem_id="process-resume-stage",
                ),
                label="Resume from stage",
                described_by="process-resume-helper",
            )

            components["resume_session_info"] = _a11y(
                gr.Markdown(
                    value=StatusMessages.info(
                        "Session Info",
                        "Click 'Find Sessions' to discover available sessions, then select one to see details."
                    ),
                    elem_id="process-resume-info",
                ),
                label="Resume session information",
                role="status",
                live="polite",
            )

            with gr.Row():
                components["resume_process_btn"] = UIComponents.create_action_button(
                    "▶️ Resume Processing",
                    variant="primary",
                    size="lg",
                    accessible_label="Resume processing",
                    aria_describedby="process-resume-helper",
                    elem_id="process-resume-start",
                )

            components["resume_status"] = _a11y(
                gr.Markdown(
                    value="",
                    elem_id="process-resume-status",
                ),
                label="Resume status",
                role="status",
                live="polite",
            )

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
        all_components["campaign_badge"] = gr.Markdown(
            value=badge_value,
            elem_classes=["campaign-badge-sticky"]
        )

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

        resume_builder = ResumeFromIntermediateBuilder()
        all_components.update(resume_builder.build())

        return all_components
