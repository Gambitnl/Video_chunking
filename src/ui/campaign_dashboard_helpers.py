
"""
Campaign Dashboard Helpers
==========================

This module contains helper functions for the campaign dashboard UI,
generating markdown content and handling data retrieval with robust error handling.
"""
import logging
from typing import Optional, Tuple, List
from pathlib import Path

from src.ui.helpers import StatusMessages
from src.ui.constants import StatusIndicators
from src.config import Config
from src.party_config import CampaignManager, PartyConfigManager
from src.knowledge_base import CampaignKnowledgeBase
from src.character_profile import CharacterProfileManager
from src.story_notebook import StoryNotebookManager
from src.artifact_counter import CampaignArtifactCounter

logger = logging.getLogger(__name__)

def count_campaign_artifacts(
    campaign_id: str,
    artifact_counter: CampaignArtifactCounter
) -> Tuple[int, int]:
    """
    Count processed sessions and narratives for a campaign.

    Args:
        campaign_id: Campaign identifier to count artifacts for
        artifact_counter: Instance of CampaignArtifactCounter

    Returns:
        Tuple of (session_count, narrative_count)
    """
    try:
        counts = artifact_counter.count_artifacts(campaign_id)
        return counts.to_tuple()
    except Exception as e:
        logger.error(f"Failed to count campaign artifacts for '{campaign_id}': {e}", exc_info=True)
        return (0, 0)

def status_tracker_summary(campaign_id: str) -> str:
    """Describe the status tracker state for the campaign."""
    status_path = Config.PROJECT_ROOT / "logs" / "session_status.json"
    if not status_path.exists():
        return f"{StatusIndicators.PENDING} Status tracker has no recorded sessions yet."

    try:
        import json
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

def build_campaign_manifest(
    campaign_id: Optional[str],
    campaign_manager: CampaignManager,
    party_manager: PartyConfigManager,
    artifact_counter: CampaignArtifactCounter
) -> str:
    """Generate manifest markdown for the selected campaign."""
    if not campaign_id:
        return StatusMessages.warning(
            "Campaign Manifest",
            "Select or create a campaign to inspect campaign assets."
        )

    try:
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
            if profile.campaign_id == campaign_id
        )
        if profile_count:
            lines.append(f"- {StatusIndicators.READY} {profile_count} character profiles assigned to this campaign.")
        else:
            lines.append(
                f"- {StatusIndicators.WARNING} No character profiles assigned. Use the Characters tab to assign or import."
            )

        session_count, narrative_count = count_campaign_artifacts(campaign_id, artifact_counter)
        if session_count:
            lines.append(
                f"- {StatusIndicators.INFO} {session_count} processed sessions "
                f"({narrative_count} narratives stored)."
            )
        else:
            lines.append(
                f"- {StatusIndicators.PENDING} No processed sessions recorded yet."
            )

        lines.append(f"- {status_tracker_summary(campaign_id)}")

        return "\n".join(lines)

    except Exception as e:
        logger.error(f"Error building campaign manifest for '{campaign_id}': {e}", exc_info=True)
        return StatusMessages.error(
            "Manifest Generation Failed",
            f"Could not generate manifest for campaign `{campaign_id}`.",
            str(e)
        )

def campaign_overview_markdown(
    campaign_id: Optional[str],
    campaign_manager: CampaignManager,
    artifact_counter: CampaignArtifactCounter
) -> str:
    if not campaign_id:
        return StatusMessages.info(
            "Campaign Overview",
            "Select a campaign to display campaign metrics."
        )

    try:
        campaign = campaign_manager.get_campaign(campaign_id)
        if not campaign:
            return StatusMessages.error("Campaign Missing", f"Campaign `{campaign_id}` not found.")

        knowledge = CampaignKnowledgeBase(campaign_id=campaign_id)
        session_count, narrative_count = count_campaign_artifacts(campaign_id, artifact_counter)
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

    except Exception as e:
        logger.error(f"Error generating campaign overview for '{campaign_id}': {e}", exc_info=True)
        return StatusMessages.error(
            "Campaign Data Error",
            f"Could not load campaign data for `{campaign_id}`.",
            f"Error: {str(e)}"
        )

def knowledge_summary_markdown(campaign_id: Optional[str]) -> str:
    if not campaign_id:
        return StatusMessages.info(
            "Knowledge Base",
            "Knowledge summaries will appear here once a campaign is selected."
        )

    try:
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

        def _format_sample(entries, attr, label):
            """Format a sample with total count indication if truncated."""
            total = len(entries)
            if not total:
                return f"- {label}: None captured"

            sample = _sample(entries, attr)
            if total > 3:
                return f"- {label}: {sample} (showing 3 of {total})"

            # For total <= 3, _sample handles the "None captured" case if no names are found.
            return f"- {label}: {sample}"

        lines = [
            "### Knowledge Highlights",
            _format_sample(quests, 'title', 'Sample quests'),
            _format_sample(npcs, 'name', 'Sample NPCs'),
            _format_sample(locations, 'name', 'Sample locations'),
            _format_sample(items, 'name', 'Sample items'),
        ]
        return "\n".join(lines)

    except Exception as e:
        logger.error(f"Error generating knowledge summary for '{campaign_id}': {e}", exc_info=True)
        return StatusMessages.error(
            "Knowledge Base Error",
            f"Could not load knowledge base for `{campaign_id}`.",
            f"Error: {str(e)}"
        )

def session_library_markdown(
    campaign_id: Optional[str],
    story_manager: StoryNotebookManager,
    campaign_manager: CampaignManager
) -> str:
    if not campaign_id:
        return StatusMessages.info(
            "Session Library",
            "Processed sessions for the active campaign will appear here."
        )

    try:
        # Fetch all sessions to audit their campaign alignment
        all_session_ids = story_manager.list_sessions(
            limit=None,
            campaign_id=None,  # Get everything
            include_unassigned=True,
        )

        valid_sessions = []
        issue_sessions = []

        # Classify sessions
        for session_id in all_session_ids:
            try:
                session = story_manager.load_session(session_id)
                session_campaign_id = session.metadata.get("campaign_id")

                if session_campaign_id == campaign_id:
                    valid_sessions.append(session)
                elif session_campaign_id is None:
                    issue_sessions.append((session_id, "Orphaned (No Campaign ID)", session))
                elif session_campaign_id != campaign_id:
                    # Check if the other campaign exists
                    if campaign_manager.get_campaign(session_campaign_id):
                        # Belongs to a valid OTHER campaign -> Hide implicitly (don't show in this campaign's list)
                        continue
                    else:
                        # Belongs to a deleted/missing campaign -> Show as issue
                        issue_sessions.append(
                            (session_id, f"Orphaned (Campaign `{session_campaign_id}` not found)", session)
                        )
            except Exception as e:
                # Corrupted metadata or load failure
                issue_sessions.append((session_id, f"Error loading metadata: {str(e)}", None))

        if not valid_sessions and not issue_sessions:
            return StatusMessages.warning(
                "No Sessions",
                "Process a session for this campaign to populate the library."
            )

        lines = ["### Processed Sessions", ""]

        # 1. List Valid Sessions
        if valid_sessions:
            for session in valid_sessions:
                session_id = session.session_id
                stats = session.metadata.get("statistics", {})
                duration = stats.get("total_duration_formatted") or f"{stats.get('total_duration_seconds', 0)}s"
                segments = stats.get("total_segments", 0)

                output_dir = Config.OUTPUT_DIR / session_id
                narratives_dir = output_dir / "narratives"
                narrative_count = len(list(narratives_dir.glob("*.md"))) if narratives_dir.exists() else 0

                lines.append(f"#### {StatusIndicators.COMPLETE} {session_id}")
                lines.append(f"- **Duration**: {duration}")
                lines.append(f"- **Segments**: {segments}")
                lines.append(f"- **Narratives**: {narrative_count}")
                lines.append(f"- **Output**: `{output_dir.relative_to(Config.PROJECT_ROOT)}`")
                lines.append("")
        else:
            lines.append(StatusMessages.info("Empty", "No valid sessions found for this campaign."))

        # 2. List Issues (Collapsible)
        if issue_sessions:
            lines.append("")
            lines.append(f"<details><summary>⚠️ Found {len(issue_sessions)} Session Issues (Orphaned/Corrupt)</summary>")
            lines.append("")
            lines.append("> These sessions are not assigned to the active campaign or have errors.")
            lines.append("")

            for sid, reason, session in issue_sessions:
                lines.append(f"- **{sid}**: {reason}")
                if session:
                    output_dir = Config.OUTPUT_DIR / sid
                    lines.append(f"  - Path: `{output_dir.relative_to(Config.PROJECT_ROOT)}`")

            lines.append("")
            lines.append("</details>")

        return "\n".join(lines)

    except Exception as e:
        logger.error(f"Error loading session library for '{campaign_id}': {e}", exc_info=True)
        return StatusMessages.error(
            "Session Library Error",
            f"Could not load sessions for `{campaign_id}`.",
            f"Error: {str(e)}"
        )

def narrative_hint_markdown(
    campaign_id: Optional[str],
    story_manager: StoryNotebookManager
) -> str:
    if not campaign_id:
        return StatusMessages.info(
            "Narratives",
            "Narrative export locations will display here once a campaign is active."
        )

    try:
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

    except Exception as e:
        # Keep this one simple as it's just a hint
        logger.warning(f"Error generating narrative hint for '{campaign_id}': {e}")
        return StatusMessages.info(
            "Narratives",
            "Could not scan for narratives due to an error."
        )

def diagnostics_markdown(campaign_id: Optional[str]) -> str:
    if not campaign_id:
        return StatusMessages.info(
            "Diagnostics",
            "Launch a campaign to track pipeline diagnostics and status."
        )

    return "\n".join(
        [
            "### Diagnostics",
            status_tracker_summary(campaign_id),
        ]
    )

def chat_status_markdown(campaign_id: Optional[str]) -> str:
    if not campaign_id:
        return StatusMessages.info(
            "LLM Chat",
            "Load a campaign to initialise chat context."
        )

    try:
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
    except Exception as e:
        logger.error(f"Error checking chat status for '{campaign_id}': {e}")
        return StatusMessages.error("LLM Chat Error", "Could not check knowledge base status.")
