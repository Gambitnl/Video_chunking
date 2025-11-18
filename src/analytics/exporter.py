"""
Analytics exporter for saving analytics data to various formats.

This module provides export functionality for analytics data:
- JSON export (structured data)
- CSV export (tabular data)
- Markdown export (formatted reports)
"""
from __future__ import annotations

import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from .data_models import SessionMetrics, CharacterStats, ComparisonResult, TimelineData
from .visualizer import AnalyticsVisualizer

logger = logging.getLogger("DDSessionProcessor.analytics_exporter")


class AnalyticsExporter:
    """
    Exporter for analytics data.

    This class provides methods to export analytics data to:
    - JSON (structured data with full details)
    - CSV (tabular comparison data)
    - Markdown (formatted report)

    Example:
        exporter = AnalyticsExporter()
        exporter.export_to_json(comparison, output_dir / "analytics.json")
        exporter.export_to_csv(comparison, output_dir / "analytics.csv")
        exporter.export_to_markdown(comparison, timeline, output_dir / "report.md")
    """

    def __init__(self):
        """Initialize the exporter."""
        self.visualizer = AnalyticsVisualizer()

    def export_to_json(
        self,
        data: Any,
        output_path: Path
    ) -> bool:
        """
        Export data to JSON format.

        Args:
            data: Data to export (ComparisonResult, SessionMetrics, etc.)
            output_path: Path to output JSON file

        Returns:
            True if export successful, False otherwise

        Raises:
            TypeError: If data cannot be serialized to JSON
        """
        logger.info(f"Exporting analytics data to JSON: {output_path}")

        try:
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Convert dataclasses to dict
            json_data = self._to_dict(data)

            # Add export metadata
            export_metadata = {
                "export_timestamp": datetime.now().isoformat(),
                "export_version": "1.0",
                "data": json_data
            }

            # Write JSON file
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_metadata, f, indent=2, ensure_ascii=False)

            logger.info(f"Successfully exported to JSON: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Error exporting to JSON: {e}", exc_info=True)
            return False

    def export_to_csv(
        self,
        comparison: ComparisonResult,
        output_path: Path
    ) -> bool:
        """
        Export comparison data to CSV format.

        Creates a CSV file with one row per session, showing key metrics.

        Args:
            comparison: ComparisonResult to export
            output_path: Path to output CSV file

        Returns:
            True if export successful, False otherwise
        """
        logger.info(f"Exporting comparison data to CSV: {output_path}")

        try:
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Define CSV headers
            headers = [
                "Session ID",
                "Session Name",
                "Duration (seconds)",
                "Duration (formatted)",
                "Messages",
                "Speakers",
                "IC Messages",
                "OOC Messages",
                "IC %",
                "OOC %",
                "IC Duration (seconds)",
                "OOC Duration (seconds)",
                "Timestamp"
            ]

            # Write CSV file
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)

                # Write header
                writer.writerow(headers)

                # Write session data
                for session in comparison.sessions:
                    row = [
                        session.session_id,
                        session.session_name,
                        session.duration,
                        session.duration_formatted(),
                        session.message_count,
                        session.speaker_count,
                        session.ic_message_count,
                        session.ooc_message_count,
                        f"{session.ic_percentage():.2f}",
                        f"{session.ooc_percentage():.2f}",
                        session.ic_duration,
                        session.ooc_duration,
                        session.timestamp.isoformat() if session.timestamp else ""
                    ]
                    writer.writerow(row)

            logger.info(f"Successfully exported to CSV: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Error exporting to CSV: {e}", exc_info=True)
            return False

    def export_character_stats_to_csv(
        self,
        session: SessionMetrics,
        output_path: Path
    ) -> bool:
        """
        Export character statistics to CSV format.

        Args:
            session: SessionMetrics with character stats
            output_path: Path to output CSV file

        Returns:
            True if export successful, False otherwise
        """
        logger.info(f"Exporting character stats to CSV: {output_path}")

        try:
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Define CSV headers
            headers = [
                "Character Name",
                "Messages",
                "Words",
                "Speaking Duration (seconds)",
                "IC Messages",
                "OOC Messages",
                "IC %",
                "OOC %",
                "Average Message Length",
                "First Appearance (seconds)",
                "Last Appearance (seconds)"
            ]

            # Write CSV file
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)

                # Write header
                writer.writerow(headers)

                # Write character data
                for char_name, char_stats in sorted(
                    session.character_stats.items(),
                    key=lambda x: x[1].speaking_duration,
                    reverse=True
                ):
                    row = [
                        char_name,
                        char_stats.message_count,
                        char_stats.word_count,
                        char_stats.speaking_duration,
                        char_stats.ic_messages,
                        char_stats.ooc_messages,
                        f"{char_stats.ic_percentage():.2f}",
                        f"{char_stats.ooc_percentage():.2f}",
                        f"{char_stats.avg_message_length:.2f}",
                        char_stats.first_appearance if char_stats.first_appearance else "",
                        char_stats.last_appearance if char_stats.last_appearance else ""
                    ]
                    writer.writerow(row)

            logger.info(f"Successfully exported character stats to CSV: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Error exporting character stats to CSV: {e}", exc_info=True)
            return False

    def export_to_markdown(
        self,
        comparison: ComparisonResult,
        timeline: TimelineData,
        output_path: Path
    ) -> bool:
        """
        Export analytics to Markdown report.

        Args:
            comparison: ComparisonResult to export
            timeline: TimelineData to include
            output_path: Path to output Markdown file

        Returns:
            True if export successful, False otherwise
        """
        logger.info(f"Exporting analytics report to Markdown: {output_path}")

        try:
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Generate report using visualizer
            report = self.visualizer.generate_full_report(comparison, timeline)

            # Write Markdown file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report)

            logger.info(f"Successfully exported to Markdown: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Error exporting to Markdown: {e}", exc_info=True)
            return False

    def export_full_report(
        self,
        comparison: ComparisonResult,
        timeline: TimelineData,
        output_dir: Path
    ) -> Dict[str, bool]:
        """
        Export full analytics report in all formats.

        Creates:
        - analytics_YYYYMMDD_HHMMSS.json
        - analytics_YYYYMMDD_HHMMSS.csv
        - analytics_YYYYMMDD_HHMMSS.md

        Args:
            comparison: ComparisonResult to export
            timeline: TimelineData to include
            output_dir: Directory to save exports

        Returns:
            Dictionary mapping format to success status
        """
        logger.info(f"Exporting full analytics report to: {output_dir}")

        # Generate timestamp for filenames
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Export to all formats
        results = {
            "json": self.export_to_json(
                comparison,
                output_dir / f"analytics_{timestamp}.json"
            ),
            "csv": self.export_to_csv(
                comparison,
                output_dir / f"analytics_{timestamp}.csv"
            ),
            "markdown": self.export_to_markdown(
                comparison,
                timeline,
                output_dir / f"analytics_{timestamp}.md"
            )
        }

        success_count = sum(1 for success in results.values() if success)
        logger.info(
            f"Exported analytics report: {success_count}/{len(results)} formats successful"
        )

        return results

    def _to_dict(self, obj: Any) -> Any:
        """
        Convert dataclasses to dict for JSON serialization.

        Args:
            obj: Object to convert

        Returns:
            Dictionary or primitive type
        """
        if hasattr(obj, '__dataclass_fields__'):
            # It's a dataclass
            result = {}
            for field_name in obj.__dataclass_fields__:
                value = getattr(obj, field_name)
                result[field_name] = self._to_dict(value)
            return result
        elif isinstance(obj, dict):
            return {k: self._to_dict(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._to_dict(item) for item in obj]
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, Path):
            return str(obj)
        else:
            return obj
