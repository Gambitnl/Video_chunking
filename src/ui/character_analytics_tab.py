"""
Character Analytics Tab - Gradio UI for character analytics features.

Provides user interface for timeline view, party analytics, and data validation.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import logging

import gradio as gr

from src.character_profile import CharacterProfileManager
from src.analytics import (
    CharacterAnalytics,
    TimelineGenerator,
    PartyAnalyzer,
    DataValidator,
)
from src.ui.helpers import StatusMessages
from src.ui.constants import StatusIndicators as SI
from src.party_config import CampaignManager

logger = logging.getLogger(__name__)


def create_character_analytics_tab(
    profile_manager: CharacterProfileManager,
    campaign_manager: CampaignManager,
    project_root: Path
) -> None:
    """
    Create the Character Analytics tab.

    Args:
        profile_manager: Character profile manager instance
        campaign_manager: Campaign manager instance
        project_root: Project root directory path
    """
    # Initialize analytics engines
    analytics = CharacterAnalytics(profile_manager)
    timeline_gen = TimelineGenerator(analytics)
    party_analyzer = PartyAnalyzer(profile_manager)
    validator = DataValidator(profile_manager)

    def get_campaign_choices() -> List[str]:
        """Get list of campaign names for dropdown."""
        names = campaign_manager.get_campaign_names()
        if not names:
            return ["All Campaigns"]
        return ["All Campaigns"] + list(names.values())

    def get_character_choices(campaign_name: str = "All Campaigns") -> List[str]:
        """Get list of character names for dropdown, filtered by campaign."""
        if campaign_name == "All Campaigns":
            return profile_manager.list_characters()

        # Find campaign_id from name
        campaign_id = None
        for cid, display_name in campaign_manager.get_campaign_names().items():
            if display_name == campaign_name:
                campaign_id = cid
                break

        if campaign_id:
            return profile_manager.list_characters(campaign_id=campaign_id)
        return []

    # ========== Timeline View Functions ==========

    def generate_timeline_ui(
        character_name: str,
        campaign_name: str,
        event_types: List[str],
        include_metadata: bool
    ) -> Tuple[str, str]:
        """Generate character timeline."""
        try:
            if not character_name:
                return "", StatusMessages.warning("Input Required", "Please select a character")

            # Convert event type checkboxes to list
            selected_types = event_types if event_types else None

            # Generate timeline
            timeline_md = timeline_gen.generate_timeline_markdown(
                character_name,
                event_types=selected_types,
                include_metadata=include_metadata
            )

            success_msg = StatusMessages.success(
                "Timeline Generated",
                f"Generated timeline for {character_name}"
            )

            return timeline_md, success_msg

        except Exception as e:
            logger.error(f"Error generating timeline: {e}", exc_info=True)
            error_msg = StatusMessages.error(
                "Timeline Generation Failed",
                "Unable to generate timeline",
                f"Error: {type(e).__name__}: {str(e)}"
            )
            return "", error_msg

    def export_timeline_ui(
        character_name: str,
        format: str
    ) -> Tuple[str, str]:
        """Export timeline to file."""
        try:
            if not character_name:
                return None, StatusMessages.warning("Input Required", "Please select a character")

            # Create output directory
            output_dir = project_root / "output" / "analytics"
            output_dir.mkdir(exist_ok=True, parents=True)

            # Generate filename
            from src.formatter import sanitize_filename
            safe_name = sanitize_filename(character_name)

            if format == "JSON":
                output_path = output_dir / f"{safe_name}_timeline.json"
                timeline_gen.export_timeline_json(character_name, output_path)
            elif format == "HTML":
                output_path = output_dir / f"{safe_name}_timeline.html"
                html_content = timeline_gen.generate_timeline_html(character_name)
                output_path.write_text(html_content, encoding="utf-8")
            else:  # Markdown
                output_path = output_dir / f"{safe_name}_timeline.md"
                md_content = timeline_gen.generate_timeline_markdown(character_name)
                output_path.write_text(md_content, encoding="utf-8")

            success_msg = StatusMessages.success(
                "Export Successful",
                f"Timeline exported to {output_path.name}"
            )

            return str(output_path), success_msg

        except Exception as e:
            logger.error(f"Error exporting timeline: {e}", exc_info=True)
            error_msg = StatusMessages.error(
                "Export Failed",
                "Unable to export timeline",
                f"Error: {type(e).__name__}"
            )
            return None, error_msg

    # ========== Party Analytics Functions ==========

    def generate_party_analytics_ui(campaign_name: str) -> Tuple[str, str]:
        """Generate party analytics dashboard."""
        try:
            # Find campaign_id from name
            campaign_id = None
            if campaign_name != "All Campaigns":
                campaigns = campaign_manager.list_campaigns()
                for c in campaigns:
                    if c["name"] == campaign_name:
                        campaign_id = c["id"]
                        break

            # Generate party dashboard
            dashboard_md = party_analyzer.generate_party_dashboard_markdown(campaign_id)

            success_msg = StatusMessages.success(
                "Analytics Generated",
                f"Generated party analytics for {campaign_name}"
            )

            return dashboard_md, success_msg

        except Exception as e:
            logger.error(f"Error generating party analytics: {e}", exc_info=True)
            error_msg = StatusMessages.error(
                "Analytics Generation Failed",
                "Unable to generate party analytics",
                f"Error: {type(e).__name__}: {str(e)}"
            )
            return "", error_msg

    # ========== Data Validation Functions ==========

    def validate_campaign_ui(campaign_name: str) -> Tuple[str, str]:
        """Validate campaign data quality."""
        try:
            # Find campaign_id from name
            campaign_id = None
            if campaign_name != "All Campaigns":
                campaigns = campaign_manager.list_campaigns()
                for c in campaigns:
                    if c["name"] == campaign_name:
                        campaign_id = c["id"]
                        break

            # Validate campaign
            report = validator.validate_campaign(campaign_id)

            # Generate report markdown
            report_md = validator.generate_report(report.warnings, campaign_id)

            # Create status message
            if report.total_warnings == 0:
                status_msg = StatusMessages.success(
                    "Validation Complete",
                    f"No issues found! Validated {report.characters_validated} characters."
                )
            else:
                errors = sum(1 for w in report.warnings if w.severity == "error")
                warnings = sum(1 for w in report.warnings if w.severity == "warning")
                status_msg = StatusMessages.warning(
                    "Validation Complete",
                    f"Found {report.total_warnings} issues ({errors} errors, {warnings} warnings)"
                )

            return report_md, status_msg

        except Exception as e:
            logger.error(f"Error validating campaign: {e}", exc_info=True)
            error_msg = StatusMessages.error(
                "Validation Failed",
                "Unable to validate campaign",
                f"Error: {type(e).__name__}: {str(e)}"
            )
            return "", error_msg

    # ========== UI Layout ==========

    with gr.Tab("Character Analytics"):
        gr.Markdown("""
        ### [CHART] Character Analytics & Insights

        Analyze character progression, party dynamics, and data quality.
        """)

        with gr.Tabs():
            # ========== Timeline View Tab ==========
            with gr.Tab("Timeline View"):
                gr.Markdown("""
                #### Character Timeline

                View chronological timeline of character events across sessions.
                Filter by event type and export in multiple formats.
                """)

                with gr.Row():
                    with gr.Column(scale=1):
                        timeline_campaign = gr.Dropdown(
                            label="Campaign",
                            choices=get_campaign_choices(),
                            value="All Campaigns",
                            interactive=True
                        )
                        timeline_character = gr.Dropdown(
                            label="Character",
                            choices=get_character_choices(),
                            interactive=True
                        )

                        timeline_event_types = gr.CheckboxGroup(
                            label="Event Types",
                            choices=["action", "quote", "development", "item", "relationship", "goal"],
                            value=["action", "quote", "development", "item", "relationship"],
                            interactive=True
                        )

                        timeline_metadata = gr.Checkbox(
                            label="Include Metadata",
                            value=False
                        )

                        timeline_btn = gr.Button(
                            f"{SI.ACTION_PROCESS} Generate Timeline",
                            variant="primary",
                            size="lg"
                        )

                        gr.Markdown("---")

                        timeline_export_format = gr.Radio(
                            label="Export Format",
                            choices=["Markdown", "HTML", "JSON"],
                            value="Markdown"
                        )

                        timeline_export_btn = gr.Button(
                            f"{SI.ACTION_DOWNLOAD} Export Timeline",
                            size="sm"
                        )

                        timeline_export_path = gr.Textbox(
                            label="Export Path",
                            interactive=False
                        )

                    with gr.Column(scale=2):
                        timeline_output = gr.Markdown(
                            label="Timeline",
                            value=StatusMessages.info(
                                "Character Timeline",
                                "Select a character and click Generate Timeline"
                            )
                        )

                timeline_status = gr.Markdown(
                    value=StatusMessages.info("Ready", "Select a character to begin")
                )

                # Event handlers
                timeline_campaign.change(
                    fn=lambda campaign: gr.update(
                        choices=get_character_choices(campaign),
                        value=None
                    ),
                    inputs=[timeline_campaign],
                    outputs=[timeline_character]
                )

                timeline_btn.click(
                    fn=generate_timeline_ui,
                    inputs=[timeline_character, timeline_campaign, timeline_event_types, timeline_metadata],
                    outputs=[timeline_output, timeline_status]
                )

                timeline_export_btn.click(
                    fn=export_timeline_ui,
                    inputs=[timeline_character, timeline_export_format],
                    outputs=[timeline_export_path, timeline_status]
                )

            # ========== Party Analytics Tab ==========
            with gr.Tab("Party Analytics"):
                gr.Markdown("""
                #### Party Dashboard

                Analyze party composition, shared relationships, item distribution, and action balance.
                """)

                with gr.Row():
                    with gr.Column(scale=1):
                        party_campaign = gr.Dropdown(
                            label="Campaign",
                            choices=get_campaign_choices(),
                            value="All Campaigns",
                            interactive=True
                        )

                        party_btn = gr.Button(
                            f"{SI.ACTION_PROCESS} Generate Analytics",
                            variant="primary",
                            size="lg"
                        )

                    with gr.Column(scale=2):
                        party_output = gr.Markdown(
                            label="Party Analytics",
                            value=StatusMessages.info(
                                "Party Analytics",
                                "Select a campaign and click Generate Analytics"
                            )
                        )

                party_status = gr.Markdown(
                    value=StatusMessages.info("Ready", "Select a campaign to begin")
                )

                # Event handlers
                party_btn.click(
                    fn=generate_party_analytics_ui,
                    inputs=[party_campaign],
                    outputs=[party_output, party_status]
                )

            # ========== Data Validation Tab ==========
            with gr.Tab("Data Validation"):
                gr.Markdown("""
                #### Data Quality Validation

                Check for data quality issues including missing actions, duplicate items,
                invalid session references, and inconsistencies.
                """)

                with gr.Row():
                    with gr.Column(scale=1):
                        validation_campaign = gr.Dropdown(
                            label="Campaign",
                            choices=get_campaign_choices(),
                            value="All Campaigns",
                            interactive=True
                        )

                        validation_btn = gr.Button(
                            f"{SI.ACTION_PROCESS} Run Validation",
                            variant="primary",
                            size="lg"
                        )

                    with gr.Column(scale=2):
                        validation_output = gr.Markdown(
                            label="Validation Report",
                            value=StatusMessages.info(
                                "Data Validation",
                                "Select a campaign and click Run Validation"
                            )
                        )

                validation_status = gr.Markdown(
                    value=StatusMessages.info("Ready", "Select a campaign to begin")
                )

                # Event handlers
                validation_btn.click(
                    fn=validate_campaign_ui,
                    inputs=[validation_campaign],
                    outputs=[validation_output, validation_status]
                )
