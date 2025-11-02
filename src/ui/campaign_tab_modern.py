"""Modern Campaign tab - campaign overview and knowledge summary."""
from typing import Dict

import gradio as gr

from src.ui.helpers import StatusMessages


def create_campaign_tab_modern(blocks: gr.Blocks) -> Dict[str, gr.components.Component]:
    """Create the Campaign tab and return references to key components."""

    with gr.Tab("Campaign"):
        gr.Markdown(
            """
            # Campaign Management

            Monitor campaign health, knowledge, and processed sessions.
            """
        )

        overview_md = gr.Markdown(
            value=StatusMessages.info(
                "No Campaign Selected",
                "Load or create a campaign from the launcher to see campaign metrics."
            )
        )

        knowledge_md = gr.Markdown(
            value=StatusMessages.info(
                "Knowledge Base",
                "Knowledge summaries will appear here after processing sessions for the active campaign."
            )
        )

        session_library_md = gr.Markdown(
            value=StatusMessages.info(
                "Session Library",
                "Processed sessions for the active campaign will be listed here."
            )
        )

    return {
        "overview": overview_md,
        "knowledge": knowledge_md,
        "session_library": session_library_md,
    }
