"""
Timeline view generation for character progression.

Generates formatted timeline views showing character events in chronological order
across sessions with various export formats (Markdown, HTML, JSON).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import logging

from .character_analytics import CharacterAnalytics, CharacterTimeline, TimelineEvent

logger = logging.getLogger(__name__)


# Icon mapping for event types (ASCII-safe)
EVENT_ICONS = {
    "action": "[ACTION]",
    "quote": "[QUOTE]",
    "development": "[DEV]",
    "item": "[ITEM]",
    "relationship": "[REL]",
    "goal": "[GOAL]",
    "level": "[LEVEL]",
}

# Icon mapping for action categories
CATEGORY_ICONS = {
    "combat": "[COMBAT]",
    "social": "[SOCIAL]",
    "exploration": "[EXPLORE]",
    "magic": "[MAGIC]",
    "divine": "[DIVINE]",
    "general": "[GENERAL]",
    "weapon": "[WEAPON]",
    "armor": "[ARMOR]",
    "magical": "[MAGICAL]",
    "consumable": "[POTION]",
    "quest": "[QUEST]",
    "misc": "[MISC]",
    "ally": "[ALLY]",
    "enemy": "[ENEMY]",
    "neutral": "[NEUTRAL]",
    "mentor": "[MENTOR]",
    "friend": "[FRIEND]",
    "personality": "[TRAIT]",
    "backstory": "[STORY]",
    "goal": "[TARGET]",
}


class TimelineGenerator:
    """
    Generate formatted timeline views for character progression.

    Provides methods to generate timeline views in various formats (Markdown, HTML, JSON)
    with support for filtering and customization.

    Example:
        ```python
        from src.analytics import CharacterAnalytics, TimelineGenerator

        analytics = CharacterAnalytics(profile_manager)
        generator = TimelineGenerator(analytics)

        # Generate markdown timeline
        timeline_md = generator.generate_timeline_markdown("Thorin")

        # Export to JSON
        generator.export_timeline_json("Thorin", Path("thorin_timeline.json"))
        ```
    """

    def __init__(self, analytics: CharacterAnalytics):
        """
        Initialize timeline generator.

        Args:
            analytics: CharacterAnalytics instance
        """
        self.analytics = analytics
        self.logger = logging.getLogger(__name__)

    def generate_timeline_markdown(
        self,
        character_name: str,
        session_filter: Optional[List[str]] = None,
        event_types: Optional[List[str]] = None,
        include_metadata: bool = False
    ) -> str:
        """
        Generate markdown-formatted timeline view.

        Args:
            character_name: Name of character
            session_filter: Optional list of session IDs to include
            event_types: Optional list of event types to include
            include_metadata: Whether to include detailed metadata in output

        Returns:
            Markdown-formatted string with timeline

        Raises:
            ValueError: If character not found
        """
        timeline = self.analytics.generate_timeline(
            character_name,
            session_filter=session_filter,
            event_types=event_types
        )

        md = f"# Character Timeline: {timeline.character_name}\n\n"
        md += f"**Total Events**: {timeline.total_events} | **Sessions**: {len(timeline.sessions)}\n\n"
        md += "---\n\n"

        # Group events by session
        events_by_session = {}
        for event in timeline.events:
            events_by_session.setdefault(event.session_id, []).append(event)

        # Generate timeline by session
        for session_id in timeline.sessions:
            if session_id not in events_by_session:
                continue

            session_events = events_by_session[session_id]
            md += f"## Session: {session_id}\n\n"
            md += f"_Events: {len(session_events)}_\n\n"

            for event in session_events:
                # Format timestamp
                time_str = event.timestamp if event.timestamp else "??:??:??"

                # Get icons
                event_icon = EVENT_ICONS.get(event.event_type, "[?]")
                category_icon = CATEGORY_ICONS.get(event.category, "")

                # Format event line
                md += f"### {time_str} - {event_icon}"
                if category_icon:
                    md += f" {category_icon}"
                md += f" {event.event_type.title()}\n\n"

                # Description
                md += f"{event.description}\n\n"

                # Include metadata if requested
                if include_metadata and event.metadata:
                    md += "_Metadata:_ "
                    metadata_items = [f"{k}={v}" for k, v in event.metadata.items() if v]
                    md += ", ".join(metadata_items)
                    md += "\n\n"

            md += "---\n\n"

        return md

    def generate_timeline_html(
        self,
        character_name: str,
        session_filter: Optional[List[str]] = None,
        event_types: Optional[List[str]] = None
    ) -> str:
        """
        Generate HTML-formatted timeline view with styling.

        Args:
            character_name: Name of character
            session_filter: Optional list of session IDs to include
            event_types: Optional list of event types to include

        Returns:
            HTML-formatted string with inline CSS styling

        Raises:
            ValueError: If character not found
        """
        timeline = self.analytics.generate_timeline(
            character_name,
            session_filter=session_filter,
            event_types=event_types
        )

        # HTML header with CSS
        html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Character Timeline: {name}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 900px;
            margin: 40px auto;
            padding: 20px;
            background-color: #f5f5f5;
            color: #333;
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        .stats {{
            background-color: #ecf0f1;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 30px;
        }}
        .session {{
            background-color: white;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .session-header {{
            color: #2980b9;
            border-bottom: 2px solid #ecf0f1;
            padding-bottom: 10px;
            margin-bottom: 15px;
        }}
        .event {{
            margin-bottom: 20px;
            padding: 15px;
            border-left: 4px solid #3498db;
            background-color: #f8f9fa;
        }}
        .event-header {{
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 8px;
        }}
        .event-time {{
            color: #7f8c8d;
            font-size: 0.9em;
        }}
        .event-type-action {{ border-left-color: #e74c3c; }}
        .event-type-quote {{ border-left-color: #9b59b6; }}
        .event-type-development {{ border-left-color: #f39c12; }}
        .event-type-item {{ border-left-color: #16a085; }}
        .event-type-relationship {{ border-left-color: #e67e22; }}
        .event-type-goal {{ border-left-color: #27ae60; }}
    </style>
</head>
<body>
    <h1>Character Timeline: {name}</h1>
    <div class="stats">
        <strong>Total Events:</strong> {total_events} |
        <strong>Sessions:</strong> {session_count}
    </div>
""".format(
            name=timeline.character_name,
            total_events=timeline.total_events,
            session_count=len(timeline.sessions)
        )

        # Group events by session
        events_by_session = {}
        for event in timeline.events:
            events_by_session.setdefault(event.session_id, []).append(event)

        # Generate HTML for each session
        for session_id in timeline.sessions:
            if session_id not in events_by_session:
                continue

            session_events = events_by_session[session_id]
            html += f'<div class="session">\n'
            html += f'  <h2 class="session-header">Session: {session_id}</h2>\n'
            html += f'  <p><em>Events: {len(session_events)}</em></p>\n'

            for event in session_events:
                time_str = event.timestamp if event.timestamp else "??:??:??"
                event_class = f"event event-type-{event.event_type}"

                html += f'  <div class="{event_class}">\n'
                html += f'    <div class="event-header">\n'
                html += f'      <span class="event-time">{time_str}</span> - '
                html += f'{event.event_type.title()}'
                if event.category:
                    html += f' [{event.category}]'
                html += '\n    </div>\n'
                html += f'    <div>{event.description}</div>\n'
                html += '  </div>\n'

            html += '</div>\n'

        # HTML footer
        html += """
</body>
</html>
"""

        return html

    def export_timeline_json(
        self,
        character_name: str,
        output_path: Path,
        session_filter: Optional[List[str]] = None,
        event_types: Optional[List[str]] = None
    ) -> None:
        """
        Export timeline as JSON file.

        Args:
            character_name: Name of character
            output_path: Path to save JSON file
            session_filter: Optional list of session IDs to include
            event_types: Optional list of event types to include

        Raises:
            ValueError: If character not found
            IOError: If unable to write file
        """
        timeline = self.analytics.generate_timeline(
            character_name,
            session_filter=session_filter,
            event_types=event_types
        )

        # Convert timeline to dictionary
        timeline_dict = {
            "character_name": timeline.character_name,
            "total_events": timeline.total_events,
            "sessions": timeline.sessions,
            "events": [
                {
                    "session_id": event.session_id,
                    "timestamp": event.timestamp,
                    "event_type": event.event_type,
                    "description": event.description,
                    "category": event.category,
                    "metadata": event.metadata,
                }
                for event in timeline.events
            ]
        }

        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(timeline_dict, f, indent=2, ensure_ascii=False)
            self.logger.info(f"Exported timeline to {output_path}")
        except Exception as e:
            self.logger.error(f"Failed to export timeline: {e}", exc_info=True)
            raise IOError(f"Failed to export timeline: {e}")

    def generate_session_summary(
        self,
        character_name: str,
        session_id: str
    ) -> str:
        """
        Generate a summary for a single session.

        Args:
            character_name: Name of character
            session_id: Session ID to summarize

        Returns:
            Markdown-formatted session summary

        Raises:
            ValueError: If character not found or session has no events
        """
        timeline = self.analytics.generate_timeline(
            character_name,
            session_filter=[session_id]
        )

        if not timeline.events:
            raise ValueError(f"No events found for session '{session_id}'")

        md = f"# Session Summary: {session_id}\n\n"
        md += f"**Character**: {character_name}\n\n"

        # Count events by type
        event_counts = {}
        for event in timeline.events:
            event_counts.setdefault(event.event_type, 0)
            event_counts[event.event_type] += 1

        md += "## Event Breakdown\n\n"
        for event_type, count in sorted(event_counts.items()):
            md += f"- **{event_type.title()}**: {count}\n"
        md += "\n"

        # List all events chronologically
        md += "## Events\n\n"
        for event in timeline.events:
            time_str = event.timestamp if event.timestamp else "??:??:??"
            event_icon = EVENT_ICONS.get(event.event_type, "[?]")
            md += f"**{time_str}** {event_icon} - {event.description}\n\n"

        return md
