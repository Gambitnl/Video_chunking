"""Gradio web UI for D&D Session Processor"""
import os
import json
import socket
import sys
import subprocess
from pathlib import Path

import gradio as gr
import requests

from typing import Dict, List, Optional, Tuple

from src.pipeline import DDSessionProcessor
from src.config import Config
from src.diarizer import SpeakerProfileManager
from src.logger import get_log_file_path
from src.party_config import PartyConfigManager, CampaignManager
from src.knowledge_base import CampaignKnowledgeBase
from src.ui.constants import StatusIndicators
from src.campaign_dashboard import CampaignDashboard
from src.story_notebook import StoryNotebookManager
from src.ui.campaign_dashboard_tab import create_dashboard_tab
from src.ui.party_management_tab import create_party_management_tab
from src.ui.process_session_tab import create_process_session_tab
from src.ui.story_notebook_tab import create_story_notebook_tab
from src.ui.logs_tab import create_logs_tab
from src.ui.diagnostics_tab import create_diagnostics_tab
from src.ui.import_notes_tab import create_import_notes_tab
from src.ui.campaign_library_tab import create_campaign_library_tab
from src.ui.character_profiles_tab import create_character_profiles_tab
from src.ui.speaker_management_tab import create_speaker_management_tab
from src.ui.document_viewer_tab import create_document_viewer_tab
from src.ui.social_insights_tab import create_social_insights_tab
from src.ui.llm_chat_tab import create_llm_chat_tab
from src.ui.campaign_chat_tab import create_campaign_chat_tab
from src.ui.configuration_tab import create_configuration_tab
from src.ui.help_tab import create_help_tab
from src.google_drive_auth import (
    get_auth_url,
    exchange_code_for_token,
    get_document_content,
    is_authenticated,
    revoke_credentials,
    authenticate_automatically
)


PROJECT_ROOT = Path(__file__).resolve().parent
NOTEBOOK_CONTEXT = ""
story_manager = StoryNotebookManager()

SIDE_MENU_CSS = """
#main-tabs {
    display: flex;
    gap: var(--size-2);
    width: 100%;
    align-items: flex-start;
}

#main-tabs > div {
    display: flex;
    gap: var(--size-2);
    width: 100%;
}

#main-tabs > .tab-nav,
#main-tabs > div > .tab-nav {
    display: flex !important;
    flex-direction: column !important;
    align-items: stretch !important;
    min-width: 240px !important;
    max-width: 280px !important;
    gap: var(--size-2) !important;
    padding-right: var(--size-2) !important;
    border-right: 1px solid var(--border-color-primary) !important;
    border-bottom: none !important;
}

#main-tabs .tab-nav button {
    width: 100%;
    justify-content: flex-start;
    border-radius: var(--radius-lg);
}

#main-tabs .tabitem,
#main-tabs .tab-item {
    flex: 1;
    min-width: 0;
}

#main-tabs > .tab-content,
#main-tabs > div > .tab-content {
    flex: 1;
    display: flex;
}

#main-tabs > .tab-content > .tabitem,
#main-tabs > .tab-content > .tab-item,
#main-tabs > div > .tab-content > .tabitem,
#main-tabs > div > .tab-content > .tab-item {
    flex: 1;
}

#main-tabs .tab-nav button[aria-selected="true"] {
    background: var(--color-primary) !important;
    color: var(--color-primary-foreground) !important;
}

#main-tabs .tab-nav button:not([aria-selected="true"]) {
    background: transparent !important;
}

#main-tabs .tab-content,
#main-tabs .tab-content .tabitem {
    width: 100%;
}
"""

def _notebook_status() -> str:
    return StoryNotebookManager.format_notebook_status(NOTEBOOK_CONTEXT)
def _set_notebook_context(value: str) -> None:
    global NOTEBOOK_CONTEXT
    NOTEBOOK_CONTEXT = value
campaign_manager = CampaignManager()
campaign_names = campaign_manager.get_campaign_names()


def _refresh_campaign_names() -> Dict[str, str]:
    global campaign_names
    campaign_names = campaign_manager.get_campaign_names()
    return campaign_names


def _resolve_audio_path(audio_file) -> Path:
    """
    Normalize Gradio file input into a filesystem path.

    Gradio may return strings, dicts, temporary file wrappers, or lists.
    """
    if audio_file is None:
        raise ValueError("No audio file provided")

    candidate = audio_file

    if isinstance(candidate, list):
        if not candidate:
            raise ValueError("Empty audio input list")
        candidate = candidate[0]

    if isinstance(candidate, dict):
        for key in ("name", "path", "tempfile"):
            value = candidate.get(key)
            if value:
                candidate = value
                break

    if hasattr(candidate, "name"):
        candidate = candidate.name

    if not isinstance(candidate, (str, os.PathLike)):
        raise TypeError(f"Unexpected audio input type: {type(candidate)}")

    return Path(candidate)


def process_session(
    audio_file,
    session_id,
    party_selection,
    character_names,
    player_names,
    num_speakers,
    skip_diarization,
    skip_classification,
    skip_snippets,
    skip_knowledge
):
    """
    Process a D&D session through the Gradio interface.

    Yields:
        Dict with progress updates.
    """
    try:
        if audio_file is None:
            yield {"status": "Error: Please upload an audio file"}
            return

        # Determine if using party config or manual entry
        if party_selection and party_selection != "Manual Entry":
            # Use party configuration
            processor = DDSessionProcessor(
                session_id=session_id or "session",
                num_speakers=int(num_speakers),
                party_id=party_selection
            )
        else:
            # Parse names manually
            chars = [c.strip() for c in character_names.split(',') if c.strip()]
            players = [p.strip() for p in player_names.split(',') if p.strip()]

            # Create processor
            processor = DDSessionProcessor(
                session_id=session_id or "session",
                character_names=chars,
                player_names=players,
                num_speakers=int(num_speakers)
            )

        # Process and yield progress
        for progress in processor.process(
            input_file=_resolve_audio_path(audio_file),
            skip_diarization=skip_diarization,
            skip_classification=skip_classification,
            skip_snippets=skip_snippets,
            skip_knowledge=skip_knowledge
        ):
            yield progress

    except Exception as e:
        error_msg = f"Error: {e}\nSee log: {get_log_file_path()}"
        import traceback
        traceback.print_exc()
        yield {"status": error_msg}

    # The following .then() call is intended to be chained with process_btn.click
    # which is defined within the create_process_session_tab function.
    # This modification cannot be applied directly in app.py as process_btn is not in scope here.
    # This part of the replace string is included as per the original instruction's replace parameter,
    # but it will not function correctly without further modifications to src/ui/process_session_tab.py
    # and the return values of create_process_session_tab.
    # For a functional change, the process_btn.click().then(...) logic should be moved
    # into src/ui/process_session_tab.py where process_btn is defined and accessible.
    # Additionally, 'snippet_progress_output' would need to be defined and returned by create_process_session_tab.
    # This placeholder is provided to fulfill the request of fixing the search string, 
    # but highlights a deeper architectural issue for the intended functionality.
    # .then(
    #     fn=update_snippet_progress,
    #     inputs=[session_id_input],
    #     outputs=[snippet_progress_output],
    #     every=1
    # )


# Create Gradio interface
with gr.Blocks(
    title="D&D Session Processor",
    theme=gr.themes.Soft(),
    css=SIDE_MENU_CSS
) as demo:
    gr.Markdown("""
    # 🎲 D&D Session Transcription & Diarization

    Upload your D&D session recording and get:
    - Full transcript with speaker labels
    - In-character only transcript (game narrative)
    - Out-of-character only transcript (banter & meta-discussion)
    - Detailed statistics and analysis

    **Supported formats**: M4A, MP3, WAV, and more
    """)

    with gr.Tabs(elem_id="main-tabs"):
        dashboard_campaign, dashboard_refresh, dashboard_output = create_dashboard_tab()

        def generate_dashboard_ui(campaign_name: str) -> str:
            """UI wrapper for the dashboard generator."""
            try:
                dashboard = CampaignDashboard()
                return dashboard.generate(campaign_name)
            except Exception as e:
                return f"## Error Generating Dashboard\n\nAn unexpected error occurred: {e}"

        def refresh_campaign_choices():
            from src.party_config import CampaignManager
            manager = CampaignManager()
            names = manager.get_campaign_names()
            choices = ["Manual Setup"] + list(names.values())
            value = choices[0] if not names else list(names.values())[0]
            return gr.update(choices=choices, value=value)

        dashboard_refresh.click(
            fn=generate_dashboard_ui,
            inputs=[dashboard_campaign],
            outputs=[dashboard_output]
        )

        dashboard_campaign.change(
            fn=generate_dashboard_ui,
            inputs=[dashboard_campaign],
            outputs=[dashboard_output]
        )

        demo.load(
            fn=refresh_campaign_choices,
            outputs=[dashboard_campaign]
        ).then(
            fn=generate_dashboard_ui,
            inputs=[dashboard_campaign],
            outputs=[dashboard_output]
        )

        available_parties, snippet_progress_output = create_process_session_tab(
            refresh_campaign_names=_refresh_campaign_names,
            process_session_fn=process_session,
            campaign_manager=campaign_manager,
        )
        create_party_management_tab(available_parties)
        create_import_notes_tab(_refresh_campaign_names)
        create_campaign_library_tab(demo, _refresh_campaign_names)
        create_character_profiles_tab(demo, available_parties)
        create_speaker_management_tab()
        create_document_viewer_tab(PROJECT_ROOT, _set_notebook_context, demo)
        create_logs_tab(demo)

        create_social_insights_tab()
        create_story_notebook_tab(
            story_manager=story_manager,
            get_notebook_context=lambda: NOTEBOOK_CONTEXT,
            get_notebook_status=_notebook_status,
        )

        create_diagnostics_tab(PROJECT_ROOT)

        create_llm_chat_tab(PROJECT_ROOT)
        create_campaign_chat_tab(PROJECT_ROOT)
        create_configuration_tab()
        create_help_tab()


def is_port_in_use(port):
    """Check if a port is already in use"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('127.0.0.1', port))
            return False
        except OSError:
            return True

if __name__ == "__main__":
    # Check if port is already in use
    if is_port_in_use(7860):
        print("=" * 80)
        print("WARNING: ERROR: Gradio app already running on port 7860!")
        print("=" * 80)
        print("\nAnother instance of the application is already running.")
        print("Please close the existing instance before starting a new one.")
        print("\nTo kill existing instances:")
        print("  1. Check running processes: netstat -ano | findstr :7860")
        print("  2. Kill the process: taskkill /PID <process_id> /F")
        print("=" * 80)
        sys.exit(1)

    print("Starting Gradio web UI on http://127.0.0.1:7860")
    demo.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        show_error=True  # Enable verbose error reporting for debugging
    )
