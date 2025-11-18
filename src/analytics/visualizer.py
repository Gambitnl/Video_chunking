"""
Analytics visualizer for generating charts and tables.

This module provides visualization capabilities for session analytics:
- Markdown-based charts (ASCII art, tables)
- Session comparison tables
- Character participation visualizations
- IC/OOC timeline charts
"""
from __future__ import annotations

import logging
from typing import Dict, List

from .data_models import SessionMetrics, CharacterStats, ComparisonResult, TimelineData
from src.ui.constants import StatusIndicators as SI

logger = logging.getLogger("DDSessionProcessor.analytics_visualizer")


class AnalyticsVisualizer:
    """
    Visualizer for analytics data.

    This class generates Markdown-formatted visualizations including:
    - Comparison tables
    - Character participation charts
    - IC/OOC timeline charts
    - Speaking time distribution

    All visualizations use Markdown and ASCII art for universal compatibility.
    """

    def __init__(self):
        """Initialize the visualizer."""
        pass

    def generate_comparison_table(self, comparison: ComparisonResult) -> str:
        """
        Generate a comparison table for multiple sessions.

        Args:
            comparison: ComparisonResult object

        Returns:
            Markdown-formatted comparison table
        """
        if not comparison.sessions:
            return f"{SI.INFO} No sessions to compare"

        # Build table header
        md = "### Session Comparison\n\n"
        md += "| Metric | " + " | ".join(s.session_name for s in comparison.sessions) + " |\n"
        md += "|" + "---|" * (len(comparison.sessions) + 1) + "\n"

        # Duration row
        md += "| **Duration** | "
        md += " | ".join(s.duration_formatted() for s in comparison.sessions)
        md += " |\n"

        # Message count row
        md += "| **Messages** | "
        md += " | ".join(str(s.message_count) for s in comparison.sessions)
        md += " |\n"

        # Speaker count row
        md += "| **Speakers** | "
        md += " | ".join(str(s.speaker_count) for s in comparison.sessions)
        md += " |\n"

        # IC percentage row
        md += "| **IC %** | "
        md += " | ".join(f"{s.ic_percentage():.1f}%" for s in comparison.sessions)
        md += " |\n"

        # OOC percentage row
        md += "| **OOC %** | "
        md += " | ".join(f"{s.ooc_percentage():.1f}%" for s in comparison.sessions)
        md += " |\n"

        # IC duration row
        md += "| **IC Time** | "
        md += " | ".join(self._format_duration(s.ic_duration) for s in comparison.sessions)
        md += " |\n"

        # OOC duration row
        md += "| **OOC Time** | "
        md += " | ".join(self._format_duration(s.ooc_duration) for s in comparison.sessions)
        md += " |\n"

        return md

    def generate_character_chart(self, sessions: List[SessionMetrics]) -> str:
        """
        Generate a character participation chart across sessions.

        Args:
            sessions: List of SessionMetrics

        Returns:
            Markdown-formatted character chart
        """
        if not sessions:
            return f"{SI.INFO} No sessions provided"

        # Collect all characters across all sessions
        all_characters: Dict[str, float] = {}

        for session in sessions:
            for char_name, char_stats in session.character_stats.items():
                if char_name not in all_characters:
                    all_characters[char_name] = 0.0
                all_characters[char_name] += char_stats.speaking_duration

        if not all_characters:
            return f"{SI.INFO} No character data available"

        # Sort by total speaking time
        sorted_chars = sorted(
            all_characters.items(),
            key=lambda x: x[1],
            reverse=True
        )

        # Generate chart
        md = "### Character Participation\n\n"
        md += "Total speaking time across all sessions:\n\n"

        # Find max duration for scaling
        max_duration = max(duration for _, duration in sorted_chars) if sorted_chars else 1.0
        bar_width = 40

        for char_name, total_duration in sorted_chars:
            # Calculate bar length (with minimum of 1 char if duration > 0)
            if max_duration > 0:
                bar_length = max(1, int((total_duration / max_duration) * bar_width))
            else:
                bar_length = 0

            bar = "#" * bar_length

            # Format duration
            duration_str = self._format_duration(total_duration)

            md += f"**{char_name}**: {bar} {duration_str}\n"

        return md

    def generate_character_stats_table(self, session: SessionMetrics) -> str:
        """
        Generate a detailed character statistics table for a session.

        Args:
            session: SessionMetrics object

        Returns:
            Markdown-formatted statistics table
        """
        if not session.character_stats:
            return f"{SI.INFO} No character statistics available"

        # Sort characters by speaking time
        sorted_chars = sorted(
            session.character_stats.items(),
            key=lambda x: x[1].speaking_duration,
            reverse=True
        )

        # Build table
        md = f"### Character Statistics - {session.session_name}\n\n"
        md += "| Character | Messages | Words | Speaking Time | IC% | OOC% | Avg Length |\n"
        md += "|-----------|----------|-------|---------------|-----|------|------------|\n"

        for char_name, stats in sorted_chars:
            md += (
                f"| **{char_name}** "
                f"| {stats.message_count} "
                f"| {stats.word_count} "
                f"| {self._format_duration(stats.speaking_duration)} "
                f"| {stats.ic_percentage():.1f}% "
                f"| {stats.ooc_percentage():.1f}% "
                f"| {stats.avg_message_length:.1f} "
                f"|\n"
            )

        return md

    def generate_ic_ooc_chart(self, timeline: TimelineData) -> str:
        """
        Generate IC/OOC timeline chart.

        Args:
            timeline: TimelineData object

        Returns:
            Markdown-formatted timeline chart
        """
        if not timeline.ic_ooc_ratios:
            return f"{SI.INFO} No timeline data available"

        md = "### IC/OOC Timeline\n\n"
        md += "IC percentage progression across sessions:\n\n"

        # Generate chart
        bar_width = 50

        for session_id, ic_pct, ooc_pct in timeline.ic_ooc_ratios:
            # Get session name
            session_name = session_id
            for session in timeline.sessions:
                if session.session_id == session_id:
                    session_name = session.session_name
                    break

            # Calculate bar lengths
            ic_bar_length = int((ic_pct / 100) * bar_width)
            ooc_bar_length = int((ooc_pct / 100) * bar_width)

            ic_bar = "=" * ic_bar_length
            ooc_bar = "-" * ooc_bar_length

            md += f"**{session_name}**\n"
            md += f"  IC  ({ic_pct:.1f}%): {ic_bar}\n"
            md += f"  OOC ({ooc_pct:.1f}%): {ooc_bar}\n\n"

        return md

    def generate_speaking_distribution(self, session: SessionMetrics) -> str:
        """
        Generate speaking time distribution for a single session.

        Args:
            session: SessionMetrics object

        Returns:
            Markdown-formatted distribution chart
        """
        if not session.character_stats:
            return f"{SI.INFO} No speaking data available"

        md = f"### Speaking Time Distribution - {session.session_name}\n\n"

        # Calculate percentages
        total_duration = sum(
            stats.speaking_duration
            for stats in session.character_stats.values()
        )

        if total_duration == 0:
            return f"{SI.INFO} No speaking time recorded"

        # Sort by speaking time
        sorted_chars = sorted(
            session.character_stats.items(),
            key=lambda x: x[1].speaking_duration,
            reverse=True
        )

        # Generate pie-chart-like visualization
        bar_width = 50

        for char_name, stats in sorted_chars:
            percentage = (stats.speaking_duration / total_duration) * 100
            bar_length = int((percentage / 100) * bar_width)
            bar = "#" * bar_length

            duration_str = self._format_duration(stats.speaking_duration)

            md += f"**{char_name}** ({percentage:.1f}%): {bar} {duration_str}\n"

        return md

    def generate_insights_display(self, insights: List[str]) -> str:
        """
        Format insights for display.

        Args:
            insights: List of insight strings

        Returns:
            Markdown-formatted insights
        """
        if not insights:
            return f"{SI.INFO} No insights generated"

        md = "### {SI.LIGHTBULB} Auto-Generated Insights\n\n"

        for i, insight in enumerate(insights, 1):
            md += f"{i}. {insight}\n"

        return md

    def generate_summary_stats(self, comparison: ComparisonResult) -> str:
        """
        Generate summary statistics for comparison.

        Args:
            comparison: ComparisonResult object

        Returns:
            Markdown-formatted summary
        """
        if not comparison.sessions:
            return f"{SI.INFO} No sessions to summarize"

        md = "### Summary Statistics\n\n"

        # Calculate averages
        avg_duration = comparison.average_duration()
        avg_ic = comparison.average_ic_percentage()

        # Find extremes
        longest = comparison.get_longest_session()
        shortest = comparison.get_shortest_session()
        most_ic = comparison.get_most_ic_session()
        most_ooc = comparison.get_most_ooc_session()

        md += f"**Sessions Analyzed**: {comparison.session_count()}\n\n"
        md += f"**Average Duration**: {self._format_duration(avg_duration)}\n\n"
        md += f"**Average IC%**: {avg_ic:.1f}%\n\n"

        if longest:
            md += f"**Longest Session**: {longest.session_name} ({longest.duration_formatted()})\n\n"

        if shortest:
            md += f"**Shortest Session**: {shortest.session_name} ({shortest.duration_formatted()})\n\n"

        if most_ic:
            md += f"**Most IC**: {most_ic.session_name} ({most_ic.ic_percentage():.1f}%)\n\n"

        if most_ooc:
            md += f"**Most OOC**: {most_ooc.session_name} ({most_ooc.ooc_percentage():.1f}%)\n\n"

        return md

    def generate_full_report(self, comparison: ComparisonResult, timeline: TimelineData) -> str:
        """
        Generate a comprehensive analytics report.

        Args:
            comparison: ComparisonResult object
            timeline: TimelineData object

        Returns:
            Markdown-formatted full report
        """
        md = f"# {SI.CHART} Session Analytics Report\n\n"
        md += f"**Generated**: {comparison.comparison_date.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        md += "---\n\n"

        # Summary statistics
        md += self.generate_summary_stats(comparison)
        md += "\n---\n\n"

        # Comparison table
        md += self.generate_comparison_table(comparison)
        md += "\n---\n\n"

        # Character participation
        md += self.generate_character_chart(comparison.sessions)
        md += "\n---\n\n"

        # IC/OOC timeline
        md += self.generate_ic_ooc_chart(timeline)
        md += "\n---\n\n"

        # Insights
        md += self.generate_insights_display(comparison.insights)
        md += "\n---\n\n"

        # Individual session details
        md += "### Individual Session Details\n\n"
        for session in comparison.sessions:
            md += f"#### {session.session_name}\n\n"
            md += self.generate_character_stats_table(session)
            md += "\n"

        return md

    @staticmethod
    def _format_duration(seconds: float) -> str:
        """
        Format duration in seconds as HH:MM:SS or MM:SS.

        Args:
            seconds: Duration in seconds

        Returns:
            Formatted duration string
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"
