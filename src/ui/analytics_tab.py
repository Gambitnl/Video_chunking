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

from pathlib import Path
from typing import Optional

import gradio as gr

from src.ui.analytics import AnalyticsActions
from src.ui.constants import StatusIndicators as SI


def create_analytics_tab(project_root: Path, ui_container: Optional[gr.Blocks] = None) -> None:
    """
    Create the Analytics tab for session analysis and comparison.

    Args:
        project_root: Root directory of the project
        ui_container: Optional Blocks instance for registering load callbacks
    """

    actions = AnalyticsActions(project_root)

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
            fn=actions.refresh_sessions,
            outputs=[session_dropdown]
        )

        analyze_btn.click(
            fn=actions.analyze_sessions,
            inputs=[session_dropdown, comparison_state, timeline_state],
            outputs=[summary_display, comparison_display, timeline_display, comparison_state, timeline_state]
        )

        export_json_btn.click(
            fn=lambda comp, timeline: actions.export_analytics("json", comp, timeline),
            inputs=[comparison_state, timeline_state],
            outputs=[export_status]
        )

        export_csv_btn.click(
            fn=lambda comp, timeline: actions.export_analytics("csv", comp, timeline),
            inputs=[comparison_state, timeline_state],
            outputs=[export_status]
        )

        export_md_btn.click(
            fn=lambda comp, timeline: actions.export_analytics("markdown", comp, timeline),
            inputs=[comparison_state, timeline_state],
            outputs=[export_status]
        )

        export_all_btn.click(
            fn=lambda comp, timeline: actions.export_analytics("all", comp, timeline),
            inputs=[comparison_state, timeline_state],
            outputs=[export_status]
        )

        # Initialize session list when the hosting Blocks finishes loading.
        if ui_container is not None:
            ui_container.load(
                fn=actions.refresh_sessions,
                outputs=[session_dropdown]
            )
