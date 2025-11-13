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
from src.ui.process_session_components import ProcessSessionTabBuilder
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
        # Use ProcessSessionTabBuilder to create all UI components
        tab_builder = ProcessSessionTabBuilder(
            available_parties=available_parties,
            initial_defaults=initial_defaults,
            campaign_badge_text=campaign_badge_text,
        )

        # Build all components using the builder
        component_refs = tab_builder.build_ui_components()

        # Extract component references for easier access in event handlers
        campaign_badge = component_refs["campaign_badge"]
        audio_input = component_refs["audio_input"]
        file_warning_display = component_refs["file_warning_display"]
        session_id_input = component_refs["session_id_input"]
        party_selection_input = component_refs["party_selection_input"]
        party_characters_display = component_refs["party_characters_display"]
        num_speakers_input = component_refs["num_speakers_input"]
        language_input = component_refs["language_input"]
        character_names_input = component_refs["character_names_input"]
        player_names_input = component_refs["player_names_input"]
        transcription_backend_input = component_refs["transcription_backend_input"]
        diarization_backend_input = component_refs["diarization_backend_input"]
        classification_backend_input = component_refs["classification_backend_input"]
        skip_diarization_input = component_refs["skip_diarization_input"]
        skip_classification_input = component_refs["skip_classification_input"]
        skip_snippets_input = component_refs["skip_snippets_input"]
        skip_knowledge_input = component_refs["skip_knowledge_input"]
        preflight_btn = component_refs["preflight_btn"]
        process_btn = component_refs["process_btn"]
        status_output = component_refs["status_output"]
        transcription_progress = component_refs["transcription_progress"]
        stage_progress_display = component_refs["stage_progress_display"]
        event_log_display = component_refs["event_log_display"]
        transcription_timer = component_refs["transcription_timer"]
        results_section = component_refs["results_section"]
        full_output = component_refs["full_output"]
        ic_output = component_refs["ic_output"]
        ooc_output = component_refs["ooc_output"]
        stats_output = component_refs["stats_output"]
        snippet_output = component_refs["snippet_output"]
        scroll_trigger = component_refs["scroll_trigger"]
        should_process_state = component_refs["should_process_state"]

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

    # Return the same structure as before for compatibility with app.py
    return_refs = {
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

    return available_parties, return_refs
