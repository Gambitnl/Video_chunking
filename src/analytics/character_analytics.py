"""
Core analytics engine for character data analysis.

This module provides comprehensive analytics capabilities for character profiles,
including timeline generation, action filtering, and progression statistics.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from pathlib import Path
import logging

from src.character_profile import (
    CharacterProfile,
    CharacterProfileManager,
    CharacterAction,
    CharacterItem,
    CharacterRelationship,
    CharacterDevelopment,
    CharacterQuote,
)

logger = logging.getLogger(__name__)


@dataclass
class TimelineEvent:
    """
    Single event in character timeline.

    Represents a unified event model across different data types (actions, quotes,
    items, relationships, etc.) for chronological display and filtering.
    """
    session_id: str
    timestamp: Optional[str] = None  # HH:MM:SS format
    event_type: str = "action"  # action, quote, development, item, relationship, goal
    description: str = ""
    category: str = "general"  # Specific to event type (combat, social, weapon, etc.)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate event data on initialization."""
        valid_types = ["action", "quote", "development", "item", "relationship", "goal", "level"]
        if self.event_type not in valid_types:
            raise ValueError(f"Invalid event_type '{self.event_type}'. Must be one of: {valid_types}")


@dataclass
class CharacterTimeline:
    """
    Complete timeline for a character.

    Provides a chronological view of all character events across sessions,
    sorted by session and timestamp.
    """
    character_name: str
    events: List[TimelineEvent] = field(default_factory=list)
    sessions: List[str] = field(default_factory=list)  # Ordered chronologically
    total_events: int = 0

    def __post_init__(self):
        """Calculate total events if not provided."""
        if not self.total_events:
            self.total_events = len(self.events)


class CharacterAnalytics:
    """
    Core analytics engine for character data analysis.

    Provides methods for generating timelines, filtering actions, calculating
    statistics, and analyzing character progression.

    Example:
        ```python
        from src.character_profile import CharacterProfileManager
        from src.analytics import CharacterAnalytics

        manager = CharacterProfileManager()
        analytics = CharacterAnalytics(manager)

        # Generate timeline
        timeline = analytics.generate_timeline("Thorin")

        # Filter actions
        combat_actions = analytics.filter_actions(
            "Thorin",
            action_types=["combat"]
        )

        # Get statistics
        stats = analytics.get_progression_stats("Thorin")
        ```
    """

    def __init__(self, profile_manager: CharacterProfileManager):
        """
        Initialize analytics engine.

        Args:
            profile_manager: Character profile manager instance
        """
        self.profile_manager = profile_manager
        self.logger = logging.getLogger(__name__)

    def generate_timeline(
        self,
        character_name: str,
        session_filter: Optional[List[str]] = None,
        event_types: Optional[List[str]] = None
    ) -> CharacterTimeline:
        """
        Generate chronological timeline of character events.

        Combines all character data (actions, quotes, items, relationships, etc.)
        into a unified timeline sorted by session and timestamp.

        Args:
            character_name: Name of character
            session_filter: Optional list of session IDs to include
            event_types: Optional list of event types to include
                       (action, quote, development, item, relationship, goal)

        Returns:
            CharacterTimeline object with sorted events

        Raises:
            ValueError: If character not found
        """
        profile = self.profile_manager.get_profile(character_name)
        if not profile:
            raise ValueError(f"Character '{character_name}' not found")

        events = []

        # Convert actions to timeline events
        for action in profile.notable_actions:
            if session_filter and action.session not in session_filter:
                continue
            if event_types and "action" not in event_types:
                continue

            events.append(TimelineEvent(
                session_id=action.session,
                timestamp=action.timestamp,
                event_type="action",
                description=action.description,
                category=action.type,
                metadata={"action_type": action.type}
            ))

        # Convert quotes to timeline events
        for quote in profile.memorable_quotes:
            if session_filter and quote.session not in session_filter:
                continue
            if event_types and "quote" not in event_types:
                continue

            events.append(TimelineEvent(
                session_id=quote.session,
                timestamp=None,  # Quotes typically don't have timestamps
                event_type="quote",
                description=quote.quote,
                category="memorable",
                metadata={"context": quote.context}
            ))

        # Convert development notes to timeline events
        for dev in profile.development_notes:
            if session_filter and dev.session not in session_filter:
                continue
            if event_types and "development" not in event_types:
                continue

            events.append(TimelineEvent(
                session_id=dev.session,
                timestamp=None,
                event_type="development",
                description=dev.note,
                category=dev.category,
                metadata={"development_category": dev.category}
            ))

        # Convert inventory to timeline events
        for item in profile.inventory:
            if not item.session_acquired:
                continue
            if session_filter and item.session_acquired not in session_filter:
                continue
            if event_types and "item" not in event_types:
                continue

            events.append(TimelineEvent(
                session_id=item.session_acquired,
                timestamp=None,
                event_type="item",
                description=f"Acquired {item.name}",
                category=item.category,
                metadata={
                    "item_name": item.name,
                    "item_description": item.description,
                    "item_category": item.category
                }
            ))

        # Convert relationships to timeline events
        for rel in profile.relationships:
            if not rel.first_met:
                continue
            if session_filter and rel.first_met not in session_filter:
                continue
            if event_types and "relationship" not in event_types:
                continue

            events.append(TimelineEvent(
                session_id=rel.first_met,
                timestamp=None,
                event_type="relationship",
                description=f"Met {rel.name} ({rel.relationship_type})",
                category=rel.relationship_type,
                metadata={
                    "relationship_name": rel.name,
                    "relationship_type": rel.relationship_type,
                    "relationship_description": rel.description
                }
            ))

        # Sort events by session (chronologically) and then by timestamp
        # For events without timestamps, they appear at the end of the session
        def event_sort_key(event: TimelineEvent) -> tuple:
            # Get session index from sessions_appeared list
            try:
                session_idx = profile.sessions_appeared.index(event.session_id)
            except (ValueError, AttributeError):
                session_idx = 9999  # Put unknown sessions at the end

            # Parse timestamp for sorting (HH:MM:SS -> seconds)
            timestamp_seconds = self._parse_timestamp_to_seconds(event.timestamp)

            return (session_idx, timestamp_seconds)

        events.sort(key=event_sort_key)

        # Get sessions list (chronologically ordered)
        if session_filter:
            sessions = [s for s in profile.sessions_appeared if s in session_filter]
        else:
            sessions = profile.sessions_appeared.copy()

        return CharacterTimeline(
            character_name=character_name,
            events=events,
            sessions=sessions,
            total_events=len(events)
        )

    def _parse_timestamp_to_seconds(self, timestamp: Optional[str]) -> float:
        """
        Parse timestamp string to seconds for sorting.

        Args:
            timestamp: Timestamp in HH:MM:SS or MM:SS format

        Returns:
            Total seconds as float. Returns 999999.0 for None/invalid timestamps.
        """
        if not timestamp:
            return 999999.0  # Put events without timestamps at the end

        try:
            parts = timestamp.split(":")
            if len(parts) == 2:  # MM:SS
                minutes, seconds = map(int, parts)
                return minutes * 60 + seconds
            elif len(parts) == 3:  # HH:MM:SS
                hours, minutes, seconds = map(int, parts)
                return hours * 3600 + minutes * 60 + seconds
            else:
                return 999999.0
        except (ValueError, AttributeError):
            return 999999.0

    def filter_actions(
        self,
        character_name: str,
        action_types: Optional[List[str]] = None,
        sessions: Optional[List[str]] = None,
        text_search: Optional[str] = None
    ) -> List[CharacterAction]:
        """
        Filter character actions with multiple criteria.

        Args:
            character_name: Name of character
            action_types: Filter by action types (combat, social, exploration, etc.)
            sessions: Filter by session IDs
            text_search: Text search in action descriptions (case-insensitive)

        Returns:
            List of matching CharacterAction objects

        Raises:
            ValueError: If character not found
        """
        profile = self.profile_manager.get_profile(character_name)
        if not profile:
            raise ValueError(f"Character '{character_name}' not found")

        actions = profile.notable_actions

        # Apply action type filter
        if action_types:
            actions = [a for a in actions if a.type in action_types]

        # Apply session filter
        if sessions:
            actions = [a for a in actions if a.session in sessions]

        # Apply text search filter
        if text_search:
            search_lower = text_search.lower()
            actions = [a for a in actions if search_lower in a.description.lower()]

        return actions

    def get_progression_stats(self, character_name: str) -> Dict[str, Any]:
        """
        Get comprehensive character progression statistics.

        Includes action counts by type and session, item acquisition timeline,
        relationship growth, and development milestones.

        Args:
            character_name: Name of character

        Returns:
            Dictionary with progression statistics

        Raises:
            ValueError: If character not found
        """
        profile = self.profile_manager.get_profile(character_name)
        if not profile:
            raise ValueError(f"Character '{character_name}' not found")

        # Get actions by session
        actions_by_session = {}
        for action in profile.notable_actions:
            actions_by_session.setdefault(action.session, []).append(action)

        # Get actions by type
        actions_by_type = {}
        for action in profile.notable_actions:
            actions_by_type.setdefault(action.type, 0)
            actions_by_type[action.type] += 1

        # Get items by session
        items_by_session = {}
        for item in profile.inventory:
            if item.session_acquired:
                items_by_session.setdefault(item.session_acquired, []).append(item)

        # Get relationships by session
        relationships_by_session = {}
        for rel in profile.relationships:
            if rel.first_met:
                relationships_by_session.setdefault(rel.first_met, []).append(rel)

        # Calculate session-by-session progression
        session_progression = []
        for session in profile.sessions_appeared:
            session_stats = {
                "session_id": session,
                "actions": len(actions_by_session.get(session, [])),
                "items_acquired": len(items_by_session.get(session, [])),
                "relationships_formed": len(relationships_by_session.get(session, [])),
            }
            session_progression.append(session_stats)

        return {
            "character_name": character_name,
            "level": profile.level,
            "total_sessions": profile.total_sessions,
            "total_actions": len(profile.notable_actions),
            "actions_by_type": actions_by_type,
            "total_items": len(profile.inventory),
            "total_relationships": len(profile.relationships),
            "total_quotes": len(profile.memorable_quotes),
            "total_developments": len(profile.development_notes),
            "current_goals": len(profile.current_goals),
            "completed_goals": len(profile.completed_goals),
            "session_progression": session_progression,
            "sessions_appeared": profile.sessions_appeared,
        }

    def get_character_activity_summary(self, character_name: str) -> str:
        """
        Generate a human-readable activity summary.

        Args:
            character_name: Name of character

        Returns:
            Formatted markdown string with activity summary

        Raises:
            ValueError: If character not found
        """
        stats = self.get_progression_stats(character_name)

        summary = f"# Activity Summary: {character_name}\n\n"
        summary += f"**Level**: {stats['level']} | **Sessions**: {stats['total_sessions']}\n\n"

        summary += "## Action Distribution\n\n"
        for action_type, count in sorted(stats['actions_by_type'].items(), key=lambda x: x[1], reverse=True):
            percentage = (count / stats['total_actions'] * 100) if stats['total_actions'] > 0 else 0
            summary += f"- **{action_type.title()}**: {count} ({percentage:.1f}%)\n"

        summary += f"\n## Totals\n\n"
        summary += f"- **Actions**: {stats['total_actions']}\n"
        summary += f"- **Items**: {stats['total_items']}\n"
        summary += f"- **Relationships**: {stats['total_relationships']}\n"
        summary += f"- **Quotes**: {stats['total_quotes']}\n"
        summary += f"- **Development Notes**: {stats['total_developments']}\n"
        summary += f"- **Current Goals**: {stats['current_goals']}\n"
        summary += f"- **Completed Goals**: {stats['completed_goals']}\n"

        return summary
