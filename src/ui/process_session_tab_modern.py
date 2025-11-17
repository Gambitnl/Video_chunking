"""
Process Session Tab for D&D Session Processor.

This module provides the main UI tab for uploading and processing D&D session
recordings. It orchestrates the complete workflow from audio file upload through
transcript generation, speaker diarization, dialogue classification, and knowledge
extraction.

Architecture:
    This module follows a clean separation of concerns pattern:

    - **Orchestration** (this module): Campaign setup and module coordination
    - **UI Components**: `src.ui.process_session_components.ProcessSessionTabBuilder`
    - **Business Logic**: `src.ui.process_session_helpers` (validation, formatting, polling)
    - **Event Wiring**: `src.ui.process_session_events.ProcessSessionEventWiring`

Features:
    - Campaign-aware session processing with saved preferences
    - Audio file upload with format validation (.wav, .mp3, .m4a, .flac)
    - Party configuration management (pre-defined or manual entry)
    - Configurable pipeline stages (transcription, diarization, classification, etc.)
    - Live progress updates with stage-by-stage tracking
    - Real-time event logging for debugging
    - Preflight validation before processing
    - Results display with multiple transcript views (full, IC, OOC)

Workflow:
    1. User selects campaign (optional) - loads saved preferences
    2. User uploads audio file - validates format and checks history
    3. User configures session - party, speakers, language, pipeline stages
    4. User runs preflight checks (optional) - validates config and credentials
    5. User starts processing - pipeline executes with live updates
    6. User views results - transcripts, statistics, exports

Usage Example:
    >>> with gr.Blocks() as demo:
    >>>     parties, refs = create_process_session_tab_modern(
    ...         demo,
    ...         refresh_fn=lambda: {"cmp1": "My Campaign"},
    ...         process_fn=process_session_handler,
    ...         preflight_fn=preflight_checks_handler,
    ...         campaign_mgr=campaign_manager,
    ...         active_state=gr.State(value="cmp1"),
    ...         campaign_badge_text="My Campaign Active",
    ...         initial_campaign_name="My Campaign"
    ...     )
    >>> # Returns: (party_list, component_references)

Design Patterns:
    - **Builder Pattern**: UI construction via ProcessSessionTabBuilder
    - **Manager Pattern**: Event wiring via ProcessSessionEventWiring
    - **Helper Functions**: Extracted business logic in process_session_helpers
    - **Component References**: Dictionary-based component access for flexibility

See Also:
    - `src.ui.process_session_components`: UI component builders
    - `src.ui.process_session_helpers`: Business logic and validation
    - `src.ui.process_session_events`: Event handler wiring
    - `docs/ui/process_session_tab.md`: Architecture guide
"""
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
from src.ui.process_session_events import ProcessSessionEventWiring
from src.status_tracker import StatusTracker


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
    cancel_fn: Optional[Callable[[str], str]] = None,
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

        # Wire all event handlers using the event wiring manager
        event_wiring = ProcessSessionEventWiring(
            components=component_refs,
            process_session_fn=process_session_fn,
            preflight_fn=preflight_fn,
            active_campaign_state=active_campaign_state,
            cancel_fn=cancel_fn,
        )
        event_wiring.wire_all_events()

    # Return party list and component references for cross-tab coordination
    # Component refs are already in the correct format from the builder
    return available_parties, component_refs
