"""
Event wiring for Process Session tab.

This module handles connecting UI components to their event handlers,
organizing all interactive behavior for the session processing workflow.

Architecture:
    - Centralized event management via ProcessSessionEventWiring class
    - Organized by functional area (upload, party, processing, preflight, polling)
    - Clean separation from UI construction and business logic

Example:
    >>> event_wiring = ProcessSessionEventWiring(
    ...     components=component_refs,
    ...     process_session_fn=process_session_fn,
    ...     preflight_fn=preflight_fn,
    ...     active_campaign_state=active_campaign_state,
    ... )
    >>> event_wiring.wire_all_events()
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional

import gradio as gr

from src.ui.helpers import StatusMessages
from src.ui.process_session_helpers import (
    validate_session_inputs,
    validate_session_id_realtime,
    render_processing_response,
    prepare_processing_status,
    poll_transcription_progress,
    poll_runtime_updates,
    poll_overall_progress,
    check_file_processing_history,
    update_party_display as update_party_display_helper,
)


class ProcessSessionEventWiring:
    """
    Manages event wiring for the Process Session tab.

    This class encapsulates all the event handler connections for the UI components,
    organizing them by functional area for maintainability.

    Attributes:
        components: Dictionary of all UI components keyed by name
        process_session_fn: Main session processing function
        preflight_fn: Preflight validation function
        active_campaign_state: Gradio state for active campaign ID

    Event Categories:
        - File Upload: Validation and history checking
        - Party Selection: Dynamic party character display
        - Processing: Main session processing workflow
        - Preflight: Pre-processing validation checks
        - Polling: Live progress updates during processing
    """

    def __init__(
        self,
        components: Dict[str, gr.Component],
        process_session_fn: Callable[..., Any],
        preflight_fn: Callable[..., Any],
        active_campaign_state: gr.State,
        cancel_fn: Optional[Callable[[str], str]] = None,
    ):
        """
        Initialize event wiring manager.

        Args:
            components: Dictionary of all UI components from ProcessSessionTabBuilder
            process_session_fn: Function to process sessions (from app.py)
            preflight_fn: Function to run preflight checks (from app.py)
            active_campaign_state: Gradio state containing active campaign ID
            cancel_fn: Optional function to cancel processing (from app.py)
        """
        self.components = components
        self.process_session_fn = process_session_fn
        self.preflight_fn = preflight_fn
        self.active_campaign_state = active_campaign_state
        self.cancel_fn = cancel_fn

    def wire_all_events(self) -> None:
        """
        Wire up all event handlers for the tab.

        This is the main entry point that connects all UI components to their
        respective event handlers. Call this after building UI components.

        Event wiring order:
            1. File upload events (validation, history)
            2. Session ID validation events (real-time)
            3. Party selection events (character display)
            4. Processing events (main workflow)
            5. Preflight events (validation)
            6. Polling events (live updates)
        """
        self._wire_file_upload_events()
        self._wire_session_id_validation_events()
        self._wire_party_selection_events()
        self._wire_processing_events()
        self._wire_cancel_events()
        self._wire_preflight_events()
        self._wire_polling_events()

    # -------------------------------------------------------------------------
    # File Upload Events
    # -------------------------------------------------------------------------

    def _wire_file_upload_events(self) -> None:
        """
        Wire events for file upload component.

        Sets up file validation and processing history checks that trigger
        when a user uploads an audio file.
        """
        def check_file_history(file):
            """Check if uploaded file was processed before."""
            warning_text, is_visible = check_file_processing_history(file)
            return gr.update(value=warning_text, visible=is_visible)

        self.components["audio_input"].change(
            fn=check_file_history,
            inputs=[self.components["audio_input"]],
            outputs=[self.components["file_warning_display"]],
        )

    # -------------------------------------------------------------------------
    # Session ID Validation Events
    # -------------------------------------------------------------------------

    def _wire_session_id_validation_events(self) -> None:
        """
        Wire events for real-time Session ID validation.

        Validates the session ID as the user types, providing immediate feedback
        about invalid characters or format issues.
        """
        self.components["session_id_input"].change(
            fn=validate_session_id_realtime,
            inputs=[self.components["session_id_input"]],
            outputs=[self.components["session_id_validation"]],
        )

    # -------------------------------------------------------------------------
    # Party Selection Events
    # -------------------------------------------------------------------------

    def _wire_party_selection_events(self) -> None:
        """
        Wire events for party selection dropdown.

        Updates the party character display when a user selects a different
        party configuration from the dropdown.
        """
        self.components["party_selection_input"].change(
            fn=update_party_display_helper,
            inputs=[self.components["party_selection_input"]],
            outputs=[self.components["party_characters_display"]],
        )

    # -------------------------------------------------------------------------
    # Processing Events
    # -------------------------------------------------------------------------

    def _wire_processing_events(self) -> None:
        """
        Wire events for the main processing button.

        Sets up the two-stage processing workflow:
            1. Prepare: Show initial status, validate inputs, clear event log
            2. Process: Run session processing pipeline with live updates

        The workflow uses a state variable (should_process_state) to gate
        the second stage based on validation results from the first stage.
        """
        def process_session_handler(
            audio_file,
            session_id,
            party_selection,
            character_names,
            player_names,
            num_speakers,
            language,
            skip_diarization,
            skip_classification,
            skip_snippets,
            skip_knowledge,
            transcription_backend,
            diarization_backend,
            classification_backend,
            campaign_id,
            enable_audit_mode,
            redact_prompts,
            generate_scenes,
            scene_summary_mode,
            should_proceed,
        ):
            """
            Handle session processing with validation.

            This wrapper validates all inputs before calling the main processing
            function. If validation fails, returns error messages without processing.

            Args:
                audio_file: Uploaded audio file
                session_id: Unique session identifier
                party_selection: Selected party configuration
                character_names: Comma-separated character names (Manual Entry only)
                player_names: Comma-separated player names (Manual Entry only)
                num_speakers: Expected number of speakers
                language: Transcription language
                skip_diarization: Whether to skip speaker diarization
                skip_classification: Whether to skip dialogue classification
                skip_snippets: Whether to skip snippet generation
                skip_knowledge: Whether to skip knowledge extraction
                transcription_backend: Selected transcription service
                diarization_backend: Selected diarization service
                classification_backend: Selected classification service
                campaign_id: Active campaign ID (or None)
                should_proceed: Gate variable from preparation stage

            Returns:
                Tuple of gr.update() objects for all output components
            """
            # Check gate variable - if False, validation failed in prep stage
            if not should_proceed:
                return (
                    gr.update(),  # status_output
                    gr.update(),  # results_section
                    gr.update(),  # full_output
                    gr.update(),  # ic_output
                    gr.update(),  # ooc_output
                    gr.update(),  # stats_output
                    gr.update(),  # snippet_output
                    gr.update(visible=False),  # scroll_trigger
                )

            # Validate inputs
            validation_errors = validate_session_inputs(
                audio_file,
                session_id,
                party_selection,
                character_names,
                player_names,
                num_speakers,
            )

            # If validation fails, show errors and abort
            if validation_errors:
                error_details = "\n".join(f"- {err}" for err in validation_errors)
                return (
                    StatusMessages.error(
                        "Validation Failed",
                        "Please fix the following issues before processing:",
                        error_details
                    ),
                    gr.update(visible=False),  # Hide results section
                    "",  # Clear outputs
                    "",
                    "",
                    StatusMessages.info("Statistics", "No statistics available."),
                    StatusMessages.info("Snippet Export", "No snippet information available."),
                    gr.update(visible=False),  # No scroll trigger
                )

            # All validation passed - proceed with processing
            response = self.process_session_fn(
                audio_file,
                session_id,
                party_selection,
                character_names,
                player_names,
                num_speakers,
                language,
                skip_diarization,
                skip_classification,
                skip_snippets,
                skip_knowledge,
                transcription_backend,
                diarization_backend,
                classification_backend,
                campaign_id,
                enable_audit_mode,
                redact_prompts,
                generate_scenes,
                scene_summary_mode,
            )

            # Render the processing response (format transcripts, stats, etc.)
            return render_processing_response(response)

        # Wire the process button with two-stage workflow
        self.components["process_btn"].click(
            fn=prepare_processing_status,
            inputs=[
                self.components["audio_input"],
                self.components["session_id_input"],
                self.components["party_selection_input"],
                self.components["character_names_input"],
                self.components["player_names_input"],
                self.components["num_speakers_input"],
            ],
            outputs=[
                self.components["status_output"],
                self.components["results_section"],
                self.components["should_process_state"],
                self.components["event_log_display"],
                self.components["cancel_btn"],
            ],
            queue=False,
        ).then(
            fn=process_session_handler,
            inputs=[
                self.components["audio_input"],
                self.components["session_id_input"],
                self.components["party_selection_input"],
                self.components["character_names_input"],
                self.components["player_names_input"],
                self.components["num_speakers_input"],
                self.components["language_input"],
                self.components["skip_diarization_input"],
                self.components["skip_classification_input"],
                self.components["skip_snippets_input"],
                self.components["skip_knowledge_input"],
                self.components["transcription_backend_input"],
                self.components["diarization_backend_input"],
                self.components["classification_backend_input"],
                self.active_campaign_state,
                self.components["enable_audit_mode_input"],
                self.components["redact_prompts_input"],
                self.components["generate_scenes_input"],
                self.components["scene_summary_mode_input"],
                self.components["should_process_state"],
            ],
            outputs=[
                self.components["status_output"],
                self.components["results_section"],
                self.components["full_output"],
                self.components["ic_output"],
                self.components["ooc_output"],
                self.components["stats_output"],
                self.components["snippet_output"],
                self.components["scroll_trigger"],
                self.components["cancel_btn"],
            ],
            queue=True,
        )

    # -------------------------------------------------------------------------
    # Cancel Events
    # -------------------------------------------------------------------------

    def _wire_cancel_events(self) -> None:
        """
        Wire events for the cancel button.

        The cancel button allows users to stop processing mid-execution.
        When clicked, it sets a cancel event that the pipeline checks periodically.
        """
        if self.cancel_fn and "cancel_btn" in self.components:
            def handle_cancel(session_id: str) -> str:
                """Handle cancel button click."""
                if not session_id:
                    return StatusMessages.warning("Cancel", "No session ID provided.")
                return StatusMessages.info("Cancel Requested", self.cancel_fn(session_id))

            self.components["cancel_btn"].click(
                fn=handle_cancel,
                inputs=[self.components["session_id_input"]],
                outputs=[self.components["status_output"]],
                queue=False,
            )

    # -------------------------------------------------------------------------
    # Preflight Events
    # -------------------------------------------------------------------------

    def _wire_preflight_events(self) -> None:
        """
        Wire events for preflight checks button.

        Preflight checks validate configuration without processing audio,
        useful for verifying party config, backends, and credentials before
        starting a long processing job.
        """
        def run_preflight_handler(
            party_selection,
            character_names,
            player_names,
            num_speakers,
            language,
            skip_diarization,
            skip_classification,
            transcription_backend,
            diarization_backend,
            classification_backend,
            campaign_id,
        ):
            """
            Run preflight validation checks.

            Args:
                party_selection: Selected party configuration
                character_names: Character names (Manual Entry only)
                player_names: Player names (Manual Entry only)
                num_speakers: Expected number of speakers
                language: Transcription language
                skip_diarization: Whether to skip diarization
                skip_classification: Whether to skip classification
                transcription_backend: Transcription service to validate
                diarization_backend: Diarization service to validate
                classification_backend: Classification service to validate
                campaign_id: Active campaign ID (or None)

            Returns:
                Tuple of (status message, results section update)
            """
            response = self.preflight_fn(
                party_selection,
                character_names,
                player_names,
                num_speakers,
                language,
                skip_diarization,
                skip_classification,
                transcription_backend,
                diarization_backend,
                classification_backend,
                campaign_id,
            )
            # Hide results section after preflight (not showing transcripts)
            return response, gr.update(visible=False)

        self.components["preflight_btn"].click(
            fn=run_preflight_handler,
            inputs=[
                self.components["party_selection_input"],
                self.components["character_names_input"],
                self.components["player_names_input"],
                self.components["num_speakers_input"],
                self.components["language_input"],
                self.components["skip_diarization_input"],
                self.components["skip_classification_input"],
                self.components["transcription_backend_input"],
                self.components["diarization_backend_input"],
                self.components["classification_backend_input"],
                self.active_campaign_state,
            ],
            outputs=[
                self.components["status_output"],
                self.components["results_section"],
            ],
            queue=False,
        )

    # -------------------------------------------------------------------------
    # Polling Events
    # -------------------------------------------------------------------------

    def _wire_polling_events(self) -> None:
        """
        Wire polling events for live progress updates.

        Sets up three polling mechanisms that run every 2 seconds via timer:
            1. Overall progress indicator (percentage, current stage, ETA)
            2. Transcription progress bar updates
            3. Runtime updates (stage progress + event log)

        These provide real-time feedback during long-running processing jobs.
        """
        # Overall progress polling (NEW: prominent progress indicator)
        self.components["transcription_timer"].tick(
            fn=poll_overall_progress,
            inputs=[self.components["session_id_input"]],
            outputs=[self.components["overall_progress_display"]],
            queue=False,
        )

        # Transcription progress polling
        self.components["transcription_timer"].tick(
            fn=poll_transcription_progress,
            inputs=[self.components["session_id_input"]],
            outputs=[self.components["transcription_progress"]],
            queue=False,
        )

        # Runtime updates polling (stage progress + event log)
        self.components["transcription_timer"].tick(
            fn=poll_runtime_updates,
            inputs=[
                self.components["session_id_input"],
                self.components["event_log_display"]
            ],
            outputs=[
                self.components["stage_progress_display"],
                self.components["event_log_display"]
            ],
            queue=False,
        )
