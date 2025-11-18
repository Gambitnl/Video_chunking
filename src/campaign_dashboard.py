from pathlib import Path
import json
from typing import Dict, List, Optional

from .config import Config
from .party_config import CampaignManager, PartyConfigManager, Campaign
from .knowledge_base import CampaignKnowledgeBase
from .ui.constants import StatusIndicators

class ComponentStatus:
    """Represents the status of a single dashboard component."""
    def __init__(self, is_ok: bool, title: str, details: str):
        self.is_ok = is_ok
        self.title = title
        self.details = details

class CampaignDashboard:
    """Generates a comprehensive campaign health check dashboard."""

    def __init__(self):
        self.campaign_manager = CampaignManager()
        self.party_manager = PartyConfigManager()

    def _check_party_config(self, campaign: Campaign) -> ComponentStatus:
        party = self.party_manager.get_party(campaign.party_id)
        if not party:
            details = f"{StatusIndicators.ERROR} **Status**: Not configured\n\n"
            details += f"**Action**: Go to **Party Management** tab → Create party '{campaign.party_id}'\n"
            return ComponentStatus(False, "Party Configuration", details)

        details = f"{StatusIndicators.SUCCESS} **Status**: Configured\n\n"
        details += f"- **Party Name**: {party.party_name}\n"
        details += f"- **DM**: {party.dm_name}\n"
        details += f"- **Characters**: {len(party.characters)}\n"
        details += "\n**Character Roster:**\n"
        for char in party.characters:
            aliases = f" (aka {', '.join(char.aliases)})" if char.aliases else ""
            details += f"- **{char.name}**{aliases}: {char.race} {char.class_name} (played by {char.player})\n"
        if party.campaign:
            details += f"\n**Campaign Setting**: {party.campaign}\n"
        return ComponentStatus(True, "Party Configuration", details)

    def _check_processing_settings(self, campaign: Campaign) -> ComponentStatus:
        details = f"{StatusIndicators.SUCCESS} **Status**: Configured\n\n"
        details += f"- **Number of Speakers**: {campaign.settings.num_speakers}\n"
        details += f"- **Skip Diarization**: {'Yes' if campaign.settings.skip_diarization else 'No'}\n"
        details += f"- **Skip IC/OOC Classification**: {'Yes' if campaign.settings.skip_classification else 'No'}\n"
        details += f"- **Skip Audio Snippets**: {'Yes' if campaign.settings.skip_snippets else 'No'}\n"
        details += f"- **Skip Knowledge Extraction**: {'Yes' if campaign.settings.skip_knowledge else 'No'}\n"
        details += f"- **Session ID Prefix**: `{campaign.settings.session_id_prefix}`\n"
        return ComponentStatus(True, "Processing Settings", details)

    def _check_knowledge_base(self, campaign_id: str) -> ComponentStatus:
        try:
            kb = CampaignKnowledgeBase(campaign_id=campaign_id)
            sessions = kb.knowledge.get('sessions_processed', [])
            quests = kb.knowledge.get('quests', [])
            npcs = kb.knowledge.get('npcs', [])
            plot_hooks = kb.knowledge.get('plot_hooks', [])
            locations = kb.knowledge.get('locations', [])
            items = kb.knowledge.get('items', [])
            total_entities = len(quests) + len(npcs) + len(plot_hooks) + len(locations) + len(items)

            if sessions or total_entities > 0:
                details = f"{StatusIndicators.SUCCESS} **Status**: Active ({total_entities} entities)\n\n"
                details += f"- **Sessions Processed**: {len(sessions)} ({', '.join(sessions) if sessions else 'None'})\n"
                details += f"- **Quests**: {len(quests)} ({len([q for q in quests if q.status == 'active'])} active)\n"
                details += f"- **NPCs**: {len(npcs)}\n"
                details += f"- **Plot Hooks**: {len(plot_hooks)} ({len([p for p in plot_hooks if not p.resolved])} unresolved)\n"
                details += f"- **Locations**: {len(locations)}\n"
                details += f"- **Items**: {len(items)}\n"
                details += f"\n**Storage**: `{kb.knowledge_file}`\n"
                return ComponentStatus(True, "Knowledge Base", details)
            else:
                details = f"{StatusIndicators.WARNING} **Status**: Empty (no sessions processed yet)\n\n"
                details += "**Action**: Process a session or import session notes to populate knowledge base\n"
                details += f"\n**Storage**: `{kb.knowledge_file}` (ready)\n"
                return ComponentStatus(False, "Knowledge Base (empty)", details)
        except Exception as e:
            details = f"{StatusIndicators.ERROR} **Status**: Error loading knowledge base\n\n"
            details += f"```\n{str(e)}\n```\n"
            return ComponentStatus(False, "Knowledge Base (error)", details)

    def _check_character_profiles(self, campaign: Campaign) -> ComponentStatus:
        try:
            from src.character_profile import CharacterProfileManager
            char_mgr = CharacterProfileManager()
            party = self.party_manager.get_party(campaign.party_id)

            if not party:
                return ComponentStatus(False, "Character Profiles (no party)", f"{StatusIndicators.WARNING} **Status**: Cannot check (party not configured)")

            party_char_names = [c.name for c in party.characters]
            profiles_for_party = [name for name in party_char_names if name in char_mgr.profiles]
            missing_profiles = [name for name in party_char_names if name not in char_mgr.profiles]

            if len(profiles_for_party) == len(party_char_names):
                details = f"{StatusIndicators.SUCCESS} **Status**: Complete ({len(profiles_for_party)}/{len(party_char_names)} characters)\n\n"
                for name in profiles_for_party:
                    profile = char_mgr.get_profile(name)
                    details += f"- **{name}**: {profile.personality[:50] if profile.personality else 'No personality set'}...\n"
                return ComponentStatus(True, "Character Profiles", details)
            elif len(profiles_for_party) > 0:
                details = f"{StatusIndicators.WARNING} **Status**: Partial ({len(profiles_for_party)}/{len(party_char_names)} characters)\n\n"
                details += f"**Configured**: {', '.join(profiles_for_party)}\n\n"
                details += f"**Missing**: {', '.join(missing_profiles)}\n\n"
                details += "**Action**: Go to **Character Profiles** tab → Create profiles for missing characters\n"
                return ComponentStatus(False, f"Character Profiles ({len(missing_profiles)} missing)", details)
            else:
                details = f"{StatusIndicators.ERROR} **Status**: None configured\n\n"
                details += "**Action**: Go to **Character Profiles** tab → Create profiles for party characters\n"
                return ComponentStatus(False, "Character Profiles (none)", details)

        except Exception as e:
            details = f"{StatusIndicators.ERROR} **Status**: Error loading profiles\n\n"
            details += f"```\n{str(e)}\n```\n"
            return ComponentStatus(False, "Character Profiles (error)", details)

    def _check_processed_sessions(self, campaign_id: str) -> ComponentStatus:
        """
        Check for processed sessions belonging to the specified campaign.

        Args:
            campaign_id: Campaign identifier to filter sessions by

        Returns:
            ComponentStatus indicating session availability for this campaign
        """
        try:
            all_session_dirs = [d for d in Config.OUTPUT_DIR.iterdir() if d.is_dir()] if Config.OUTPUT_DIR.exists() else []

            # Filter sessions by campaign_id
            campaign_sessions = []
            for session_dir in all_session_dirs:
                # Find the session's _data.json file
                data_files = list(session_dir.glob('*_data.json'))
                if data_files:
                    try:
                        with open(data_files[0], 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                            if isinstance(metadata, dict):
                                # Check if session belongs to this campaign
                                session_campaign_id = metadata.get('campaign_id')
                                if session_campaign_id == campaign_id:
                                    campaign_sessions.append(session_dir)
                                # Handle legacy sessions without campaign_id (exclude them)
                                # Empty campaign_id is treated as not matching
                    except (json.JSONDecodeError, IOError):
                        # Skip sessions with invalid or unreadable metadata
                        continue

            if campaign_sessions:
                details = f"{StatusIndicators.SUCCESS} **Status**: {len(campaign_sessions)} session(s) found\n\n"
                recent = sorted(campaign_sessions, key=lambda d: d.stat().st_mtime, reverse=True)[:5]
                details += "**Recent Sessions:**\n"
                for session_dir in recent:
                    # TODO: Implement session status check (e.g., complete, incomplete)
                    details += f"- `{session_dir.name}` ✓\n"
                return ComponentStatus(True, "Processed Sessions", details)
            else:
                details = f"{StatusIndicators.WARNING} **Status**: No sessions processed yet for this campaign\n\n"
                details += "**Action**: Go to **Process Session** tab → Process your first recording\n"
                return ComponentStatus(False, "Processed Sessions (none)", details)
        except Exception as e:
            details = f"{StatusIndicators.ERROR} **Status**: Error checking sessions\n\n"
            details += f"```\n{str(e)}\n```\n"
            return ComponentStatus(False, "Processed Sessions (error)", details)

    def _check_session_narratives(self, campaign_id: str) -> ComponentStatus:
        try:
            narrative_count = 0
            if Config.OUTPUT_DIR.exists():
                for session_dir in Config.OUTPUT_DIR.iterdir():
                    if session_dir.is_dir():
                        # Find the session's _data.json file (same pattern as _check_processed_sessions)
                        data_files = list(session_dir.glob('*_data.json'))
                        if data_files:
                            try:
                                with open(data_files[0], 'r', encoding='utf-8') as f:
                                    data = json.load(f)
                                    metadata = data.get('metadata', {})
                                    session_campaign_id = metadata.get('campaign_id')

                                    # Only count narratives for this campaign's sessions
                                    if session_campaign_id == campaign_id:
                                        narratives_dir = session_dir / "narratives"
                                        if narratives_dir.exists():
                                            narrative_count += len(list(narratives_dir.glob("*.md")))
                            except (json.JSONDecodeError, IOError):
                                # Skip sessions with invalid metadata
                                continue

            # Note: imported_narratives are global and not campaign-specific
            # They should be manually reviewed/categorized by users
            # For now, we exclude them from campaign-specific counts

            if narrative_count > 0:
                details = f"{StatusIndicators.SUCCESS} **Status**: {narrative_count} narrative(s) generated\n\n"
                details += "**Action**: View in **Story Notebooks** tab\n"
                return ComponentStatus(True, "Session Narratives", details)
            else:
                details = f"{StatusIndicators.WARNING} **Status**: No narratives yet\n\n"
                details += "**Action**: Use **Story Notebooks** tab to generate narratives from processed sessions\n"
                return ComponentStatus(False, "Session Narratives (none)", details)
        except Exception as e:
            return ComponentStatus(False, "Session Narratives (error)", f"{StatusIndicators.ERROR} **Status**: Error checking narratives")

    def generate(self, campaign_name: str) -> str:
        """Generate the full dashboard markdown string."""
        campaign_names = self.campaign_manager.get_campaign_names()
        if campaign_name == "Manual Setup":
            return "## Manual Setup Mode\n\nNo campaign profile selected. Choose a campaign from the dropdown to see its dashboard."

        campaign_id = next((cid for cid, cname in campaign_names.items() if cname == campaign_name), None)
        if not campaign_id:
            return f"## Error\n\nCampaign '{campaign_name}' not found."

        campaign = self.campaign_manager.get_campaign(campaign_id)
        if not campaign:
            return f"## Error\n\nCampaign '{campaign_id}' configuration not found."

        # --- Build Dashboard --- #
        output = f"# 🎲 Campaign Dashboard: {campaign.name}\n\n"
        if campaign.description:
            output += f"*{campaign.description}*\n\n"
        output += "---\n\n"

        # --- Gather Component Statuses --- #
        checks = [
            self._check_party_config(campaign),
            self._check_processing_settings(campaign),
            self._check_knowledge_base(campaign_id),
            self._check_character_profiles(campaign),
            self._check_processed_sessions(campaign_id),
            self._check_session_narratives(campaign_id),
        ]

        all_good_titles = [c.title for c in checks if c.is_ok]
        needs_attention_titles = [c.title for c in checks if not c.is_ok]

        # --- Render Summary --- #
        total_components = len(checks)
        health_percent = 0
        if total_components > 0:
            health_percent = int((len(all_good_titles) / total_components) * 100)

        if health_percent == 100:
            health_emoji = StatusIndicators.HEALTH_EXCELLENT
            health_status = "Excellent"
        elif health_percent >= 75:
            health_emoji = StatusIndicators.HEALTH_GOOD
            health_status = "Good"
        elif health_percent >= 50:
            health_emoji = StatusIndicators.HEALTH_FAIR
            health_status = "Fair"
        else:
            health_emoji = StatusIndicators.HEALTH_POOR
            health_status = "Needs Setup"

        output += f"## 📊 Campaign Health Summary\n\n"
        output += f"### {health_emoji} Health: {health_status} ({health_percent}%)\n\n"

        if all_good_titles:
            output += f"**{StatusIndicators.SUCCESS} Configured ({len(all_good_titles)}):**\n"
            for item in all_good_titles:
                output += f"- {item}\n"
            output += "\n"

        if needs_attention_titles:
            output += f"**{StatusIndicators.WARNING} Needs Attention ({len(needs_attention_titles)}):**\n"
            for item in needs_attention_titles:
                output += f"- {item}\n"
            output += "\n"
        
        output += "---\n\n"

        # --- Render Detailed Sections --- #
        for i, status in enumerate(checks):
            output += f"## {i+1}️⃣ {status.title}\n\n"
            output += status.details + "\n\n---\n\n"

        output += "💡 **Tip**: A complete campaign setup includes party configuration, character profiles, and at least one processed session or imported notes.\n"

        return output