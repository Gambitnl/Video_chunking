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
        )
        event_wiring.wire_all_events()

    # Return party list and component references for cross-tab coordination
    # Component refs are already in the correct format from the builder
    return available_parties, component_refs
