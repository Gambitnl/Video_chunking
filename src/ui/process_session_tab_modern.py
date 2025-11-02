"""Modern Process Session tab with campaign-aware workflow."""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple

import gradio as gr

from src.party_config import PartyConfigManager
from src.ui.constants import StatusIndicators as SI
from src.ui.helpers import InfoText, Placeholders, StatusMessages, UIComponents


def create_workflow_header() -> gr.HTML:
    """Create a visual workflow stepper."""
    return gr.HTML(
        """
        <div class="stepper">
            <div class="step active">
                <div class="step-number">1</div>
                <div class="step-label">Upload</div>
                <div class="step-connector"></div>
            </div>
            <div class="step">
                <div class="step-number">2</div>
                <div class="step-label">Configure</div>
                <div class="step-connector"></div>
            </div>
            <div class="step">
                <div class="step-number">3</div>
                <div class="step-label">Process</div>
                <div class="step-connector"></div>
            </div>
            <div class="step">
                <div class="step-number">4</div>
                <div class="step-label">Review</div>
            </div>
        </div>
        """
    )


def create_process_session_tab_modern(
    blocks: gr.Blocks,
    refresh_campaign_names: Callable[[], Dict[str, str]],
    process_session_fn: Callable[..., Any],
    campaign_manager,
    active_campaign_state: gr.State,
    *,
    campaign_badge_text: str,
    initial_campaign_name: str = "Manual Setup",
) -> Tuple[List[str], Dict[str, gr.components.Component]]:
    """Create the campaign-aware Process Session tab.

    Returns:
        Tuple of (available party identifiers, component references for cross-tab coordination)
    """
    party_manager = PartyConfigManager()
    available_parties = ["Manual Entry"] + party_manager.list_parties()

    campaign_names = refresh_campaign_names()
    campaign_choices = ["Manual Setup"] + list(campaign_names.values())

    initial_defaults = {
        "party_selection": "Manual Entry" if "Manual Entry" in available_parties else (available_parties[0] if available_parties else None),
        "num_speakers": 4,
        "skip_diarization": False,
        "skip_classification": False,
        "skip_snippets": True,
        "skip_knowledge": False,
    }

    initial_selector_value = (
        initial_campaign_name
        if initial_campaign_name in campaign_choices
        else "Manual Setup"
    )

    if initial_selector_value != "Manual Setup":
        selected_campaign_id = next(
            (cid for cid, name in campaign_names.items() if name == initial_selector_value),
            None,
        )
        if selected_campaign_id:
            campaign = campaign_manager.get_campaign(selected_campaign_id)
            if campaign:
                initial_defaults.update(
                    {
                        "party_selection": campaign.party_id or "Manual Entry",
                        "num_speakers": campaign.settings.num_speakers,
                        "skip_diarization": campaign.settings.skip_diarization,
                        "skip_classification": campaign.settings.skip_classification,
                        "skip_snippets": campaign.settings.skip_snippets,
                        "skip_knowledge": campaign.settings.skip_knowledge,
                    }
                )

    with gr.Tab("Process Session"):
        create_workflow_header()

        gr.Markdown(
            """
            # Process Session Recording

            Upload an audio file, apply campaign defaults, and run the pipeline.
            """
        )

    badge_value = campaign_badge_text or StatusMessages.info(
        "Campaign",
        "No campaign selected. Use the Campaign Launcher above to choose one."
    )
    campaign_badge = gr.Markdown(value=badge_value)

    with gr.Group():
        gr.Markdown("### Step 1: Upload Audio")
        audio_input = gr.File(
            label="Session Audio File",
            file_types=[".m4a", ".mp3", ".wav", ".flac"],
        )

    with gr.Group():
        gr.Markdown("### Step 2: Configure Session")

        with gr.Row():
            campaign_selector = gr.Dropdown(
                label="Campaign Profile",
                choices=campaign_choices,
                value=initial_selector_value,
                info=InfoText.CAMPAIGN_SELECT,
            )

            new_campaign_btn = UIComponents.create_action_button(
                "New Blank Campaign",
                variant="secondary",
                size="sm",
            )

        session_id_input = gr.Textbox(
            label="Session ID",
            placeholder=Placeholders.SESSION_ID,
            info=InfoText.SESSION_ID,
        )

        with gr.Row():
            party_selection_input = gr.Dropdown(
                label="Party Configuration",
                choices=available_parties,
                value=initial_defaults.get("party_selection") or "Manual Entry",
                info="Select an existing party profile or choose Manual Entry.",
            )

            num_speakers_input = gr.Slider(
                minimum=2,
                maximum=10,
                value=initial_defaults.get("num_speakers", 4),
                step=1,
                label="Expected Speakers",
                info="Helps diarization accuracy. Typical table is 3 players + 1 DM.",
            )

            character_names_input = gr.Textbox(
                label="Character Names (comma-separated)",
                placeholder=Placeholders.CHARACTER_NAME,
                info="Used when Manual Entry is selected.",
            )

            player_names_input = gr.Textbox(
                label="Player Names (comma-separated)",
                placeholder=Placeholders.PLAYER_NAME,
                info="Optional player name mapping for manual entry.",
            )

            with gr.Row():
                skip_diarization_input = gr.Checkbox(
                    label="Skip Speaker Identification",
                    value=initial_defaults.get("skip_diarization", False),
                    info="Saves time but all segments will be UNKNOWN.",
                )
                skip_classification_input = gr.Checkbox(
                    label="Skip IC/OOC Classification",
                    value=initial_defaults.get("skip_classification", False),
                    info="Disables in-character versus out-of-character separation.",
                )
                skip_snippets_input = gr.Checkbox(
                    label="Skip Snippet Export",
                    value=initial_defaults.get("skip_snippets", True),
                    info="Skip exporting WAV snippets to save disk space.",
                )
                skip_knowledge_input = gr.Checkbox(
                    label="Skip Knowledge Extraction",
                    value=initial_defaults.get("skip_knowledge", False),
                    info="Disable automatic quest/NPC extraction.",
                )

        with gr.Group():
            gr.Markdown("### Step 3: Process")

            process_btn = UIComponents.create_action_button(
                "Start Processing",
                variant="primary",
                size="lg",
                full_width=True,
            )

            status_output = gr.Markdown(
                value=StatusMessages.info(
                    "Ready",
                    "Provide a session ID and audio file, then click Start Processing."
                )
            )

        with gr.Group(visible=False) as results_section:
            gr.Markdown("### Step 4: Review Results")
            full_output = gr.Textbox(label="Full Transcript", lines=10)
            ic_output = gr.Textbox(label="In-Character Transcript", lines=10)
            ooc_output = gr.Textbox(label="Out-of-Character Transcript", lines=10)
            stats_output = gr.Markdown()
            snippet_output = gr.Markdown()

        def load_campaign_settings(selected_name: str) -> Dict[gr.components.Component, Any]:
            names = refresh_campaign_names()
            if selected_name == "Manual Setup":
                return {
                    party_selection_input: "Manual Entry",
                    num_speakers_input: 4,
                    skip_diarization_input: False,
                    skip_classification_input: False,
                    skip_snippets_input: True,
                    skip_knowledge_input: False,
                }

            campaign_id = next((cid for cid, cname in names.items() if cname == selected_name), None)
            if not campaign_id:
                return {}

            campaign = campaign_manager.get_campaign(campaign_id)
            if not campaign:
                return {}

            return {
                party_selection_input: campaign.party_id or "Manual Entry",
                num_speakers_input: campaign.settings.num_speakers,
                skip_diarization_input: campaign.settings.skip_diarization,
                skip_classification_input: campaign.settings.skip_classification,
                skip_snippets_input: campaign.settings.skip_snippets,
                skip_knowledge_input: campaign.settings.skip_knowledge,
            }

        def _prepare_processing_outputs():
            return (
                StatusMessages.loading("Processing session"),
                gr.update(visible=False),
            )

        def _format_statistics(stats: Dict[str, Any], knowledge: Dict[str, Any]) -> str:
            if not stats:
                return StatusMessages.info("Statistics", "No statistics available.")

            duration = stats.get("total_duration_formatted") or f"{stats.get('total_duration_seconds', 0)} seconds"
            lines = [
                "### Session Statistics",
                f"{SI.INFO} Duration: {duration}",
                f"{SI.INFO} Segments: {stats.get('total_segments', 0)}",
                f"{SI.INFO} IC Segments: {stats.get('ic_segments', 0)}",
                f"{SI.INFO} OOC Segments: {stats.get('ooc_segments', 0)}",
            ]

            if knowledge:
                extracted = knowledge.get("extracted") or {}
                if extracted:
                    lines.append("")
                    lines.append("### Knowledge Extracted")
                    for key, count in extracted.items():
                        lines.append(f"- {key.replace('_', ' ').title()}: {count}")

            return "\n".join(lines)

        def _format_snippet_export(snippet: Dict[str, Any]) -> str:
            if not snippet:
                return StatusMessages.info("Snippet Export", "Snippet export disabled.")

            manifest_path = snippet.get("manifest")
            segments_dir = snippet.get("segments_dir")

            lines = [
                "### Snippet Export",
            ]

            if segments_dir:
                lines.append(f"{SI.SUCCESS} Segments saved to `{segments_dir}`.")
            if manifest_path:
                lines.append(f"- Manifest: `{manifest_path}`")

            return "\n".join(lines) if len(lines) > 1 else StatusMessages.info("Snippet Export", "No snippet data.")

        def _render_processing_response(response: Dict[str, Any]):
            if not isinstance(response, dict):
                return (
                    StatusMessages.error("Processing Failed", "Unexpected response from pipeline."),
                    gr.update(visible=False),
                    "",
                    "",
                    "",
                    StatusMessages.info("Statistics", "No statistics available."),
                    StatusMessages.info("Snippet Export", "No snippet information available."),
                )

            if response.get("status") != "success":
                return (
                    StatusMessages.error(
                        "Processing Failed",
                        response.get("message", "Unable to process session."),
                        response.get("details", "")
                    ),
                    gr.update(visible=False),
                    response.get("full", ""),
                    response.get("ic", ""),
                    response.get("ooc", ""),
                    StatusMessages.info("Statistics", "No statistics available."),
                    StatusMessages.info("Snippet Export", "No snippet information available."),
                )

            stats_markdown = _format_statistics(response.get("stats") or {}, response.get("knowledge") or {})
            snippet_markdown = _format_snippet_export(response.get("snippet") or {})

            return (
                StatusMessages.success("Processing Complete", response.get("message", "Session processed successfully.")),
                gr.update(visible=True),
                response.get("full", ""),
                response.get("ic", ""),
                response.get("ooc", ""),
                stats_markdown,
                snippet_markdown,
            )

        def process_session_handler(
            audio_file,
            session_id,
            party_selection,
            character_names,
            player_names,
            num_speakers,
            skip_diarization,
            skip_classification,
            skip_snippets,
            skip_knowledge,
            campaign_id,
        ):
            response = process_session_fn(
                audio_file,
                session_id,
                party_selection,
                character_names,
                player_names,
                num_speakers,
                skip_diarization,
                skip_classification,
                skip_snippets,
                skip_knowledge,
                campaign_id,
            )
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
                results_section,
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
                active_campaign_state,
            ],
            outputs=[
                status_output,
                results_section,
                full_output,
                ic_output,
                ooc_output,
                stats_output,
                snippet_output,
            ],
            queue=True,
        )

    component_refs = {
        "campaign_badge": campaign_badge,
        "campaign_selector": campaign_selector,
        "new_campaign_btn": new_campaign_btn,
        "party_selection_input": party_selection_input,
        "session_id_input": session_id_input,
        "character_names_input": character_names_input,
        "player_names_input": player_names_input,
        "num_speakers_input": num_speakers_input,
        "skip_diarization_input": skip_diarization_input,
        "skip_classification_input": skip_classification_input,
        "skip_snippets_input": skip_snippets_input,
        "skip_knowledge_input": skip_knowledge_input,
        "status_output": status_output,
        "results_section": results_section,
        "full_output": full_output,
        "ic_output": ic_output,
        "ooc_output": ooc_output,
        "stats_output": stats_output,
        "snippet_output": snippet_output,
    }

    return available_parties, component_refs
