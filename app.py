"""Gradio web UI for D&D Session Processor - Modern UI"""
import os
import json
import socket
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))
import subprocess
from pathlib import Path

import gradio as gr
import requests

from typing import Any, Dict, List, Optional, Tuple

from src.pipeline import DDSessionProcessor
from src.config import Config
from src.diarizer import SpeakerProfileManager
from src.character_profile import CharacterProfileManager
from src.logger import (
    get_log_file_path,
    get_logger,
    get_console_log_level,
    set_console_log_level,
    LOG_LEVEL_CHOICES,
)
from src.audit import log_audit_event
from src.party_config import PartyConfigManager, CampaignManager
from src.knowledge_base import CampaignKnowledgeBase
from src.preflight import PreflightIssue
from src.ui.constants import StatusIndicators
from src.ui.helpers import StatusMessages, UIComponents
from src.campaign_dashboard import CampaignDashboard
from src.story_notebook import StoryNotebookManager
from src.artifact_counter import CampaignArtifactCounter

# Modern UI imports
from src.ui.theme import create_modern_theme, MODERN_CSS
from src.ui.process_session_tab_modern import create_process_session_tab_modern
from src.ui.api_key_manager import load_api_keys, save_api_keys
from src.ui.campaign_tab_modern import create_campaign_tab_modern
from src.ui.characters_tab_modern import (
    create_characters_tab_modern,
    character_tab_snapshot,
)
from src.ui.stories_output_tab_modern import create_stories_output_tab_modern
from src.ui.settings_tools_tab_modern import create_settings_tools_tab_modern
from src.ui.session_artifacts_tab import create_session_artifacts_tab, refresh_sessions as refresh_artifact_sessions

from src.google_drive_auth import (
    get_auth_url,
    exchange_code_for_token,
    get_document_content,
    is_authenticated,
    revoke_credentials,
    authenticate_automatically
)
from src.restart_manager import RestartManager


def ui_load_api_keys() -> Tuple[str, str, str, str]:
    """Load API keys on UI startup and format for Gradio."""
    keys = load_api_keys()
    groq_key = keys.get("GROQ_API_KEY", "")
    openai_key = keys.get("OPENAI_API_KEY", "")
    hf_key = keys.get("HUGGING_FACE_API_KEY", "")

    if groq_key or openai_key or hf_key:
        status = StatusMessages.success("API Keys", "Existing API keys loaded from `.env`.")
    else:
        status = StatusMessages.info("API Keys", "Enter your API keys to enable cloud services.")
    return groq_key, openai_key, hf_key, status

def _save_config_helper(group_name: str, allow_empty: bool = False, **kwargs) -> str:
    """
    Helper function to validate and save configuration settings.

    Args:
        group_name: Display name for the configuration group (e.g., "API Keys")
        allow_empty: If True, return info message when no changes to save
        **kwargs: Configuration parameters to validate and save

    Returns:
        Status message for UI display
    """
    try:
        from src.ui.config_manager import ConfigManager

        validated, errors = ConfigManager.validate_config(**kwargs)

        if errors:
            return StatusMessages.error(group_name, f"Validation failed: {'; '.join(errors)}")

        if not validated:
            if allow_empty:
                return StatusMessages.info(group_name, "No changes to save.")
            # Even if empty, we might want to show success for consistency
            return StatusMessages.info(group_name, "No changes to save.")

        ConfigManager.save_config(validated)
        return StatusMessages.success(
            group_name,
            f"{group_name} saved successfully. Restart the application to apply changes."
        )

    except Exception as e:
        logger.exception("Failed to save %s from UI", group_name)
        return StatusMessages.error(group_name, f"Failed to save: {e}")


def ui_save_api_keys(
    groq_api_key: str,
    openai_api_key: str,
    hugging_face_api_key: str
) -> str:
    """UI wrapper to save API keys from Gradio inputs."""
    return _save_config_helper(
        "API Keys",
        allow_empty=True,
        groq_api_key=groq_api_key if groq_api_key else None,
        openai_api_key=openai_api_key if openai_api_key else None,
        hugging_face_api_key=hugging_face_api_key if hugging_face_api_key else None,
    )


def ui_save_model_config(
    whisper_backend: str,
    whisper_model: str,
    whisper_language: str,
    diarization_backend: str,
    llm_backend: str,
) -> str:
    """UI wrapper to save model configuration."""
    return _save_config_helper(
        "Model Configuration",
        whisper_backend=whisper_backend,
        whisper_model=whisper_model,
        whisper_language=whisper_language,
        diarization_backend=diarization_backend,
        llm_backend=llm_backend,
    )


def ui_save_processing_config(
    chunk_length: int,
    chunk_overlap: int,
    sample_rate: int,
    clean_stale: bool,
    save_intermediate: bool,
) -> str:
    """UI wrapper to save processing settings."""
    return _save_config_helper(
        "Processing Settings",
        chunk_length_seconds=chunk_length,
        chunk_overlap_seconds=chunk_overlap,
        audio_sample_rate=sample_rate,
        clean_stale_clips=clean_stale,
        save_intermediate_outputs=save_intermediate,
    )


def ui_save_ollama_config(
    ollama_model: str,
    ollama_fallback: str,
    ollama_url: str,
) -> str:
    """UI wrapper to save Ollama settings."""
    return _save_config_helper(
        "Ollama Settings",
        allow_empty=True,
        ollama_model=ollama_model if ollama_model else None,
        ollama_fallback_model=ollama_fallback if ollama_fallback else None,
        ollama_base_url=ollama_url if ollama_url else None,
    )


def ui_save_advanced_config(
    groq_max_calls: int,
    groq_rate_period: float,
    groq_rate_burst: int,
    colab_poll: int,
    colab_timeout: int,
) -> str:
    """UI wrapper to save advanced settings."""
    return _save_config_helper(
        "Advanced Settings",
        groq_max_calls_per_second=groq_max_calls,
        groq_rate_limit_period_seconds=groq_rate_period,
        groq_rate_limit_burst=groq_rate_burst,
        colab_poll_interval=colab_poll,
        colab_timeout=colab_timeout,
    )


def ui_restart_application() -> str:
    """UI handler for application restart."""
    logger.info("Restart requested from UI")
    log_audit_event(
        "ui.app.restart",
        actor="ui",
        source="gradio",
        metadata={"restart_method": "ui_button"},
    )

    success = RestartManager.restart_application(delay_seconds=2.0)

    if success:
        return StatusMessages.success(
            "Restart Initiated",
            "Application is restarting... The page will reload automatically.",
            "Wait a few seconds, then refresh your browser if needed."
        )
    else:
        return StatusMessages.error(
            "Restart Failed",
            "Could not initiate automatic restart.",
            RestartManager.get_restart_instructions()
        )


PROJECT_ROOT = Path(__file__).resolve().parent
NOTEBOOK_CONTEXT = ""
story_manager = StoryNotebookManager()
speaker_profile_manager = SpeakerProfileManager()
logger = get_logger(__name__)

# Create global artifact counter with 5-minute cache
_artifact_counter = CampaignArtifactCounter(
    output_dir=Config.OUTPUT_DIR,
    cache_ttl_seconds=300,
    logger=logger
)


def _notebook_status() -> str:
    return StoryNotebookManager.format_notebook_status(NOTEBOOK_CONTEXT)


def _set_notebook_context(value: str) -> None:
    global NOTEBOOK_CONTEXT
    NOTEBOOK_CONTEXT = value


campaign_manager = CampaignManager()
campaign_names = campaign_manager.get_campaign_names()


def _refresh_campaign_names() -> Dict[str, str]:
    """Forces a reload of campaign data from disk and returns an updated name map."""
    global campaign_names
    # By calling _load_campaigns() directly, we bypass any in-memory cache and
    # ensure the CampaignManager has the latest data from the campaigns.json file.
    # This is critical after operations like creation or deletion.
    campaign_manager.campaigns = campaign_manager._load_campaigns()
    campaign_names = campaign_manager.get_campaign_names()
    logger.debug(f"Refreshed campaign names: {list(campaign_names.values())}")
    return campaign_names


def _campaign_id_from_name(display_name: Optional[str]) -> Optional[str]:
    """Resolve campaign_id from display name."""
    if not display_name:
        return None
    names = _refresh_campaign_names()
    for cid, name in names.items():
        if name == display_name:
            return cid
    return None


def _format_campaign_badge(campaign_id: Optional[str]) -> str:
    """Return campaign badge markdown for the Process tab."""
    if not campaign_id:
        return StatusMessages.warning(
            "Campaign",
            "No campaign selected. Use the Campaign Launcher to choose one."
        )

    campaign = campaign_manager.get_campaign(campaign_id)
    if not campaign:
        return StatusMessages.error(
            "Campaign",
            f"Campaign `{campaign_id}` was not found in campaigns.json."
        )

    party_line = "No party assigned yet."
    if campaign.party_id:
        party = party_manager.get_party(campaign.party_id)
        if party:
            party_line = f"Party `{campaign.party_id}`: {len(party.characters)} characters."
        else:
            party_line = f"Party `{campaign.party_id}` not found. Update party configuration."

    return StatusMessages.success(
        "Campaign Active",
        f"Working in **{campaign.name}** (`{campaign_id}`).",
        party_line,
    )


def _count_campaign_artifacts(campaign_id: str) -> Tuple[int, int]:
    """
    Count processed sessions and narratives for a campaign.

    This function now uses CampaignArtifactCounter for better
    performance, error handling, and observability.

    Args:
        campaign_id: Campaign identifier to count artifacts for

    Returns:
        Tuple of (session_count, narrative_count)
    """
    try:
        counts = _artifact_counter.count_artifacts(campaign_id)
        return counts.to_tuple()
    except Exception as e:
        logger.error(f"Failed to count campaign artifacts for '{campaign_id}': {e}", exc_info=True)
        return (0, 0)


def _status_tracker_summary(campaign_id: str) -> str:
    """Describe the status tracker state for the campaign."""
    status_path = Config.PROJECT_ROOT / "logs" / "session_status.json"
    if not status_path.exists():
        return f"{StatusIndicators.PENDING} Status tracker has no recorded sessions yet."

    try:
        snapshot = json.loads(status_path.read_text(encoding="utf-8"))
    except Exception:
        return f"{StatusIndicators.WARNING} Status tracker data is unreadable."

    recorded_campaign = snapshot.get("campaign_id")
    session_id = snapshot.get("session_id") or "unknown_session"
    status = snapshot.get("status") or "unknown"

    if recorded_campaign != campaign_id:
        display_campaign = recorded_campaign or "unassigned"
        return f"{StatusIndicators.INFO} Last recorded session belongs to `{display_campaign}` (session `{session_id}` - status {status})."

    if snapshot.get("processing"):
        stage = snapshot.get("current_stage")
        return f"{StatusIndicators.PROCESSING} Processing `{session_id}` (stage {stage or 'n/a'})."

    indicator = StatusIndicators.READY if status == "completed" else StatusIndicators.INFO
    return f"{indicator} Last session `{session_id}` finished with status `{status}`."


def _build_campaign_manifest(campaign_id: Optional[str]) -> str:
    """Generate manifest markdown for the selected campaign."""
    if not campaign_id:
        return StatusMessages.warning(
            "Campaign Manifest",
            "Select or create a campaign to inspect campaign assets."
        )

    campaign = campaign_manager.get_campaign(campaign_id)
    if not campaign:
        return StatusMessages.error(
            "Campaign Manifest",
            f"Campaign `{campaign_id}` was not found in campaigns.json."
        )

    lines: List[str] = [
        f"### Campaign Manifest",
        f"- ID: `{campaign_id}`",
        f"- Name: {campaign.name}",
        "",
    ]

    if campaign.party_id:
        party = party_manager.get_party(campaign.party_id)
        if party:
            lines.append(
                f"- {StatusIndicators.READY} Party profile `{campaign.party_id}` loaded "
                f"({len(party.characters)} characters)."
            )
        else:
            lines.append(
                f"- {StatusIndicators.WARNING} Party `{campaign.party_id}` missing. Update the Party Manager."
            )
    else:
        lines.append(f"- {StatusIndicators.PENDING} No party linked to this campaign yet.")

    knowledge = CampaignKnowledgeBase(campaign_id=campaign_id)
    sessions_tracked = len(knowledge.knowledge.get("sessions_processed", []))
    if knowledge.knowledge_file.exists():
        lines.append(
            f"- {StatusIndicators.READY} Knowledge base `{knowledge.knowledge_file.name}` "
            f"tracks {sessions_tracked} sessions."
        )
    else:
        lines.append(
            f"- {StatusIndicators.PENDING} Knowledge base will be created after the first processed session."
        )

    profile_manager = CharacterProfileManager()
    profile_count = sum(
        1 for profile in profile_manager.profiles.values()
        if getattr(profile, "campaign_id", None) == campaign_id
    )
    if profile_count:
        lines.append(f"- {StatusIndicators.READY} {profile_count} character profiles assigned to this campaign.")
    else:
        lines.append(
            f"- {StatusIndicators.WARNING} No character profiles assigned. Use the Characters tab to assign or import."
        )

    session_count, narrative_count = _count_campaign_artifacts(campaign_id)
    if session_count:
        lines.append(
            f"- {StatusIndicators.INFO} {session_count} processed sessions "
            f"({narrative_count} narratives stored)."
        )
    else:
        lines.append(
            f"- {StatusIndicators.PENDING} No processed sessions recorded yet."
        )

    lines.append(f"- { _status_tracker_summary(campaign_id) }")

    return "\n".join(lines)


def _campaign_summary_message(campaign_id: Optional[str], *, is_new: bool = False) -> str:
    """Return summary markdown for the active campaign."""
    if not campaign_id:
        return StatusMessages.warning(
            "No Campaign Selected",
            "Choose an existing campaign or create a new one to begin."
        )

    campaign = campaign_manager.get_campaign(campaign_id)
    if not campaign:
        return StatusMessages.error(
            "Campaign Not Found",
            f"Campaign `{campaign_id}` could not be loaded."
        )

    details = []
    if campaign.party_id:
        party = party_manager.get_party(campaign.party_id)
        if party:
            details.append(f"Party `{campaign.party_id}` with {len(party.characters)} characters.")
        else:
            details.append(f"Party `{campaign.party_id}` is missing.")
    else:
        details.append("No party linked yet.")

    prefix = "New campaign created." if is_new else "Campaign ready."
    return StatusMessages.success(
        "Campaign Loaded",
        f"{prefix} Active campaign: **{campaign.name}** (`{campaign_id}`).",
        " ".join(details),
    )


def _process_defaults_for_campaign(campaign_id: Optional[str]) -> Dict[str, Any]:
    """Return default process tab settings for the campaign."""
    defaults = {
        "party_selection": "Manual Entry",
        "num_speakers": 4,
        "skip_diarization": False,
        "skip_classification": False,
        "skip_snippets": True,
        "skip_knowledge": False,
    }

    if not campaign_id:
        return defaults

    campaign = campaign_manager.get_campaign(campaign_id)
    if not campaign:
        return defaults

    defaults["party_selection"] = campaign.party_id or "Manual Entry"
    defaults["num_speakers"] = campaign.settings.num_speakers
    defaults["skip_diarization"] = campaign.settings.skip_diarization
    defaults["skip_classification"] = campaign.settings.skip_classification
    defaults["skip_snippets"] = campaign.settings.skip_snippets
    defaults["skip_knowledge"] = campaign.settings.skip_knowledge
    return defaults


def _campaign_overview_markdown(campaign_id: Optional[str]) -> str:
    if not campaign_id:
        return StatusMessages.info(
            "Campaign Overview",
            "Select a campaign to display campaign metrics."
        )

    campaign = campaign_manager.get_campaign(campaign_id)
    if not campaign:
        return StatusMessages.error("Campaign Missing", f"Campaign `{campaign_id}` not found.")

    knowledge = CampaignKnowledgeBase(campaign_id=campaign_id)
    session_count, narrative_count = _count_campaign_artifacts(campaign_id)
    knowledge_sessions = len(knowledge.knowledge.get("sessions_processed", []))
    quest_count = len(knowledge.knowledge.get("quests", []))
    npc_count = len(knowledge.knowledge.get("npcs", []))
    location_count = len(knowledge.knowledge.get("locations", []))

    lines = [
        "### Campaign Summary",
        f"- **Name**: {campaign.name}",
        f"- **Campaign ID**: `{campaign_id}`",
        f"- **Linked Party**: `{campaign.party_id or 'None'}`",
        "",
        "### Activity",
        f"- Sessions processed: {session_count}",
        f"- Narratives stored: {narrative_count}",
        f"- Knowledge sessions tracked: {knowledge_sessions}",
        "",
        "### Knowledge Totals",
        f"- Quests: {quest_count}",
        f"- NPCs: {npc_count}",
        f"- Locations: {location_count}",
    ]
    return "\n".join(lines)


def _knowledge_summary_markdown(campaign_id: Optional[str]) -> str:
    if not campaign_id:
        return StatusMessages.info(
            "Knowledge Base",
            "Knowledge summaries will appear here once a campaign is selected."
        )

    knowledge = CampaignKnowledgeBase(campaign_id=campaign_id)
    quests = knowledge.knowledge.get("quests", [])
    npcs = knowledge.knowledge.get("npcs", [])
    locations = knowledge.knowledge.get("locations", [])
    items = knowledge.knowledge.get("items", [])

    def _sample(entries, attr):
        names = []
        for entry in entries[:3]:
            value = getattr(entry, attr, None)
            if value:
                names.append(value)
        return ", ".join(names) if names else "None captured"

    lines = [
        "### Knowledge Highlights",
        f"- Sample quests: {_sample(quests, 'title')}",
        f"- Sample NPCs: {_sample(npcs, 'name')}",
        f"- Sample locations: {_sample(locations, 'name')}",
        f"- Sample items: {_sample(items, 'name')}",
    ]
    return "\n".join(lines)


def _character_overview_placeholder() -> str:
    return StatusMessages.info(
        "Character Overview",
        "Select a character to view their profile summary."
    )


def _character_tab_updates(
    campaign_id: Optional[str]
) -> Tuple[Any, Any, Any, Any, Any]:
    snapshot = character_tab_snapshot(campaign_id)
    characters = snapshot["characters"]
    default_value = characters[0] if characters else None
    dropdown_update = gr.update(choices=characters, value=default_value)
    table_update = gr.update(value=snapshot["table"])
    status_update = gr.update(value=snapshot["status"])
    overview_update = gr.update(value=_character_overview_placeholder())
    return status_update, table_update, dropdown_update, dropdown_update, overview_update


def _character_profiles_markdown(campaign_id: Optional[str]) -> str:
    snapshot = character_tab_snapshot(campaign_id)
    characters = snapshot["characters"]
    if not campaign_id or not characters:
        return snapshot["status"]

    manager = CharacterProfileManager()
    lines = ["### Characters"]
    for name in characters:
        profile = manager.get_profile(name)
        if not profile:
            continue
        class_name = profile.class_name or "Unknown class"
        level = profile.level if profile.level is not None else "n/a"
        last_updated = profile.last_updated or "unknown"
        lines.append(
            f"- **{profile.name}** ({class_name}, level {level}) - last updated {last_updated}"
        )
    return "\n".join(lines)


def _extract_party_dropdown_update(campaign_id: Optional[str]) -> Any:
    party_choices = [party for party in party_manager.list_parties() if party != "Manual Entry"]
    preferred_party = None
    if campaign_id:
        campaign = campaign_manager.get_campaign(campaign_id)
        if campaign and campaign.party_id and campaign.party_id in party_choices:
            preferred_party = campaign.party_id
    if preferred_party is None and party_choices:
        preferred_party = party_choices[0]
    return gr.update(choices=party_choices, value=preferred_party)



def _session_library_markdown(campaign_id: Optional[str]) -> str:
    if not campaign_id:
        return StatusMessages.info(
            "Session Library",
            "Processed sessions for the active campaign will appear here."
        )

    session_ids = story_manager.list_sessions(
        limit=None,
        campaign_id=campaign_id,
        include_unassigned=False,
    )
    if not session_ids:
        return StatusMessages.warning(
            "No Sessions",
            "Process a session for this campaign to populate the library."
        )

    lines = ["### Processed Sessions", ""]
    for session_id in session_ids:
        try:
            session = story_manager.load_session(session_id)
            stats = session.metadata.get("statistics", {})
            duration = stats.get("total_duration_formatted") or f"{stats.get('total_duration_seconds', 0)}s"
            segments = stats.get("total_segments", 0)

            # Get output directory path for this session
            output_dir = Config.OUTPUT_DIR / session_id
            narratives_dir = output_dir / "narratives"
            narrative_count = len(list(narratives_dir.glob("*.md"))) if narratives_dir.exists() else 0

            lines.append(f"#### {StatusIndicators.COMPLETE} {session_id}")
            lines.append(f"- **Duration**: {duration}")
            lines.append(f"- **Segments**: {segments}")
            lines.append(f"- **Narratives**: {narrative_count}")
            lines.append(f"- **Output**: `{output_dir.relative_to(Config.PROJECT_ROOT)}`")
            lines.append("")
        except Exception as e:
            lines.append(f"#### {StatusIndicators.ERROR} {session_id}")
            lines.append(f"- **Status**: Error loading metadata: {str(e)}")
            lines.append("")
    return "\n".join(lines)


def _narrative_hint_markdown(campaign_id: Optional[str]) -> str:
    if not campaign_id:
        return StatusMessages.info(
            "Narratives",
            "Narrative export locations will display here once a campaign is active."
        )

    session_ids = story_manager.list_sessions(
        limit=None,
        campaign_id=campaign_id,
        include_unassigned=False,
    )
    narrative_paths: List[str] = []
    for session_id in session_ids:
        try:
            session = story_manager.load_session(session_id)
            narratives_dir = session.json_path.parent / "narratives"
            if narratives_dir.exists():
                for path in sorted(narratives_dir.glob("*.md")):
                    narrative_paths.append(str(path.relative_to(Config.PROJECT_ROOT)))
        except Exception:
            continue

    if not narrative_paths:
        return StatusMessages.info(
            "Narratives",
            "Generate narratives from the Stories tab to create markdown files per campaign."
        )

    lines = ["### Narratives"]
    for path in narrative_paths[:8]:
        lines.append(f"- `{path}`")
    if len(narrative_paths) > 8:
        lines.append(f"- ... {len(narrative_paths) - 8} more files")
    return "\n".join(lines)


def _diagnostics_markdown(campaign_id: Optional[str]) -> str:
    if not campaign_id:
        return StatusMessages.info(
            "Diagnostics",
            "Launch a campaign to track pipeline diagnostics and status."
        )

    return "\n".join(
        [
            "### Diagnostics",
            _status_tracker_summary(campaign_id),
        ]
    )


def _chat_status_markdown(campaign_id: Optional[str]) -> str:
    if not campaign_id:
        return StatusMessages.info(
            "LLM Chat",
            "Load a campaign to initialise chat context."
        )

    knowledge = CampaignKnowledgeBase(campaign_id=campaign_id)
    if knowledge.knowledge_file.exists():
        return StatusMessages.success(
            "LLM Chat Ready",
            f"Knowledge base `{knowledge.knowledge_file.name}` is available for prompting."
        )
    return StatusMessages.warning(
        "LLM Chat",
        "Knowledge base file not created yet. Process a session with knowledge extraction enabled."
    )


def _resolve_audio_path(audio_file) -> str:
    """Resolve the audio file path from Gradio file upload."""
    if isinstance(audio_file, str):
        return audio_file
    elif hasattr(audio_file, 'name'):
        return audio_file.name
    else:
        raise ValueError(f"Unsupported audio file type: {type(audio_file)}")


def _create_processor_for_context(
    session_id: str,
    party_selection: Optional[str],
    character_names: str,
    player_names: str,
    num_speakers: Optional[int],
    language: Optional[str],
    campaign_id: Optional[str],
    transcription_backend: str,
    diarization_backend: str,
    classification_backend: str,
    *,
    allow_empty_names: bool = False,
    enable_audit_mode: bool = False,
    redact_prompts: bool = False,
    generate_scenes: bool = True,
    scene_summary_mode: str = "template",
) -> DDSessionProcessor:
    """Instantiate a session processor respecting party/manual inputs."""
    resolved_speakers = int(num_speakers) if num_speakers else 4
    resolved_language = language or "en"

    kwargs: Dict[str, Any] = {
        "session_id": session_id,
        "campaign_id": campaign_id,
        "num_speakers": resolved_speakers,
        "language": resolved_language,
        "transcription_backend": transcription_backend,
        "diarization_backend": diarization_backend,
        "classification_backend": classification_backend,
        "enable_audit_mode": enable_audit_mode,
        "redact_prompts": redact_prompts,
        "generate_scenes": generate_scenes,
        "scene_summary_mode": scene_summary_mode,
    }

    if party_selection and party_selection != "Manual Entry":
        kwargs["party_id"] = party_selection
    else:
        chars = [c.strip() for c in (character_names or "").split(',') if c.strip()]
        players = [p.strip() for p in (player_names or "").split(',') if p.strip()]

        if not chars and not allow_empty_names:
            raise ValueError("Character names are required when using Manual Entry")

        if chars:
            kwargs["character_names"] = chars
        if players:
            kwargs["player_names"] = players

    return DDSessionProcessor(**kwargs)


def _format_highlighted_transcript(classification_file_path: Optional[str]) -> Optional[List[Tuple[str, str]]]:
    """
    Reads a classification JSON file and formats it for Gradio's HighlightedText component.
    """
    if not classification_file_path or not Path(classification_file_path).exists():
        return None
    
    try:
        with open(classification_file_path, 'r', encoding='utf-8') as f:
            segments = json.load(f)
        
        highlighted_text = []
        for segment in segments:
            text = segment.get("text", "")
            # Use the granular type if available, fall back to primary classification
            label = segment.get("classification_type", segment.get("classification", "UNKNOWN"))
            
            # Add speaker/character name for context, similar to a transcript
            actor = segment.get("character_name") or segment.get("speaker_name", "???")
            
            # Format with a newline for readability between segments
            formatted_text = f'{actor}: {text}\n'
            
            highlighted_text.append((formatted_text, label))
            
        return highlighted_text
    except Exception as e:
        logger.error(f"Failed to format highlighted transcript: {e}", exc_info=True)
        return None


def process_session(
    audio_file,
    session_id: str,
    party_selection: Optional[str],
    character_names: str,
    player_names: str,
    num_speakers: int,
    language: str,
    skip_diarization: bool,
    skip_classification: bool,
    skip_snippets: bool,
    skip_knowledge: bool,
    transcription_backend: str,
    diarization_backend: str,
    classification_backend: str,
    campaign_id: Optional[str] = None,
    enable_audit_mode: bool = False,
    redact_prompts: bool = False,
    generate_scenes: bool = True,
    scene_summary_mode: str = "template",
) -> Dict:
    """Main session processing function."""
    try:
        if audio_file is None:
            return {"status": "error", "message": "Please upload an audio file."}

        resolved_session_id = session_id or "session"

        log_audit_event(
            "ui.session.process.start",
            actor="ui",
            source="gradio",
            metadata={
                "session_id": resolved_session_id,
                "party_selection": party_selection,
                "num_speakers": num_speakers,
                "skip_diarization": skip_diarization,
                "skip_classification": skip_classification,
                "skip_snippets": skip_snippets,
                "skip_knowledge": skip_knowledge,
                "transcription_backend": transcription_backend,
                "diarization_backend": diarization_backend,
                "classification_backend": classification_backend,
                "campaign_id": campaign_id,
                "enable_audit_mode": enable_audit_mode,
                "redact_prompts": redact_prompts,
                "generate_scenes": generate_scenes,
                "scene_summary_mode": scene_summary_mode,
            },
        )

        # Determine if using party config or manual entry
        processor = _create_processor_for_context(
            resolved_session_id,
            party_selection,
            character_names,
            player_names,
            num_speakers,
            language,
            campaign_id,
            transcription_backend,
            diarization_backend,
            classification_backend,
            allow_empty_names=False,
            enable_audit_mode=enable_audit_mode,
            redact_prompts=redact_prompts,
            generate_scenes=generate_scenes,
            scene_summary_mode=scene_summary_mode,
        )

        pipeline_result = processor.process(
            input_file=_resolve_audio_path(audio_file),
            skip_diarization=skip_diarization,
            skip_classification=skip_classification,
            skip_snippets=skip_snippets,
            skip_knowledge=skip_knowledge
        )

        if not isinstance(pipeline_result, dict):
            log_audit_event(
                "ui.session.process.error",
                actor="ui",
                source="gradio",
                status="error",
                metadata={
                    "session_id": resolved_session_id,
                    "campaign_id": campaign_id,
                    "error": "Non-dict pipeline response",
                },
            )
            return {
                "status": "error",
                "message": "Pipeline did not return a result. Check preflight checks and logs for details.",
                "details": f"Unexpected pipeline response: {type(pipeline_result).__name__}",
            }

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

        # IMPROVEMENT: Format the highlighted transcript for the new UI component
        highlighted_transcript = _format_highlighted_transcript(
            output_files.get("classification_json")
        )

        log_audit_event(
            "ui.session.process.complete",
            actor="ui",
            source="gradio",
            status="success",
            metadata={
                "session_id": resolved_session_id,
                "campaign_id": campaign_id,
                "outputs": list(output_files.keys()),
                "has_snippets": bool(snippet_payload["segments_dir"]),
            },
        )

        # Clear artifact cache for this campaign to ensure fresh counts on next UI refresh
        if campaign_id:
            _artifact_counter.clear_cache(campaign_id)
            logger.debug(f"Cleared artifact cache for campaign '{campaign_id}' after processing session '{resolved_session_id}'")

        return {
            "status": "success",
            "message": "Session processed successfully.",
            "full": _read_output_file("full"),
            "ic": _read_output_file("ic_only"),
            "ooc": _read_output_file("ooc_only"),
            "highlighted_transcript": highlighted_transcript, # Add new data to response
            "stats": pipeline_result.get("statistics") or {},
            "snippet": snippet_payload,
            "knowledge": pipeline_result.get("knowledge_extraction") or {},
            "output_files": output_files,
        }

    except Exception as e:
        logger.exception("Error during session processing in Gradio UI")
        log_audit_event(
            "ui.session.process.error",
            actor="ui",
            source="gradio",
            status="error",
            metadata={
                "session_id": session_id or "session",
                "campaign_id": campaign_id,
                "error": str(e),
            },
        )
        return {
            "status": "error",
            "message": str(e),
            "details": f"See log for details: {get_log_file_path()}",
        }


def run_preflight_checks(
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
    """Run dependency checks before long-running processing."""
    try:
        processor = _create_processor_for_context(
            session_id="preflight_check",
            party_selection=party_selection,
            character_names=character_names or "",
            player_names=player_names or "",
            num_speakers=num_speakers,
            language=language,
            campaign_id=campaign_id,
            transcription_backend=transcription_backend,
            diarization_backend=diarization_backend,
            classification_backend=classification_backend,
            allow_empty_names=True,
        )
        processor.is_test_run = True
        issues = processor.run_preflight_checks_only(
            skip_diarization=bool(skip_diarization),
            skip_classification=bool(skip_classification),
        )

        if not issues:
            return StatusMessages.success(
                "Preflight Checks",
                "All systems ready for processing."
            )

        error_issues = [issue for issue in issues if issue.is_error()]
        warning_issues = [issue for issue in issues if not issue.is_error()]

        def _format_section(title: str, entries: List[PreflightIssue]) -> List[str]:
            if not entries:
                return []
            lines = [f"**{title}:**"]
            lines.extend(
                f"- `{issue.component}`: {issue.message}" for issue in entries
            )
            return lines

        sections: List[str] = []
        sections.extend(_format_section("Errors", error_issues))
        sections.extend(_format_section("Warnings", warning_issues))
        details = "\n".join(sections)

        if error_issues:
            return "\n".join([
                f"### {StatusIndicators.ERROR} Preflight Failed",
                "",
                "Resolve the blocking issues below before starting processing.",
                "",
                details,
            ])

        return "\n".join([
            f"### {StatusIndicators.WARNING} Preflight Warnings",
            "",
            "Processing can continue, but review the warnings below:",
            "",
            details,
        ])
    except Exception as exc:
        return StatusMessages.error(
            "Preflight Failed",
            "An unexpected error occurred while running the checks.",
            str(exc),
        )


# ============================================================================
# Pipeline Stage Control Functions
# ============================================================================

def update_skip_flags_from_stage(run_until_stage):
    """
    Automatically set skip flags based on 'Run Until Stage' selection.

    Args:
        run_until_stage: Selected stage to run until

    Returns:
        Tuple of (skip_diarization, skip_classification, skip_snippets, skip_knowledge)
    """
    stage_configs = {
        "full": (False, False, False, False),  # Run all stages
        "stage_4": (True, True, True, True),   # Stop after transcription
        "stage_5": (False, True, True, True),  # Stop after diarization
        "stage_6": (False, False, True, True), # Stop after classification
        "stage_7": (False, False, True, True), # Stop after outputs (skip snippets & knowledge)
    }

    skip_diarization, skip_classification, skip_snippets, skip_knowledge = stage_configs.get(
        run_until_stage, (False, False, False, False)
    )

    return (
        gr.update(value=skip_diarization),
        gr.update(value=skip_classification),
        gr.update(value=skip_snippets),
        gr.update(value=skip_knowledge),
    )


# ============================================================================
# Resume from Intermediate Outputs Functions
# ============================================================================

def refresh_resume_sessions():
    """Refresh the list of sessions with intermediate outputs."""
    from src.ui.intermediate_resume_helper import discover_sessions_with_intermediates

    sessions = discover_sessions_with_intermediates()
    if not sessions:
        return gr.update(choices=[], value=None)

    # Format as (label, value) tuples
    choices = [(name, path) for name, path in sessions]
    return gr.update(choices=choices, value=choices[0][1] if choices else None)


def update_resume_session_info(session_dir):
    """Update session info display when a session is selected."""
    if not session_dir:
        return StatusMessages.info(
            "Session Info",
            "Select a session to see details."
        )

    from src.ui.intermediate_resume_helper import get_session_info
    info = get_session_info(session_dir)

    if not info or not info.get("has_intermediates"):
        return StatusMessages.warning(
            "No Intermediate Outputs",
            f"Session {info.get('session_name', 'unknown')} does not have intermediate outputs saved."
        )

    return StatusMessages.success(
        info["session_name"],
        f"**Available stages:** {info['available_stages']}\n\n"
        f"**Path:** `{info['session_path']}`"
    )


def process_from_intermediate_ui(session_dir, from_stage, progress=gr.Progress()):
    """Process from intermediate outputs via UI."""
    if not session_dir:
        return StatusMessages.error(
            "No Session Selected",
            "Please select a session to resume."
        )

    from pathlib import Path
    from src.pipeline import DDSessionProcessor

    try:
        # Extract session ID from directory name
        session_path = Path(session_dir)
        session_id = session_path.name.split("_", 2)[-1]

        progress(0.1, desc="Initializing...")

        # Create processor
        processor = DDSessionProcessor(
            session_id=session_id,
            resume=False,
        )

        progress(0.2, desc=f"Loading stage {from_stage} outputs...")

        # Process from intermediate
        result = processor.process_from_intermediate(
            session_dir=session_path,
            from_stage=from_stage,
            skip_snippets=False,
            skip_knowledge=False,
        )

        progress(1.0, desc="Complete!")

        if result['success']:
            stats = result.get('statistics', {})
            return StatusMessages.success(
                "Processing Complete",
                f"✅ Successfully resumed from stage {from_stage}\n\n"
                f"**Statistics:**\n"
                f"- Total duration: {stats.get('total_duration_formatted', 'N/A')}\n"
                f"- IC percentage: {stats.get('ic_percentage', 0):.1f}%\n"
                f"- Total segments: {stats.get('total_segments', 0)}\n\n"
                f"**Outputs saved to:** `{session_dir}`"
            )
        else:
            return StatusMessages.error(
                "Processing Failed",
                "Processing from intermediate failed. Check logs for details."
            )

    except Exception as e:
        return StatusMessages.error(
            "Error",
            f"Failed to process from intermediate: {str(e)}"
        )


# Get available parties
party_manager = PartyConfigManager()
available_parties = party_manager.list_parties()

# Create modern theme
theme = create_modern_theme()

# Determine initial campaign context
initial_campaign_id = next(iter(campaign_names.keys()), None)
initial_campaign_name = campaign_names.get(initial_campaign_id, "Manual Setup")
initial_badge = _format_campaign_badge(initial_campaign_id)
initial_summary = _campaign_summary_message(initial_campaign_id)
initial_manifest = _build_campaign_manifest(initial_campaign_id)

# Create Gradio interface
with gr.Blocks(
    title="D&D Session Processor",
    theme=theme,
    css=MODERN_CSS,
) as demo:
    active_campaign_state = gr.State(value=initial_campaign_id)

    gr.Markdown("# Campaign Launcher")
    campaign_summary_md = gr.Markdown(value=initial_summary)

    with gr.Row():
        with gr.Column():
            existing_campaign_dropdown = gr.Dropdown(
                label="Existing Campaigns",
                choices=list(campaign_names.values()),
                value=initial_campaign_name if initial_campaign_id else None,
                info="Load a campaign profile to apply its defaults.",
            )
            load_campaign_btn = UIComponents.create_action_button(
                "Load Existing Campaign",
                variant="primary",
                size="md",
            )

        with gr.Column():
            new_campaign_name = gr.Textbox(
                label="New Campaign Name",
                placeholder="New Campaign",
                info="Provide an optional display name for the new campaign.",
            )
            start_new_campaign_btn = UIComponents.create_action_button(
                "Start New Campaign",
                variant="secondary",
                size="md",
            )

    campaign_manifest_md = gr.Markdown(value=initial_manifest)

    gr.Markdown("---")

    available_parties, process_tab_refs = create_process_session_tab_modern(
        demo,
        refresh_campaign_names=_refresh_campaign_names,
        process_session_fn=process_session,
        preflight_fn=run_preflight_checks,
        campaign_manager=campaign_manager,
        active_campaign_state=active_campaign_state,
        campaign_badge_text=initial_badge,
        initial_campaign_name=initial_campaign_name if initial_campaign_id else "Manual Setup",
    )

    campaign_tab_refs = create_campaign_tab_modern(demo)
    characters_tab_refs = create_characters_tab_modern(
        demo,
        available_parties,
        refresh_campaign_names=_refresh_campaign_names,
        active_campaign_state=active_campaign_state,
        initial_campaign_id=initial_campaign_id,
    )
    stories_tab_refs = create_stories_output_tab_modern(demo)
    artifacts_tab_refs = create_session_artifacts_tab(demo)
    settings_tab_refs = create_settings_tools_tab_modern(
        demo,
        story_manager=story_manager,
        refresh_campaign_names=_refresh_campaign_names,
        initial_campaign_id=initial_campaign_id,
        speaker_profile_manager=speaker_profile_manager,
        log_level_choices=list(LOG_LEVEL_CHOICES),
        initial_console_level=get_console_log_level(),
    )

    def _apply_console_log_level(level: Optional[str]) -> str:
        if not level:
            return StatusMessages.warning("Logging", "Select a log level before applying.")
        try:
            set_console_log_level(level)
            logger.info("Console log level updated via UI: %s", level)
            return StatusMessages.success("Logging", f"Console log level set to {level}.")
        except ValueError:
            logger.error("Unsupported log level selected in UI: %s", level)
            return StatusMessages.error("Logging", f"Unsupported log level: {level}")

    def _compute_process_updates(campaign_id: Optional[str]) -> Tuple:
        settings = _process_defaults_for_campaign(campaign_id)
        return (
            _format_campaign_badge(campaign_id),
            gr.update(value=""),
            gr.update(value=""),
            gr.update(value=""),
            gr.update(value=settings["party_selection"]),
            gr.update(value=settings["num_speakers"]),
            gr.update(value=settings["skip_diarization"]),
            gr.update(value=settings["skip_classification"]),
            gr.update(value=settings["skip_snippets"]),
            gr.update(value=settings["skip_knowledge"]),
            StatusMessages.info("Ready", "Campaign loaded. Configure session options and click Start Processing."),
            gr.update(visible=False),
            None, # highlighted_transcript
            "",
            "",
            StatusMessages.info("Statistics", "No statistics available."),
            StatusMessages.info("Snippet Export", "No snippet information available."),
        )

    def _build_full_ui_update(campaign_id: Optional[str]) -> tuple:
        """
        Builds a tuple of Gradio updates for a full UI refresh based on a campaign_id.
        This is the refactored, centralized UI update logic.
        """
        process_updates = _compute_process_updates(campaign_id)
        campaign_names_map = _refresh_campaign_names()
        campaign_choices = list(campaign_names_map.values())
        selected_campaign_name = campaign_names_map.get(campaign_id) if campaign_id else None

        # Main dropdowns
        dropdown_update = gr.update(choices=campaign_choices, value=selected_campaign_name)
        campaign_selector_update = dropdown_update

        # Campaign Tab
        overview_update = gr.update(value=_campaign_overview_markdown(campaign_id))
        knowledge_update = gr.update(value=_knowledge_summary_markdown(campaign_id))
        session_library_update = gr.update(value=_session_library_markdown(campaign_id))

        # Characters Tab
        (
            character_profiles_update,
            character_table_update,
            character_select_update,
            character_export_update,
            character_overview_update,
        ) = _character_tab_updates(campaign_id)
        extract_party_update = _extract_party_dropdown_update(campaign_id)

        # Stories Tab
        story_session_update = gr.update(value=_session_library_markdown(campaign_id))
        narrative_hint_update = gr.update(value=_narrative_hint_markdown(campaign_id))

        # Settings & Tools Tab
        diagnostics_update = gr.update(value=_diagnostics_markdown(campaign_id))
        chat_update = gr.update(value=_chat_status_markdown(campaign_id))

        # Social Insights
        social_campaign_choices = ["All Campaigns"] + campaign_choices
        social_campaign_value = selected_campaign_name or "All Campaigns"
        social_campaign_update = gr.update(choices=social_campaign_choices, value=social_campaign_value)
        social_sessions = story_manager.list_sessions(campaign_id=campaign_id) if campaign_id else story_manager.list_sessions()
        social_session_update = gr.update(choices=social_sessions, value=social_sessions[0] if social_sessions else None)
        social_keyword_update = gr.update(value=StatusMessages.info("Social Insights", "Select a session and run analysis."))
        social_nebula_update = gr.update(value=None)

        # Artifact Explorer
        artifacts_session_picker_update = gr.update(choices=[], value=None)
        artifacts_file_list_update = gr.update(value=None)
        artifacts_file_preview_update = gr.update(value="")
        artifacts_download_button_update = gr.update(visible=False)
        artifacts_status_update = gr.update(value=StatusMessages.info("Ready", "Select a session to begin."))

        return (
            campaign_id,
            dropdown_update,
            *process_updates,
            overview_update,
            knowledge_update,
            session_library_update,
            campaign_selector_update,
            character_profiles_update,
            character_table_update,
            character_select_update,
            character_export_update,
            character_overview_update,
            extract_party_update,
            story_session_update,
            narrative_hint_update,
            diagnostics_update,
            chat_update,
            social_campaign_update,
            social_session_update,
            social_keyword_update,
            social_nebula_update,
            artifacts_session_picker_update,
            artifacts_file_list_update,
            artifacts_file_preview_update,
            artifacts_download_button_update,
            artifacts_status_update,
        )

    def _load_campaign(display_name: Optional[str], current_campaign_id: Optional[str]):
        campaign_id = _campaign_id_from_name(display_name) or current_campaign_id or initial_campaign_id
        summary = _campaign_summary_message(campaign_id)
        manifest = _build_campaign_manifest(campaign_id)
        
        ui_updates = _build_full_ui_update(campaign_id)
        
        return (
            ui_updates[0], # campaign_id
            summary,
            manifest,
            *ui_updates[1:], # The rest of the UI updates
        )

    def _create_new_campaign(name: str):
        proposed_name = name.strip() if name else ""
        new_campaign_id, _ = campaign_manager.create_blank_campaign(name=proposed_name or None)

        knowledge = CampaignKnowledgeBase(campaign_id=new_campaign_id)
        if not knowledge.knowledge_file.exists():
            knowledge._save_knowledge()
        _set_notebook_context("")

        summary = _campaign_summary_message(new_campaign_id, is_new=True)
        manifest = _build_campaign_manifest(new_campaign_id)
        
        ui_updates = _build_full_ui_update(new_campaign_id)

        return (
            ui_updates[0], # new_campaign_id
            summary,
            manifest,
            gr.update(value=""), # Clear the new campaign name textbox
            *ui_updates[1:], # The rest of the UI updates
        )

    def _handle_rename_campaign(campaign_display_name: str, new_name: str, active_campaign_id: Optional[str]):
        """Handler for the rename campaign button."""
        campaign_id = _campaign_id_from_name(campaign_display_name) or active_campaign_id
        if not campaign_id:
            return StatusMessages.error("Rename Failed", "No campaign selected to rename."), *[gr.update()] * 31

        if not new_name or not new_name.strip():
            return StatusMessages.error("Rename Failed", "New campaign name cannot be empty."), *[gr.update()] * 31

        success = campaign_manager.rename_campaign(campaign_id, new_name)
        if not success:
            return StatusMessages.error("Rename Failed", f"Could not rename to '{new_name}'. Check logs for details (e.g., name already in use)."), *[gr.update()] * 31

        # On success, refresh everything
        _refresh_campaign_names()
        ui_updates = _build_full_ui_update(campaign_id)
        
        return (
            StatusMessages.success("Rename Successful", f"Campaign renamed to '{new_name}'."),
            *ui_updates
        )

    def _handle_delete_campaign(campaign_display_name: str, active_campaign_id: Optional[str]):
        """Handler for the delete campaign button."""
        campaign_id = _campaign_id_from_name(campaign_display_name) or active_campaign_id
        if not campaign_id:
            return StatusMessages.error("Delete Failed", "No campaign selected to delete."), None, None, *[gr.update()] * 29

        success = campaign_manager.delete_campaign(campaign_id)
        if not success:
            return StatusMessages.error("Delete Failed", f"Could not delete campaign '{campaign_display_name}'. Check logs.")

        # On success, refresh and load the first available campaign
        _refresh_campaign_names()
        new_active_id = next(iter(campaign_names.keys()), None)
        
        summary = _campaign_summary_message(new_active_id)
        manifest = _build_campaign_manifest(new_active_id)
        ui_updates = _build_full_ui_update(new_active_id)

        return (
            StatusMessages.success("Delete Successful", f"Campaign '{campaign_display_name}' has been deleted."),
            summary,
            manifest,
            *ui_updates
        )

    def _refresh_campaign_tab(campaign_display_name: Optional[str], current_campaign_id: Optional[str]):
        """Refresh the Campaign tab with current data for the selected campaign."""
        campaign_id = _campaign_id_from_name(campaign_display_name) or current_campaign_id

        campaign_names_map = _refresh_campaign_names()
        campaign_choices = list(campaign_names_map.values())
        selected_campaign_name = campaign_names_map.get(campaign_id) if campaign_id else None

        if campaign_id:
            _artifact_counter.clear_cache(campaign_id)

        return (
            gr.update(choices=campaign_choices, value=selected_campaign_name),
            _campaign_overview_markdown(campaign_id),
            _knowledge_summary_markdown(campaign_id),
            _session_library_markdown(campaign_id),
            gr.update(value=""), # Clear rename textbox
        )

    # This list defines all the UI components that need to be updated during a full refresh.
    shared_ui_outputs = [
        active_campaign_state,
        existing_campaign_dropdown,
        process_tab_refs["campaign_badge"],
        process_tab_refs["session_id_input"],
        process_tab_refs["character_names_input"],
        process_tab_refs["player_names_input"],
        process_tab_refs["party_selection_input"],
        process_tab_refs["num_speakers_input"],
        process_tab_refs["skip_diarization_input"],
        process_tab_refs["skip_classification_input"],
        process_tab_refs["skip_snippets_input"],
        process_tab_refs["skip_knowledge_input"],
        process_tab_refs["status_output"],
        process_tab_refs["results_section"],
        process_tab_refs["full_output"],
        process_tab_refs["ic_output"],
        process_tab_refs["ooc_output"],
        process_tab_refs["stats_output"],
        process_tab_refs["snippet_output"],
        campaign_tab_refs["overview"],
        campaign_tab_refs["knowledge"],
        campaign_tab_refs["session_library"],
        campaign_tab_refs["campaign_selector"],
        characters_tab_refs["profiles"],
        characters_tab_refs["table"],
        characters_tab_refs["character_dropdown"],
        characters_tab_refs["export_dropdown"],
        characters_tab_refs["overview"],
        characters_tab_refs["extract_party_dropdown"],
        stories_tab_refs["session_list"],
        stories_tab_refs["narrative_hint"],
        settings_tab_refs["diagnostics"],
        settings_tab_refs["chat"],
        settings_tab_refs["social_campaign_selector"],
        settings_tab_refs["social_session_dropdown"],
        settings_tab_refs["social_keyword_output"],
        settings_tab_refs["social_nebula_output"],
        artifacts_tab_refs["session_picker"],
        artifacts_tab_refs["file_list"],
        artifacts_tab_refs["file_preview"],
        artifacts_tab_refs["download_button"],
        artifacts_tab_refs["status_display"],
    ]

    load_campaign_outputs = [
        active_campaign_state,
        campaign_summary_md,
        campaign_manifest_md,
        *shared_ui_outputs[1:] # Skip active_campaign_state as it's already first
    ]
    
    create_campaign_outputs = [
        active_campaign_state,
        campaign_summary_md,
        campaign_manifest_md,
        new_campaign_name, # To clear it
        *shared_ui_outputs[1:]
    ]

    rename_campaign_outputs = [
        campaign_tab_refs["manage_status"],
        *shared_ui_outputs
    ]

    delete_campaign_outputs = [
        campaign_tab_refs["manage_status"],
        campaign_summary_md,
        campaign_manifest_md,
        *shared_ui_outputs
    ]

    settings_tab_refs["save_api_keys_btn"].click(
        fn=ui_save_api_keys,
        inputs=[
            settings_tab_refs["groq_api_key_input"],
            settings_tab_refs["openai_api_key_input"],
            settings_tab_refs["hugging_face_api_key_input"],
        ],
        outputs=settings_tab_refs["api_keys_status"],
    )

    settings_tab_refs["save_model_config_btn"].click(
        fn=ui_save_model_config,
        inputs=[
            settings_tab_refs["whisper_backend_dropdown"],
            settings_tab_refs["whisper_model_dropdown"],
            settings_tab_refs["whisper_language_dropdown"],
            settings_tab_refs["diarization_backend_dropdown"],
            settings_tab_refs["llm_backend_dropdown"],
        ],
        outputs=settings_tab_refs["model_config_status"],
    )

    settings_tab_refs["save_processing_config_btn"].click(
        fn=ui_save_processing_config,
        inputs=[
            settings_tab_refs["chunk_length_input"],
            settings_tab_refs["chunk_overlap_input"],
            settings_tab_refs["audio_sample_rate_input"],
            settings_tab_refs["clean_stale_clips_checkbox"],
            settings_tab_refs["save_intermediate_outputs_checkbox"],
        ],
        outputs=settings_tab_refs["processing_config_status"],
    )

    settings_tab_refs["save_ollama_config_btn"].click(
        fn=ui_save_ollama_config,
        inputs=[
            settings_tab_refs["ollama_model_input"],
            settings_tab_refs["ollama_fallback_model_input"],
            settings_tab_refs["ollama_base_url_input"],
        ],
        outputs=settings_tab_refs["ollama_config_status"],
    )

    settings_tab_refs["save_advanced_config_btn"].click(
        fn=ui_save_advanced_config,
        inputs=[
            settings_tab_refs["groq_max_calls_input"],
            settings_tab_refs["groq_rate_period_input"],
            settings_tab_refs["groq_rate_burst_input"],
            settings_tab_refs["colab_poll_interval_input"],
            settings_tab_refs["colab_timeout_input"],
        ],
        outputs=settings_tab_refs["advanced_config_status"],
    )

    demo.load(
        fn=ui_load_api_keys,
        outputs=[
            settings_tab_refs["groq_api_key_input"],
            settings_tab_refs["openai_api_key_input"],
            settings_tab_refs["hugging_face_api_key_input"],
            settings_tab_refs["api_keys_status"],
        ],
    )

    settings_tab_refs["apply_log_level_btn"].click(
        fn=_apply_console_log_level,
        inputs=settings_tab_refs["log_level_dropdown"],
        outputs=settings_tab_refs["log_level_status"],
    )

    settings_tab_refs["restart_app_btn"].click(
        fn=ui_restart_application,
        outputs=settings_tab_refs["restart_status"],
    )

    demo.load(
        fn=refresh_artifact_sessions,
        outputs=artifacts_tab_refs["session_picker"]
    )

    load_campaign_btn.click(
        fn=_load_campaign,
        inputs=[existing_campaign_dropdown, active_campaign_state],
        outputs=load_campaign_outputs,
    )

    start_new_campaign_btn.click(
        fn=_create_new_campaign,
        inputs=[new_campaign_name],
        outputs=create_campaign_outputs,
    )

    # Pipeline Stage Control
    process_tab_refs["run_until_stage_input"].change(
        fn=update_skip_flags_from_stage,
        inputs=process_tab_refs["run_until_stage_input"],
        outputs=[
            process_tab_refs["skip_diarization_input"],
            process_tab_refs["skip_classification_input"],
            process_tab_refs["skip_snippets_input"],
            process_tab_refs["skip_knowledge_input"],
        ],
    )

    # Resume from Intermediate Outputs controls
    process_tab_refs["resume_refresh_btn"].click(
        fn=refresh_resume_sessions,
        outputs=process_tab_refs["resume_session_dropdown"],
    )

    process_tab_refs["resume_session_dropdown"].change(
        fn=update_resume_session_info,
        inputs=process_tab_refs["resume_session_dropdown"],
        outputs=process_tab_refs["resume_session_info"],
    )

    process_tab_refs["resume_process_btn"].click(
        fn=process_from_intermediate_ui,
        inputs=[
            process_tab_refs["resume_session_dropdown"],
            process_tab_refs["resume_stage_dropdown"],
        ],
        outputs=process_tab_refs["resume_status"],
    )

    # Campaign Tab interactive controls
    campaign_tab_refresh_args = {
        "fn": _refresh_campaign_tab,
        "inputs": [campaign_tab_refs["campaign_selector"], active_campaign_state],
        "outputs": [
            campaign_tab_refs["campaign_selector"],
            campaign_tab_refs["overview"],
            campaign_tab_refs["knowledge"],
            campaign_tab_refs["session_library"],
            campaign_tab_refs["new_campaign_name_input"],
        ],
    }
    campaign_tab_refs["campaign_selector"].change(**campaign_tab_refresh_args)
    campaign_tab_refs["refresh_btn"].click(**campaign_tab_refresh_args)

    # Wire new campaign management buttons
    campaign_tab_refs["rename_campaign_btn"].click(
        fn=_handle_rename_campaign,
        inputs=[
            campaign_tab_refs["campaign_selector"],
            campaign_tab_refs["new_campaign_name_input"],
            active_campaign_state
        ],
        outputs=rename_campaign_outputs
    )

    campaign_tab_refs["delete_campaign_btn"].click(
        fn=_handle_delete_campaign,
        inputs=[
            campaign_tab_refs["campaign_selector"],
            active_campaign_state
        ],
        outputs=delete_campaign_outputs,
        # Add confirmation dialog for safety
        js="() => confirm('Are you sure you want to permanently delete this campaign? This action cannot be undone.')"
    )


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
        logger.error("=" * 80)
        logger.error("WARNING: Gradio app already running on port 7860!")
        logger.error("=" * 80)
        logger.error("Another instance of the application is already running.")
        logger.error("Please close the existing instance before starting a new one.")
        logger.info("To kill the existing process:")
        logger.info("  1. Find the process ID (PID) monitoring port 7860:")
        logger.info("     netstat -ano | findstr :7860 | findstr LISTENING")
        logger.info("  2. The PID appears in the last column on the LISTENING entry.")
        logger.info("  3. Kill the process using its PID: taskkill /PID <process_id> /F")
        logger.error("=" * 80)
        sys.exit(1)

    logger.info("Starting D&D Session Processor - Modern UI")
    logger.info("Access the interface at http://127.0.0.1:7860")
    demo.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        show_error=True
    )
