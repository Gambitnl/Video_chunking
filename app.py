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
from src.story_notebook import StoryNotebookManager, StorySessionData
from src.ui.campaign_dashboard_tab import create_dashboard_tab
from src.ui.party_management_tab import create_party_management_tab
from src.ui.process_session_tab import create_process_session_tab
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

    Returns:
        Tuple of (status_message, full_transcript, ic_transcript, ooc_transcript, stats_json)
    """
    try:
        if audio_file is None:
            return "Error: Please upload an audio file", "", "", "", ""

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

        # Process
        result = processor.process(
            input_file=_resolve_audio_path(audio_file),
            skip_diarization=skip_diarization,
            skip_classification=skip_classification,
            skip_snippets=skip_snippets,
            skip_knowledge=skip_knowledge
        )

        # Read output files
        output_files = result['output_files']

        full_text = output_files['full'].read_text(encoding='utf-8')
        ic_text = output_files['ic_only'].read_text(encoding='utf-8')
        ooc_text = output_files['ooc_only'].read_text(encoding='utf-8')
        stats_json = output_files['json'].read_text(encoding='utf-8')

        # Format statistics for display
        stats = result['statistics']
        stats_display = f"""
## Session Statistics

- **Total Duration**: {stats['total_duration_formatted']}
- **IC Duration**: {stats['ic_duration_formatted']} ({stats['ic_percentage']:.1f}%)
- **Total Segments**: {stats['total_segments']}
- **IC Segments**: {stats['ic_segments']}
- **OOC Segments**: {stats['ooc_segments']}

### Character Appearances
"""
        for char, count in sorted(stats.get('character_appearances', {}).items(), key=lambda x: -x[1]):
            stats_display += f"- **{char}**: {count} times\n"

        status = f"Processing complete! Files saved to: {output_files['full'].parent}"
        segments_info = result.get('audio_segments', {})
        manifest_path = segments_info.get('manifest') if segments_info else None
        if manifest_path:
            status += f"\nSegment manifest: {manifest_path}"
        status += f"\nVerbose log: {get_log_file_path()}"
        status += f"\nVerbose log: {get_log_file_path()}"

        return status, full_text, ic_text, ooc_text, stats_display

    except Exception as e:
        error_msg = f"Error: {e}\nSee log: {get_log_file_path()}"
        import traceback
        traceback.print_exc()
        return error_msg, "", "", "", ""


def map_speaker_ui(session_id, speaker_id, person_name):
    """Map a speaker ID to a person name"""
    try:
        manager = SpeakerProfileManager()
        manager.map_speaker(session_id, speaker_id, person_name)
        return f"Mapped {speaker_id} -> {person_name}"
    except Exception as e:
        return f"Error: {e}"


def get_speaker_profiles(session_id):
    """Get speaker profiles for a session"""
    try:
        manager = SpeakerProfileManager()
        if session_id not in manager.profiles:
            return "No speaker profiles found for this session"

        profiles = manager.profiles[session_id]
        result = f"## Speaker Profiles for {session_id}\n\n"
        for speaker_id, person_name in profiles.items():
            result += f"- **{speaker_id}**: {person_name}\n"

        return result
    except Exception as e:
        return f"Error: {str(e)}"

def view_google_doc(doc_url):
    """Downloads a Google Doc using authenticated Drive API."""
    global NOTEBOOK_CONTEXT
    try:
        if not is_authenticated():
            return "Error: Not authenticated with Google Drive. Please authorize first using the 'Authorize Google Drive' section below."

        content = get_document_content(doc_url)

        # Only update NOTEBOOK_CONTEXT if we got valid content
        if not content.startswith("Error"):
            NOTEBOOK_CONTEXT = content

        return content
    except Exception as e:
        return f"Error downloading document: {e}"


def check_auth_status():
    """Check if Google Drive is authenticated."""
    if is_authenticated():
        return "Status: Authenticated with Google Drive"
    else:
        return "Status: Not authenticated. Click 'Start Authorization' below."


def start_oauth_flow():
    """Initiate OAuth flow and return authorization URL and flow object."""
    try:
        auth_url, flow = get_auth_url()
        instructions = (
            f"Authorization URL generated!\n\n"
            f"Please follow these steps:\n"
            f"1. Click this link to authorize: {auth_url}\n\n"
            f"2. Sign in with your Google account and grant access\n"
            f"3. After granting access, your browser will try to redirect to localhost\n"
            f"   (the page won't load - this is normal!)\n"
            f"4. Copy the ENTIRE URL from your browser's address bar\n"
            f"   (it will look like: http://localhost:8080/?code=...&scope=...)\n"
            f"5. Paste the full URL below and click 'Complete Authorization'"
        )
        return instructions, flow
    except FileNotFoundError as e:
        return str(e), None
    except Exception as e:
        return f"Error starting OAuth flow: {e}", None


def complete_oauth_flow(flow_object, auth_code: str):
    """Complete OAuth flow with authorization code. Returns (result_message, cleared_flow_state)."""
    if not flow_object:
        return "Error: OAuth flow not started. Please click 'Start Authorization' first.", None

    if not auth_code or not auth_code.strip():
        return "Error: Please paste the authorization code.", flow_object

    success = exchange_code_for_token(flow_object, auth_code.strip())
    if success:
        return "Success! You are now authenticated with Google Drive. You can now load documents.", None
    else:
        return "Error: Failed to complete authorization. Please try again.", flow_object


def revoke_oauth():
    """Revoke Google Drive authentication."""
    revoke_credentials()
    return "Authentication revoked. You will need to authorize again to access documents."


def start_automatic_oauth():
    """
    Start automatic OAuth flow with browser popup.
    Returns status message indicating success or failure.
    """
    success, message = authenticate_automatically()
    return message


def open_setup_guide():
    """Open the setup guide in the default text editor or browser."""
    import os
    import subprocess

    guide_path = PROJECT_ROOT / "docs" / "GOOGLE_OAUTH_SIMPLE_SETUP.md"

    if not guide_path.exists():
        return "Error: Setup guide not found. Please check docs/GOOGLE_OAUTH_SIMPLE_SETUP.md"

    try:
        # Try to open with default application
        if os.name == 'nt':  # Windows
            os.startfile(str(guide_path))
        elif os.name == 'posix':  # macOS, Linux
            subprocess.run(['open' if sys.platform == 'darwin' else 'xdg-open', str(guide_path)])

        return f"✓ Opening setup guide: {guide_path.name}"
    except Exception as e:
        return f"Guide location: {guide_path}\n(Could not auto-open: {e})"




STORY_NO_DATA = "No transcription data available for this session yet."


def _session_from_state(session_state: Dict) -> StorySessionData:
    return StorySessionData(
        session_id=session_state.get("session_id", "session"),
        json_path=Path(session_state.get("json_path", Config.OUTPUT_DIR)),
        metadata=session_state.get("metadata", {}),
        segments=session_state.get("segments", []),
    )


def _prepare_story_session_outputs(
    session_id: Optional[str],
    session_choices: List[str]
) -> Tuple[dict, dict, str, Dict, str]:
    """Build component updates for story notebook session interactions."""
    notebook_status = _notebook_status()

    selected = session_id if session_id in session_choices else (session_choices[0] if session_choices else None)
    session_dropdown = gr.update(choices=session_choices, value=selected)

    if not selected:
        message = (
            f"## {StatusIndicators.WARNING} No Sessions Available\n\n"
            f"{STORY_NO_DATA}\n\n"
            "Process a session with the pipeline, then click **Refresh Sessions**."
        )
        return (
            session_dropdown,
            gr.update(choices=[], value=None, interactive=False),
            message,
            {},
            notebook_status,
        )

    try:
        session = story_manager.load_session(selected)
    except FileNotFoundError:
        message = (
            f"## {StatusIndicators.WARNING} Session Not Found\n\n"
            f"{STORY_NO_DATA}\n\n"
            f"Could not locate processed data for `{selected}`. Re-run the session processing and refresh."
        )
        return (
            session_dropdown,
            gr.update(choices=[], value=None, interactive=False),
            message,
            {},
            notebook_status,
        )
    except Exception as exc:
        message = (
            f"## {StatusIndicators.ERROR} Failed to Load Session\n\n"
            f"An unexpected error occurred while loading `{selected}`: {exc}"
        )
        return (
            session_dropdown,
            gr.update(choices=[], value=None, interactive=False),
            message,
            {},
            notebook_status,
        )

    segments = session.segments
    character_names = session.character_names
    character_dropdown = gr.update(
        choices=character_names,
        value=(character_names[0] if character_names else None),
        interactive=bool(character_names),
    )

    if not segments:
        message = (
            f"## {StatusIndicators.WARNING} {STORY_NO_DATA}\n\n"
            "The selected session file is missing segment data."
        )
    else:
        details = story_manager.build_session_info(session)
        message = (
            f"### {StatusIndicators.SUCCESS} Session Ready\n\n"
            f"{details}"
        )

    session_state: Dict = {
        "session_id": session.session_id,
        "json_path": str(session.json_path),
        "metadata": session.metadata,
        "segments": segments,
    }

    return (
        session_dropdown,
        character_dropdown,
        message,
        session_state,
        notebook_status,
    )


def story_refresh_sessions_ui() -> Tuple[dict, dict, str, Dict, str]:
    """Refresh available sessions and prime state for the first entry."""
    sessions = story_manager.list_sessions()
    return _prepare_story_session_outputs(None, sessions)


def story_select_session_ui(session_id: Optional[str]) -> Tuple[dict, dict, str, Dict, str]:
    """Update UI state when a session is selected."""
    sessions = story_manager.list_sessions()
    return _prepare_story_session_outputs(session_id, sessions)


def story_generate_narrator(session_state: Dict, temperature: float) -> tuple[str, str]:
    if not session_state or not session_state.get("segments"):
        return f"## {StatusIndicators.WARNING} No Session Loaded\n\nPlease select a session from the dropdown above, then try again.", ""

    try:
        session = _session_from_state(session_state)
        story, file_path = story_manager.generate_narrator(
            session,
            notebook_context=NOTEBOOK_CONTEXT,
            temperature=temperature
        )
        saved_path = str(file_path) if file_path else ""
        return story, saved_path
    except Exception as e:
        return f"Error generating narrative: {e}", ""


def story_generate_character(session_state: Dict, character_name: str, temperature: float) -> tuple[str, str]:
    if not session_state or not session_state.get("segments"):
        return f"## {StatusIndicators.WARNING} No Session Loaded\n\nPlease select a session from the dropdown at the top of this tab, then try again.", ""
    if not character_name:
        return "Select a character perspective to generate.", ""
    
    try:
        session = _session_from_state(session_state)
        story, file_path = story_manager.generate_character(
            session,
            character_name=character_name,
            notebook_context=NOTEBOOK_CONTEXT,
            temperature=temperature
        )
        saved_path = str(file_path) if file_path else ""
        return story, saved_path
    except Exception as e:
        return f"Error generating narrative: {e}", ""



def _collect_pytest_nodes():
    """Collect pytest node ids for display in the diagnostics tab."""
    try:
        result = subprocess.run(
            ["pytest", "--collect-only", "-q"],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT)
        )
    except FileNotFoundError as exc:
        raise RuntimeError("pytest not found. Install dev dependencies (pip install -r requirements.txt).") from exc

    stdout = result.stdout.strip()
    stderr = result.stderr.strip()

    if result.returncode != 0:
        combined = stderr or stdout or f"pytest exited with status {result.returncode}"
        raise RuntimeError(combined)

    nodes = [
        line.strip()
        for line in stdout.splitlines()
        if line.strip() and not line.startswith('<') and '::' in line
    ]
    return nodes, stderr


def collect_pytest_tests_ui():
    """Gradio handler to discover available pytest tests."""
    try:
        nodes, warnings = _collect_pytest_nodes()
    except RuntimeError as exc:
        message = f"Warning: Unable to collect tests:\n```\n{exc}\n```"
        return message, gr.update(choices=[], value=[])

    if not nodes:
        return "No pytest tests discovered in this repository.", gr.update(choices=[], value=[])

    message = f"Discovered {len(nodes)} tests. Select entries to run individually."
    if warnings:
        message += f"\n\nWarnings:\n```\n{warnings}\n```"

    return message, gr.update(choices=nodes, value=[])


def _run_pytest(args):
    try:
        result = subprocess.run(
            ["pytest", *args],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT)
        )
    except FileNotFoundError:
        return ("pytest not found. Install dev dependencies (pip install -r requirements.txt).", "")

    combined = (result.stdout or '') + ("\n" + result.stderr if result.stderr else '')
    combined = combined.strip() or "(no output)"

    max_len = 5000
    if len(combined) > max_len:
        combined = "... (output truncated)\n" + combined[-max_len:]

    status = "PASS: Tests succeeded" if result.returncode == 0 else f"FAIL: Tests exited with code {result.returncode}"
    return status, combined


def run_pytest_selection(selected_tests):
    """Run user-selected pytest nodes and return status plus output."""
    if not selected_tests:
        return "Select at least one test to run.", ""

    return _run_pytest(["-q", *selected_tests])


def run_all_tests_ui():
    """Run the entire pytest suite."""
    return _run_pytest(["-q"])


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

        available_parties = create_process_session_tab(
            refresh_campaign_names=_refresh_campaign_names,
            process_session_fn=process_session,
            campaign_manager=campaign_manager,
        )
        create_party_management_tab(available_parties)
        with gr.Tab("Import Session Notes"):
            gr.Markdown("""
            ### 📝 Import Session Notes

            **Backfill your campaign with sessions you didn't record!**

            This tool automatically extracts:
            - 🎯 **Quests** - Started, progressed, or completed
            - 👥 **NPCs** - Characters the party met
            - 📍 **Locations** - Places visited
            - ⚡ **Items** - Important objects found
            - 🔓 **Plot Hooks** - Mysteries and future threads

            Perfect for importing sessions 1-5 before you started recording!
            """)

            # Quick Start Guide
            with gr.Accordion("📖 Quick Start Guide & Example Format", open=False):
                gr.Markdown("""
                ### How to Use This Tool:

                1. **Enter Session ID** (e.g., `Session_01`) - Required ⚠️
                2. **Select Campaign** - Choose which campaign these notes belong to
                3. **Paste Your Notes** - Copy/paste from your document OR upload a .txt/.md file
                4. **Check Options**:
                   - ✅ **Extract Knowledge** (Recommended) - Finds NPCs, quests, locations automatically
                   - ☐ **Generate Narrative** (Optional) - Creates a story-style summary
                5. **Click "Import Session Notes"**

                ---

                ### 📋 Example Notes Format:

                ```markdown
                Session 1 - The Adventure Begins

                The party met at the Broken Compass tavern in Neverwinter.
                Guard Captain Thorne approached them with a quest to find
                Marcus, a merchant who disappeared on the Waterdeep Road.

                NPCs Met:
                - Guard Captain Thorne (stern but fair, quest giver)
                - Innkeeper Mara (friendly, provided rumors)

                Locations Visited:
                - The Broken Compass tavern
                - Waterdeep Road

                Quests:
                - Find Marcus the Missing Merchant (active)

                The party set out at dawn...
                ```

                **Don't worry about perfect formatting!** The AI can understand natural language notes.
                Even a simple paragraph describing what happened works fine.
                """)

            # Input validation status indicator
            validation_status = gr.Markdown(
                value="",
                visible=False
            )

            with gr.Row():
                with gr.Column(scale=2):
                    notes_session_id = gr.Textbox(
                        label="1️⃣ Session ID (Required)",
                        placeholder="e.g., Session_01, Session_02, Direlambs_Session_01",
                        info="💡 Tip: Use a consistent naming scheme like 'Session_01', 'Session_02', etc."
                    )
                    notes_campaign_choices = ["default"] + list(_refresh_campaign_names().keys())
                    notes_campaign = gr.Dropdown(
                        choices=notes_campaign_choices,
                        value="default",
                        label="2️⃣ Campaign (Required)",
                        info="Select which campaign these notes belong to. 'default' works if you only have one campaign."
                    )
                with gr.Column(scale=1):
                    gr.Markdown("### Options:")
                    notes_extract_knowledge = gr.Checkbox(
                        label="✅ Extract Knowledge (Recommended)",
                        value=True,
                        info="AI will automatically find: NPCs, quests, locations, items, plot hooks"
                    )
                    notes_generate_narrative = gr.Checkbox(
                        label="📖 Generate Narrative Summary",
                        value=False,
                        info="Creates a story-style summary (takes extra time)"
                    )

            notes_input = gr.Textbox(
                label="3️⃣ Session Notes (Required)",
                placeholder="Paste your session notes here...\n\nExample:\n'Session 1 - The party met at the tavern. They spoke with Guard Captain Thorne who gave them a quest to find Marcus, a missing merchant. They traveled to the Waterdeep Road and found...'\n\nClick 'Quick Start Guide' above for more examples!",
                lines=15,
                max_lines=30
            )

            notes_file_upload = gr.File(
                label="📎 Or Upload Notes File (.txt or .md)",
                file_types=[".txt", ".md"],
                type="filepath"
            )

            # Ready indicator
            ready_indicator = gr.Markdown(
                value="",
                visible=True
            )

            with gr.Row():
                notes_import_btn = gr.Button(
                    "📥 Import Session Notes",
                    variant="primary",
                    size="lg",
                    scale=3
                )
                notes_clear_btn = gr.Button(
                    "🗑️ Clear All Fields",
                    variant="secondary",
                    scale=1
                )

            notes_output = gr.Markdown(label="Import Results")

            def load_notes_from_file(file_path):
                """Load notes from uploaded file"""
                if not file_path:
                    return ""
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        return f.read()
                except Exception as e:
                    return f"Error reading file: {e}"

            def validate_import_inputs(session_id, notes_text):
                """Validate import inputs and provide real-time feedback"""
                has_session_id = session_id and session_id.strip()
                has_notes = notes_text and notes_text.strip()

                if has_session_id and has_notes:
                    return "✅ **Ready to import!** All required fields are filled. Click the button below to start."
                elif has_session_id and not has_notes:
                    return "⚠️ **Missing**: Session notes are required. Paste your notes or upload a file."
                elif not has_session_id and has_notes:
                    return "⚠️ **Missing**: Session ID is required. Enter an ID like 'Session_01'."
                else:
                    return "ℹ️ Fill in the required fields above to get started."

            def clear_import_fields():
                """Clear all import fields"""
                return "", "default", "", None, ""

            def import_session_notes(session_id, campaign_id, notes_text, extract_knowledge, generate_narrative):
                """Import session notes and extract knowledge"""
                if not session_id or not session_id.strip():
                    return "⚠️ **Error**: Please provide a Session ID"

                if not notes_text or not notes_text.strip():
                    return "⚠️ **Error**: Please provide session notes (paste text or upload a file)"

                session_id = session_id.strip()
                results = f"# Import Results: {session_id}\n\n"
                results += f"**Campaign**: {campaign_id}\n\n"
                results += "---\n\n"

                # Extract knowledge if requested
                if extract_knowledge:
                    try:
                        from src.knowledge_base import KnowledgeExtractor, CampaignKnowledgeBase

                        results += "## 📚 Knowledge Extraction\n\n"
                        results += "Analyzing your notes with LLM...\n\n"

                        # Get party context
                        party_context_dict = None
                        if campaign_id and campaign_id != "default":
                            party_mgr = PartyConfigManager()
                            party = party_mgr.get_party(campaign_id)
                            if party:
                                party_context_dict = {
                                    'character_names': [c.name for c in party.characters],
                                    'campaign': party.campaign or 'Unknown'
                                }

                        # Extract knowledge
                        extractor = KnowledgeExtractor()
                        extracted = extractor.extract_knowledge(
                            notes_text,
                            session_id,
                            party_context_dict
                        )

                        # Merge into knowledge base
                        kb = CampaignKnowledgeBase(campaign_id=campaign_id)
                        kb.merge_new_knowledge(extracted, session_id)

                        # Report what was extracted
                        counts = {
                            'quests': len(extracted.get('quests', [])),
                            'npcs': len(extracted.get('npcs', [])),
                            'plot_hooks': len(extracted.get('plot_hooks', [])),
                            'locations': len(extracted.get('locations', [])),
                            'items': len(extracted.get('items', []))
                        }
                        total = sum(counts.values())

                        results += f"✅ **Extracted {total} entities:**\n\n"
                        if counts['quests'] > 0:
                            results += f"- 🎯 **Quests**: {counts['quests']}\n"
                            for q in extracted['quests']:
                                results += f"  - {q.title} ({q.status})\n"
                            results += "\n"

                        if counts['npcs'] > 0:
                            results += f"- 👥 **NPCs**: {counts['npcs']}\n"
                            for n in extracted['npcs']:
                                results += f"  - {n.name} ({n.role or 'unknown'})\n"
                            results += "\n"

                        if counts['plot_hooks'] > 0:
                            results += f"- 🔓 **Plot Hooks**: {counts['plot_hooks']}\n"
                            for p in extracted['plot_hooks']:
                                results += f"  - {p.summary}\n"
                            results += "\n"

                        if counts['locations'] > 0:
                            results += f"- 📍 **Locations**: {counts['locations']}\n"
                            for l in extracted['locations']:
                                results += f"  - {l.name} ({l.type or 'unknown'})\n"
                            results += "\n"

                        if counts['items'] > 0:
                            results += f"- ⚡ **Items**: {counts['items']}\n"
                            for i in extracted['items']:
                                results += f"  - {i.name}\n"
                            results += "\n"

                        results += f"\n**Knowledge saved to**: `{kb.knowledge_file}`\n\n"
                        results += "💡 *Visit the Campaign Library tab to view all extracted knowledge!*\n\n"

                    except Exception as e:
                        results += f"❌ **Knowledge extraction failed**: {str(e)}\n\n"
                        import traceback
                        results += f"```\n{traceback.format_exc()}\n```\n\n"

                # Generate narrative if requested
                if generate_narrative:
                    try:
                        import ollama
                        results += "---\n\n## 📖 Narrative Generation\n\n"
                        results += "Generating narrative summary...\n\n"

                        # Build prompt
                        prompt = f"""You are a D&D session narrator. Based on the following session notes, create a concise narrative summary (3-5 paragraphs) capturing the key events, character actions, and story developments.

    Session: {session_id}

    Session Notes:
    {notes_text[:4000]}

    Write a narrative summary that:
    - Captures the main events and story beats
    - Highlights character actions and decisions
    - Maintains a consistent narrative voice
    - Stays under 500 words

    Narrative:"""

                        client = ollama.Client(host=Config.OLLAMA_BASE_URL)
                        response = client.generate(
                            model=Config.OLLAMA_MODEL,
                            prompt=prompt,
                            options={"temperature": 0.6, "num_predict": 800}
                        )

                        narrative = response.get("response", "(No narrative generated)")

                        results += f"### {session_id} - Narrator Summary\n\n"
                        results += f"{narrative}\n\n"

                        # Save narrative
                        narratives_dir = Config.OUTPUT_DIR / "imported_narratives"
                        narratives_dir.mkdir(exist_ok=True, parents=True)
                        narrative_file = narratives_dir / f"{session_id}_narrator.md"
                        narrative_file.write_text(narrative, encoding='utf-8')

                        results += f"**Narrative saved to**: `{narrative_file}`\n\n"

                    except Exception as e:
                        results += f"❌ **Narrative generation failed**: {str(e)}\n\n"

                results += "---\n\n"
                results += "## ✅ Import Complete!\n\n"
                if extract_knowledge:
                    results += "- Check the **Campaign Library** tab to view extracted knowledge\n"
                if generate_narrative:
                    results += "- Narrative saved to `output/imported_narratives/`\n"

                return results

            # File upload handler
            notes_file_upload.change(
                fn=load_notes_from_file,
                inputs=[notes_file_upload],
                outputs=[notes_input]
            )

            # Real-time validation as user types
            notes_session_id.change(
                fn=validate_import_inputs,
                inputs=[notes_session_id, notes_input],
                outputs=[ready_indicator]
            )

            notes_input.change(
                fn=validate_import_inputs,
                inputs=[notes_session_id, notes_input],
                outputs=[ready_indicator]
            )

            # Import button
            notes_import_btn.click(
                fn=import_session_notes,
                inputs=[notes_session_id, notes_campaign, notes_input, notes_extract_knowledge, notes_generate_narrative],
                outputs=[notes_output]
            )

            # Clear button - clears all fields
            notes_clear_btn.click(
                fn=clear_import_fields,
                outputs=[notes_session_id, notes_campaign, notes_input, notes_file_upload, notes_output]
            )

        with gr.Tab("Campaign Library"):
            gr.Markdown("""
            ### Campaign Library

            Automatically extracted campaign knowledge from your sessions. View quests, NPCs, plot hooks, locations, and items that have been mentioned across all processed sessions.

            Knowledge is extracted from IC-only transcripts using your local LLM (Ollama) and accumulated over time.
            """)

            with gr.Row():
                with gr.Column(scale=2):
                    kb_campaign_choices = ["default"] + list(_refresh_campaign_names().keys())
                    kb_campaign_selector = gr.Dropdown(
                        choices=kb_campaign_choices,
                        value="default",
                        label="Select Campaign",
                        info="Choose which campaign's knowledge base to view"
                    )
                with gr.Column(scale=3):
                    kb_search_input = gr.Textbox(
                        label="Search Knowledge Base",
                        placeholder="Search across all quests, NPCs, locations, items, and plot hooks..."
                    )
                with gr.Column(scale=1):
                    kb_search_btn = gr.Button("🔍 Search", size="sm")
                    kb_refresh_btn = gr.Button("🔄 Refresh", size="sm")

            kb_output = gr.Markdown(value="Select a campaign and click Refresh to load knowledge.")

            def format_quest(q):
                """Format a quest for display"""
                status_emoji = {
                    "active": StatusIndicators.QUEST_ACTIVE,
                    "completed": StatusIndicators.QUEST_COMPLETE,
                    "failed": StatusIndicators.QUEST_FAILED,
                    "unknown": StatusIndicators.QUEST_UNKNOWN
                }
                emoji = status_emoji.get(q.status, StatusIndicators.QUEST_UNKNOWN)

                md = f"**{emoji} {q.title}** ({q.status.upper()})\n\n"
                md += f"{q.description}\n\n"
                md += f"*First mentioned: {q.first_mentioned} | Last updated: {q.last_updated}*"

                if q.related_npcs:
                    md += f"\n\n**Related NPCs:** {', '.join(q.related_npcs)}"
                if q.related_locations:
                    md += f"\n\n**Related Locations:** {', '.join(q.related_locations)}"
                if q.notes:
                    md += f"\n\n**Notes:**\n" + "\n".join(f"- {note}" for note in q.notes)

                return md

            def format_npc(n):
                """Format an NPC for display"""
                role_emoji = {
                    "quest_giver": "📜",
                    "merchant": "🛒",
                    "enemy": "⚔️",
                    "ally": "🤝",
                    "unknown": "👤"
                }
                emoji = role_emoji.get(n.role, "👤")

                md = f"**{emoji} {n.name}** ({n.role or 'unknown'})\n\n"
                md += f"{n.description}\n\n"

                if n.location:
                    md += f"**Location:** {n.location}\n\n"

                md += f"*Appearances: {', '.join(n.appearances)}*"

                if n.relationships:
                    md += f"\n\n**Relationships:**\n"
                    for char, rel in n.relationships.items():
                        md += f"- **{char}:** {rel}\n"

                if n.notes:
                    md += f"\n**Notes:**\n" + "\n".join(f"- {note}" for note in n.notes)

                return md

            def format_plot_hook(p):
                """Format a plot hook for display"""
                status = "🔒 Resolved" if p.resolved else "🔓 Unresolved"

                md = f"**{status}: {p.summary}**\n\n"
                md += f"{p.details}\n\n"
                md += f"*First mentioned: {p.first_mentioned} | Last updated: {p.last_updated}*"

                if p.related_npcs:
                    md += f"\n\n**Related NPCs:** {', '.join(p.related_npcs)}"
                if p.related_quests:
                    md += f"\n\n**Related Quests:** {', '.join(p.related_quests)}"
                if p.resolved and p.resolution:
                    md += f"\n\n**Resolution:** {p.resolution}"

                return md

            def format_location(l):
                """Format a location for display"""
                type_emoji = {
                    "city": "🏙️",
                    "dungeon": "🏰",
                    "wilderness": "🌲",
                    "building": "🏛️",
                    "unknown": "📍"
                }
                emoji = type_emoji.get(l.type, "📍")

                md = f"**{emoji} {l.name}** ({l.type or 'unknown'})\n\n"
                md += f"{l.description}\n\n"
                md += f"*Visited: {', '.join(l.visits)}*"

                if l.notable_features:
                    md += f"\n\n**Notable Features:**\n" + "\n".join(f"- {feat}" for feat in l.notable_features)
                if l.npcs_present:
                    md += f"\n\n**NPCs Present:** {', '.join(l.npcs_present)}"

                return md

            def format_item(i):
                """Format an item for display"""
                md = f"**⚡ {i.name}**\n\n"
                md += f"{i.description}\n\n"

                if i.owner:
                    md += f"**Owner:** {i.owner}\n\n"
                if i.location:
                    md += f"**Location:** {i.location}\n\n"

                md += f"*First mentioned: {i.first_mentioned} | Last updated: {i.last_updated}*"

                if i.properties:
                    md += f"\n\n**Properties:**\n" + "\n".join(f"- {prop}" for prop in i.properties)
                if i.significance:
                    md += f"\n\n**Significance:** {i.significance}"

                return md

            def load_knowledge_base(campaign_id):
                """Load and format knowledge base for display"""
                try:
                    kb = CampaignKnowledgeBase(campaign_id=campaign_id)

                    if not kb.knowledge['sessions_processed']:
                        return f"## No Knowledge Found\n\nNo sessions have been processed for campaign `{campaign_id}` yet.\n\nProcess a session with knowledge extraction enabled to start building your campaign library!"

                    output = f"# Campaign Knowledge Base: {campaign_id}\n\n"
                    output += f"**Sessions Processed:** {', '.join(kb.knowledge['sessions_processed'])}\n\n"
                    output += f"**Last Updated:** {kb.knowledge.get('last_updated', 'Unknown')}\n\n"
                    output += "---\n\n"

                    # Active Quests
                    active_quests = kb.get_active_quests()
                    if active_quests:
                        output += f"## 🎯 Active Quests ({len(active_quests)})\n\n"
                        for q in active_quests:
                            output += format_quest(q) + "\n\n---\n\n"

                    # All Quests
                    all_quests = kb.knowledge['quests']
                    completed = [q for q in all_quests if q.status == "completed"]
                    failed = [q for q in all_quests if q.status == "failed"]

                    if completed:
                        output += f"## ✅ Completed Quests ({len(completed)})\n\n"
                        for q in completed:
                            output += format_quest(q) + "\n\n---\n\n"

                    if failed:
                        output += f"## ❌ Failed Quests ({len(failed)})\n\n"
                        for q in failed:
                            output += format_quest(q) + "\n\n---\n\n"

                    # NPCs
                    npcs = kb.get_all_npcs()
                    if npcs:
                        output += f"## 👥 Non-Player Characters ({len(npcs)})\n\n"
                        for n in npcs:
                            output += format_npc(n) + "\n\n---\n\n"

                    # Plot Hooks
                    plot_hooks = kb.get_unresolved_plot_hooks()
                    if plot_hooks:
                        output += f"## 🔓 Unresolved Plot Hooks ({len(plot_hooks)})\n\n"
                        for p in plot_hooks:
                            output += format_plot_hook(p) + "\n\n---\n\n"

                    resolved_hooks = [p for p in kb.knowledge['plot_hooks'] if p.resolved]
                    if resolved_hooks:
                        output += f"## 🔒 Resolved Plot Hooks ({len(resolved_hooks)})\n\n"
                        for p in resolved_hooks:
                            output += format_plot_hook(p) + "\n\n---\n\n"

                    # Locations
                    locations = kb.get_all_locations()
                    if locations:
                        output += f"## 📍 Locations ({len(locations)})\n\n"
                        for l in locations:
                            output += format_location(l) + "\n\n---\n\n"

                    # Items
                    items = kb.knowledge['items']
                    if items:
                        output += f"## ⚡ Important Items ({len(items)})\n\n"
                        for i in items:
                            output += format_item(i) + "\n\n---\n\n"

                    if not any([all_quests, npcs, kb.knowledge['plot_hooks'], locations, items]):
                        output += "## No Knowledge Found\n\nNo entities have been extracted yet. Process sessions with knowledge extraction enabled!"

                    return output

                except Exception as e:
                    return f"## Error Loading Knowledge Base\n\n```\n{str(e)}\n```"

            def search_knowledge_base(campaign_id, query):
                """Search knowledge base and format results"""
                if not query or not query.strip():
                    return "Please enter a search query."

                try:
                    kb = CampaignKnowledgeBase(campaign_id=campaign_id)
                    results = kb.search_knowledge(query)

                    output = f"# Search Results for: \"{query}\"\n\n"
                    output += f"Campaign: `{campaign_id}`\n\n---\n\n"

                    total_results = sum(len(v) for v in results.values())
                    if total_results == 0:
                        return output + "No results found."

                    output += f"**Total Results:** {total_results}\n\n"

                    if results['quests']:
                        output += f"## 🎯 Quests ({len(results['quests'])})\n\n"
                        for q in results['quests']:
                            output += format_quest(q) + "\n\n---\n\n"

                    if results['npcs']:
                        output += f"## 👥 NPCs ({len(results['npcs'])})\n\n"
                        for n in results['npcs']:
                            output += format_npc(n) + "\n\n---\n\n"

                    if results['plot_hooks']:
                        output += f"## 🔓 Plot Hooks ({len(results['plot_hooks'])})\n\n"
                        for p in results['plot_hooks']:
                            output += format_plot_hook(p) + "\n\n---\n\n"

                    if results['locations']:
                        output += f"## 📍 Locations ({len(results['locations'])})\n\n"
                        for l in results['locations']:
                            output += format_location(l) + "\n\n---\n\n"

                    if results['items']:
                        output += f"## ⚡ Items ({len(results['items'])})\n\n"
                        for i in results['items']:
                            output += format_item(i) + "\n\n---\n\n"

                    return output

                except Exception as e:
                    return f"## Search Error\n\n```\n{str(e)}\n```"

            kb_refresh_btn.click(
                fn=load_knowledge_base,
                inputs=[kb_campaign_selector],
                outputs=[kb_output]
            )

            kb_search_btn.click(
                fn=search_knowledge_base,
                inputs=[kb_campaign_selector, kb_search_input],
                outputs=[kb_output]
            )

            kb_campaign_selector.change(
                fn=load_knowledge_base,
                inputs=[kb_campaign_selector],
                outputs=[kb_output]
            )

            demo.load(
                fn=load_knowledge_base,
                inputs=[kb_campaign_selector],
                outputs=[kb_output]
            )

        with gr.Tab("Character Profiles"):
            gr.Markdown("""
            ### Character Profiles & Overviews

            This tab is your central hub for managing detailed character profiles. It allows you to track character development, view comprehensive overviews, and automatically extract new information from session transcripts.

            #### Key Features:

            -   **Centralized Tracking**: Keep a detailed record for each character, including their player, race, class, level, notable actions, inventory, relationships, and memorable quotes.
            -   **Dynamic Overviews**: Select a character to view a dynamically generated overview of their entire profile.
            -   **Automatic Profile Extraction**: Use the power of an LLM to automatically analyze an in-character session transcript. The system will extract and append new information to the relevant character profiles, such as:
                -   Notable actions performed.
                -   Items acquired or lost.
                -   New relationships formed.
                -   Memorable quotes.
            -   **Import/Export**: Save individual character profiles to a `.json` file for backup or sharing, and import them back into the system.

            This powerful tool helps you maintain a living document for each character, ensuring no detail from your campaign is ever lost.
            """)

            # Load characters initially
            from src.character_profile import CharacterProfileManager
            char_mgr = CharacterProfileManager()
            initial_chars = char_mgr.list_characters()

            with gr.Row():
                with gr.Column():
                    gr.Markdown("#### View Characters")
                    char_refresh_btn = gr.Button("Refresh Character List", size="sm")
                    char_table = gr.Dataframe(
                        headers=["Character", "Player", "Race/Class", "Level", "Sessions"],
                        datatype=["str", "str", "str", "number", "number"],
                        label="Characters",
                        interactive=False,
                        wrap=True
                    )

                    char_select = gr.Dropdown(
                        label="Select Character",
                        choices=initial_chars,
                        value=initial_chars[0] if initial_chars else None,
                        interactive=True
                    )
                    view_char_btn = gr.Button("View Character Overview", variant="primary")

                with gr.Column():
                    gr.Markdown("#### Export/Import")
                    export_char_dropdown = gr.Dropdown(
                        label="Character to Export",
                        choices=initial_chars,
                        value=initial_chars[0] if initial_chars else None,
                        interactive=True
                    )
                    export_char_btn = gr.Button("Export Character")
                    export_char_file = gr.File(label="Download Character Profile")
                    export_char_status = gr.Textbox(label="Status", interactive=False)

                    gr.Markdown("---")

                    import_char_file = gr.File(label="Upload Character JSON", file_types=[".json"])
                    import_char_btn = gr.Button("Import Character")
                    import_char_status = gr.Textbox(label="Status", interactive=False)

            # Automatic extraction section
            with gr.Row():
                gr.Markdown("### 🤖 Automatic Profile Extraction")

            with gr.Row():
                with gr.Column():
                    gr.Markdown("""
                    **Extract character data from session transcripts automatically!**

                    Upload an IC-only transcript and select the party - the AI will:
                    - Extract notable actions
                    - Find items acquired
                    - Identify relationships
                    - Capture memorable quotes
                    - Note character development
                    """)

                with gr.Column():
                    extract_transcript_file = gr.File(
                        label="IC-Only Transcript (TXT)",
                        file_types=[".txt"]
                    )
                    # Filter out "Manual Entry" for extraction dropdown
                    extract_party_choices = [p for p in available_parties if p != "Manual Entry"]
                    extract_party_dropdown = gr.Dropdown(
                        choices=extract_party_choices,
                        label="Party Configuration",
                        value="default" if "default" in extract_party_choices else (extract_party_choices[0] if extract_party_choices else None)
                    )
                    extract_session_id = gr.Textbox(
                        label="Session ID",
                        placeholder="e.g., Session 1"
                    )
                    extract_btn = gr.Button("🚀 Extract Character Data", variant="primary")
                    extract_status = gr.Textbox(label="Extraction Status", lines=5, interactive=False)

            with gr.Row():
                char_overview_output = gr.Markdown(
                    label="Character Overview",
                    value="Select a character to view their profile.",
                    elem_classes="character-overview-scrollable"
                )

            # Add custom CSS for scrollable character overview
            demo.css = """
            .character-overview-scrollable {
                max-height: 600px;
                overflow-y: auto;
            }
            .scrollable-log {
                max-height: 600px;
                overflow-y: auto !important;
            }
            """

            # Character profile functions
            def load_character_list():
                from src.character_profile import CharacterProfileManager
                manager = CharacterProfileManager()
                characters = manager.list_characters()

                if not characters:
                    return [], [], []

                # Create data for Dataframe
                table_data = []
                for char_name in characters:
                    profile = manager.get_profile(char_name)
                    table_data.append([
                        profile.name,
                        profile.player,
                        f"{profile.race} {profile.class_name}",
                        profile.level,
                        profile.total_sessions
                    ])

                return table_data, characters, characters

            def view_character_profile(character_name):
                if not character_name:
                    return "Please select a character."

                from src.character_profile import CharacterProfileManager
                manager = CharacterProfileManager()
                overview = manager.generate_character_overview(character_name, format="markdown")
                return overview

            def export_character_ui(character_name):
                if not character_name:
                    return None, "Please select a character"

                try:
                    from src.character_profile import CharacterProfileManager
                    from tempfile import NamedTemporaryFile

                    manager = CharacterProfileManager()
                    temp_file = NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8')
                    temp_path = Path(temp_file.name)
                    temp_file.close()

                    manager.export_profile(character_name, temp_path)
                    return temp_path, f"Exported '{character_name}'"
                except Exception as e:
                    return None, f"Error: {str(e)}"

            def import_character_ui(file_obj):
                if file_obj is None:
                    return "Please upload a file"

                try:
                    from src.character_profile import CharacterProfileManager
                    manager = CharacterProfileManager()
                    imported_name = manager.import_profile(Path(file_obj.name))
                    return f"Successfully imported character '{imported_name}'. Click Refresh to see it."
                except Exception as e:
                    return f"Error: {str(e)}"

            def extract_profiles_ui(transcript_file, party_id, session_id):
                """Extract character profiles from IC transcript using LLM"""
                if transcript_file is None:
                    return "❌ Please upload an IC-only transcript file"

                if not party_id or party_id == "Manual Entry":
                    return "❌ Please select a party configuration (not Manual Entry)"

                if not session_id:
                    return "❌ Please enter a session ID"

                try:
                    from src.profile_extractor import CharacterProfileExtractor
                    from src.character_profile import CharacterProfileManager
                    from src.party_config import PartyConfigManager

                    # Initialize managers
                    extractor = CharacterProfileExtractor()
                    profile_mgr = CharacterProfileManager()
                    party_mgr = PartyConfigManager()

                    # Extract and update profiles
                    status = f"🔄 Extracting character data from transcript...\n"
                    status += f"Party: {party_id}\n"
                    status += f"Session: {session_id}\n\n"

                    results = extractor.batch_extract_and_update(
                        transcript_path=Path(transcript_file.name),
                        party_id=party_id,
                        session_id=session_id,
                        profile_manager=profile_mgr,
                        party_manager=party_mgr
                    )

                    status += f"✅ Extraction complete!\n\n"
                    status += f"Updated {len(results)} character profile(s):\n"

                    for char_name, extracted_data in results.items():
                        status += f"\n**{char_name}**:\n"
                        status += f"  - Actions: {len(extracted_data.notable_actions)}\n"
                        status += f"  - Items: {len(extracted_data.items_acquired)}\n"
                        status += f"  - Relationships: {len(extracted_data.relationships_mentioned)}\n"
                        status += f"  - Quotes: {len(extracted_data.memorable_quotes)}\n"
                        status += f"  - Developments: {len(extracted_data.character_development)}\n"

                    status += "\n✅ Click 'Refresh Character List' to see updates!"

                    return status

                except Exception as e:
                    import traceback
                    error_details = traceback.format_exc()
                    return f"❌ Extraction failed:\n{str(e)}\n\nDetails:\n{error_details}"

            # Handler for clicking on table rows
            def on_table_select(evt: gr.SelectData):
                """When a row is clicked, select that character"""
                if evt.index[0] >= 0:  # evt.index is (row, col)
                    from src.character_profile import CharacterProfileManager
                    manager = CharacterProfileManager()
                    characters = manager.list_characters()
                    if evt.index[0] < len(characters):
                        selected_char = characters[evt.index[0]]
                        return selected_char
                return None

            # Wire up the buttons
            char_refresh_btn.click(
                fn=load_character_list,
                outputs=[char_table, char_select, export_char_dropdown]
            )

            # When table row is clicked, update dropdown
            char_table.select(
                fn=on_table_select,
                outputs=[char_select]
            )

            view_char_btn.click(
                fn=view_character_profile,
                inputs=[char_select],
                outputs=[char_overview_output]
            )

            export_char_btn.click(
                fn=export_character_ui,
                inputs=[export_char_dropdown],
                outputs=[export_char_file, export_char_status]
            )

            import_char_btn.click(
                fn=import_character_ui,
                inputs=[import_char_file],
                outputs=[import_char_status]
            )

            extract_btn.click(
                fn=extract_profiles_ui,
                inputs=[extract_transcript_file, extract_party_dropdown, extract_session_id],
                outputs=[extract_status]
            )

            # Load character list on page load
            demo.load(
                fn=load_character_list,
                outputs=[char_table, char_select, export_char_dropdown]
            )

        with gr.Tab("Speaker Management"):
            gr.Markdown("""
            ### Manage Speaker Profiles

            After processing, you can map speaker IDs (like SPEAKER_00) to actual person names.
            This mapping will be remembered for future sessions.
            """)

            with gr.Row():
                with gr.Column():
                    map_session_id = gr.Textbox(label="Session ID")
                    map_speaker_id = gr.Textbox(
                        label="Speaker ID",
                        placeholder="e.g., SPEAKER_00"
                    )
                    map_person_name = gr.Textbox(
                        label="Person Name",
                        placeholder="e.g., Alice"
                    )
                    map_btn = gr.Button("Map Speaker", variant="primary")
                    map_status = gr.Textbox(label="Status", interactive=False)

                with gr.Column():
                    view_session_id = gr.Textbox(label="Session ID")
                    view_btn = gr.Button("View Speaker Profiles")
                    profiles_output = gr.Markdown(label="Profiles")

            map_btn.click(
                fn=map_speaker_ui,
                inputs=[map_session_id, map_speaker_id, map_person_name],
                outputs=[map_status]
            )

            view_btn.click(
                fn=get_speaker_profiles,
                inputs=[view_session_id],
                outputs=[profiles_output]
            )

        with gr.Tab("Document Viewer"):
            gr.Markdown("""
            ### Google Drive Document Viewer

            View your private Google Docs without needing to make them publicly shared.

            **First-time setup (5-10 minutes, completely free):**
            1. Create Google Cloud credentials → See **`docs/GOOGLE_OAUTH_SIMPLE_SETUP.md`** for step-by-step guide
            2. Click "Authorize with Google" below
            3. Load any Google Doc you have access to!

            **Features:**
            - Access your private documents securely via OAuth
            - No need to make documents publicly shared
            - Import campaign notes for use in profile extraction and knowledge base
            - **No billing required** - completely free for personal use!
            """)

            # State to store OAuth flow object per session
            oauth_flow_state = gr.State(None)

            # OAuth Authorization Section
            gr.Markdown("### Authorization")

            with gr.Row():
                with gr.Column(scale=3):
                    auth_status = gr.Textbox(
                        label="Current Status",
                        value="Checking...",
                        interactive=False
                    )
                with gr.Column(scale=1):
                    setup_guide_btn = gr.Button("📖 Open Setup Guide", size="sm", variant="secondary")
                    setup_guide_result = gr.Textbox(
                        label="",
                        value="",
                        interactive=False,
                        visible=False,
                        show_label=False
                    )

            with gr.Row():
                with gr.Column(scale=2):
                    gr.Markdown("""
                    **Quick Setup (Recommended):**
                    Click the button below - your browser will open for Google authorization.
                    Just approve access and return here. That's it!
                    """)
                    auto_auth_btn = gr.Button(
                        "🔐 Authorize with Google",
                        variant="primary",
                        size="lg"
                    )
                    auto_auth_result = gr.Textbox(
                        label="Authorization Result",
                        lines=3,
                        interactive=False
                    )
                with gr.Column(scale=1):
                    check_auth_btn = gr.Button("🔄 Check Status", size="sm")
                    revoke_auth_btn = gr.Button("🗑️ Revoke Authorization", variant="secondary", size="sm")

            # Advanced/Manual OAuth Section (collapsed by default)
            with gr.Accordion("Advanced: Manual Authorization (if automatic doesn't work)", open=False):
                gr.Markdown("""
                Use this method if the automatic authorization doesn't work (e.g., browser doesn't open automatically).
                """)
                with gr.Row():
                    with gr.Column():
                        start_auth_btn = gr.Button("Start Manual Authorization", variant="secondary")
                        revoke_auth_btn_manual = gr.Button("Revoke Authorization", variant="secondary", size="sm")
                    with gr.Column():
                        auth_output = gr.Textbox(
                            label="Authorization Instructions",
                            lines=8,
                            interactive=False
                        )

                with gr.Row():
                    with gr.Column():
                        auth_code_input = gr.Textbox(
                            label="Redirect URL or Authorization Code",
                            placeholder="Paste the full redirect URL from your browser (http://localhost:8080/?code=...)",
                            lines=2
                        )
                        complete_auth_btn = gr.Button("Complete Authorization", variant="primary")
                    with gr.Column():
                        auth_result = gr.Textbox(
                            label="Result",
                            lines=3,
                            interactive=False
                        )

            # Document Loading Section
            gr.Markdown("### Load Document")
            with gr.Row():
                with gr.Column():
                    gdoc_url_input = gr.Textbox(
                        label="Google Doc URL or ID",
                        placeholder="https://docs.google.com/document/d/... or just the document ID"
                    )
                    gdoc_view_btn = gr.Button("Load Document", variant="primary")

            with gr.Row():
                gdoc_output = gr.Textbox(
                    label="Document Content",
                    lines=20,
                    max_lines=50,
                    show_copy_button=True,
                    interactive=False
                )

            # Wire up the OAuth controls

            # Setup guide button
            setup_guide_btn.click(
                fn=open_setup_guide,
                outputs=[auth_status]
            )

            # Check status button
            check_auth_btn.click(
                fn=check_auth_status,
                outputs=[auth_status]
            )

            # Automatic OAuth button (recommended)
            auto_auth_btn.click(
                fn=start_automatic_oauth,
                outputs=[auto_auth_result]
            )

            # Revoke button (main)
            revoke_auth_btn.click(
                fn=revoke_oauth,
                outputs=[auto_auth_result]
            )

            # Manual OAuth controls (advanced)
            start_auth_btn.click(
                fn=start_oauth_flow,
                outputs=[auth_output, oauth_flow_state]
            )

            complete_auth_btn.click(
                fn=complete_oauth_flow,
                inputs=[oauth_flow_state, auth_code_input],
                outputs=[auth_result, oauth_flow_state]
            )

            revoke_auth_btn_manual.click(
                fn=revoke_oauth,
                outputs=[auth_result]
            )

            # Wire up document loading
            gdoc_view_btn.click(
                fn=view_google_doc,
                inputs=[gdoc_url_input],
                outputs=[gdoc_output]
            )

        with gr.Tab("Logs"):
            gr.Markdown("""
            ### System Logs

            View application logs, errors, and processing history.
            """)

            with gr.Row():
                with gr.Column():
                    refresh_logs_btn = gr.Button("Refresh Logs", size="sm")
                    show_errors_only = gr.Checkbox(label="Show Errors/Warnings Only", value=False)
                    log_lines = gr.Slider(minimum=10, maximum=500, value=100, step=10,
                                         label="Number of lines to display")

                with gr.Column():
                    clear_old_logs_btn = gr.Button("Clear Old Logs (7+ days)", size="sm")
                    clear_logs_status = gr.Textbox(label="Status", interactive=False)

            logs_output = gr.Textbox(label="Log Output", lines=20, max_lines=40, show_copy_button=True, interactive=False, elem_classes="scrollable-log")

            def refresh_logs_ui(errors_only, num_lines):
                try:
                    from src.logger import _logger_instance
                    if errors_only:
                        logs = _logger_instance.get_error_logs(lines=int(num_lines))
                    else:
                        logs = _logger_instance.get_recent_logs(lines=int(num_lines))
                    return logs
                except Exception as e:
                    return f"Error loading logs: {str(e)}"

            def clear_old_logs_ui():
                try:
                    from src.logger import _logger_instance
                    count = _logger_instance.clear_old_logs(days=7)
                    return f"Cleared {count} old log file(s)"
                except Exception as e:
                    return f"Error clearing logs: {str(e)}"

            refresh_logs_btn.click(
                fn=refresh_logs_ui,
                inputs=[show_errors_only, log_lines],
                outputs=[logs_output]
            )

            clear_old_logs_btn.click(
                fn=clear_old_logs_ui,
                outputs=[clear_logs_status]
            )

            # Load logs on page load
            demo.load(
                fn=lambda: refresh_logs_ui(False, 100),
                outputs=[logs_output]
            )

        with gr.Tab("Social Insights"):
            gr.Markdown("""
            ### OOC Keyword Analysis (Topic Nebula)

            Analyze the out-of-character banter to find the most common topics and keywords.

            **Workflow**
            - Enter the session ID that matches the processed output folder (e.g., `session_2024_05_01`).
            - Click **Analyze Banter** to compute TF-IDF keywords from the saved OOC transcript and render the nebula word cloud.
            - If no OOC transcript exists yet, run the main pipeline first or verify the session ID matches the generated files.

            **Interpreting results**
            - The markdown table highlights the top terms with raw counts so you can skim popular jokes and topics.
            - The nebula graphic saves to `temp/` for reuse in retrospectives or recap decks.
            - Rerun the analysis after updating speaker mappings or classifications to compare topic shifts between sessions.
            """)
            with gr.Row():
                with gr.Column():
                    insight_session_id = gr.Textbox(
                        label="Session ID",
                        placeholder="Enter the ID of a completed session"
                    )
                    insight_btn = gr.Button("☁️ Analyze Banter", variant="primary")
                with gr.Column():
                    keyword_output = gr.Markdown(label="Top Keywords")
            with gr.Row():
                nebula_output = gr.Image(label="Topic Nebula")

            def analyze_ooc_ui(session_id):
                try:
                    from src.analyzer import OOCAnalyzer
                    from src.config import Config
                    from wordcloud import WordCloud
                    import matplotlib.pyplot as plt

                    if not session_id:
                        return "Please enter a session ID.", None

                    # Sanitize session_id for file path
                    from src.formatter import sanitize_filename
                    sanitized_session_id = sanitize_filename(session_id)

                    ooc_file = Config.OUTPUT_DIR / f"{sanitized_session_id}_ooc_only.txt"
                    if not ooc_file.exists():
                        return f"OOC transcript not found for session: {session_id}", None

                    # Analyze
                    analyzer = OOCAnalyzer(ooc_file)
                    keywords = analyzer.get_keywords(top_n=30)

                    if not keywords:
                        return "No significant keywords found in the OOC transcript.", None

                    # Generate Word Cloud (Topic Nebula)
                    wc = WordCloud(
                        width=800, 
                        height=400, 
                        background_color="#0C111F", # Deep Space Blue
                        colormap="cool", # A good starting point, can be customized
                        max_words=100,
                        contour_width=3,
                        contour_color='#89DDF5' # Cyan Dwarf
                    )
                    wc.generate_from_frequencies(dict(keywords))

                    # Save to a temporary file
                    temp_path = Config.TEMP_DIR / f"{sanitized_session_id}_nebula.png"
                    wc.to_file(str(temp_path))

                    # Format keyword list for display
                    keyword_md = "### Top Keywords\n\n| Rank | Keyword | Frequency |\n|---|---|---|"
                    for i, (word, count) in enumerate(keywords, 1):
                        keyword_md += f"| {i} | {word} | {count} |\n"

                    return keyword_md, temp_path

                except Exception as e:
                    return f"Error during analysis: {e}", None

            insight_btn.click(
                fn=analyze_ooc_ui,
                inputs=[insight_session_id],
                outputs=[keyword_output, nebula_output]
            )

        story_session_state = gr.State({})
        initial_story_sessions = _list_available_sessions()

        with gr.Tab("Story Notebooks"):
            gr.Markdown("""
            ### Story Notebooks - Generate Session Narratives

            Transform your processed session transcripts into compelling story narratives using AI.

            #### How It Works:

            1. **Select a Session**: Choose a processed session from the dropdown
            2. **Adjust Creativity**: Lower = faithful retelling (0.1-0.4), Higher = more dramatic flair (0.6-1.0)
            3. **Generate Narrator Summary**: Creates an omniscient overview of the session (DM perspective)
            4. **Generate Character Narratives**: Creates first-person recaps from each PC's point of view

            #### What You Get:

            - **Narrator Perspective**: A balanced, objective summary highlighting all characters' contributions
            - **Character Perspectives**: Personal, emotional accounts from each character's viewpoint
            - **Campaign Continuity**: References your campaign notebook (if loaded) for context
            - **Saved Narratives**: All narratives are saved to `output/<session>/narratives/` folder

            #### Tips:

            - **First run?** Click "Refresh Sessions" to load available sessions
            - **Want more context?** Use the Document Viewer tab to import campaign notes first
            - **Creativity slider**: 0.3-0.5 works well for accurate summaries, 0.6-0.8 for dramatic storytelling
            - **Save time**: Generate narrator first to get the big picture, then character perspectives

            ---
            """)

            story_session_dropdown = gr.Dropdown(
                label="Session",
                choices=initial_story_sessions,
                value=initial_story_sessions[0] if initial_story_sessions else None,
                interactive=True,
                info="Select which processed session to summarize"
            )
            refresh_story_btn = gr.Button("Refresh Sessions", variant="secondary")
            story_temperature = gr.Slider(
                minimum=0.1,
                maximum=1.0,
                value=0.55,
                step=0.05,
                label="Creativity",
                info="Lower = faithful retelling, higher = more flourish"
            )

            story_notebook_status = gr.Markdown(_notebook_status())
            story_session_info = gr.Markdown("Select a session to view transcript stats.")

            with gr.Accordion("Narrator Perspective", open=True):
                narrator_btn = gr.Button("Generate Narrator Summary", variant="primary")
                narrator_story = gr.Markdown("Narrator perspective will appear here once generated.")
                narrator_path = gr.Textbox(label="Saved Narrative Path", interactive=False)

            with gr.Accordion("Character Perspectives", open=False):
                character_dropdown = gr.Dropdown(
                    label="Select Character",
                    choices=[],
                    value=None,
                    interactive=False,
                    info="Choose which character voice to write from"
                )
                character_btn = gr.Button("Generate Character Narrative", variant="primary")
                character_story = gr.Markdown("Pick a character and generate to see their POV recap.")
                character_path = gr.Textbox(label="Saved Narrative Path", interactive=False)

            refresh_notebook_btn = gr.Button("Refresh Notebook Context", variant="secondary")

            refresh_story_btn.click(
                fn=story_refresh_sessions_ui,
                outputs=[story_session_dropdown, character_dropdown, story_session_info, story_session_state, story_notebook_status]
            )

            story_session_dropdown.change(
                fn=story_select_session_ui,
                inputs=[story_session_dropdown],
                outputs=[character_dropdown, story_session_info, story_session_state, story_notebook_status]
            )

            narrator_btn.click(
                fn=story_generate_narrator,
                inputs=[story_session_state, story_temperature],
                outputs=[narrator_story, narrator_path]
            )

            character_btn.click(
                fn=story_generate_character,
                inputs=[story_session_state, character_dropdown, story_temperature],
                outputs=[character_story, character_path]
            )

            refresh_notebook_btn.click(
                fn=_notebook_status,
                outputs=[story_notebook_status]
            )

            demo.load(
                fn=story_refresh_sessions_ui,
                outputs=[story_session_dropdown, character_dropdown, story_session_info, story_session_state, story_notebook_status]
            )

        with gr.Tab("Diagnostics"):
            gr.Markdown("""
            ### Test Diagnostics

            Discover pytest tests and run them without leaving the app.

            **Buttons**
            - **Discover Tests**: Runs `pytest --collect-only -q` and populates the list with discoverable test node IDs.
            - **Run Selected Tests**: Executes the chosen node IDs with `pytest -q`, returning pass/fail plus truncated output.
            - **Run All Tests**: Launches the entire pytest suite (`pytest -q`) for a quick regression check.

            **Notes**
            - Requires the development dependencies from `requirements.txt` (pytest, etc.).
            - Output is capped to keep the UI responsive; open `logs/app_stdout.log` if you need the full trace.
            - Use this tab while iterating on pipeline components to validate fixes without leaving the dashboard.
            """)
            discover_btn = gr.Button("Discover Tests", variant="secondary")
            tests_list = gr.CheckboxGroup(label="Available Tests", choices=[], interactive=True)
            with gr.Row():
                run_selected_btn = gr.Button("Run Selected Tests", variant="primary")
                run_all_btn = gr.Button("Run All Tests", variant="secondary")
            test_status = gr.Markdown("")
            test_output = gr.Textbox(label="Pytest Output", value="", lines=12, interactive=False)

            discover_btn.click(
                fn=collect_pytest_tests_ui,
                inputs=[],
                outputs=[test_status, tests_list]
            )

            run_selected_btn.click(
                fn=run_pytest_selection,
                inputs=[tests_list],
                outputs=[test_status, test_output]
            )

            run_all_btn.click(
                fn=run_all_tests_ui,
                inputs=[],
                outputs=[test_status, test_output]
            )

        with gr.Tab("LLM Chat"):
            gr.Markdown("""
            ### Chat with the Local LLM

            Interact with the configured Ollama model, optionally as a specific character.
            """)

            # Load character profiles
            try:
                with open(PROJECT_ROOT / "models" / "character_profiles.json", "r", encoding="utf-8") as f:
                    character_profiles = json.load(f)
                character_names = ["None"] + list(character_profiles.keys())
            except (FileNotFoundError, json.JSONDecodeError):
                character_profiles = {}
                character_names = ["None"]

            with gr.Row():
                character_dropdown = gr.Dropdown(
                    label="Chat as Character",
                    choices=character_names,
                    value="None",
                    info="Select a character to role-play as."
                )

            chatbot = gr.Chatbot(label="Chat History", type="messages")
            msg = gr.Textbox(label="Your Message")
            clear = gr.Button("Clear Chat")

            def chat_with_llm(message: str, chat_history: list, character_name: str):
                try:
                    import ollama
                    client = ollama.Client(host="http://localhost:11434")

                    # Prepare the messages for the Ollama API
                    ollama_messages = []

                    # Add system prompt if a character is selected
                    if character_name and character_name != "None":
                        profile = character_profiles.get(character_name)
                        if profile:
                            system_prompt = (
                                f"You are role-playing as the character '{profile['name']}'. "
                                f"Description: {profile.get('description', 'N/A')}. "
                                f"Personality: {profile.get('personality', 'N/A')}. "
                                f"Backstory: {profile.get('backstory', 'N/A')}. "
                                "Stay in character and respond as they would."
                            )
                            ollama_messages.append({'role': 'system', 'content': system_prompt})

                    # Add existing chat history and the new message
                    ollama_messages.extend(chat_history)
                    ollama_messages.append({'role': 'user', 'content': message})

                    # Stream response
                    stream = client.chat(
                        model=Config.OLLAMA_MODEL,
                        messages=ollama_messages,
                        stream=True
                    )

                    # Append the user's message to the chat history for display
                    chat_history.append({"role": "user", "content": message})
                    # Add a placeholder for the assistant's response
                    chat_history.append({"role": "assistant", "content": ""})

                    # Stream the response into the placeholder and yield the updated history
                    for chunk in stream:
                        content = chunk['message']['content']
                        if content:
                            chat_history[-1]['content'] += content
                            yield chat_history

                except Exception as e:
                    import traceback
                    error_details = traceback.format_exc()
                    # Append an error message to the history for display
                    chat_history.append({"role": "assistant", "content": f"Error: {str(e)}\nDetails: {error_details}"})
                    yield chat_history

            # Clear chat when a new character is selected
            character_dropdown.change(lambda: [], None, [chatbot, msg])

            msg.submit(chat_with_llm, [msg, chatbot, character_dropdown], chatbot)
            clear.click(lambda: [], None, [chatbot, msg])


        with gr.Tab("Configuration"):
            # Get GPU information
            try:
                import torch
                gpu_available = torch.cuda.is_available()
                if gpu_available:
                    gpu_name = torch.cuda.get_device_name(0)
                    gpu_count = torch.cuda.device_count()
                    cuda_version = torch.version.cuda
                    gpu_status = f"✅ **{gpu_name}** (CUDA {cuda_version})"
                else:
                    pytorch_version = torch.__version__
                    if "+cpu" in pytorch_version:
                        gpu_status = "❌ **CPU-only PyTorch installed** - No GPU acceleration"
                    else:
                        gpu_status = "❌ **No GPU detected** - Using CPU"
            except Exception as e:
                gpu_status = f"⚠️ **Error checking GPU**: {str(e)}"

            gr.Markdown(f"""
            ### Current Configuration

            - **Whisper Model**: {Config.WHISPER_MODEL}
            - **Whisper Backend**: {Config.WHISPER_BACKEND}
            - **LLM Backend**: {Config.LLM_BACKEND}
            - **Chunk Length**: {Config.CHUNK_LENGTH_SECONDS}s
            - **Chunk Overlap**: {Config.CHUNK_OVERLAP_SECONDS}s
            - **Sample Rate**: {Config.AUDIO_SAMPLE_RATE} Hz
            - **Output Directory**: {Config.OUTPUT_DIR}

            ### GPU Status

            - **GPU Acceleration**: {gpu_status}

            To change settings, edit the `.env` file in the project root.

            **What this tab tells you**
            - Confirms which transcription and LLM backends are active before you launch a run.
            - Shows chunking parameters so you can double-check overlap and duration when troubleshooting alignment issues.
            - Mirrors the effective output and temp directories, useful when you are processing from an alternate drive.

            **When GPU data matters**
            - If GPU acceleration reads as CPU-only, install CUDA-enabled PyTorch or ensure the right Python environment is active.
            - Multi-GPU rigs display the primary device name; switch devices via `CUDA_VISIBLE_DEVICES` if you want to target another card.

            **Next steps**
            - Need to tweak defaults? Update `.env`, then reload this tab (or restart the app) to verify the new values.
            - After changing hardware drivers, revisit this tab to confirm the runtime still detects your GPU.
            """)

        with gr.Tab("Help"):
            gr.Markdown("""
            ## How to Use

            ### First Time Setup

            1. **Install Dependencies**:
               ```bash
               pip install -r requirements.txt
               ```

            2. **Install FFmpeg**:
               - Download from https://ffmpeg.org
               - Add to system PATH

            3. **Setup Ollama** (for IC/OOC classification):
               ```bash
               # Install Ollama from https://ollama.ai
               ollama pull gpt-oss:20b
               ```

            4. **Setup PyAnnote** (for speaker diarization):
               - Visit https://huggingface.co/pyannote/speaker-diarization
               - Accept terms and create token
               - Add `HF_TOKEN=your_token` to `.env` file

            ### Processing a Session

            1. Upload your D&D session recording (M4A, MP3, WAV, etc.)
            2. Enter a unique session ID
            3. List your character and player names (helps with classification)
            4. Adjust number of speakers if needed
            5. Click "Process Session" and wait
            6. View results in different tabs

            ### Expected Processing Time

            - **4-hour session with local models**: ~2-4 hours
            - **4-hour session with Groq API**: ~30-60 minutes
            - Depends on your hardware (GPU helps a lot!)

            ### Tips

            - First processing takes longer (model downloads)
            - GPU significantly speeds up transcription
            - You can skip diarization/classification for faster results
            - Speaker mappings improve with manual correction

            ### Troubleshooting

            - **FFmpeg not found**: Install FFmpeg and add to PATH
            - **Ollama connection failed**: Start Ollama server
            - **PyAnnote error**: Set HF_TOKEN in .env
            - **Out of memory**: Try processing shorter clips first
            """)

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
