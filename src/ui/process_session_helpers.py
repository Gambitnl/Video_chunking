"""
Helper functions for the Process Session UI tab.

This module contains validation, formatting, and polling logic extracted from
the main UI creation function for better testability, reusability, and maintainability.

Function Categories:
    - **Validation**: Input validation for session processing
    - **Formatting**: Markdown formatting for statistics, snippets, party displays
    - **Polling**: Live progress updates from StatusTracker
    - **Response Handling**: Processing response formatting and rendering

Functions:
    Validation:
        - validate_session_inputs: Validate all inputs before processing
        - _validate_session_id: Validate session ID format
        - _validate_audio_file: Validate audio file presence and format
        - _validate_party_config: Validate party configuration

    Formatting:
        - format_statistics_markdown: Format processing statistics
        - format_snippet_export_markdown: Format snippet export info
        - format_party_display: Format party character list
        - update_party_display: Update party display (wrapper)

    Polling:
        - poll_transcription_progress: Poll transcription progress from status file
        - poll_runtime_updates: Poll stage progress and event log
        - _parse_stage_progress: Parse stage status from StatusTracker
        - _parse_event_log: Parse event log entries

    Response Handling:
        - render_processing_response: Render complete processing response
        - prepare_processing_status: Prepare initial processing status
        - check_file_processing_history: Check if file was processed before

Design Philosophy:
    - Pure functions where possible (no side effects)
    - Comprehensive input validation with clear error messages
    - Gradio-aware (returns gr.update() for UI updates)
    - Status file polling for live updates (non-blocking)

See Also:
    - `src.ui.process_session_tab_modern`: Main orchestration
    - `src.ui.process_session_components`: UI component builders
    - `src.ui.process_session_events`: Event handler wiring
    - `src.status_tracker`: Status tracking infrastructure
"""

from datetime import datetime
from pathlib import Path
import re
from typing import Any, Callable, Dict, List, Optional, Tuple
import gradio as gr

from src.party_config import PartyConfigManager
from src.file_tracker import FileProcessingTracker
from src.status_tracker import StatusTracker
from src.ui.constants import StatusIndicators as SI
from src.ui.helpers import StatusMessages


# Constants from main module
ALLOWED_AUDIO_EXTENSIONS: Tuple[str, ...] = (".m4a", ".mp3", ".wav", ".flac")
SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


def validate_session_id_realtime(session_id: str) -> str:
    """
    Validate session ID in real-time and return status message.

    Args:
        session_id: User-provided session identifier

    Returns:
        Markdown-formatted validation status message (empty string if no input)
    """
    # Don't show anything if the field is empty
    if not session_id or not session_id.strip():
        return ""

    session_id = session_id.strip()

    # Check against pattern
    if SESSION_ID_PATTERN.match(session_id):
        return StatusMessages.success(
            "Valid",
            f"Session ID `{session_id}` is valid"
        )
    else:
        # Find invalid characters
        invalid_chars = set()
        for char in session_id:
            if not (char.isalnum() or char in "_-"):
                invalid_chars.add(char)

        if invalid_chars:
            invalid_str = " ".join(repr(c) for c in sorted(invalid_chars))
            return StatusMessages.error(
                "Invalid",
                f"Session ID contains invalid characters: {invalid_str}. Only letters, numbers, underscores (_), and hyphens (-) are allowed."
            )
        else:
            return StatusMessages.error(
                "Invalid",
                "Session ID format is invalid. Use only letters, numbers, underscores (_), and hyphens (-)."
            )


def validate_processing_readiness(
    audio_file,
    session_id: str,
    party_selection: str,
    character_names: str,
    player_names: str,
    num_speakers: int,
) -> Tuple[bool, str]:
    """
    Validate if all requirements are met to enable the Process button.

    Args:
        audio_file: Gradio file upload object
        session_id: User-provided session identifier
        party_selection: Selected party ID or "Manual Entry"
        character_names: Comma-separated character names
        player_names: Comma-separated player names
        num_speakers: Expected number of speakers

    Returns:
        Tuple of (is_ready: bool, checklist_markdown: str)
    """
    checks = []
    is_ready = True

    # Check 1: Audio file uploaded
    if audio_file:
        file_name = getattr(audio_file, "name", None) or getattr(audio_file, "orig_name", None)
        if file_name:
            file_extension = Path(file_name).suffix.lower()
            if file_extension in ALLOWED_AUDIO_EXTENSIONS:
                checks.append("- ✓ Audio file uploaded")
            else:
                checks.append(f"- ✗ Invalid audio format ({file_extension})")
                is_ready = False
        else:
            checks.append("- ✗ Audio file not readable")
            is_ready = False
    else:
        checks.append("- ✗ Audio file not uploaded")
        is_ready = False

    # Check 2: Session ID valid
    if session_id and session_id.strip() and SESSION_ID_PATTERN.match(session_id.strip()):
        checks.append("- ✓ Session ID valid")
    elif not session_id or not session_id.strip():
        checks.append("- ✗ Session ID required")
        is_ready = False
    else:
        checks.append("- ✗ Session ID invalid (use only letters, numbers, _, -)")
        is_ready = False

    # Check 3: Party configuration
    if party_selection and party_selection != "Manual Entry":
        # Using a pre-defined party
        checks.append(f"- ✓ Party configured ({party_selection})")
    elif party_selection == "Manual Entry":
        # Manual entry - check if character names are provided
        if character_names and character_names.strip():
            char_list = [c.strip() for c in character_names.split(",") if c.strip()]
            if len(char_list) > 0:
                checks.append(f"- ✓ {len(char_list)} character(s) specified")
            else:
                checks.append("- ✗ Character names required for Manual Entry")
                is_ready = False
        else:
            checks.append("- ⚠️ Character names recommended for Manual Entry")
            # Don't block processing, but warn
    else:
        checks.append("- ✗ Party selection required")
        is_ready = False

    # Check 4: Speaker count reasonable
    try:
        speakers = int(num_speakers)
        if 2 <= speakers <= 10:
            checks.append(f"- ✓ Expected speakers: {speakers}")
        else:
            checks.append(f"- ⚠️ Speaker count unusual ({speakers})")
            # Don't block, just warn
    except (ValueError, TypeError):
        checks.append("- ✗ Speaker count invalid")
        is_ready = False

    # Build checklist markdown
    if is_ready:
        header = "### ✓ Ready to Process\n\n"
    else:
        header = "### ⚠️ Configuration Incomplete\n\n"

    checklist = header + "\n".join(checks)

    return is_ready, checklist


def _utcnow() -> datetime:
    """Return the current UTC time (isolated for testing)."""

    return datetime.utcnow()


def _parse_timestamp(value: Optional[str]) -> Optional[datetime]:
    """Parse an ISO-8601 timestamp, tolerating a trailing Z suffix."""

    if not value:
        return None

    cleaned = value[:-1] if value.endswith("Z") else value
    try:
        return datetime.fromisoformat(cleaned)
    except ValueError:
        return None


def _format_duration(seconds: Optional[float]) -> str:
    """Format a duration in seconds into a human-readable string."""

    if seconds is None:
        return "n/a"

    total_seconds = int(max(0, round(seconds)))
    minutes, secs = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)

    if hours:
        return f"{hours}h {minutes}m {secs}s"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def _stage_elapsed_seconds(stage: Dict[str, Any], now: datetime) -> Optional[float]:
    """Return elapsed seconds for a stage using duration or timestamps."""

    if stage.get("duration_seconds") is not None:
        try:
            return float(stage["duration_seconds"])
        except (TypeError, ValueError):
            return None

    started_at = _parse_timestamp(stage.get("started_at"))
    ended_at = _parse_timestamp(stage.get("ended_at")) or now

    if not started_at:
        return None

    return (ended_at - started_at).total_seconds()


def _compute_progress_timings(snapshot: Dict[str, Any], total_stages: int) -> Tuple[Optional[float], Optional[float], Optional[str]]:
    """Compute elapsed time, ETA, and next stage name from the snapshot."""

    stages = snapshot.get("stages") or []
    now = _utcnow()

    completed_count = len([s for s in stages if s.get("state") == "completed"])
    running_stage = next((s for s in stages if s.get("state") == "running"), None)
    running_stage_id = running_stage.get("id") if running_stage else None

    # Sum completed durations and include the running stage so ETA reflects work in progress
    completed_seconds = sum(
        filter(None, (_stage_elapsed_seconds(stage, now) for stage in stages if stage.get("state") == "completed"))
    )

    running_seconds = _stage_elapsed_seconds(running_stage, now) if running_stage else 0

    active_stage_count = completed_count + (1 if running_stage else 0)
    average_stage_duration = None

    if active_stage_count:
        average_stage_duration = (completed_seconds + running_seconds) / active_stage_count

    remaining_stages = max(total_stages - active_stage_count, 0)
    eta_seconds = None

    if average_stage_duration is not None and remaining_stages:
        eta_seconds = average_stage_duration * remaining_stages

    started_at = _parse_timestamp(snapshot.get("started_at"))
    elapsed_seconds = (now - started_at).total_seconds() if started_at else None

    # Identify the next stage for user awareness
    next_stage_name = None
    if running_stage_id:
        for stage in stages:
            if stage.get("state") in {"skipped", "completed"}:
                continue
            if stage.get("id") == running_stage_id:
                continue
            next_stage_name = stage.get("name")
            break

    return elapsed_seconds, eta_seconds, next_stage_name


# ============================================================================
# Validation Functions
# ============================================================================

def validate_session_inputs(
    audio_file,
    session_id: str,
    party_selection: str,
    character_names: str,
    player_names: str,
    num_speakers: int,
) -> List[str]:
    """
    Validate all inputs before processing.

    Args:
        audio_file: Gradio file upload object
        session_id: User-provided session identifier
        party_selection: Selected party ID or "Manual Entry"
        character_names: Comma-separated character names
        player_names: Comma-separated player names
        num_speakers: Expected number of speakers

    Returns:
        List of error messages (empty if validation passes)
    """
    errors = []

    # Audio file validation
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

    # Session ID validation
    if not session_id or not session_id.strip():
        errors.append("Session ID is required.")
    else:
        session_id = session_id.strip()
        if not SESSION_ID_PATTERN.match(session_id):
            errors.append("Session ID may only contain letters, numbers, underscores, and hyphens.")

    # Speaker count validation
    try:
        speaker_count = int(num_speakers)
        if not 2 <= speaker_count <= 10:
            errors.append("Expected speakers must be a whole number between 2 and 10.")
    except (TypeError, ValueError):
        errors.append("Expected speakers must be a valid whole number.")

    # Party/character validation
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


# ============================================================================
# Formatting Functions
# ============================================================================

def format_statistics_markdown(stats: Dict[str, Any], knowledge: Dict[str, Any]) -> str:
    """
    Format session statistics as markdown.

    Args:
        stats: Statistics dictionary from pipeline results
        knowledge: Knowledge extraction results

    Returns:
        Formatted markdown string
    """
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


def format_snippet_export_markdown(snippet: Dict[str, Any]) -> str:
    """
    Format snippet export information as markdown.

    Args:
        snippet: Snippet export dictionary

    Returns:
        Formatted markdown string
    """
    if not snippet:
        return StatusMessages.info("Snippet Export", "Snippet export disabled.")

    manifest_path = snippet.get("manifest")
    segments_dir = snippet.get("segments_dir")

    lines = ["### Snippet Export"]

    if segments_dir:
        lines.append(f"{SI.SUCCESS} Segments saved to `{segments_dir}`.")
    if manifest_path:
        lines.append(f"- Manifest: `{manifest_path}`")

    return "\n".join(lines) if len(lines) > 1 else StatusMessages.info("Snippet Export", "No snippet data.")


def format_party_display(party_id: str) -> Tuple[str, bool]:
    """
    Format party character information for display.

    Args:
        party_id: Party identifier

    Returns:
        Tuple of (markdown string, is_visible)
    """
    if not party_id or party_id == "Manual Entry":
        return "", False

    party_manager = PartyConfigManager()
    party = party_manager.get_party(party_id)

    if not party:
        return "", False

    char_lines = [f"**Characters**: {party.party_name}"]
    for char in party.characters:
        char_lines.append(f"- {char.name} ({char.class_name})")

    return "\n".join(char_lines), True


# ============================================================================
# Response Rendering Functions
# ============================================================================

def render_processing_response(response: Dict[str, Any]) -> Tuple:
    """
    Render pipeline processing response for UI display.

    Args:
        response: Response dictionary from process_session function

    Returns:
        Tuple of (status_md, results_visible, full, full_text, ic, ooc, stats_md, snippet_md, scroll_js, cancel_btn_update)

    Implementation Notes (2025-11-18):
        BUG-20251103-007: Improved auto-scroll reliability
        - Increased initial delay from 100ms to 300ms for Gradio rendering
        - Added retry logic (5 attempts, 200ms intervals) for robustness
        - Checks both element existence AND visibility (offsetParent !== null)
        - Handles edge cases where results section renders slowly

    Implementation Notes (2025-11-22):
        UX-14: Added full_text output for copy button support
        - Returns plain text version of full transcript for easy copying
    """
    # JavaScript to scroll to results section
    # Uses retry logic to handle Gradio's rendering delays
    scroll_js = """
    <script>
    (function() {
        let attempts = 0;
        const maxAttempts = 5;
        const retryInterval = 200; // ms

        function tryScroll() {
            const resultsSection = document.getElementById('process-results-section');
            if (resultsSection && resultsSection.offsetParent !== null) {
                // Element exists and is visible
                resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
                return;
            }

            attempts++;
            if (attempts < maxAttempts) {
                setTimeout(tryScroll, retryInterval);
            }
        }

        // Initial attempt after short delay for DOM updates
        setTimeout(tryScroll, 300);
    })();
    </script>
    """

    if not isinstance(response, dict):
        return (
            StatusMessages.error("Processing Failed", "Unexpected response from pipeline."),
            gr.update(visible=False),
            None, # highlighted_transcript
            "",  # full_text
            "",  # ic
            "",  # ooc
            StatusMessages.info("Statistics", "No statistics available."),
            StatusMessages.info("Snippet Export", "No snippet information available."),
            gr.update(visible=False),
            gr.update(visible=False),  # Hide cancel button when processing completes
        )

    if response.get("status") != "success":
        return (
            StatusMessages.error(
                "Processing Failed",
                response.get("message", "Unable to process session."),
                response.get("details", "")
            ),
            gr.update(visible=False),
            response.get("highlighted_transcript") or None,
            response.get("full", ""),  # full_text
            response.get("ic", ""),
            response.get("ooc", ""),
            StatusMessages.info("Statistics", "No statistics available."),
            StatusMessages.info("Snippet Export", "No snippet information available."),
            gr.update(visible=False),
            gr.update(visible=False),  # Hide cancel button when processing fails
        )

    stats_markdown = format_statistics_markdown(
        response.get("stats") or {},
        response.get("knowledge") or {}
    )
    snippet_markdown = format_snippet_export_markdown(response.get("snippet") or {})

    return (
        StatusMessages.success("Processing Complete", response.get("message", "Session processed successfully.")),
        gr.update(visible=True),
        response.get("highlighted_transcript") or [], # Use new highlighted data for full_output
        response.get("full", ""),  # full_text for copy button
        response.get("ic", ""),
        response.get("ooc", ""),
        stats_markdown,
        snippet_markdown,
        gr.update(value=scroll_js, visible=True),
        gr.update(visible=False),  # Hide cancel button when processing succeeds
    )


def prepare_processing_status(
    audio_file,
    session_id: str,
    party_selection: str,
    character_names: str,
    player_names: str,
    num_speakers: int,
) -> Tuple:
    """
    Validate inputs and prepare UI status before processing.

    Returns:
        Tuple of (status_message, results_section_update, should_proceed_flag, event_log_clear, cancel_btn_update)
    """
    validation_errors = validate_session_inputs(
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
            gr.update(visible=False),  # Hide cancel button on validation error
        )

    return (
        StatusMessages.loading("Processing session"),
        gr.update(visible=False),
        True,
        "",  # Clear event log when starting new session
        gr.update(visible=True),  # Show cancel button when processing starts
    )


# ============================================================================
# Status Polling Functions
# ============================================================================

def poll_transcription_progress(session_id_value: str) -> gr.update:
    """
    Poll the status tracker for live transcription progress.

    Args:
        session_id_value: Target session ID to monitor

    Returns:
        Gradio update for progress display
    """
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


def poll_runtime_updates(session_id_value: str, current_log: str) -> Tuple:
    """
    Poll for comprehensive runtime updates including stage progress and event log.

    Args:
        session_id_value: Target session ID
        current_log: Current log content

    Returns:
        Tuple of (stage_progress_update, updated_log)
    """
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
                    last_logged_timestamp = parts[0][1:]
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


def poll_overall_progress(session_id_value: str) -> gr.update:
    """
    Poll for overall session progress with percentage completion.

    Args:
        session_id_value: Target session ID

    Returns:
        Gradio update for overall progress display
    """
    snapshot = StatusTracker.get_snapshot()

    # If no processing active, hide progress indicator
    if not snapshot or not snapshot.get("processing"):
        return gr.update(value="", visible=False)

    # Check if session matches
    active_session = snapshot.get("session_id")
    target_session = (session_id_value or "").strip()
    if target_session and active_session != target_session:
        return gr.update(value="", visible=False)

    # Calculate overall progress
    stages = snapshot.get("stages") or []

    # Count stages (excluding skipped ones from total)
    total_stages = len([s for s in stages if s.get("state") != "skipped"])
    completed_stages = len([s for s in stages if s.get("state") == "completed"])
    failed_stages = len([s for s in stages if s.get("state") == "failed"])

    # Calculate percentage
    if total_stages > 0:
        overall_percent = int((completed_stages / total_stages) * 100)
    else:
        overall_percent = 0

    # Get current stage info
    current_stage_id = snapshot.get("current_stage")
    current_stage_name = "Initializing"
    current_stage_details = {}

    if current_stage_id:
        current_stage = next((s for s in stages if s.get("id") == current_stage_id), None)
        if current_stage:
            current_stage_name = current_stage.get("name", "Processing")
            current_stage_details = current_stage.get("details") or {}

    # Build HTML display with visual progress bar
    html_parts = []
    html_parts.append('<div style="padding: 1rem; background: #f9fafb; border-radius: 8px; border: 1px solid #e5e7eb;">')
    html_parts.append('<h3 style="margin: 0 0 1rem 0; color: #111827;">Overall Progress</h3>')

    # Visual progress bar
    html_parts.append('<div class="progress-bar" style="height: 12px; margin-bottom: 0.5rem;">')
    html_parts.append(f'<div class="progress-fill" style="width: {overall_percent}%;"></div>')
    html_parts.append('</div>')
    html_parts.append(f'<p style="text-align: center; font-weight: 600; color: #6366f1; margin: 0.5rem 0 1rem 0; font-size: 1.1rem;">{overall_percent}%</p>')

    # Current stage info
    if failed_stages > 0:
        html_parts.append(f'<p style="color: #dc2626; font-weight: 600; margin: 0.5rem 0;">{SI.ERROR} Status: Failed at {current_stage_name}</p>')
    elif current_stage_id:
        html_parts.append(f'<p style="color: #6366f1; font-weight: 600; margin: 0.5rem 0;">{SI.PROCESSING} Current Stage: {current_stage_name}</p>')

        # Add stage-specific progress if available
        if "progress_percent" in current_stage_details:
            stage_percent = current_stage_details["progress_percent"]
            html_parts.append(f'<p style="margin: 0.25rem 0 0.25rem 1.5rem; color: #6b7280;">Stage Progress: {stage_percent}%</p>')

        if "chunks_transcribed" in current_stage_details and "total_chunks" in current_stage_details:
            chunks_done = current_stage_details["chunks_transcribed"]
            chunks_total = current_stage_details["total_chunks"]
            html_parts.append(f'<p style="margin: 0.25rem 0 0.25rem 1.5rem; color: #6b7280;">Chunks: {chunks_done}/{chunks_total}</p>')

        if "eta_minutes" in current_stage_details:
            eta_minutes = current_stage_details["eta_minutes"]
            html_parts.append(f'<p style="margin: 0.25rem 0 0.25rem 1.5rem; color: #6b7280;">ETA: {eta_minutes} minutes</p>')
    else:
        html_parts.append(f'<p style="color: #6b7280; margin: 0.5rem 0;">{SI.INFO} Waiting to start processing...</p>')

    # Summary stats
    html_parts.append(f'<p style="font-weight: 600; margin: 1rem 0 0.5rem 0; color: #111827;">Progress: {completed_stages}/{total_stages} stages completed</p>')

    # High-level timing summary using completed durations
    elapsed_seconds, eta_seconds, next_stage_name = _compute_progress_timings(snapshot, total_stages)

    if elapsed_seconds is not None:
        html_parts.append(f'<p style="margin: 0.25rem 0; color: #6b7280;">{SI.INFO} Elapsed: {_format_duration(elapsed_seconds)}</p>')

    if eta_seconds is not None:
        html_parts.append(f'<p style="margin: 0.25rem 0; color: #6b7280;">{SI.INFO} ETA: ~{_format_duration(eta_seconds)} remaining</p>')

    if next_stage_name:
        html_parts.append(f'<p style="margin: 0.25rem 0; color: #6b7280;">{SI.INFO} Next: {next_stage_name}</p>')

    html_parts.append('</div>')

    return gr.update(value="".join(html_parts), visible=True)


# ============================================================================
# File History Functions
# ============================================================================

def check_file_processing_history(file) -> Tuple[str, bool]:
    """
    Check if uploaded file was previously processed.

    Args:
        file: Gradio file upload object

    Returns:
        Tuple of (warning_markdown, is_visible)
    """
    if not file:
        return "", False

    # Get file path from Gradio file object
    file_path = Path(file.name) if hasattr(file, 'name') else Path(file)

    if not file_path.exists():
        return "", False

    tracker = FileProcessingTracker()
    existing_record = tracker.check_file(file_path)

    if not existing_record:
        # New file, no warning
        return "", False

    # File was processed before - show warning
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

    return "\n".join(warning_lines), True


# ============================================================================
# UI Update Functions
# ============================================================================

def update_party_display(party_id: str) -> gr.update:
    """
    Display character names when a party is selected.

    Args:
        party_id: Party identifier

    Returns:
        Gradio update for party display component
    """
    markdown, visible = format_party_display(party_id)
    return gr.update(
        value=markdown,
        visible=visible
    )
