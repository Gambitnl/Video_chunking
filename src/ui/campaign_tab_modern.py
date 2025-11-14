"""Modern Campaign tab - campaign overview and knowledge summary."""
from typing import Dict, Optional

import gradio as gr

from src.ui.helpers import StatusMessages
from src.ui.constants import StatusIndicators as SI


def create_campaign_tab_modern(blocks: gr.Blocks) -> Dict[str, gr.components.Component]:
    """Create the Campaign tab and return references to key components."""

    with gr.Tab("Campaign"):
        gr.Markdown(
            """
            # Campaign Management

            Monitor campaign health, knowledge, and processed sessions.
            """
        )

        # Campaign selector and controls
        with gr.Row():
            campaign_selector = gr.Dropdown(
                label="Campaign",
                choices=[],
                value=None,
                info="Select a campaign to view its details (updates from Campaign Launcher)",
                scale=3
            )
            refresh_btn = gr.Button(
                f"{SI.ACTION_REFRESH} Refresh",
                variant="secondary",
                size="sm",
                scale=0
            )

        # Campaign Overview Section
        gr.Markdown("## Campaign Overview")
        overview_md = gr.Markdown(
            value=StatusMessages.info(
                "No Campaign Selected",
                "Select a campaign above or load one from the Campaign Launcher to see campaign metrics."
            )
        )

        # Knowledge Base Section
        gr.Markdown("## Knowledge Base")
        knowledge_md = gr.Markdown(
            value=StatusMessages.info(
                "Knowledge Base",
                "Knowledge summaries will appear here after selecting a campaign with processed sessions."
            )
        )

        # Session Library Section
        gr.Markdown("## Session Library")
        session_library_md = gr.Markdown(
            value=StatusMessages.info(
                "Session Library",
                "Processed sessions for the selected campaign will be listed here with clickable navigation."
            )
        )

    return {
        "overview": overview_md,
        "knowledge": knowledge_md,
        "session_library": session_library_md,
        "campaign_selector": campaign_selector,
        "refresh_btn": refresh_btn,
    }
