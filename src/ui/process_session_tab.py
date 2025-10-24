"""Process Session tab UI construction."""
from __future__ import annotations

from typing import Any, Callable, Dict, List

import gradio as gr

from src.party_config import PartyConfigManager


def create_process_session_tab(
    *,
    refresh_campaign_names: Callable[[], Dict[str, str]],
    process_session_fn: Callable[..., Any],
    campaign_manager,
) -> List[str]:
    """Build the Process Session tab and wire associated handlers.

    Args:
        refresh_campaign_names: Callback that returns campaign_id -> name mapping.
        process_session_fn: Pipeline entry function invoked when user clicks Process.
        campaign_manager: Shared CampaignManager instance for lookups.

    Returns:
        List of available party identifiers for reuse in other tabs.
    """
    party_manager = PartyConfigManager()
    available_parties = ["Manual Entry"] + party_manager.list_parties()

    campaign_names = refresh_campaign_names()
    campaign_choices = ["Manual Setup"] + list(campaign_names.values())

    with gr.Tab("Process Session"):
        with gr.Row():
            with gr.Column():
                campaign_selector = gr.Dropdown(
                    choices=campaign_choices,
                    value="Manual Setup",
                    label="Campaign Profile",
                    info="Select your campaign to auto-fill all settings, or choose 'Manual Setup' to configure manually",
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
                    placeholder="e.g., session_2024_01_15",
                    info="Unique identifier for this session",
                )

                party_selection_input = gr.Dropdown(
                    choices=available_parties,
                    value="default",
                    label="Party Configuration",
                    info="Select your party or choose 'Manual Entry' to enter names manually",
                )

                character_names_input = gr.Textbox(
                    label="Character Names (comma-separated)",
                    placeholder="e.g., Thorin, Elara, Zyx",
                    info="Names of player characters in the campaign (only used if Manual Entry selected)",
                )

                player_names_input = gr.Textbox(
                    label="Player Names (comma-separated)",
                    placeholder="e.g., Alice, Bob, Charlie, DM",
                    info="Names of actual players (only used if Manual Entry selected)",
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
                        info="Skip identifying who is speaking. Faster processing (~30% time saved), but all speakers labeled as 'UNKNOWN'. Requires HuggingFace token if enabled.",
                    )
                    skip_classification_input = gr.Checkbox(
                        label="Skip IC/OOC Classification",
                        info="Skip separating in-character dialogue from out-of-character banter. Faster processing (~20% time saved), but no IC/OOC filtering. All content labeled as IC.",
                    )
                    skip_snippets_input = gr.Checkbox(
                        label="Skip Audio Snippets",
                        info="Skip exporting individual WAV files for each dialogue segment. Saves disk space and processing time (~10% time saved). You'll still get all transcripts (TXT, SRT, JSON).",
                    )
                    skip_knowledge_input = gr.Checkbox(
                        label="Skip Campaign Knowledge Extraction",
                        info="Skip automatic extraction of quests, NPCs, plot hooks, locations, and items from the session. Saves processing time (~5% time saved), but campaign library won't be updated.",
                        value=False,
                    )

                process_btn = gr.Button("Process Session", variant="primary", size="lg")

            with gr.Column():
                status_output = gr.Textbox(
                    label="Status",
                    lines=2,
                    interactive=False,
                )

                stats_output = gr.Markdown(label="Statistics")

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
            fn=process_session_fn,
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
            ],
            outputs=[
                status_output,
                full_output,
                ic_output,
                ooc_output,
                stats_output,
            ],
        )

    return available_parties
