"""
Party-wide analytics and relationship analysis.

Provides comprehensive party composition analysis, shared relationships detection,
item distribution analysis, and action balance calculations.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Set
from collections import Counter, defaultdict
import logging

from src.character_profile import CharacterProfileManager, CharacterProfile

logger = logging.getLogger(__name__)


@dataclass
class PartyComposition:
    """
    Party-wide statistics and composition data.

    Provides a comprehensive view of party makeup, participation, shared relationships,
    and item distribution.
    """
    campaign_id: Optional[str]
    characters: List[str] = field(default_factory=list)
    total_sessions: int = 0
    character_participation: Dict[str, int] = field(default_factory=dict)  # char -> session count
    shared_relationships: List[Tuple[str, str, str]] = field(default_factory=list)  # (entity, chars, rel_types)
    item_distribution: Dict[str, List[str]] = field(default_factory=dict)  # char -> items
    action_balance: Dict[str, Dict[str, int]] = field(default_factory=dict)  # char -> {action_type: count}


class PartyAnalyzer:
    """
    Party-wide analytics and relationship analysis.

    Analyzes patterns across all characters in a campaign/party, identifying
    shared relationships, item distribution, and action balance.

    Example:
        ```python
        from src.analytics import PartyAnalyzer

        analyzer = PartyAnalyzer(profile_manager)

        # Analyze party composition
        composition = analyzer.analyze_party_composition("crimson_company")

        # Find shared relationships
        shared = analyzer.find_shared_relationships("crimson_company")

        # Analyze item distribution
        items = analyzer.analyze_item_distribution("crimson_company")
        ```
    """

    def __init__(self, profile_manager: CharacterProfileManager):
        """
        Initialize party analyzer.

        Args:
            profile_manager: Character profile manager instance
        """
        self.profile_manager = profile_manager
        self.logger = logging.getLogger(__name__)

    def analyze_party_composition(
        self,
        campaign_id: Optional[str] = None
    ) -> PartyComposition:
        """
        Analyze complete party composition.

        Gathers all party-wide statistics including character participation,
        shared relationships, item distribution, and action balance.

        Args:
            campaign_id: Campaign ID to analyze. If None, analyzes all characters.

        Returns:
            PartyComposition object with complete party analysis

        Raises:
            ValueError: If campaign has no characters
        """
        # Get characters for campaign
        if campaign_id:
            profiles = self.profile_manager.get_profiles_by_campaign(campaign_id)
        else:
            profiles = self.profile_manager.profiles

        if not profiles:
            raise ValueError(f"No characters found for campaign '{campaign_id}'")

        characters = list(profiles.keys())

        # Calculate character participation (session counts)
        participation = {}
        all_sessions = set()
        for char_name, profile in profiles.items():
            participation[char_name] = profile.total_sessions
            all_sessions.update(profile.sessions_appeared)

        # Find shared relationships
        shared_rels = self.find_shared_relationships(campaign_id)

        # Analyze item distribution
        item_dist = {}
        for char_name, profile in profiles.items():
            item_dist[char_name] = [item.name for item in profile.inventory]

        # Calculate action balance
        action_balance = {}
        for char_name, profile in profiles.items():
            action_counts = Counter([action.type for action in profile.notable_actions])
            action_balance[char_name] = dict(action_counts)

        return PartyComposition(
            campaign_id=campaign_id,
            characters=characters,
            total_sessions=len(all_sessions),
            character_participation=participation,
            shared_relationships=shared_rels,
            item_distribution=item_dist,
            action_balance=action_balance
        )

    def find_shared_relationships(
        self,
        campaign_id: Optional[str] = None
    ) -> List[Tuple[str, str, str]]:
        """
        Find NPCs/entities known to multiple characters.

        Identifies relationships (NPCs, factions, etc.) that are shared across
        multiple party members, along with the relationship types.

        Args:
            campaign_id: Campaign ID to analyze. If None, analyzes all characters.

        Returns:
            List of tuples: (entity_name, character_list, relationship_types)

        Example:
            ```python
            >>> shared = analyzer.find_shared_relationships("crimson_company")
            >>> print(shared[0])
            ("Shadow Lord", "Thorin, Elara, Grimm", "enemy, enemy, enemy")
            ```
        """
        # Get characters for campaign
        if campaign_id:
            profiles = self.profile_manager.get_profiles_by_campaign(campaign_id)
        else:
            profiles = self.profile_manager.profiles

        # Build relationship index: entity -> [(character, rel_type), ...]
        relationship_index = defaultdict(list)

        for char_name, profile in profiles.items():
            for rel in profile.relationships:
                relationship_index[rel.name].append((char_name, rel.relationship_type))

        # Filter to only shared relationships (known to 2+ characters)
        shared_relationships = []
        for entity, connections in relationship_index.items():
            if len(connections) >= 2:
                # Sort by character name for consistency
                connections.sort(key=lambda x: x[0])

                char_list = ", ".join([c[0] for c in connections])
                rel_types = ", ".join([c[1] for c in connections])

                shared_relationships.append((entity, char_list, rel_types))

        # Sort by number of connections (most shared first)
        shared_relationships.sort(key=lambda x: len(x[1].split(", ")), reverse=True)

        return shared_relationships

    def analyze_item_distribution(
        self,
        campaign_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze item distribution and categories across the party.

        Provides detailed breakdown of items by category, character, and rarity.

        Args:
            campaign_id: Campaign ID to analyze. If None, analyzes all characters.

        Returns:
            Dictionary with item distribution statistics

        Example:
            ```python
            >>> dist = analyzer.analyze_item_distribution("crimson_company")
            >>> print(dist["by_category"]["weapon"])
            {"total": 15, "characters": {"Thorin": 4, "Elara": 3, ...}}
            ```
        """
        # Get characters for campaign
        if campaign_id:
            profiles = self.profile_manager.get_profiles_by_campaign(campaign_id)
        else:
            profiles = self.profile_manager.profiles

        # Count items by category
        by_category = defaultdict(lambda: {"total": 0, "characters": defaultdict(int)})
        by_character = defaultdict(lambda: {"total": 0, "by_category": defaultdict(int)})

        for char_name, profile in profiles.items():
            for item in profile.inventory:
                category = item.category or "misc"

                # Update category counts
                by_category[category]["total"] += 1
                by_category[category]["characters"][char_name] += 1

                # Update character counts
                by_character[char_name]["total"] += 1
                by_character[char_name]["by_category"][category] += 1

        # Convert defaultdicts to regular dicts
        by_category = {k: {"total": v["total"], "characters": dict(v["characters"])}
                      for k, v in by_category.items()}
        by_character = {k: {"total": v["total"], "by_category": dict(v["by_category"])}
                       for k, v in by_character.items()}

        # Calculate totals
        total_items = sum(v["total"] for v in by_character.values())

        return {
            "total_items": total_items,
            "by_category": by_category,
            "by_character": by_character,
            "categories": list(by_category.keys()),
        }

    def get_session_participation_matrix(
        self,
        campaign_id: Optional[str] = None
    ) -> List[List[str]]:
        """
        Generate session participation matrix.

        Creates a 2D matrix showing which characters appeared in which sessions.

        Args:
            campaign_id: Campaign ID to analyze. If None, analyzes all characters.

        Returns:
            2D list (matrix) where rows are sessions and columns are characters.
            Cell values are "X" if character appeared, "" if not.

        Example:
            ```python
            >>> matrix = analyzer.get_session_participation_matrix("crimson_company")
            >>> # matrix[0] = ["session_001", "X", "X", "", "X"]  # Thorin, Elara, Grimm present
            ```
        """
        # Get characters for campaign
        if campaign_id:
            profiles = self.profile_manager.get_profiles_by_campaign(campaign_id)
        else:
            profiles = self.profile_manager.profiles

        if not profiles:
            return []

        # Get all sessions
        all_sessions = set()
        for profile in profiles.values():
            all_sessions.update(profile.sessions_appeared)

        sessions_sorted = sorted(all_sessions)
        characters_sorted = sorted(profiles.keys())

        # Build matrix
        matrix = [["Session"] + characters_sorted]  # Header row

        for session in sessions_sorted:
            row = [session]
            for char_name in characters_sorted:
                profile = profiles[char_name]
                row.append("X" if session in profile.sessions_appeared else "")
            matrix.append(row)

        return matrix

    def calculate_party_synergy(
        self,
        campaign_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate party role balance and synergy.

        Analyzes action types and character roles to determine party balance.

        Args:
            campaign_id: Campaign ID to analyze. If None, analyzes all characters.

        Returns:
            Dictionary with synergy statistics

        Example:
            ```python
            >>> synergy = analyzer.calculate_party_synergy("crimson_company")
            >>> print(synergy["role_balance"])
            {"combat": 0.45, "social": 0.25, "exploration": 0.20, "magic": 0.10}
            ```
        """
        # Get characters for campaign
        if campaign_id:
            profiles = self.profile_manager.get_profiles_by_campaign(campaign_id)
        else:
            profiles = self.profile_manager.profiles

        if not profiles:
            return {}

        # Count total actions by type across all characters
        total_actions_by_type = Counter()
        for profile in profiles.values():
            for action in profile.notable_actions:
                total_actions_by_type[action.type] += 1

        # Calculate percentages
        total_actions = sum(total_actions_by_type.values())
        role_balance = {}
        if total_actions > 0:
            role_balance = {
                action_type: count / total_actions
                for action_type, count in total_actions_by_type.items()
            }

        # Identify character specializations (action type with highest percentage)
        specializations = {}
        for char_name, profile in profiles.items():
            action_counts = Counter([action.type for action in profile.notable_actions])
            if action_counts:
                primary_role = action_counts.most_common(1)[0][0]
                specializations[char_name] = primary_role

        return {
            "role_balance": role_balance,
            "total_actions_by_type": dict(total_actions_by_type),
            "character_specializations": specializations,
            "party_size": len(profiles),
        }

    def generate_party_dashboard_markdown(
        self,
        campaign_id: Optional[str] = None
    ) -> str:
        """
        Generate comprehensive party dashboard in markdown format.

        Args:
            campaign_id: Campaign ID to analyze. If None, analyzes all characters.

        Returns:
            Markdown-formatted party dashboard

        Raises:
            ValueError: If campaign has no characters
        """
        composition = self.analyze_party_composition(campaign_id)
        synergy = self.calculate_party_synergy(campaign_id)
        item_dist = self.analyze_item_distribution(campaign_id)

        campaign_name = campaign_id or "All Campaigns"
        md = f"# Party Analytics: {campaign_name}\n\n"

        # Overview
        md += "## Composition\n\n"
        md += f"- **Characters**: {len(composition.characters)}\n"
        md += f"- **Sessions**: {composition.total_sessions}\n"
        md += f"- **Total Actions**: {sum(sum(counts.values()) for counts in composition.action_balance.values())}\n"
        md += f"- **Total Items**: {item_dist['total_items']}\n\n"

        # Character Participation Table
        md += "## Character Participation\n\n"
        md += "| Character | Sessions | Actions | Items | Relationships |\n"
        md += "|-----------|----------|---------|----------|---------------|\n"

        for char_name in sorted(composition.characters):
            sessions = composition.character_participation.get(char_name, 0)
            actions = sum(composition.action_balance.get(char_name, {}).values())
            items = len(composition.item_distribution.get(char_name, []))

            # Count relationships
            profile = self.profile_manager.get_profile(char_name)
            relationships = len(profile.relationships) if profile else 0

            md += f"| {char_name} | {sessions} | {actions} | {items} | {relationships} |\n"

        md += "\n"

        # Shared Relationships
        if composition.shared_relationships:
            md += "## Shared Connections\n\n"
            for entity, chars, rel_types in composition.shared_relationships[:10]:  # Top 10
                md += f"- **{entity}**: Known to {chars} ({rel_types})\n"
            md += "\n"

        # Item Distribution by Category
        if item_dist["by_category"]:
            md += "## Item Distribution\n\n"
            for category in sorted(item_dist["by_category"].keys()):
                total = item_dist["by_category"][category]["total"]
                md += f"- **{category.title()}**: {total} total\n"
            md += "\n"

        # Action Balance
        if synergy.get("role_balance"):
            md += "## Action Balance\n\n"
            for action_type, percentage in sorted(synergy["role_balance"].items(), key=lambda x: x[1], reverse=True):
                md += f"- **{action_type.title()}**: {percentage*100:.1f}%\n"
            md += "\n"

        # Character Specializations
        if synergy.get("character_specializations"):
            md += "## Character Specializations\n\n"
            for char_name, role in sorted(synergy["character_specializations"].items()):
                md += f"- **{char_name}**: {role.title()}\n"
            md += "\n"

        return md
