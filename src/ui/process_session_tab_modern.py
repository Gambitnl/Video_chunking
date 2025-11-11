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

        def _prepare_processing_outputs(
            audio_file,
            session_id,
            party_selection,
            character_names,
            player_names,
            num_speakers,
        ):
            """Validate inputs and prepare status output before processing."""
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
                        "Please resolve these issues before starting processing.",
                        error_details,
                    ),
                    gr.update(visible=False),
                    False,
                    "",  # Clear event log on error
                )

            return (
                StatusMessages.loading("Processing session"),
                gr.update(visible=False),
                True,
                "",  # Clear event log when starting new session
            )

        def _format_statistics(stats: Dict[str, Any], knowledge: Dict[str, Any]) -> str:
            if not stats:
                return StatusMessages.info("Statistics", "No statistics available.")

            duration = stats.get("total_duration_formatted") or f"{stats.get('total_duration_seconds', 0)} seconds"
            lines = [
                "### Session Statistics",
                f"{SI.INFO} Duration: {duration}",
                f"{SI.INFO} Segments: {stats.get('total_segments', 0)}",
                f"{SI.INFO} IC Segments: {stats.get('ic_segments', 0)}",
                f"{SI.INFO} OOC Segments: {stats.get('ooc_segments', 0)}",
            ]

            if knowledge:
                extracted = knowledge.get("extracted") or {}
                if extracted:
                    lines.append("")
                    lines.append("### Knowledge Extracted")
                    for key, count in extracted.items():
                        lines.append(f"- {key.replace('_', ' ').title()}: {count}")

            return "\n".join(lines)

        def _format_snippet_export(snippet: Dict[str, Any]) -> str:
            if not snippet:
                return StatusMessages.info("Snippet Export", "Snippet export disabled.")

            manifest_path = snippet.get("manifest")
            segments_dir = snippet.get("segments_dir")

            lines = [
                "### Snippet Export",
            ]

            if segments_dir:
                lines.append(f"{SI.SUCCESS} Segments saved to `{segments_dir}`.")
            if manifest_path:
                lines.append(f"- Manifest: `{manifest_path}`")

            return "\n".join(lines) if len(lines) > 1 else StatusMessages.info("Snippet Export", "No snippet data.")

        def _render_processing_response(response: Dict[str, Any]):
            # JavaScript to scroll to results section when it becomes visible
            scroll_js = """
            <script>
            setTimeout(function() {
                const resultsSection = document.getElementById('process-results-section');
                if (resultsSection) {
                    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            }, 100);
            </script>
            """

            if not isinstance(response, dict):
                return (
                    StatusMessages.error("Processing Failed", "Unexpected response from pipeline."),
                    gr.update(visible=False),
                    "",
                    "",
                    "",
                    StatusMessages.info("Statistics", "No statistics available."),
                    StatusMessages.info("Snippet Export", "No snippet information available."),
                    gr.update(visible=False),
                )

            if response.get("status") != "success":
                return (
                    StatusMessages.error(
                        "Processing Failed",
                        response.get("message", "Unable to process session."),
                        response.get("details", "")
                    ),
                    gr.update(visible=False),
                    response.get("full", ""),
                    response.get("ic", ""),
                    response.get("ooc", ""),
                    StatusMessages.info("Statistics", "No statistics available."),
                    StatusMessages.info("Snippet Export", "No snippet information available."),
                    gr.update(visible=False),
                )

            stats_markdown = _format_statistics(response.get("stats") or {}, response.get("knowledge") or {})
            snippet_markdown = _format_snippet_export(response.get("snippet") or {})

            return (
                StatusMessages.success("Processing Complete", response.get("message", "Session processed successfully.")),
                gr.update(visible=True),
                response.get("full", ""),
                response.get("ic", ""),
                response.get("ooc", ""),
                stats_markdown,
                snippet_markdown,
                gr.update(value=scroll_js, visible=True),
            )

        def validate_inputs(
            audio_file,
            session_id,
            party_selection,
            character_names,
            player_names,
            num_speakers,
        ):
            """Validate inputs before processing."""
            errors = []

            if not audio_file:
                errors.append("Upload a session audio file before processing.")
            else:
                file_name = getattr(audio_file, "name", None) or getattr(audio_file, "orig_name", None)
                if not file_name:
                    errors.append("Unable to read the uploaded audio file. Please try re-uploading.")
                else:
                    file_extension = Path(file_name).suffix.lower()
                    if file_extension and file_extension not in ALLOWED_AUDIO_EXTENSIONS:
                        allowed = ", ".join(ALLOWED_AUDIO_EXTENSIONS)
                        errors.append(f"Audio format {file_extension} is not supported. Allowed formats: {allowed}.")
                    try:
                        file_path = Path(file_name)
                        if not file_path.exists():
                            errors.append("Uploaded audio file could not be found on disk. Please upload it again.")
                    except OSError:
                        errors.append("Uploaded audio file path is invalid. Please upload the file again.")

            if not session_id or not session_id.strip():
                errors.append("Session ID is required.")
            else:
                session_id = session_id.strip()
                if not SESSION_ID_PATTERN.match(session_id):
                    errors.append("Session ID may only contain letters, numbers, underscores, and hyphens.")

            try:
                speaker_count = int(num_speakers)
            except (TypeError, ValueError):
                speaker_count = 0
                errors.append("Expected speakers must be a whole number between 2 and 10.")
            else:
                if speaker_count < 2:
                    errors.append("Expected speakers must be at least 2.")

            if party_selection == "Manual Entry":
                if not character_names or not character_names.strip():
                    errors.append("Enter at least one character name when using Manual Entry.")
                else:
                    character_list = [name.strip() for name in character_names.split(",") if name.strip()]
                    if not character_list:
                        errors.append("Character names cannot be empty or whitespace only.")
                    else:
                        deduped = {name.lower() for name in character_list}
                        if len(deduped) != len(character_list):
                            errors.append("Character names must be unique to avoid diarization conflicts.")
                    if player_names and player_names.strip():
                        player_list = [name.strip() for name in player_names.split(",") if name.strip()]
                        if len(player_list) != len(character_list):
                            errors.append("Number of player names must match the number of character names.")
            else:
                party_manager = PartyConfigManager()
                selected_party = party_manager.get_party(party_selection)
                if selected_party is None:
                    errors.append(f"Party '{party_selection}' could not be loaded. Refresh Campaign Launcher and try again.")
                elif not selected_party.characters:
                    errors.append(f"Party '{party_selection}' has no characters configured.")

            return errors

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

        def _poll_transcription_progress(session_id_value: str):
            snapshot = StatusTracker.get_snapshot()
            if not snapshot or not snapshot.get("processing"):
                return gr.update(value="", visible=False)

            active_session = snapshot.get("session_id")
            target_session = (session_id_value or "").strip()
            if target_session and active_session != target_session:
                return gr.update(value="", visible=False)

            stages = snapshot.get("stages") or []
            stage_three = next((stage for stage in stages if stage.get("id") == 3), None)
            if not stage_three:
                return gr.update(value="", visible=False)

            details = stage_three.get("details") or {}
            preview = details.get("last_chunk_preview") or ""
            if not preview.strip():
                return gr.update(value="", visible=False)

            chunks_transcribed = details.get("chunks_transcribed")
            total_chunks = details.get("total_chunks")
            percent = details.get("progress_percent")
            chunk_label = details.get("last_chunk_index") or chunks_transcribed or "?"
            timing_range = ""
            start_time = details.get("last_chunk_start")
            end_time = details.get("last_chunk_end")
            duration = details.get("last_chunk_duration")
            if isinstance(start_time, (int, float)) and isinstance(end_time, (int, float)):
                timing_range = f" ({start_time:.2f}s → {end_time:.2f}s"
                if isinstance(duration, (int, float)):
                    timing_range += f", {duration:.2f}s"
                timing_range += ")"

            progress_bits: List[str] = []
            if chunks_transcribed is not None and total_chunks:
                progress_bits.append(f"{chunks_transcribed}/{total_chunks}")
            if percent is not None:
                progress_bits.append(f"{percent}%")
            progress_line = " | ".join(progress_bits)

            lines = [
                "### Live Transcription Preview",
                f"{SI.PROCESSING} Chunk {chunk_label}{timing_range}",
            ]
            if progress_line:
                lines.append(progress_line)
            lines.extend([
                "",
                "```",
                preview.strip(),
                "```",
            ])
            return gr.update(value="\n".join(lines), visible=True)

        transcription_timer.tick(
            fn=_poll_transcription_progress,
            inputs=[session_id_input],
            outputs=[transcription_progress],
            queue=False,
        )

        def _poll_runtime_updates(session_id_value: str, current_log: str):
            """Poll for comprehensive runtime updates including stage progress and event log."""
            snapshot = StatusTracker.get_snapshot()

            # If no processing active, return empty updates
            if not snapshot or not snapshot.get("processing"):
                return gr.update(value="", visible=False), current_log

            # Check if session matches
            active_session = snapshot.get("session_id")
            target_session = (session_id_value or "").strip()
            if target_session and active_session != target_session:
                return gr.update(value="", visible=False), current_log

            # Build stage progress display
            stages = snapshot.get("stages") or []
            stage_lines = ["### Stage Progress"]

            for stage in stages:
                stage_id = stage.get("id", "?")
                stage_name = stage.get("name", "Unknown")
                stage_state = stage.get("state", "pending")
                stage_message = stage.get("message", "")
                details = stage.get("details") or {}

                # State icon
                state_icon = {
                    "pending": "⏸",
                    "running": SI.PROCESSING,
                    "completed": SI.COMPLETE,
                    "skipped": "⏭",
                    "failed": SI.ERROR,
                }.get(stage_state, "❓")

                # Build stage line
                stage_line = f"{state_icon} **Stage {stage_id}: {stage_name}** - {stage_state}"

                # Add timing info if available
                started_at = stage.get("started_at")
                ended_at = stage.get("ended_at")
                duration = stage.get("duration_seconds")

                if started_at and not ended_at:
                    stage_line += f" (started: {started_at})"
                elif duration:
                    stage_line += f" (duration: {duration:.2f}s)"

                stage_lines.append(stage_line)

                # Add message if present
                if stage_message:
                    stage_lines.append(f"  ↳ {stage_message}")

                # Add progress details for active stages
                if stage_state == "running" and details:
                    if "progress_percent" in details:
                        stage_lines.append(f"  ↳ Progress: {details['progress_percent']}%")
                    if "chunks_transcribed" in details and "total_chunks" in details:
                        stage_lines.append(
                            f"  ↳ Chunks: {details['chunks_transcribed']}/{details['total_chunks']}"
                        )

                stage_lines.append("")  # Empty line between stages

            # Build event log (append new events to existing log)
            events = snapshot.get("events") or []
            new_log_lines = []

            # Parse existing log to find last event timestamp to avoid duplicates
            last_logged_timestamp = None
            if current_log.strip():
                log_lines = current_log.strip().split("\n")
                for line in reversed(log_lines):
                    if line.startswith("["):
                        # Extract timestamp from line like "[2025-01-11 10:30:45]"
                        parts = line.split("]", 1)
                        if len(parts) > 1:
                            last_logged_timestamp = parts[0] + "]"
                            break

            # Add new events
            for event in events:
                timestamp = event.get("timestamp", "")
                event_type = event.get("type", "info")
                message = event.get("message", "")

                # Skip if already logged
                if last_logged_timestamp and timestamp <= last_logged_timestamp:
                    continue

                # Format event line
                type_prefix = {
                    "info": "ℹ",
                    "success": "✓",
                    "warning": "⚠",
                    "error": "✗",
                    "debug": "⚙",
                }.get(event_type, "•")

                event_line = f"[{timestamp}] {type_prefix} {message}"
                new_log_lines.append(event_line)

            # Append new events to existing log
            if new_log_lines:
                updated_log = current_log + "\n" + "\n".join(new_log_lines)
            else:
                updated_log = current_log

            # Limit log size to prevent excessive growth (keep last 500 lines)
            log_lines = updated_log.strip().split("\n")
            if len(log_lines) > 500:
                updated_log = "\n".join(log_lines[-500:])

            return (
                gr.update(value="\n".join(stage_lines), visible=True),
                updated_log
            )

        # Wire up enhanced runtime updates polling
        transcription_timer.tick(
            fn=_poll_runtime_updates,
            inputs=[session_id_input, event_log_display],
            outputs=[stage_progress_display, event_log_display],
            queue=False,
        )

        def update_party_display(party_id: str):
            """Display character names when a party is selected."""
            if not party_id or party_id == "Manual Entry":
                return gr.update(value="", visible=False)

            party_manager = PartyConfigManager()
            party = party_manager.get_party(party_id)

            if not party:
                return gr.update(value="", visible=False)

            char_lines = [f"**Characters**: {party.party_name}"]
            for char in party.characters:
                char_lines.append(f"- {char.name} ({char.class_name})")

            return gr.update(
                value="\n".join(char_lines),
                visible=True
            )

        def check_file_history(file):
            """Check if uploaded file was processed before."""
            if not file:
                return gr.update(value="", visible=False)

            from pathlib import Path

            # Get file path from Gradio file object
            file_path = Path(file.name) if hasattr(file, 'name') else Path(file)

            if not file_path.exists():
                return gr.update(value="", visible=False)

            tracker = FileProcessingTracker()
            existing_record = tracker.check_file(file_path)

            if not existing_record:
                # New file, no warning
                return gr.update(value="", visible=False)

            # File was processed before - show warning
            from datetime import datetime

            last_processed_date = datetime.fromisoformat(existing_record.last_processed)
            date_str = last_processed_date.strftime("%Y-%m-%d %H:%M")

            warning_lines = [
                f"### {SI.WARNING} File Previously Processed",
                f"",
                f"This file was last processed on **{date_str}**",
                f"- Session ID: `{existing_record.session_id}`",
                f"- Times processed: {existing_record.process_count}",
                f"- Last stage reached: {existing_record.processing_stage}",
                f"- Status: {existing_record.status}",
                f"",
                f"**Do you want to process it again?** Click 'Start Processing' to continue.",
            ]

            return gr.update(
                value="\n".join(warning_lines),
                visible=True
            )

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
