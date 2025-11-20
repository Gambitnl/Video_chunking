"""Event handlers and helpers for the Analytics tab."""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

import gradio as gr

from src.analytics import SessionAnalyzer
from src.analytics.exporter import AnalyticsExporter
from src.analytics.visualizer import AnalyticsVisualizer
from src.ui.helpers import StatusMessages

logger = logging.getLogger("DDSessionProcessor.analytics_actions")


class AnalyticsActions:
    """Encapsulate analytics tab actions to keep UI wiring thin."""

    MAX_SESSIONS = 5

    def __init__(
        self,
        project_root: Path,
        analyzer: Optional[SessionAnalyzer] = None,
        visualizer: Optional[AnalyticsVisualizer] = None,
        exporter: Optional[AnalyticsExporter] = None,
    ) -> None:
        self.project_root = Path(project_root)
        self.analyzer = analyzer or SessionAnalyzer(self.project_root)
        self.visualizer = visualizer or AnalyticsVisualizer()
        self.exporter = exporter or AnalyticsExporter()

    def refresh_sessions(self) -> gr.Dropdown:
        """Refresh the list of available sessions for selection."""
        try:
            sessions = self.analyzer.list_available_sessions()

            if not sessions:
                logger.warning("No sessions found in output directory")
                return gr.update(choices=["No sessions available"], value=[])

            logger.info("Found %s sessions", len(sessions))
            return gr.update(choices=sessions, value=[])

        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Error refreshing sessions: %s", exc, exc_info=True)
            return gr.update(choices=["Error loading sessions"], value=[])

    def analyze_sessions(
        self,
        selected_sessions: List[str],
        comparison_state,
        timeline_state,
    ) -> Tuple[str, str, str, object, object]:
        """Analyze selected sessions and generate comparison outputs."""
        validation_response = self._validate_selection(selected_sessions)
        if validation_response:
            return validation_response

        try:
            sessions = self.analyzer.load_multiple_sessions(selected_sessions)

            if not sessions:
                return (
                    StatusMessages.error(
                        "Load Failed",
                        "Could not load any of the selected sessions.",
                    ),
                    "",
                    "",
                    None,
                    None,
                )

            if len(sessions) < len(selected_sessions):
                logger.warning(
                    "Only loaded %s/%s sessions",
                    len(sessions),
                    len(selected_sessions),
                )

            comparison = self.analyzer.compare_sessions(sessions)
            timeline = self.analyzer.generate_timeline(sessions)

            summary_md = self.visualizer.generate_summary_stats(comparison)
            comparison_md = self.visualizer.generate_comparison_table(comparison)
            character_md = self.visualizer.generate_character_chart(sessions)
            timeline_md = self.visualizer.generate_ic_ooc_chart(timeline)
            insights_md = self.visualizer.generate_insights_display(comparison.insights)

            full_comparison_md = comparison_md + "\n\n---\n\n" + character_md
            timeline_insights_md = timeline_md + "\n\n---\n\n" + insights_md

            logger.info("Successfully analyzed %s sessions", len(sessions))

            return (
                summary_md,
                full_comparison_md,
                timeline_insights_md,
                comparison,
                timeline,
            )

        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Error analyzing sessions: %s", exc, exc_info=True)
            return (
                StatusMessages.error(
                    "Analysis Failed",
                    "An unexpected error occurred while analyzing sessions.",
                    "Check the application logs for more details.",
                ),
                "",
                "",
                None,
                None,
            )

    def export_analytics(self, export_format: str, comparison_state, timeline_state) -> str:
        """Export analytics data in the requested format."""
        if not comparison_state:
            return StatusMessages.warning(
                "No Data",
                "Please analyze sessions before exporting",
            )

        try:
            export_dir = self._ensure_export_dir()

            if export_format == "all":
                return self._export_all_formats(comparison_state, timeline_state, export_dir)

            filename = f"analytics_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            return self._export_single_format(export_format, filename, comparison_state, timeline_state, export_dir)

        except PermissionError:
            logger.error("Permission denied while exporting analytics", exc_info=True)
            return StatusMessages.error(
                "Permission Denied",
                "Cannot write to export directory. Check file permissions.",
            )
        except OSError as exc:
            logger.error("OS error while exporting analytics: %s", exc, exc_info=True)
            if "disk full" in str(exc).lower() or "no space" in str(exc).lower():
                return StatusMessages.error(
                    "Disk Full",
                    "Not enough disk space to save export.",
                )
            return StatusMessages.error(
                "File System Error",
                "Could not save file. Check disk space and permissions.",
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Error exporting analytics: %s", exc, exc_info=True)
            return StatusMessages.error(
                "Export Failed",
                "An unexpected error occurred while exporting.",
                "Check the application logs for more details.",
            )

    def _validate_selection(
        self, selected_sessions: List[str]
    ) -> Optional[Tuple[str, str, str, object, object]]:
        if not selected_sessions:
            return (
                StatusMessages.info(
                    "No Selection", "Please select at least one session to analyze"
                ),
                "",
                "",
                None,
                None,
            )

        if len(selected_sessions) > self.MAX_SESSIONS:
            return (
                StatusMessages.warning(
                    "Too Many Sessions",
                    f"You selected {len(selected_sessions)} sessions. Please select {self.MAX_SESSIONS} or fewer.",
                ),
                "",
                "",
                None,
                None,
            )

        return None

    def _ensure_export_dir(self) -> Path:
        export_dir = self.project_root / "exports" / "analytics"
        export_dir.mkdir(parents=True, exist_ok=True)
        return export_dir

    def _export_all_formats(self, comparison_state, timeline_state, export_dir: Path) -> str:
        results = self.exporter.export_full_report(
            comparison_state,
            timeline_state,
            export_dir,
        )

        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)

        if success_count == total_count:
            return StatusMessages.success(
                "Export Complete",
                f"Analytics exported to {export_dir}",
                "Exported: JSON, CSV, Markdown",
            )

        failed = [fmt for fmt, success in results.items() if not success]
        return StatusMessages.warning(
            "Partial Export",
            f"Exported {success_count}/{total_count} formats",
            f"Failed: {', '.join(failed)}",
        )

    def _export_single_format(
        self,
        export_format: str,
        filename: str,
        comparison_state,
        timeline_state,
        export_dir: Path,
    ) -> str:
        if export_format == "json":
            success = self.exporter.export_to_json(
                comparison_state,
                export_dir / f"{filename}.json",
            )
        elif export_format == "csv":
            success = self.exporter.export_to_csv(
                comparison_state,
                export_dir / f"{filename}.csv",
            )
        elif export_format == "markdown":
            success = self.exporter.export_to_markdown(
                comparison_state,
                timeline_state,
                export_dir / f"{filename}.md",
            )
        else:
            return StatusMessages.error(
                "Invalid Format",
                f"Unknown export format: {export_format}",
            )

        if success:
            return StatusMessages.success(
                "Export Complete",
                f"Analytics exported to {export_dir}",
                f"Format: {export_format.upper()}",
            )

        return StatusMessages.error(
            "Export Failed",
            f"Could not export to {export_format}",
        )
