"""Gradio web UI for D&D Session Processor - Modern UI"""
import os
import json
import socket
import sys
import subprocess
from pathlib import Path

import gradio as gr
import requests

from typing import Any, Dict, List, Optional, Tuple

from src.pipeline import DDSessionProcessor
from src.config import Config
from src.diarizer import SpeakerProfileManager
from src.character_profile import CharacterProfileManager
from src.logger import get_log_file_path
from src.party_config import PartyConfigManager, CampaignManager
from src.knowledge_base import CampaignKnowledgeBase
from src.preflight import PreflightIssue
from src.ui.constants import StatusIndicators
from src.ui.helpers import StatusMessages, UIComponents
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
speaker_profile_manager = SpeakerProfileManager()


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
    """Count processed sessions and narratives for a campaign."""
    if not campaign_id:
        return 0, 0

    session_count = 0
    narrative_count = 0
    output_dir = Config.OUTPUT_DIR
    if not output_dir.exists():
        return 0, 0

    for data_path in output_dir.glob("**/*_data.json"):
        try:
            payload = json.loads(data_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        metadata = payload.get("metadata") or {}
        if metadata.get("campaign_id") != campaign_id:
            continue
        session_count += 1
        narratives_dir = data_path.parent / "narratives"
        if narratives_dir.exists():
            narrative_count += len([p for p in narratives_dir.glob("*.md") if p.is_file()])
    return session_count, narrative_count


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


def _character_profiles_markdown(campaign_id: Optional[str]) -> str:
    manager = CharacterProfileManager()
    if not campaign_id:
        return StatusMessages.info(
            "Character Profiles",
            "Load a campaign to list character profiles associated with it."
        )

    profiles = [
        profile for profile in manager.profiles.values()
        if getattr(profile, "campaign_id", None) == campaign_id
    ]
    if not profiles:
        return StatusMessages.warning(
            "No Profiles Found",
            "No character profiles are assigned to this campaign yet."
        )

    lines = ["### Characters"]
    for profile in sorted(profiles, key=lambda p: p.name.lower()):
        class_name = getattr(profile, "class_name", "Unknown class")
        level = getattr(profile, "level", "n/a")
        last_updated = getattr(profile, "last_updated", "unknown")
        lines.append(
            f"- **{profile.name}** ({class_name}, level {level}) — last updated {last_updated}"
        )
    return "\n".join(lines)


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

    lines = ["### Processed Sessions"]
    for session_id in session_ids:
        try:
            session = story_manager.load_session(session_id)
            stats = session.metadata.get("statistics", {})
            duration = stats.get("total_duration_formatted") or f"{stats.get('total_duration_seconds', 0)}s"
            segments = stats.get("total_segments", 0)
            lines.append(f"- `{session_id}` — {duration}, segments: {segments}")
        except Exception:
            lines.append(f"- `{session_id}` — metadata unavailable")
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
    *,
    allow_empty_names: bool = False,
) -> DDSessionProcessor:
    """Instantiate a session processor respecting party/manual inputs."""
    resolved_speakers = int(num_speakers) if num_speakers else 4
    resolved_language = language or "en"

    if party_selection and party_selection != "Manual Entry":
        processor = DDSessionProcessor(
            session_id=session_id,
            campaign_id=campaign_id,
            num_speakers=resolved_speakers,
            party_id=party_selection,
            language=resolved_language,
        )
    else:
        chars = [c.strip() for c in (character_names or "").split(',') if c.strip()]
        players = [p.strip() for p in (player_names or "").split(',') if p.strip()]

        if not chars and not allow_empty_names:
            raise ValueError("Character names are required when using Manual Entry")

        kwargs: Dict[str, Any] = {
            "session_id": session_id,
            "campaign_id": campaign_id,
            "num_speakers": resolved_speakers,
            "language": resolved_language,
        }
        if chars:
            kwargs["character_names"] = chars
        if players:
            kwargs["player_names"] = players

        processor = DDSessionProcessor(**kwargs)

    return processor


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
    campaign_id: Optional[str] = None,
) -> Dict:
    """Main session processing function."""
    try:
        if audio_file is None:
            return {"status": "error", "message": "Please upload an audio file."}

        resolved_session_id = session_id or "session"

        # Determine if using party config or manual entry
        processor = _create_processor_for_context(
            resolved_session_id,
            party_selection,
            character_names,
            player_names,
            num_speakers,
            language,
            campaign_id,
            allow_empty_names=False,
        )

        pipeline_result = processor.process(
            input_file=_resolve_audio_path(audio_file),
            skip_diarization=skip_diarization,
            skip_classification=skip_classification,
            skip_snippets=skip_snippets,
            skip_knowledge=skip_knowledge
        )

        if not isinstance(pipeline_result, dict):
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


def run_preflight_checks(
    party_selection,
    character_names,
    player_names,
    num_speakers,
    language,
    skip_diarization,
    skip_classification,
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
    characters_tab_refs = create_characters_tab_modern(demo, available_parties)
    stories_tab_refs = create_stories_output_tab_modern(demo)
    settings_tab_refs = create_settings_tools_tab_modern(
        demo,
        story_manager=story_manager,
        refresh_campaign_names=_refresh_campaign_names,
        initial_campaign_id=initial_campaign_id,
        speaker_profile_manager=speaker_profile_manager,
    )

    def _compute_process_updates(campaign_id: Optional[str]) -> Tuple:
        settings = _process_defaults_for_campaign(campaign_id)
        campaign_names_map = _refresh_campaign_names()
        display_name = campaign_names_map.get(campaign_id, "Manual Setup") if campaign_id else "Manual Setup"

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
            "",
            "",
            "",
            StatusMessages.info("Statistics", "No statistics available."),
            StatusMessages.info("Snippet Export", "No snippet information available."),
        )

    def _load_campaign(display_name: Optional[str], current_campaign_id: Optional[str]):
        campaign_id = _campaign_id_from_name(display_name) or current_campaign_id or initial_campaign_id
        summary = _campaign_summary_message(campaign_id)
        manifest = _build_campaign_manifest(campaign_id)

        process_updates = _compute_process_updates(campaign_id)
        campaign_names_map = _refresh_campaign_names()
        dropdown_update = gr.update(
            choices=list(campaign_names_map.values()),
            value=campaign_names_map.get(campaign_id) if campaign_id else None,
        )

        overview_update = gr.update(value=_campaign_overview_markdown(campaign_id))
        knowledge_update = gr.update(value=_knowledge_summary_markdown(campaign_id))
        session_library_update = gr.update(value=_session_library_markdown(campaign_id))
        character_profiles_update = gr.update(value=_character_profiles_markdown(campaign_id))
        story_session_update = gr.update(value=_session_library_markdown(campaign_id))
        narrative_hint_update = gr.update(value=_narrative_hint_markdown(campaign_id))
        diagnostics_update = gr.update(value=_diagnostics_markdown(campaign_id))
        chat_update = gr.update(value=_chat_status_markdown(campaign_id))

        social_campaign_choices = ["All Campaigns"] + list(campaign_names_map.values())
        social_campaign_value = campaign_names_map.get(campaign_id) if campaign_id else "All Campaigns"
        if not social_campaign_value:
            social_campaign_value = "All Campaigns"
        social_campaign_update = gr.update(
            choices=social_campaign_choices,
            value=social_campaign_value,
        )

        social_sessions = (
            story_manager.list_sessions(campaign_id=campaign_id)
            if campaign_id
            else story_manager.list_sessions()
        )
        social_session_update = gr.update(
            choices=social_sessions,
            value=social_sessions[0] if social_sessions else None,
        )
        social_keyword_update = gr.update(
            value=StatusMessages.info(
                "Social Insights",
                "Select a session and run Analyze Banter for the current campaign.",
            )
        )
        social_nebula_update = gr.update(value=None)

        return (
            campaign_id,
            summary,
            manifest,
            dropdown_update,
            *process_updates,
            overview_update,
            knowledge_update,
            session_library_update,
            character_profiles_update,
            story_session_update,
            narrative_hint_update,
            diagnostics_update,
            chat_update,
            social_campaign_update,
            social_session_update,
            social_keyword_update,
            social_nebula_update,
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
        process_updates = _compute_process_updates(new_campaign_id)
        campaign_names_map = _refresh_campaign_names()

        dropdown_update = gr.update(
            choices=list(campaign_names_map.values()),
            value=campaign_names_map.get(new_campaign_id),
        )

        overview_update = gr.update(value=_campaign_overview_markdown(new_campaign_id))
        knowledge_update = gr.update(value=_knowledge_summary_markdown(new_campaign_id))
        session_library_update = gr.update(value=_session_library_markdown(new_campaign_id))
        character_profiles_update = gr.update(value=_character_profiles_markdown(new_campaign_id))
        story_session_update = gr.update(value=_session_library_markdown(new_campaign_id))
        narrative_hint_update = gr.update(value=_narrative_hint_markdown(new_campaign_id))
        diagnostics_update = gr.update(value=_diagnostics_markdown(new_campaign_id))
        chat_update = gr.update(value=_chat_status_markdown(new_campaign_id))

        social_campaign_choices = ["All Campaigns"] + list(campaign_names_map.values())
        social_campaign_update = gr.update(
            choices=social_campaign_choices,
            value=campaign_names_map.get(new_campaign_id),
        )
        social_session_update = gr.update(choices=[], value=None)
        social_keyword_update = gr.update(
            value=StatusMessages.info(
                "Social Insights",
                "No sessions available yet for this campaign. Process a session, then rerun analysis.",
            )
        )
        social_nebula_update = gr.update(value=None)

        return (
            new_campaign_id,
            summary,
            manifest,
            dropdown_update,
            gr.update(value=""),
            *process_updates,
            overview_update,
            knowledge_update,
            session_library_update,
            character_profiles_update,
            story_session_update,
            narrative_hint_update,
            diagnostics_update,
            chat_update,
            social_campaign_update,
            social_session_update,
            social_keyword_update,
            social_nebula_update,
        )

    shared_outputs_load = [
        active_campaign_state,
        campaign_summary_md,
        campaign_manifest_md,
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
        characters_tab_refs["profiles"],
        stories_tab_refs["session_list"],
        stories_tab_refs["narrative_hint"],
        settings_tab_refs["diagnostics"],
        settings_tab_refs["chat"],
        settings_tab_refs["social_campaign_selector"],
        settings_tab_refs["social_session_dropdown"],
        settings_tab_refs["social_keyword_output"],
        settings_tab_refs["social_nebula_output"],
    ]

    load_campaign_btn.click(
        fn=_load_campaign,
        inputs=[existing_campaign_dropdown, active_campaign_state],
        outputs=shared_outputs_load,
    )

    create_campaign_outputs = [
        active_campaign_state,
        campaign_summary_md,
        campaign_manifest_md,
        existing_campaign_dropdown,
        new_campaign_name,
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
        characters_tab_refs["profiles"],
        stories_tab_refs["session_list"],
        stories_tab_refs["narrative_hint"],
        settings_tab_refs["diagnostics"],
        settings_tab_refs["chat"],
        settings_tab_refs["social_campaign_selector"],
        settings_tab_refs["social_session_dropdown"],
        settings_tab_refs["social_keyword_output"],
        settings_tab_refs["social_nebula_output"],
    ]

    start_new_campaign_btn.click(
        fn=_create_new_campaign,
        inputs=[new_campaign_name],
        outputs=create_campaign_outputs,
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
