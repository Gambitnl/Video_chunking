"""Modern Process Session tab with campaign-aware workflow."""
from __future__ import annotations

from pathlib import Path
import re
from typing import Any, Callable, Dict, List, Optional, Tuple

import gradio as gr

from src.party_config import PartyConfigManager
from src.file_tracker import FileProcessingTracker
from src.ui.constants import StatusIndicators as SI
from src.ui.helpers import InfoText, Placeholders, StatusMessages, UIComponents
from src.status_tracker import StatusTracker
from src.ui.process_session_helpers import (
    validate_session_inputs,
    format_statistics_markdown,
    format_snippet_export_markdown,
    format_party_display,
    render_processing_response,
    prepare_processing_status,
    poll_transcription_progress,
    poll_runtime_updates,
    check_file_processing_history,
    update_party_display as update_party_display_helper,
)


ALLOWED_AUDIO_EXTENSIONS: Tuple[str, ...] = (".m4a", ".mp3", ".wav", ".flac")
SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


def create_workflow_header() -> gr.HTML:
    """Create a visual workflow stepper."""
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


def create_process_session_tab_modern(
    blocks: gr.Blocks,
    refresh_campaign_names: Callable[[], Dict[str, str]],
    process_session_fn: Callable[..., Any],
    preflight_fn: Callable[..., Any],
    campaign_manager,
    active_campaign_state: gr.State,
    *,
    campaign_badge_text: str,
    initial_campaign_name: str = "Manual Setup",
) -> Tuple[List[str], Dict[str, gr.components.Component]]:
    """Create the campaign-aware Process Session tab.

    Returns:
        Tuple of (available party identifiers, component references for cross-tab coordination)
    """
    party_manager = PartyConfigManager()
    available_parties = ["Manual Entry"] + party_manager.list_parties()

    campaign_names = refresh_campaign_names()

    # Default values when no campaign is loaded
    initial_defaults = {
        "party_selection": "Manual Entry" if "Manual Entry" in available_parties else (available_parties[0] if available_parties else None),
        "num_speakers": 4,
        "skip_diarization": False,
        "skip_classification": False,
        "skip_snippets": True,
        "skip_knowledge": False,
    }

    # If initial campaign is specified, load its settings
    if initial_campaign_name != "Manual Setup":
        selected_campaign_id = next(
            (cid for cid, name in campaign_names.items() if name == initial_campaign_name),
            None,
        )
        if selected_campaign_id:
            campaign = campaign_manager.get_campaign(selected_campaign_id)
            if campaign:
                initial_defaults.update(
                    {
                        "party_selection": campaign.party_id or "Manual Entry",
                        "num_speakers": campaign.settings.num_speakers,
                        "skip_diarization": campaign.settings.skip_diarization,
                        "skip_classification": campaign.settings.skip_classification,
                        "skip_snippets": campaign.settings.skip_snippets,
                        "skip_knowledge": campaign.settings.skip_knowledge,
                    }
                )

    with gr.Tab("Process Session"):
        create_workflow_header()

        gr.Markdown(
            """
            # Process Session Recording

            Upload an audio file, apply campaign defaults, and run the pipeline.
            """
        )

    badge_value = campaign_badge_text or StatusMessages.info(
        "Campaign",
        "No campaign selected. Use the Campaign Launcher above to choose one."
    )
    campaign_badge = gr.Markdown(value=badge_value)

    with gr.Group():
        gr.Markdown("### Step 1: Upload Audio")
        audio_input = gr.File(
            label="Session Audio File",
            file_types=[".m4a", ".mp3", ".wav", ".flac"],
        )

        file_warning_display = gr.Markdown(
            value="",
            visible=False,
        )

    with gr.Group():
        gr.Markdown("### Step 2: Configure Session")

        session_id_input = gr.Textbox(
            label="Session ID",
            placeholder=Placeholders.SESSION_ID,
            info=InfoText.SESSION_ID,
        )

        with gr.Row():
            party_selection_input = gr.Dropdown(
                label="Party Configuration",
                choices=available_parties,
                value=initial_defaults.get("party_selection") or "Manual Entry",
                info="Select an existing party profile or choose Manual Entry.",
            )

        party_characters_display = gr.Markdown(
            value="",
            visible=False,
        )

        with gr.Row():
            num_speakers_input = gr.Slider(
                minimum=2,
                maximum=10,
                value=initial_defaults.get("num_speakers", 4),
                step=1,
                label="Expected Speakers",
                info="Helps diarization accuracy. Typical table is 3 players + 1 DM.",
            )

            language_input = gr.Dropdown(
                label="Language",
                choices=["en", "nl"],
                value="nl",
                info="Select the language spoken in the session.",
            )

            character_names_input = gr.Textbox(
                label="Character Names (comma-separated)",
                placeholder=Placeholders.CHARACTER_NAME,
                info="Used when Manual Entry is selected.",
            )

            player_names_input = gr.Textbox(
                label="Player Names (comma-separated)",
                placeholder=Placeholders.PLAYER_NAME,
                info="Optional player name mapping for manual entry.",
            )

        with gr.Accordion("Advanced Backend Settings", open=False):
            transcription_backend_input = gr.Dropdown(
                label="Transcription Backend",
                choices=["whisper", "groq"],
                value="whisper",
                info="Use local Whisper or cloud Groq API.",
            )
            diarization_backend_input = gr.Dropdown(
                label="Diarization Backend",
                choices=["pyannote", "hf_api"],
                value="pyannote",
                info="Use local PyAnnote or cloud Hugging Face API.",
            )
            classification_backend_input = gr.Dropdown(
                label="Classification Backend",
                choices=["ollama", "groq"],
                value="ollama",
                info="Use local Ollama or cloud Groq API.",
            )

        with gr.Row():
                skip_diarization_input = gr.Checkbox(
                    label="Skip Speaker Identification",
                    value=initial_defaults.get("skip_diarization", False),
                    info="Saves time but all segments will be UNKNOWN.",
                )
                skip_classification_input = gr.Checkbox(
                    label="Skip IC/OOC Classification",
                    value=initial_defaults.get("skip_classification", False),
                    info="Disables in-character versus out-of-character separation.",
                )
                skip_snippets_input = gr.Checkbox(
                    label="Skip Snippet Export",
                    value=initial_defaults.get("skip_snippets", True),
                    info="Skip exporting WAV snippets to save disk space.",
                )
                skip_knowledge_input = gr.Checkbox(
                    label="Skip Knowledge Extraction",
                    value=initial_defaults.get("skip_knowledge", False),
                    info="Disable automatic quest/NPC extraction.",
                )

        with gr.Group():
            gr.Markdown("### Step 3: Process")

            preflight_btn = UIComponents.create_action_button(
                "Run Preflight Checks",
                variant="secondary",
                size="md",
                full_width=True,
            )

            process_btn = UIComponents.create_action_button(
                "Start Processing",
                variant="primary",
                size="lg",
                full_width=True,
            )

            status_output = gr.Markdown(
                value=StatusMessages.info(
                    "Ready",
                    "Provide a session ID and audio file, then click Start Processing."
                )
            )

            transcription_progress = gr.Markdown(
                value="",
                visible=False,
            )

            # Enhanced Runtime Updates Section
            with gr.Accordion("Runtime Updates & Event Log", open=False) as runtime_accordion:
                gr.Markdown("**Live processing status, stage progress, and detailed event log**")

                # Stage Progress Overview
                stage_progress_display = gr.Markdown(
                    value="",
                    visible=False,
                )

                # Persistent Event Log
                event_log_display = gr.Textbox(
                    label="Event Log",
                    lines=15,
                    max_lines=30,
                    value="",
                    interactive=False,
                    show_copy_button=True,
                    elem_classes=["event-log-textbox"],
                )

            transcription_timer = gr.Timer(value=2.0, active=True)

        with gr.Group(visible=False, elem_id="process-results-section") as results_section:
            gr.Markdown("### Step 4: Review Results")
            full_output = gr.Textbox(label="Full Transcript", lines=10)
            ic_output = gr.Textbox(label="In-Character Transcript", lines=10)
            ooc_output = gr.Textbox(label="Out-of-Character Transcript", lines=10)
            stats_output = gr.Markdown()
            snippet_output = gr.Markdown()

        # Auto-scroll JavaScript component (hidden, triggers when results appear)
        scroll_trigger = gr.HTML(visible=False)

        should_process_state = gr.State(value=False)

        # Use imported helper function
        _prepare_processing_outputs = prepare_processing_status

        # Use imported helper function
        _format_statistics = format_statistics_markdown

        # Use imported helper function
        _format_snippet_export = format_snippet_export_markdown

        # Use imported helper function
        _render_processing_response = render_processing_response

        # Use imported helper function
        validate_inputs = validate_session_inputs

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
            should_proceed,
        ):
            if not should_proceed:
                return (
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    gr.update(visible=False),
                )

            # Validate inputs first
            validation_errors = validate_inputs(
                audio_file,
                session_id,
                party_selection,
                character_names,
                player_names,
                num_speakers,
            )
            if validation_errors:
                error_details = "\n".join(f"- {err}" for err in validation_errors)
                return (
                    StatusMessages.error(
                        "Validation Failed",
                        "Please fix the following issues before processing:",
                        error_details
                    ),
                    gr.update(visible=False),
                    "",
                    "",
                    "",
                    StatusMessages.info("Statistics", "No statistics available."),
                    StatusMessages.info("Snippet Export", "No snippet information available."),
                    gr.update(visible=False),
                )

            response = process_session_fn(
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
            )
            return _render_processing_response(response)

        # Use imported helper function
        _poll_transcription_progress = poll_transcription_progress

        transcription_timer.tick(
            fn=_poll_transcription_progress,
            inputs=[session_id_input],
            outputs=[transcription_progress],
            queue=False,
        )

        # Use imported helper function
        _poll_runtime_updates = poll_runtime_updates

        # Wire up enhanced runtime updates polling
        transcription_timer.tick(
            fn=_poll_runtime_updates,
            inputs=[session_id_input, event_log_display],
            outputs=[stage_progress_display, event_log_display],
            queue=False,
        )

        # Use imported helper function
        update_party_display = update_party_display_helper

        def check_file_history(file):
            """Check if uploaded file was processed before."""
            # Use imported helper function and convert tuple result to gr.update
            warning_text, is_visible = check_file_processing_history(file)
            return gr.update(value=warning_text, visible=is_visible)

        audio_input.change(
            fn=check_file_history,
            inputs=[audio_input],
            outputs=[file_warning_display],
        )

        party_selection_input.change(
            fn=update_party_display,
            inputs=[party_selection_input],
            outputs=[party_characters_display],
        )

        process_btn.click(
            fn=_prepare_processing_outputs,
            inputs=[
                audio_input,
                session_id_input,
                party_selection_input,
                character_names_input,
                player_names_input,
                num_speakers_input,
            ],
            outputs=[
                status_output,
                results_section,
                should_process_state,
                event_log_display,
            ],
            queue=False,
        ).then(
            fn=process_session_handler,
            inputs=[
                audio_input,
                session_id_input,
                party_selection_input,
                character_names_input,
                player_names_input,
                num_speakers_input,
                language_input,
                skip_diarization_input,
                skip_classification_input,
                skip_snippets_input,
                skip_knowledge_input,
                transcription_backend_input,
                diarization_backend_input,
                classification_backend_input,
                active_campaign_state,
                should_process_state,
            ],
            outputs=[
                status_output,
                results_section,
                full_output,
                ic_output,
                ooc_output,
                stats_output,
                snippet_output,
                scroll_trigger,
            ],
            queue=True,
        )

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
            response = preflight_fn(
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
            return response, gr.update(visible=False)

        preflight_btn.click(
            fn=run_preflight_handler,
            inputs=[
                party_selection_input,
                character_names_input,
                player_names_input,
                num_speakers_input,
                language_input,
                skip_diarization_input,
                skip_classification_input,
                transcription_backend_input,
                diarization_backend_input,
                classification_backend_input,
                active_campaign_state,
            ],
            outputs=[
                status_output,
                results_section,
            ],
            queue=False,
        )

    component_refs = {
        "campaign_badge": campaign_badge,
        "preflight_btn": preflight_btn,
        "audio_input": audio_input,
        "file_warning_display": file_warning_display,
        "party_selection_input": party_selection_input,
        "party_characters_display": party_characters_display,
        "session_id_input": session_id_input,
        "character_names_input": character_names_input,
        "player_names_input": player_names_input,
        "num_speakers_input": num_speakers_input,
        "skip_diarization_input": skip_diarization_input,
        "skip_classification_input": skip_classification_input,
        "skip_snippets_input": skip_snippets_input,
        "skip_knowledge_input": skip_knowledge_input,
        "status_output": status_output,
        "transcription_progress": transcription_progress,
        "stage_progress_display": stage_progress_display,
        "event_log_display": event_log_display,
        "results_section": results_section,
        "full_output": full_output,
        "ic_output": ic_output,
        "ooc_output": ooc_output,
        "stats_output": stats_output,
        "snippet_output": snippet_output,
        "transcription_backend_input": transcription_backend_input,
        "diarization_backend_input": diarization_backend_input,
        "classification_backend_input": classification_backend_input,
    }

    return available_parties, component_refs
