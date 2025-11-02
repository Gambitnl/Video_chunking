"""Gradio web UI for D&D Session Processor - Modern UI"""
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
from src.ui.helpers import StatusMessages
from src.campaign_dashboard import CampaignDashboard
from src.story_notebook import StoryNotebookManager

# Modern UI imports
from src.ui.theme import create_modern_theme, MODERN_CSS
from src.ui.process_session_tab_modern import create_process_session_tab_modern
from src.ui.campaign_tab_modern import create_campaign_tab_modern
from src.ui.characters_tab_modern import create_characters_tab_modern
from src.ui.stories_output_tab_modern import create_stories_output_tab_modern
from src.ui.settings_tools_tab_modern import create_settings_tools_tab_modern

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


def _resolve_audio_path(audio_file) -> str:
    """Resolve the audio file path from Gradio file upload."""
    if isinstance(audio_file, str):
        return audio_file
    elif hasattr(audio_file, 'name'):
        return audio_file.name
    else:
        raise ValueError(f"Unsupported audio file type: {type(audio_file)}")


def process_session(
    audio_file,
    session_id: str,
    party_selection: Optional[str],
    character_names: str,
    player_names: str,
    num_speakers: int,
    skip_diarization: bool,
    skip_classification: bool,
    skip_snippets: bool,
    skip_knowledge: bool,
) -> Dict:
    """Main session processing function."""
    try:
        if audio_file is None:
            return {"status": "error", "message": "Please upload an audio file."}

        resolved_session_id = session_id or "session"

        # Determine if using party config or manual entry
        if party_selection and party_selection != "Manual Entry":
            # Use party configuration
            processor = DDSessionProcessor(
                session_id=resolved_session_id,
                num_speakers=int(num_speakers),
                party_id=party_selection
            )
        else:
            # Parse names manually
            chars = [c.strip() for c in character_names.split(',') if c.strip()]
            players = [p.strip() for p in player_names.split(',') if p.strip()]

            # Create processor
            processor = DDSessionProcessor(
                session_id=resolved_session_id,
                character_names=chars,
                player_names=players,
                num_speakers=int(num_speakers)
            )

        pipeline_result = processor.process(
            input_file=_resolve_audio_path(audio_file),
            skip_diarization=skip_diarization,
            skip_classification=skip_classification,
            skip_snippets=skip_snippets,
            skip_knowledge=skip_knowledge
        )

        output_files = pipeline_result.get("output_files") or {}

        def _read_output_file(key: str) -> str:
            path = output_files.get(key)
            if not path:
                return ""
            try:
                return Path(path).read_text(encoding="utf-8")
            except Exception:
                return ""

        snippet_export = pipeline_result.get("audio_segments") or {}
        snippet_payload = {
            "segments_dir": str(snippet_export.get("segments_dir")) if snippet_export.get("segments_dir") else None,
            "manifest": str(snippet_export.get("manifest")) if snippet_export.get("manifest") else None,
        }

        return {
            "status": "success",
            "message": "Session processed successfully.",
            "full": _read_output_file("full"),
            "ic": _read_output_file("ic_only"),
            "ooc": _read_output_file("ooc_only"),
            "stats": pipeline_result.get("statistics") or {},
            "snippet": snippet_payload,
            "knowledge": pipeline_result.get("knowledge_extraction") or {},
            "output_files": output_files,
        }

    except Exception as e:
        import traceback

        traceback.print_exc()
        return {
            "status": "error",
            "message": str(e),
            "details": f"See log for details: {get_log_file_path()}",
        }


# Get available parties
party_manager = PartyConfigManager()
available_parties = party_manager.list_parties()

# Create modern theme
theme = create_modern_theme()

# Create Gradio interface
with gr.Blocks(
    title="D&D Session Processor",
    theme=theme,
    css=MODERN_CSS,
) as demo:
    gr.Markdown("""
    # 🎲 D&D Session Processor
    ### Modern, Streamlined Interface

    Transform your D&D session recordings into organized transcripts, character profiles, and story narratives.
    """)

    with gr.Tabs():
        # Tab 1: Process Session (the main workflow)
        create_process_session_tab_modern(demo, available_parties)

        # Tab 2: Campaign (dashboard, knowledge, library, party)
        create_campaign_tab_modern(demo)

        # Tab 3: Characters (profiles, extraction, import/export)
        create_characters_tab_modern(demo, available_parties)

        # Tab 4: Stories & Output (notebooks, transcripts, insights, export)
        create_stories_output_tab_modern(demo)

        # Tab 5: Settings & Tools (config, diagnostics, logs, chat, help)
        create_settings_tools_tab_modern(demo)


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
        print("To kill the existing process:")
        print("  1. Find the process ID (PID) of the application that is listening on port 7860:")
        print("     netstat -ano | findstr :7860 | findstr LISTENING")
        print("  2. The PID will be in the last column of the output. Look for the line with \"LISTENING\" in the \"State\" column.")
        print("  3. Kill the process using its PID:")
        print("     taskkill /PID <process_id> /F")
        print("=" * 80)
        sys.exit(1)

    print("Starting D&D Session Processor - Modern UI")
    print("Access the interface at http://127.0.0.1:7860")
    demo.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        show_error=True
    )
