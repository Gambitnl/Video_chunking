"""Gradio web UI for D&D Session Processor"""
import os
import json
import socket
import sys
import subprocess
from pathlib import Path

import gradio as gr
import requests

from typing import Dict, List

from src.pipeline import DDSessionProcessor
from src.config import Config
from src.diarizer import SpeakerProfileManager
from src.logger import get_log_file_path
from src.party_config import PartyConfigManager, CampaignManager
from src.knowledge_base import CampaignKnowledgeBase


PROJECT_ROOT = Path(__file__).resolve().parent
NOTEBOOK_CONTEXT = ""

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
    """Downloads a public Google Doc as plain text."""
    global NOTEBOOK_CONTEXT
    try:
        doc_id_start = doc_url.find("/d/") + 3
        doc_id_end = doc_url.find("/edit")
        if doc_id_end == -1:
            doc_id_end = doc_url.find("/view")
        if doc_id_end == -1:
            doc_id_end = len(doc_url)

        doc_id = doc_url[doc_id_start:doc_id_end]
        export_url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"

        response = requests.get(export_url)
        response.raise_for_status()
        NOTEBOOK_CONTEXT = response.text or ""
        return NOTEBOOK_CONTEXT
    except Exception as e:
        return f"Error downloading document: {e}"




def _load_session_json(session_id: str) -> tuple[Path, Dict]:
    """Load session JSON data for the latest matching session."""
    session_prefix = session_id.replace(" ", "_")
    candidates = list(Config.OUTPUT_DIR.glob(f"**/{session_prefix}*_data.json"))
    if not candidates:
        raise FileNotFoundError(f"No session data found for session_id={session_id}")
    latest = max(candidates, key=lambda p: p.stat().st_mtime)
    data = json.loads(latest.read_text(encoding="utf-8"))
    return latest, data


STORY_NO_DATA = "No transcription data available for this session yet."


def _list_available_sessions() -> List[str]:
    """Return recent session IDs based on available JSON output."""
    session_ids: List[str] = []
    seen = set()
    candidates = sorted(
        Config.OUTPUT_DIR.glob("**/*_data.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for candidate in candidates:
        try:
            data = json.loads(candidate.read_text(encoding="utf-8"))
            session_id = (
                data.get("metadata", {}).get("session_id")
                or candidate.stem.replace("_data", "")
            )
        except Exception:
            session_id = candidate.stem.replace("_data", "")
        if session_id and session_id not in seen:
            seen.add(session_id)
            session_ids.append(session_id)
        if len(session_ids) >= 25:
            break
    return session_ids








def _build_perspective_prompt(
    perspective_name: str,
    segments: List[Dict],
    character_names: List[str],
    narrator: bool,
    notebook_context: str,
) -> str:
    """Construct prompt for the narrative generator."""
    key_segments: List[str] = []
    for seg in segments:
        if seg.get("classification", "IC") != "IC":
            continue
        text = (seg.get("text") or "").strip()
        if not text:
            continue
        char = seg.get("character") or seg.get("speaker_name") or ""
        timestamp = seg.get("start_time")
        try:
            stamp = float(timestamp)
        except (TypeError, ValueError):
            stamp = 0.0
        key_segments.append(f"[{stamp:06.2f}] {char}: {text}")
        if len(key_segments) >= 60:
            break

    joined_segments = "\n".join(key_segments) if key_segments else "(Transcript excerpts unavailable)"
    persona = (
        f"You are the character {perspective_name}, one of the main protagonists."
        if not narrator
        else "You are an omniscient narrator summarizing events for the campaign log."
    )
    supporting = (
        "Campaign notebook excerpt:\n" + (notebook_context[:3000] if notebook_context else "(no additional notes provided)")
    )
    instructions = (
        "Write a concise per-session narrative (~3-5 paragraphs) capturing actions, emotions, and consequences. Maintain continuity with prior sessions and keep vocabulary consistent with the character's voice."
        if not narrator
        else "Provide a balanced overview highlighting each character's contributions while keeping the tone neutral and descriptive."
    )

    return (
        f"{persona}\n"
        "You are summarizing a D&D session using the following transcript extracts.\n"
        "Focus on the referenced events; infer light transitions when necessary but avoid inventing new story beats.\n"
        "Keep the output under 500 words.\n\n"
        "Transcript snippets:\n"
        f"{joined_segments}\n\n"
        f"{supporting}\n\n"
        "Instructions:\n"
        f"{instructions}\n"
    )


def _generate_perspective_story(prompt: str, temperature: float = 0.5) -> str:
    """Use the configured LLM to generate narrative text."""
    try:
        import ollama
        import logging
        import sys
        import io

        # Suppress ollama and other library logging temporarily
        ollama_logger = logging.getLogger("ollama")
        original_level = ollama_logger.level
        ollama_logger.setLevel(logging.CRITICAL)

        # Capture and suppress stdout/stderr temporarily
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()

        try:
            client = ollama.Client(host=Config.OLLAMA_BASE_URL)
            response = client.generate(
                model=Config.OLLAMA_MODEL,
                prompt=prompt,
                options={"temperature": temperature, "num_predict": 800},
            )
            narrative = response.get("response", "(LLM returned no text)")
        finally:
            # Restore stdout/stderr and logging
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            ollama_logger.setLevel(original_level)

        return narrative
    except Exception as exc:
        # Make sure stdout/stderr are restored even on exception
        sys.stdout = old_stdout if 'old_stdout' in locals() else sys.stdout
        sys.stderr = old_stderr if 'old_stderr' in locals() else sys.stderr
        return f"Error generating narrative: {exc}"


def _save_narrative(json_path: Path, session_id: str, perspective: str, story: str) -> Path:
    """Persist generated narrative to the session's narrative folder."""
    safe_perspective = perspective.lower().replace(" ", "_")
    narratives_dir = (json_path.parent / "narratives")
    narratives_dir.mkdir(parents=True, exist_ok=True)
    file_path = narratives_dir / f"{session_id}_{safe_perspective}.md"
    file_path.write_text(story, encoding="utf-8")
    return file_path






def _notebook_status() -> str:
    if NOTEBOOK_CONTEXT:
        sample = NOTEBOOK_CONTEXT[:200].replace('\r', ' ').replace('\n', ' ')
        return f"Notebook context loaded ({len(NOTEBOOK_CONTEXT)} chars). Sample: {sample}..."
    return "No notebook context loaded yet. Use the Document Viewer tab to import campaign notes."


def _story_prepare_session(session_id: str):
    try:
        json_path, data = _load_session_json(session_id)
    except Exception as exc:
        raise RuntimeError(f"Error loading session '{session_id}': {exc}")
    metadata = data.get("metadata", {})
    segments = data.get("segments", [])
    character_names = metadata.get("character_names") or []
    state = {
        "json_path": str(json_path),
        "metadata": metadata,
        "segments": segments,
        "session_id": metadata.get("session_id") or session_id,
    }
    info = (
        f"Loaded {metadata.get('session_id', session_id)} -> {len(segments)} segment(s). "
        f"Character perspectives available: {', '.join(character_names) if character_names else 'None discovered.'}"
    )
    return character_names, info, state


def story_refresh_sessions_ui():
    sessions = _list_available_sessions()
    if not sessions:
        return (
            gr.update(choices=[], value=None, interactive=True),
            gr.update(choices=[], value=None, interactive=False),
            "No session data found under 'output/'. Run the pipeline first.",
            {},
            _notebook_status(),
        )
    session_id = sessions[0]
    try:
        character_names, info, state = _story_prepare_session(session_id)
    except Exception as exc:
        return (
            gr.update(choices=sessions, value=session_id, interactive=True),
            gr.update(choices=[], value=None, interactive=False),
            f"Error loading session: {exc}",
            {},
            _notebook_status(),
        )
    char_update = gr.update(
        choices=character_names,
        value=character_names[0] if character_names else None,
        interactive=bool(character_names),
    )
    drop_update = gr.update(choices=sessions, value=session_id, interactive=True)
    return drop_update, char_update, info, state, _notebook_status()


def story_select_session_ui(session_id: str):
    if not session_id:
        return (
            gr.update(choices=[], value=None, interactive=False),
            "Select a session to begin generating narratives.",
            {},
            _notebook_status(),
        )
    try:
        character_names, info, state = _story_prepare_session(session_id)
    except Exception as exc:
        return (
            gr.update(choices=[], value=None, interactive=False),
            f"Error loading session: {exc}",
            {},
            _notebook_status(),
        )
    char_update = gr.update(
        choices=character_names,
        value=character_names[0] if character_names else None,
        interactive=bool(character_names),
    )
    return char_update, info, state, _notebook_status()


def story_generate_narrator(session_state: Dict, temperature: float) -> tuple[str, str]:
    if not session_state or not session_state.get("segments"):
        return "## ⚠️ No Session Loaded\n\nPlease select a session from the dropdown above, then try again.", ""

    segments = session_state.get("segments") or []
    metadata = session_state.get("metadata") or {}
    session_id = metadata.get("session_id", "session")

    # Show generation message
    generating_msg = f"## 🎲 Generating Narrator Summary for {session_id}...\n\n"
    generating_msg += f"- **Temperature**: {temperature:.2f}\n"
    generating_msg += f"- **Segments**: {len(segments)}\n"
    generating_msg += f"- **Characters**: {', '.join(metadata.get('character_names', ['None']))}\n\n"
    generating_msg += "*This may take 10-30 seconds depending on your LLM speed...*"

    prompt = _build_perspective_prompt(
        perspective_name="Narrator",
        segments=segments,
        character_names=metadata.get("character_names") or [],
        narrator=True,
        notebook_context=NOTEBOOK_CONTEXT,
    )
    story = _generate_perspective_story(prompt, temperature=temperature)

    try:
        json_path = Path(session_state.get("json_path"))
        file_path = _save_narrative(json_path, session_id, "narrator", story)
        saved_path = str(file_path)
    except Exception as exc:
        saved_path = f"Could not save narrative: {exc}"

    return story, saved_path


def story_generate_character(session_state: Dict, character_name: str, temperature: float) -> tuple[str, str]:
    if not session_state or not session_state.get("segments"):
        return "## ⚠️ No Session Loaded\n\nPlease select a session from the dropdown at the top of this tab, then try again.", ""
    if not character_name:
        return "Select a character perspective to generate.", ""
    segments = session_state.get("segments") or []
    metadata = session_state.get("metadata") or {}
    prompt = _build_perspective_prompt(
        perspective_name=character_name,
        segments=segments,
        character_names=metadata.get("character_names") or [],
        narrator=False,
        notebook_context=NOTEBOOK_CONTEXT,
    )
    story = _generate_perspective_story(prompt, temperature=temperature)
    try:
        json_path = Path(session_state.get("json_path"))
        file_path = _save_narrative(json_path, session_state.get("session_id", "session"), character_name, story)
        saved_path = str(file_path)
    except Exception as exc:
        saved_path = f"Could not save narrative: {exc}"
    return story, saved_path


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
with gr.Blocks(title="D&D Session Processor", theme=gr.themes.Soft()) as demo:
    gr.Markdown("""
    # 🎲 D&D Session Transcription & Diarization

    Upload your D&D session recording and get:
    - Full transcript with speaker labels
    - In-character only transcript (game narrative)
    - Out-of-character only transcript (banter & meta-discussion)
    - Detailed statistics and analysis

    **Supported formats**: M4A, MP3, WAV, and more
    """)

    with gr.Tab("Campaign Dashboard"):
        gr.Markdown("""
        ### Campaign Overview & Health Check

        Select a campaign to see its complete configuration status and what data you have.
        """)

        campaign_names = _refresh_campaign_names()
        dashboard_campaign = gr.Dropdown(
            choices=["Manual Setup"] + list(campaign_names.values()),
            value=list(campaign_names.values())[0] if campaign_names else "Manual Setup",
            label="📋 Select Campaign to Review",
            info="Choose which campaign to inspect"
        )

        dashboard_refresh = gr.Button("🔄 Refresh Dashboard", variant="secondary", size="sm")

        dashboard_output = gr.Markdown()

        def generate_campaign_dashboard(campaign_name):
            """Generate comprehensive campaign status dashboard"""
            names = _refresh_campaign_names()
            if campaign_name == "Manual Setup":
                return "## Manual Setup Mode\n\nNo campaign profile selected. Choose a campaign from the dropdown to see its dashboard."

            # Find campaign ID
            campaign_id = None
            for cid, cname in names.items():
                if cname == campaign_name:
                    campaign_id = cid
                    break

            if not campaign_id:
                return f"## Error\n\nCampaign '{campaign_name}' not found."

            campaign = campaign_manager.get_campaign(campaign_id)
            if not campaign:
                return f"## Error\n\nCampaign '{campaign_id}' configuration not found."

            # Start building dashboard
            output = f"# 🎲 Campaign Dashboard: {campaign.name}\n\n"

            if campaign.description:
                output += f"*{campaign.description}*\n\n"

            output += "---\n\n"

            # Component status tracking
            all_good = []
            needs_attention = []

            # 1. PARTY CONFIGURATION
            output += "## 1️⃣ Party Configuration\n\n"
            party_mgr = PartyConfigManager()
            party = party_mgr.get_party(campaign.party_id)

            if party:
                output += f"✅ **Status**: Configured\n\n"
                output += f"- **Party Name**: {party.party_name}\n"
                output += f"- **DM**: {party.dm_name}\n"
                output += f"- **Characters**: {len(party.characters)}\n"

                output += f"\n**Character Roster:**\n"
                for char in party.characters:
                    aliases = f" (aka {', '.join(char.aliases)})" if char.aliases else ""
                    output += f"- **{char.name}**{aliases}: {char.race} {char.class_name} (played by {char.player})\n"

                if party.campaign:
                    output += f"\n**Campaign Setting**: {party.campaign}\n"

                all_good.append("Party Configuration")
            else:
                output += f"❌ **Status**: Not configured\n\n"
                output += f"**Action**: Go to **Party Management** tab → Create party '{campaign.party_id}'\n"
                needs_attention.append("Party Configuration")

            output += "\n---\n\n"

            # 2. PROCESSING SETTINGS
            output += "## 2️⃣ Processing Settings\n\n"
            output += "✅ **Status**: Configured\n\n"
            output += f"- **Number of Speakers**: {campaign.settings.num_speakers}\n"
            output += f"- **Skip Diarization**: {'Yes' if campaign.settings.skip_diarization else 'No'}\n"
            output += f"- **Skip IC/OOC Classification**: {'Yes' if campaign.settings.skip_classification else 'No'}\n"
            output += f"- **Skip Audio Snippets**: {'Yes' if campaign.settings.skip_snippets else 'No'}\n"
            output += f"- **Skip Knowledge Extraction**: {'Yes' if campaign.settings.skip_knowledge else 'No'}\n"
            output += f"- **Session ID Prefix**: `{campaign.settings.session_id_prefix}`\n"
            all_good.append("Processing Settings")

            output += "\n---\n\n"

            # 3. KNOWLEDGE BASE
            output += "## 3️⃣ Campaign Knowledge Base\n\n"
            try:
                from src.knowledge_base import CampaignKnowledgeBase
                kb = CampaignKnowledgeBase(campaign_id=campaign_id)

                sessions = kb.knowledge.get('sessions_processed', [])
                quests = kb.knowledge.get('quests', [])
                npcs = kb.knowledge.get('npcs', [])
                plot_hooks = kb.knowledge.get('plot_hooks', [])
                locations = kb.knowledge.get('locations', [])
                items = kb.knowledge.get('items', [])

                total_entities = len(quests) + len(npcs) + len(plot_hooks) + len(locations) + len(items)

                if sessions or total_entities > 0:
                    output += f"✅ **Status**: Active ({total_entities} entities)\n\n"
                    output += f"- **Sessions Processed**: {len(sessions)} ({', '.join(sessions) if sessions else 'None'})\n"
                    output += f"- **Quests**: {len(quests)} ({len([q for q in quests if q.status == 'active'])} active)\n"
                    output += f"- **NPCs**: {len(npcs)}\n"
                    output += f"- **Plot Hooks**: {len(plot_hooks)} ({len([p for p in plot_hooks if not p.resolved])} unresolved)\n"
                    output += f"- **Locations**: {len(locations)}\n"
                    output += f"- **Items**: {len(items)}\n"
                    output += f"\n**Storage**: `{kb.knowledge_file}`\n"
                    all_good.append("Knowledge Base")
                else:
                    output += f"⚠️ **Status**: Empty (no sessions processed yet)\n\n"
                    output += f"**Action**: Process a session or import session notes to populate knowledge base\n"
                    output += f"\n**Storage**: `{kb.knowledge_file}` (ready)\n"
                    needs_attention.append("Knowledge Base (empty)")

            except Exception as e:
                output += f"❌ **Status**: Error loading knowledge base\n\n"
                output += f"```\n{str(e)}\n```\n"
                needs_attention.append("Knowledge Base (error)")

            output += "\n---\n\n"

            # 4. CHARACTER PROFILES
            output += "## 4️⃣ Character Profiles\n\n"
            try:
                profiles_file = Config.MODELS_DIR / "character_profiles.json"
                if profiles_file.exists():
                    with open(profiles_file, 'r', encoding='utf-8') as f:
                        profiles = json.load(f)

                    if party:
                        party_char_names = [c.name for c in party.characters]
                        profiles_for_party = [name for name in party_char_names if name in profiles]
                        missing_profiles = [name for name in party_char_names if name not in profiles]

                        if len(profiles_for_party) == len(party_char_names):
                            output += f"✅ **Status**: Complete ({len(profiles_for_party)}/{len(party_char_names)} characters)\n\n"
                            for name in profiles_for_party:
                                profile = profiles[name]
                                output += f"- **{name}**: {profile.get('personality', 'No personality set')[:50]}...\n"
                            all_good.append("Character Profiles")
                        elif len(profiles_for_party) > 0:
                            output += f"⚠️ **Status**: Partial ({len(profiles_for_party)}/{len(party_char_names)} characters)\n\n"
                            output += f"**Configured**: {', '.join(profiles_for_party)}\n\n"
                            output += f"**Missing**: {', '.join(missing_profiles)}\n\n"
                            output += f"**Action**: Go to **Character Profiles** tab → Create profiles for missing characters\n"
                            needs_attention.append(f"Character Profiles ({len(missing_profiles)} missing)")
                        else:
                            output += f"❌ **Status**: None configured\n\n"
                            output += f"**Action**: Go to **Character Profiles** tab → Create profiles for party characters\n"
                            needs_attention.append("Character Profiles (none)")
                    else:
                        output += f"⚠️ **Status**: Cannot check (party not configured)\n"
                        needs_attention.append("Character Profiles (no party)")
                else:
                    output += f"❌ **Status**: No profiles file found\n\n"
                    output += f"**Action**: Go to **Character Profiles** tab → Create first character profile\n"
                    needs_attention.append("Character Profiles (no file)")

            except Exception as e:
                output += f"❌ **Status**: Error loading profiles\n\n"
                output += f"```\n{str(e)}\n```\n"
                needs_attention.append("Character Profiles (error)")

            output += "\n---\n\n"

            # 5. PROCESSED SESSIONS
            output += "## 5️⃣ Processed Audio Sessions\n\n"
            try:
                # Look for session output directories
                session_dirs = []
                if Config.OUTPUT_DIR.exists():
                    session_dirs = [d for d in Config.OUTPUT_DIR.iterdir() if d.is_dir()]

                if session_dirs:
                    output += f"✅ **Status**: {len(session_dirs)} session(s) found\n\n"

                    # List recent sessions
                    recent = sorted(session_dirs, key=lambda d: d.stat().st_mtime, reverse=True)[:5]
                    output += "**Recent Sessions:**\n"
                    for d in recent:
                        # Check for data.json
                        data_files = list(d.glob("*_data.json"))
                        if data_files:
                            output += f"- `{d.name}` ✓\n"
                        else:
                            output += f"- `{d.name}` (incomplete)\n"

                    all_good.append("Processed Sessions")
                else:
                    output += f"⚠️ **Status**: No sessions processed yet\n\n"
                    output += f"**Action**: Go to **Process Session** tab → Process your first recording\n"
                    needs_attention.append("Processed Sessions (none)")

            except Exception as e:
                output += f"❌ **Status**: Error checking sessions\n\n"
                output += f"```\n{str(e)}\n```\n"
                needs_attention.append("Processed Sessions (error)")

            output += "\n---\n\n"

            # 6. SESSION NARRATIVES
            output += "## 6️⃣ Session Narratives\n\n"
            try:
                narrative_count = 0

                # Check processed session narratives
                if Config.OUTPUT_DIR.exists():
                    for session_dir in Config.OUTPUT_DIR.iterdir():
                        if session_dir.is_dir():
                            narratives_dir = session_dir / "narratives"
                            if narratives_dir.exists():
                                narrative_count += len(list(narratives_dir.glob("*.md")))

                # Check imported narratives
                imported_dir = Config.OUTPUT_DIR / "imported_narratives"
                if imported_dir.exists():
                    narrative_count += len(list(imported_dir.glob("*.md")))

                if narrative_count > 0:
                    output += f"✅ **Status**: {narrative_count} narrative(s) generated\n\n"
                    output += f"**Action**: View in **Story Notebooks** tab\n"
                    all_good.append("Session Narratives")
                else:
                    output += f"⚠️ **Status**: No narratives yet\n\n"
                    output += f"**Action**: Use **Story Notebooks** tab to generate narratives from processed sessions\n"
                    needs_attention.append("Session Narratives (none)")

            except Exception as e:
                output += f"❌ **Status**: Error checking narratives\n\n"
                needs_attention.append("Session Narratives (error)")

            output += "\n---\n\n"

            # SUMMARY
            output += "## 📊 Campaign Health Summary\n\n"

            total_components = len(all_good) + len(needs_attention)
            health_percent = int((len(all_good) / total_components) * 100) if total_components > 0 else 0

            if health_percent == 100:
                health_emoji = "🟢"
                health_status = "Excellent"
            elif health_percent >= 75:
                health_emoji = "🟡"
                health_status = "Good"
            elif health_percent >= 50:
                health_emoji = "🟠"
                health_status = "Fair"
            else:
                health_emoji = "🔴"
                health_status = "Needs Setup"

            output += f"### {health_emoji} Health: {health_status} ({health_percent}%)\n\n"

            if all_good:
                output += f"**✅ Configured ({len(all_good)}):**\n"
                for item in all_good:
                    output += f"- {item}\n"
                output += "\n"

            if needs_attention:
                output += f"**⚠️ Needs Attention ({len(needs_attention)}):**\n"
                for item in needs_attention:
                    output += f"- {item}\n"
                output += "\n"

            output += "---\n\n"
            output += "💡 **Tip**: A complete campaign setup includes party configuration, character profiles, and at least one processed session or imported notes.\n"

            return output

        dashboard_refresh.click(
            fn=generate_campaign_dashboard,
            inputs=[dashboard_campaign],
            outputs=[dashboard_output]
        )

        dashboard_campaign.change(
            fn=generate_campaign_dashboard,
            inputs=[dashboard_campaign],
            outputs=[dashboard_output]
        )

        # Load dashboard on app start
        demo.load(
            fn=generate_campaign_dashboard,
            inputs=[dashboard_campaign],
            outputs=[dashboard_output]
        )

    with gr.Tab("Process Session"):
        with gr.Row():
            with gr.Column():
                # Campaign profile selector
                campaign_names = _refresh_campaign_names()
                campaign_choices = ["Manual Setup"] + list(campaign_names.values())

                campaign_selector = gr.Dropdown(
                    choices=campaign_choices,
                    value="Manual Setup",
                    label="📋 Campaign Profile",
                    info="Select your campaign to auto-fill all settings, or choose 'Manual Setup' to configure manually"
                )

                batch_mode = gr.Checkbox(
                    label="🔄 Batch Mode - Process Multiple Sessions",
                    value=False,
                    info="Upload multiple audio files to process them sequentially"
                )

                audio_input = gr.File(
                    label="Upload Audio File(s)",
                    file_types=["audio"],
                    file_count="multiple"
                )

                session_id_input = gr.Textbox(
                    label="Session ID",
                    placeholder="e.g., session_2024_01_15",
                    info="Unique identifier for this session"
                )

                # Party configuration selector
                party_manager = PartyConfigManager()
                available_parties = ["Manual Entry"] + party_manager.list_parties()

                party_selection_input = gr.Dropdown(
                    choices=available_parties,
                    value="default",
                    label="Party Configuration",
                    info="Select your party or choose 'Manual Entry' to enter names manually"
                )

                character_names_input = gr.Textbox(
                    label="Character Names (comma-separated)",
                    placeholder="e.g., Thorin, Elara, Zyx",
                    info="Names of player characters in the campaign (only used if Manual Entry selected)"
                )

                player_names_input = gr.Textbox(
                    label="Player Names (comma-separated)",
                    placeholder="e.g., Alice, Bob, Charlie, DM",
                    info="Names of actual players (only used if Manual Entry selected)"
                )

                num_speakers_input = gr.Slider(
                    minimum=2,
                    maximum=10,
                    value=4,
                    step=1,
                    label="Number of Speakers",
                    info="Expected number of speakers (helps accuracy)"
                )

                with gr.Row():
                    skip_diarization_input = gr.Checkbox(
                        label="Skip Speaker Diarization",
                        info="Skip identifying who is speaking. Faster processing (~30% time saved), but all speakers labeled as 'UNKNOWN'. Requires HuggingFace token if enabled."
                    )
                    skip_classification_input = gr.Checkbox(
                        label="Skip IC/OOC Classification",
                        info="Skip separating in-character dialogue from out-of-character banter. Faster processing (~20% time saved), but no IC/OOC filtering. All content labeled as IC."
                    )
                    skip_snippets_input = gr.Checkbox(
                        label="Skip Audio Snippets",
                        info="Skip exporting individual WAV files for each dialogue segment. Saves disk space and processing time (~10% time saved). You'll still get all transcripts (TXT, SRT, JSON)."
                    )
                    skip_knowledge_input = gr.Checkbox(
                        label="Skip Campaign Knowledge Extraction",
                        info="Skip automatic extraction of quests, NPCs, plot hooks, locations, and items from the session. Saves processing time (~5% time saved), but campaign library won't be updated.",
                        value=False
                    )

                process_btn = gr.Button("🚀 Process Session", variant="primary", size="lg")

            with gr.Column():
                status_output = gr.Textbox(
                    label="Status",
                    lines=2,
                    interactive=False
                )

                stats_output = gr.Markdown(
                    label="Statistics"
                )

        with gr.Row():
            with gr.Tab("Full Transcript"):
                full_output = gr.Textbox(
                    label="Full Transcript",
                    lines=20,
                    max_lines=50,
                    show_copy_button=True
                )

            with gr.Tab("In-Character Only"):
                ic_output = gr.Textbox(
                    label="In-Character Transcript",
                    lines=20,
                    max_lines=50,
                    show_copy_button=True
                )

            with gr.Tab("Out-of-Character Only"):
                ooc_output = gr.Textbox(
                    label="Out-of-Character Transcript",
                    lines=20,
                    max_lines=50,
                    show_copy_button=True
                )

        # Campaign selector handler
        def load_campaign_settings(campaign_name):
            """Load campaign settings when selected"""
            names = _refresh_campaign_names()
            if campaign_name == "Manual Setup":
                # Return empty/default values for manual setup
                return {
                    party_selection_input: "Manual Entry",
                    num_speakers_input: 4,
                    skip_diarization_input: False,
                    skip_classification_input: False,
                    skip_snippets_input: True,
                    skip_knowledge_input: False,
                }

            # Find the campaign ID from the name
            campaign_id = None
            for cid, cname in names.items():
                if cname == campaign_name:
                    campaign_id = cid
                    break

            if not campaign_id:
                return {}

            campaign = campaign_manager.get_campaign(campaign_id)
            if not campaign:
                return {}

            # Return all settings to update
            return {
                party_selection_input: campaign.party_id,
                num_speakers_input: campaign.settings.num_speakers,
                skip_diarization_input: campaign.settings.skip_diarization,
                skip_classification_input: campaign.settings.skip_classification,
                skip_snippets_input: campaign.settings.skip_snippets,
                skip_knowledge_input: campaign.settings.skip_knowledge,
            }

        campaign_selector.change(
            fn=load_campaign_settings,
            inputs=[campaign_selector],
            outputs=[
                party_selection_input,
                num_speakers_input,
                skip_diarization_input,
                skip_classification_input,
                skip_snippets_input,
                skip_knowledge_input
            ]
        )

        process_btn.click(
            fn=process_session,
            inputs=[
                audio_input,
                session_id_input,
                party_selection_input,
                character_names_input,
                player_names_input,
                num_speakers_input,
                skip_diarization_input,
                skip_classification_input,
                skip_snippets_input,
                skip_knowledge_input
            ],
            outputs=[
                status_output,
                full_output,
                ic_output,
                ooc_output,
                stats_output
            ]
        )

    with gr.Tab("Party Management"):
        gr.Markdown("""
        ### Manage Your D&D Parties

        This section allows you to save and load your party configurations. A party configuration is a JSON file that stores the details of your adventuring group, including:

        -   **Character Names**: The names of the player characters.
        -   **Player Names**: The names of the people playing.
        -   **Campaign Name**: The name of your campaign.
        -   **Character Details**: Additional info like race, class, and aliases that help the system better identify characters.

        #### Why Use Party Configurations?

        -   **Save Time**: Avoid manually typing character and player names every time you process a session.
        -   **Ensure Consistency**: Use the exact same names across all sessions for a campaign, which improves data tracking.
        -   **Improve Accuracy**: Providing detailed character information helps the AI more accurately distinguish between in-character (IC) and out-of-character (OOC) dialogue.

        #### How It Works

        -   **Export**: Select an existing party and click "Export Party" to save its configuration as a `.json` file. You can share this file with others or keep it as a backup.
        -   **Import**: Upload a party `.json` file to add it to your list of available parties. You can then select it on the "Process Session" tab.
        """)

        with gr.Row():
            with gr.Column():
                gr.Markdown("#### Export Party")
                # Filter out "Manual Entry" for export dropdown
                export_party_choices = [p for p in available_parties if p != "Manual Entry"]
                export_party_dropdown = gr.Dropdown(
                    choices=export_party_choices,
                    label="Select Party to Export",
                    value="default" if "default" in export_party_choices else (export_party_choices[0] if export_party_choices else None)
                )
                export_btn = gr.Button("Export Party", variant="primary")
                export_output = gr.File(label="Download Party File")
                export_status = gr.Textbox(label="Status", interactive=False)

            with gr.Column():
                gr.Markdown("#### Import Party")
                import_file = gr.File(
                    label="Upload Party JSON File",
                    file_types=[".json"]
                )
                import_party_id = gr.Textbox(
                    label="Party ID (optional)",
                    placeholder="Leave empty to use ID from file"
                )
                import_btn = gr.Button("Import Party", variant="primary")
                import_status = gr.Textbox(label="Status", interactive=False)

        def export_party_ui(party_id):
            try:
                from tempfile import NamedTemporaryFile
                import os

                # Create temp file
                temp_file = NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8')
                temp_path = Path(temp_file.name)
                temp_file.close()

                # Export party
                party_manager.export_party(party_id, temp_path)

                return temp_path, f"✓ Exported '{party_id}'"
            except Exception as e:
                return None, f"✗ Error: {str(e)}"

        def import_party_ui(file_obj, party_id_override):
            try:
                if file_obj is None:
                    return "✗ Please upload a file"

                # Import the party
                imported_id = party_manager.import_party(
                    Path(file_obj.name),
                    party_id_override if party_id_override else None
                )

                return f"✓ Successfully imported party '{imported_id}'. Refresh the page to use it."
            except Exception as e:
                return f"Error: {e}"

        export_btn.click(
            fn=export_party_ui,
            inputs=[export_party_dropdown],
            outputs=[export_output, export_status]
        )

        import_btn.click(
            fn=import_party_ui,
            inputs=[import_file, import_party_id],
            outputs=[import_status]
        )

    with gr.Tab("Import Session Notes"):
        gr.Markdown("""
        ### Import Session Notes

        Have session notes from sessions you didn't record? Import them here!

        This tool will:
        - Extract campaign knowledge (quests, NPCs, plot hooks, locations, items) from your notes
        - Add extracted knowledge to your campaign library
        - Optionally generate a narrative summary
        - Update character profiles with any new information

        **Perfect for:** Backfilling sessions 1-5 that you only have written notes for!
        """)

        with gr.Row():
            with gr.Column(scale=2):
                notes_session_id = gr.Textbox(
                    label="Session ID",
                    placeholder="Session_01",
                    info="What session are these notes from? (e.g., Session_01, Session_02)"
                )
                notes_campaign_choices = ["default"] + list(_refresh_campaign_names().keys())
                notes_campaign = gr.Dropdown(
                    choices=notes_campaign_choices,
                    value="default",
                    label="Campaign",
                    info="Which campaign do these notes belong to?"
                )
            with gr.Column(scale=1):
                notes_extract_knowledge = gr.Checkbox(
                    label="Extract Knowledge",
                    value=True,
                    info="Extract quests, NPCs, locations, items, plot hooks"
                )
                notes_generate_narrative = gr.Checkbox(
                    label="Generate Narrative",
                    value=False,
                    info="Use LLM to create a story summary"
                )

        notes_input = gr.Textbox(
            label="Session Notes",
            placeholder="Paste your session notes here...\n\nYou can include:\n- What happened during the session\n- NPCs encountered\n- Locations visited\n- Quests started or completed\n- Items found\n- Plot developments",
            lines=15,
            max_lines=30
        )

        notes_file_upload = gr.File(
            label="Or Upload Notes File",
            file_types=[".txt", ".md"],
            type="filepath"
        )

        with gr.Row():
            notes_import_btn = gr.Button("📥 Import Session Notes", variant="primary", size="lg")
            notes_clear_btn = gr.Button("Clear", variant="secondary")

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

        notes_file_upload.change(
            fn=load_notes_from_file,
            inputs=[notes_file_upload],
            outputs=[notes_input]
        )

        notes_import_btn.click(
            fn=import_session_notes,
            inputs=[notes_session_id, notes_campaign, notes_input, notes_extract_knowledge, notes_generate_narrative],
            outputs=[notes_output]
        )

        notes_clear_btn.click(
            lambda: ("", "", ""),
            outputs=[notes_session_id, notes_input, notes_output]
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
            status_emoji = {"active": "🎯", "completed": "✅", "failed": "❌", "unknown": "❓"}
            emoji = status_emoji.get(q.status, "❓")

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
        ### View a Public Google Doc

        Paste the URL of a publicly shared Google Doc to view its text content here.

        - Make sure the document is set to \"Anyone with the link\" → View in Google Docs before pasting the URL.
        - Copy the full link (it should contain `/d/<document_id>/`) so the exporter can fetch the plain-text version.
        - The viewer converts the doc to text only; formatting, images, or comments are not included.

        **Usage tips**
        - Use this tab to quickly pull campaign briefings or prep notes directly into the tool for reference while processing sessions.
        - Combine with the Diagnostics tab to keep instructions and test notes side-by-side in the same UI session.
        """)
        with gr.Row():
            with gr.Column():
                gdoc_url_input = gr.Textbox(
                    label="Google Doc URL",
                    placeholder="https://docs.google.com/document/d/..."
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
