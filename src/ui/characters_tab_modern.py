"""Modern Characters tab - campaign-aware character list."""
from typing import Dict, List

import gradio as gr

from src.ui.helpers import StatusMessages


def create_characters_tab_modern(blocks: gr.Blocks, available_parties: List[str]) -> Dict[str, gr.components.Component]:
    """Create the Characters tab and return references to campaign-aware components."""

    _ = available_parties  # Placeholder until party-aware controls are reintroduced

    with gr.Tab("Characters"):
        gr.Markdown(
            """
            # Character Profiles

            View character profiles associated with the active campaign.
            """
        )

        profiles_md = gr.Markdown(
            value=StatusMessages.info(
                "No Campaign Selected",
                "Load a campaign to display character profiles for that campaign."
            )
        )

    return {"profiles": profiles_md}
