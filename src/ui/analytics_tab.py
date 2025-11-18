"""
Analytics Tab - Session analytics and comparison dashboard.

This tab provides:
- Session selection and loading
- Multi-session comparison
- Character participation tracking
- IC/OOC timeline visualization
- Export functionality (JSON, CSV, Markdown)
"""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

import gradio as gr

from src.analytics import SessionAnalyzer
from src.analytics.visualizer import AnalyticsVisualizer
from src.analytics.exporter import AnalyticsExporter
from src.ui.constants import StatusIndicators as SI
from src.ui.helpers import StatusMessages

logger = logging.getLogger("DDSessionProcessor.analytics_tab")


def create_analytics_tab(project_root: Path) -> None:
    """
    Create the Analytics tab for session analysis and comparison.

    Args:
        project_root: Root directory of the project
    """

    # Initialize analytics components
    analyzer = SessionAnalyzer(project_root)
    visualizer = AnalyticsVisualizer()
    exporter = AnalyticsExporter()

    def refresh_sessions() -> gr.Dropdown:
        """Refresh the list of available sessions."""
        try:
            sessions = analyzer.list_available_sessions()

            if not sessions:
                logger.warning("No sessions found in output directory")
                return gr.update(
                    choices=["No sessions available"],
                    value=[]
                )

            logger.info(f"Found {len(sessions)} sessions")
            return gr.update(choices=sessions, value=[])

        except Exception as e:
            logger.error(f"Error refreshing sessions: {e}", exc_info=True)
            return gr.update(
                choices=["Error loading sessions"],
                value=[]
            )

    def analyze_sessions(
        selected_sessions: List[str],
        comparison_state,
        timeline_state
    ) -> Tuple[str, str, str, object, object]:
        """
        Analyze selected sessions and generate comparison.

        Args:
            selected_sessions: List of session IDs to analyze
            comparison_state: Current comparison state
            timeline_state: Current timeline state

        Returns:
            Tuple of (summary_md, comparison_md, insights_md, new_comparison, new_timeline)
        """
        if not selected_sessions:
            return (
                StatusMessages.info("No Selection", "Please select at least one session to analyze"),
                "",
                "",
                None,
                None
            )

        if len(selected_sessions) > 5:
            return (
                StatusMessages.warning(
                    "Too Many Sessions",
                    f"You selected {len(selected_sessions)} sessions. Please select 5 or fewer."
                ),
                "",
                "",
                None,
                None
            )

        try:
            logger.info(f"Analyzing {len(selected_sessions)} sessions")

            # Load sessions
            sessions = analyzer.load_multiple_sessions(selected_sessions)

            if not sessions:
                return (
                    StatusMessages.error(
                        "Load Failed",
                        "Could not load any of the selected sessions."
                    ),
                    "",
                    "",
                    None,
                    None
                )

            if len(sessions) < len(selected_sessions):
                logger.warning(
                    f"Only loaded {len(sessions)}/{len(selected_sessions)} sessions"
                )

            # Generate comparison
            comparison = analyzer.compare_sessions(sessions)
            timeline = analyzer.generate_timeline(sessions)

            # Generate visualizations
            summary_md = visualizer.generate_summary_stats(comparison)
            comparison_md = visualizer.generate_comparison_table(comparison)
            character_md = visualizer.generate_character_chart(sessions)
            timeline_md = visualizer.generate_ic_ooc_chart(timeline)
            insights_md = visualizer.generate_insights_display(comparison.insights)

            # Combine comparison view
            full_comparison_md = comparison_md + "\n\n---\n\n" + character_md

            # Combine timeline and insights
            timeline_insights_md = timeline_md + "\n\n---\n\n" + insights_md

            logger.info(f"Successfully analyzed {len(sessions)} sessions")

            return (
                summary_md,
                full_comparison_md,
                timeline_insights_md,
                comparison,
                timeline
            )

        except Exception as e:
            logger.error(f"Error analyzing sessions: {e}", exc_info=True)
            return (
                StatusMessages.error(
                    "Analysis Failed",
                    "An unexpected error occurred while analyzing sessions.",
                    "Check the application logs for more details."
                ),
                "",
                "",
                None,
                None
            )

    def export_analytics(export_format: str, comparison_state, timeline_state) -> str:
        """
        Export analytics data to selected format.

        Args:
            export_format: Format to export ("json", "csv", "markdown", "all")
            comparison_state: Current comparison state
            timeline_state: Current timeline state

        Returns:
            Status message
        """
        if not comparison_state:
            return StatusMessages.warning(
                "No Data",
                "Please analyze sessions before exporting"
            )

        try:
            # Create exports directory
            export_dir = project_root / "exports" / "analytics"
            export_dir.mkdir(parents=True, exist_ok=True)

            if export_format == "all":
                # Export all formats
                results = exporter.export_full_report(
                    comparison_state,
                    timeline_state,
                    export_dir
                )

                success_count = sum(1 for success in results.values() if success)
                total_count = len(results)

                if success_count == total_count:
                    return StatusMessages.success(
                        "Export Complete",
                        f"Analytics exported to {export_dir}",
                        f"Exported: JSON, CSV, Markdown"
                    )
                else:
                    failed = [fmt for fmt, success in results.items() if not success]
                    return StatusMessages.warning(
                        "Partial Export",
                        f"Exported {success_count}/{total_count} formats",
                        f"Failed: {', '.join(failed)}"
                    )

            elif export_format == "json":
                filename = f"analytics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                success = exporter.export_to_json(
                    comparison_state,
                    export_dir / filename
                )

            elif export_format == "csv":
                filename = f"analytics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                success = exporter.export_to_csv(
                    comparison_state,
                    export_dir / filename
                )

            elif export_format == "markdown":
                filename = f"analytics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
                success = exporter.export_to_markdown(
                    comparison_state,
                    timeline_state,
                    export_dir / filename
                )

            else:
                return StatusMessages.error(
                    "Invalid Format",
                    f"Unknown export format: {export_format}"
                )

            if success:
                return StatusMessages.success(
                    "Export Complete",
                    f"Analytics exported to {export_dir}",
                    f"Format: {export_format.upper()}"
                )
            else:
                return StatusMessages.error(
                    "Export Failed",
                    f"Could not export to {export_format}"
                )

        except PermissionError:
            logger.error("Permission denied while exporting analytics", exc_info=True)
            return StatusMessages.error(
                "Permission Denied",
                "Cannot write to export directory. Check file permissions."
            )
        except OSError as e:
            logger.error(f"OS error while exporting analytics: {e}", exc_info=True)
            if "disk full" in str(e).lower() or "no space" in str(e).lower():
                return StatusMessages.error(
                    "Disk Full",
                    "Not enough disk space to save export."
                )
            else:
                return StatusMessages.error(
                    "File System Error",
                    "Could not save file. Check disk space and permissions."
                )
        except Exception as e:
            logger.error(f"Error exporting analytics: {e}", exc_info=True)
            return StatusMessages.error(
                "Export Failed",
                "An unexpected error occurred while exporting.",
                "Check the application logs for more details."
            )

    # Create the UI
    with gr.Tab("Analytics"):
        # State variables for thread-safe storage
        comparison_state = gr.State(value=None)
        timeline_state = gr.State(value=None)

        gr.Markdown(f"""
        ### {SI.CHART} Session Analytics Dashboard

        Analyze and compare D&D sessions to understand:
        - Session duration and participation patterns
        - Character speaking time and engagement
        - IC/OOC balance over time
        - Campaign progression and trends

        **How to use:**
        1. Click "Refresh Sessions" to load available sessions
        2. Select 1-5 sessions to compare
        3. Click "Analyze" to generate metrics
        4. Export results in your preferred format
        """)

        # Session selection section
        with gr.Accordion(f"{SI.ACTION_SELECT} Session Selection", open=True):
            with gr.Row():
                session_dropdown = gr.Dropdown(
                    label="Select Sessions (1-5)",
                    choices=["No sessions available"],
                    multiselect=True,
                    value=[],
                    interactive=True,
                    info="Select up to 5 sessions to analyze"
                )
                refresh_btn = gr.Button(
                    f"{SI.ACTION_REFRESH} Refresh",
                    size="sm"
                )

            with gr.Row():
                analyze_btn = gr.Button(
                    f"{SI.ACTION_SEARCH} Analyze Sessions",
                    variant="primary",
                    size="lg"
                )

        # Results section
        with gr.Accordion(f"{SI.INFO} Summary", open=True):
            summary_display = gr.Markdown(
                f"{SI.INFO} Select and analyze sessions to see summary statistics"
            )

        with gr.Accordion(f"{SI.CHART} Comparison View", open=False):
            comparison_display = gr.Markdown(
                f"{SI.INFO} Analysis results will appear here"
            )

        with gr.Accordion(f"{SI.CHART} Timeline & Insights", open=False):
            timeline_display = gr.Markdown(
                f"{SI.INFO} Timeline and insights will appear here"
            )

        # Export section
        with gr.Accordion(f"{SI.ACTION_SAVE} Export Analytics", open=False):
            gr.Markdown("""
            Export analytics data in various formats:
            - **JSON**: Structured data for further processing
            - **CSV**: Tabular data for spreadsheets
            - **Markdown**: Formatted report for documentation
            - **All**: Export all formats at once
            """)

            with gr.Row():
                export_json_btn = gr.Button(
                    f"{SI.ACTION_SAVE} Export JSON",
                    size="sm"
                )
                export_csv_btn = gr.Button(
                    f"{SI.ACTION_SAVE} Export CSV",
                    size="sm"
                )
                export_md_btn = gr.Button(
                    f"{SI.ACTION_SAVE} Export Markdown",
                    size="sm"
                )
                export_all_btn = gr.Button(
                    f"{SI.ACTION_SAVE} Export All",
                    size="sm",
                    variant="primary"
                )

            export_status = gr.Markdown(
                f"{SI.INFO} Click an export button to save analytics data"
            )

        # Event handlers
        refresh_btn.click(
            fn=refresh_sessions,
            outputs=[session_dropdown]
        )

        analyze_btn.click(
            fn=analyze_sessions,
            inputs=[session_dropdown, comparison_state, timeline_state],
            outputs=[summary_display, comparison_display, timeline_display, comparison_state, timeline_state]
        )

        export_json_btn.click(
            fn=lambda comp, timeline: export_analytics("json", comp, timeline),
            inputs=[comparison_state, timeline_state],
            outputs=[export_status]
        )

        export_csv_btn.click(
            fn=lambda comp, timeline: export_analytics("csv", comp, timeline),
            inputs=[comparison_state, timeline_state],
            outputs=[export_status]
        )

        export_md_btn.click(
            fn=lambda comp, timeline: export_analytics("markdown", comp, timeline),
            inputs=[comparison_state, timeline_state],
            outputs=[export_status]
        )

        export_all_btn.click(
            fn=lambda comp, timeline: export_analytics("all", comp, timeline),
            inputs=[comparison_state, timeline_state],
            outputs=[export_status]
        )

        # Initialize session list on tab load
        gr.on(
            triggers=[gr.Tab.select],
            fn=refresh_sessions,
            outputs=[session_dropdown]
        )
