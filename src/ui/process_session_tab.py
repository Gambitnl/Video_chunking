"""Process Session tab UI construction."""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Tuple

import gradio as gr

from src.ui.constants import StatusIndicators as SI
from src.ui.helpers import (
    InfoText,
    Placeholders,
    StatusMessages,
    UIComponents,
)
from src.party_config import PartyConfigManager


def create_process_session_tab(
    *,
    refresh_campaign_names: Callable[[], Dict[str, str]],
    process_session_fn: Callable[..., Any],
    campaign_manager,
) -> Tuple[List[str], Dict[str, Any]]:
    """Build the Process Session tab and wire associated handlers.

    Args:
        refresh_campaign_names: Callback that returns campaign_id -> name mapping.
        process_session_fn: Pipeline entry function invoked when user clicks Process.
        campaign_manager: Shared CampaignManager instance for lookups.

    Returns:
        Tuple of (available party identifiers, component references for cross-tab coordination).
    """
    party_manager = PartyConfigManager()
    available_parties = ["Manual Entry"] + party_manager.list_parties()

    campaign_names = refresh_campaign_names()
    campaign_choices = ["Manual Setup"] + list(campaign_names.values())

    with gr.Tab("Process Session"):
        with gr.Row():
            with gr.Column():
                with gr.Row():
                    campaign_selector = gr.Dropdown(
                        choices=campaign_choices,
                        value="Manual Setup",
                        label="Campaign Profile",
                        info="Select your campaign to auto-fill settings, or choose Manual Setup to configure manually.",
                        scale=3,
                    )
                    create_blank_campaign_btn = UIComponents.create_action_button(
                        "New Blank Campaign",
                        variant="secondary",
                        size="sm",
                    )

                batch_mode = gr.Checkbox(
                    label="Batch Mode - Process Multiple Sessions",
                    value=False,
                    info="Upload multiple audio files to process them sequentially",
                )

                audio_input = gr.File(
                    label="Upload Audio File(s)",
                    file_types=["audio"],
                    file_count="multiple",
                )

                session_id_input = gr.Textbox(
                    label="Session ID",
                    placeholder=Placeholders.SESSION_ID,
                    info=InfoText.SESSION_ID,
                )

                party_selection_input = gr.Dropdown(
                    choices=available_parties,
                    value="default",
                    label="Party Configuration",
                    info="Select your party or choose Manual Entry to enter names manually.",
                )

                character_names_input = gr.Textbox(
                    label="Character Names (comma-separated)",
                    placeholder=Placeholders.CHARACTER_NAME,
                    info="Names of player characters (used when Manual Entry is selected).",
                )

                player_names_input = gr.Textbox(
                    label="Player Names (comma-separated)",
                    placeholder=Placeholders.PLAYER_NAME,
                    info="Names of actual players (used when Manual Entry is selected).",
                )

                num_speakers_input = gr.Slider(
                    minimum=2,
                    maximum=10,
                    value=4,
                    step=1,
                    label="Number of Speakers",
                    info="Expected number of speakers (helps accuracy)",
                )

                with gr.Row():
                    skip_diarization_input = gr.Checkbox(
                        label="Skip Speaker Diarization",
                        info="Skip identifying individual speakers. Saves time, but all transcript lines will be labeled UNKNOWN.",
                    )
                    skip_classification_input = gr.Checkbox(
                        label="Skip IC/OOC Classification",
                        info="Skip separating in-character dialogue from out-of-character banter. All segments will be marked IC.",
                    )
                    skip_snippets_input = gr.Checkbox(
                        label="Skip Audio Snippets",
                        info="Skip exporting individual WAV files. Saves disk space; transcripts will be generated.",
                    )
                    skip_knowledge_input = gr.Checkbox(
                        label="Skip Campaign Knowledge Extraction",
                        info="Skip automatic extraction of quests, NPCs, locations, and items. Recommended to leave enabled.",
                        value=False,
                    )

                with gr.Accordion("Advanced Processing Options", open=False):
                    with gr.Row():
                        enable_audit_mode_input = gr.Checkbox(
                            label="Enable Audit Mode",
                            info="Save detailed classification prompts and responses for reproducibility. Increases disk usage but enables debugging.",
                            value=False,
                        )
                        redact_prompts_input = gr.Checkbox(
                            label="Redact Prompts in Logs",
                            info="When audit mode is enabled, redact full dialogue text from audit logs (preserves privacy).",
                            value=False,
                        )

                    with gr.Row():
                        generate_scenes_input = gr.Checkbox(
                            label="Generate Scene Bundles",
                            info="Automatically detect and bundle segments into narrative scenes. Improves story extraction quality.",
                            value=True,
                        )
                        scene_summary_mode_input = gr.Dropdown(
                            choices=["template", "llm", "none"],
                            value="template",
                            label="Scene Summary Mode",
                            info="How to generate scene summaries: template (fast), llm (detailed), none (no summaries)"
                        )

                process_btn = UIComponents.create_action_button(
                    "Process Session",
                    variant="primary",
                    size="lg",
                    full_width=True,
                )

            with gr.Column():
                status_output = gr.Markdown(
                    label="Status",
                    value=StatusMessages.info(
                        "Ready",
                        "Upload an audio file and click Process Session to begin."
                    )
                )

                stats_output = gr.Markdown(
                    label="Statistics",
                    value=StatusMessages.info(
                        "Statistics",
                        "No session has been processed yet."
                    )
                )

                snippet_progress_output = gr.Markdown(
                    label="Snippet Export Progress",
                    value=StatusMessages.info(
                        "Snippet Export",
                        "Snippet export results will appear here after processing."
                    )
                )

        with gr.Row():
            with gr.Tab("Full Transcript"):
                full_output = gr.Textbox(
                    label="Full Transcript",
                    lines=20,
                    max_lines=50,
                    show_copy_button=True,
                )

            with gr.Tab("In-Character Only"):
                ic_output = gr.Textbox(
                    label="In-Character Transcript",
                    lines=20,
                    max_lines=50,
                    show_copy_button=True,
                )

            with gr.Tab("Out-of-Character Only"):
                ooc_output = gr.Textbox(
                    label="Out-of-Character Transcript",
                    lines=20,
                    max_lines=50,
                    show_copy_button=True,
                )

        def load_campaign_settings(campaign_name):
            names = refresh_campaign_names()
            if campaign_name == "Manual Setup":
                return {
                    party_selection_input: "Manual Entry",
                    num_speakers_input: 4,
                    skip_diarization_input: False,
                    skip_classification_input: False,
                    skip_snippets_input: True,
                    skip_knowledge_input: False,
                }

            campaign_id = next(
                (cid for cid, cname in names.items() if cname == campaign_name), None
            )
            if not campaign_id:
                return {}

            campaign = campaign_manager.get_campaign(campaign_id)
            if not campaign:
                return {}

            return {
                party_selection_input: campaign.party_id,
                num_speakers_input: campaign.settings.num_speakers,
                skip_diarization_input: campaign.settings.skip_diarization,
                skip_classification_input: campaign.settings.skip_classification,
                skip_snippets_input: campaign.settings.skip_snippets,
                skip_knowledge_input: campaign.settings.skip_knowledge,
            }

        def _prepare_processing_outputs():
            return (
                StatusMessages.loading("Processing session"),
                "",
                "",
                "",
                StatusMessages.info("Statistics", "Processing session..."),
                StatusMessages.info("Snippet Export", "Analyzing audio snippets..."),
            )

        def _format_statistics(stats: Dict[str, Any], knowledge: Dict[str, Any]) -> str:
            if not stats:
                return StatusMessages.info("Statistics", "No statistics available.")

            lines: List[str] = ["### Session Statistics"]

            total_duration = stats.get("total_duration_formatted")
            ic_duration = stats.get("ic_duration_formatted")
            ic_percentage = stats.get("ic_percentage")
            total_segments = stats.get("total_segments")
            ic_segments = stats.get("ic_segments")
            ooc_segments = stats.get("ooc_segments")

            if total_duration:
                lines.append(f"- Total Duration: {total_duration}")
            if ic_duration:
                duration_line = f"- IC Duration: {ic_duration}"
                if isinstance(ic_percentage, (int, float)):
                    duration_line += f" ({ic_percentage:.1f}% IC)"
                lines.append(duration_line)
            if total_segments is not None:
                lines.append(f"- Segments: {total_segments} total")
            if ic_segments is not None and ooc_segments is not None:
                lines.append(f"  - IC Segments: {ic_segments}")
                lines.append(f"  - OOC Segments: {ooc_segments}")

            speaker_dist = stats.get("speaker_distribution") or {}
            if speaker_dist:
                lines.append("- Speaker Distribution:")
                for speaker, count in speaker_dist.items():
                    lines.append(f"  - {speaker}: {count}")

            character_appearances = stats.get("character_appearances") or {}
            if character_appearances:
                lines.append("- Character Appearances:")
                for character, count in sorted(character_appearances.items(), key=lambda item: -item[1]):
                    lines.append(f"  - {character}: {count}")

            extracted = (knowledge or {}).get("extracted") or {}
            if extracted:
                lines.append("")
                lines.append("### Knowledge Extraction")
                for key, value in extracted.items():
                    label = key.replace("_", " ").title()
                    lines.append(f"- {label}: {value}")

            return "\n".join(lines)

        def _format_snippet_export(snippet: Dict[str, Any]) -> str:
            if not snippet or not snippet.get("segments_dir"):
                return StatusMessages.info("Snippet Export", "Audio snippets were not generated for this run.")

            segments_dir = str(snippet.get("segments_dir"))
            manifest = snippet.get("manifest")

            lines = [
                "### Snippet Export",
                f"{SI.SUCCESS} Audio clips saved to `{segments_dir}`.",
            ]

            if manifest:
                lines.append(f"- Manifest: `{manifest}`")

            return "\n".join(lines)

        def _render_processing_response(response: Dict[str, Any]):
            default_stats = StatusMessages.info("Statistics", "No statistics available.")
            default_snippets = StatusMessages.info("Snippet Export", "No snippet information available.")

            if not isinstance(response, dict):
                return (
                    StatusMessages.error("Processing Failed", "An unexpected response was returned by the pipeline."),
                    "",
                    "",
                    "",
                    default_stats,
                    default_snippets,
                )

            if response.get("status") != "success":
                return (
                    StatusMessages.error(
                        "Processing Failed",
                        response.get("message", "Unable to process session."),
                        response.get("details", ""),
                    ),
                    "",
                    "",
                    "",
                    default_stats,
                    default_snippets,
                )

            stats_markdown = _format_statistics(response.get("stats") or {}, response.get("knowledge") or {})
            snippet_markdown = _format_snippet_export(response.get("snippet") or {})

            return (
                StatusMessages.success("Processing Complete", response.get("message", "Session processed successfully.")),
                response.get("full", ""),
                response.get("ic", ""),
                response.get("ooc", ""),
                stats_markdown,
                snippet_markdown,
            )

        def process_session_handler(*handler_args):
            response = process_session_fn(*handler_args)
            return _render_processing_response(response)

        campaign_selector.change(
            fn=load_campaign_settings,
            inputs=[campaign_selector],
            outputs=[
                party_selection_input,
                num_speakers_input,
                skip_diarization_input,
                skip_classification_input,
                skip_snippets_input,
                skip_knowledge_input,
            ],
        )

        process_btn.click(
            fn=_prepare_processing_outputs,
            outputs=[
                status_output,
                full_output,
                ic_output,
                ooc_output,
                stats_output,
                snippet_progress_output,
            ],
            queue=True,
        ).then(
            fn=process_session_handler,
            inputs=[
                audio_input,
                session_id_input,
                party_selection_input,
                character_names_input,
                player_names_input,
                num_speakers_input,
                skip_diarization_input,
                skip_classification_input,
                skip_snippets_input,
                skip_knowledge_input,
                enable_audit_mode_input,
                redact_prompts_input,
                generate_scenes_input,
                scene_summary_mode_input,
            ],
            outputs=[
                status_output,
                full_output,
                ic_output,
                ooc_output,
                stats_output,
                snippet_progress_output,
            ],
            queue=True,
        )

    component_refs = {
        "campaign_selector": campaign_selector,
        "new_campaign_btn": create_blank_campaign_btn,
        "party_selection_input": party_selection_input,
        "character_names_input": character_names_input,
        "player_names_input": player_names_input,
        "num_speakers_input": num_speakers_input,
        "skip_diarization_input": skip_diarization_input,
        "skip_classification_input": skip_classification_input,
        "skip_snippets_input": skip_snippets_input,
        "skip_knowledge_input": skip_knowledge_input,
        "enable_audit_mode_input": enable_audit_mode_input,
        "redact_prompts_input": redact_prompts_input,
        "generate_scenes_input": generate_scenes_input,
        "scene_summary_mode_input": scene_summary_mode_input,
        "status_output": status_output,
        "full_output": full_output,
        "ic_output": ic_output,
        "ooc_output": ooc_output,
        "stats_output": stats_output,
        "snippet_output": snippet_progress_output,
        "session_id_input": session_id_input,
    }

    return available_parties, component_refs
