"""Modern Settings & Tools tab - diagnostics and chat helpers."""
from typing import Dict

import gradio as gr

from src.ui.helpers import StatusMessages


def create_settings_tools_tab_modern(blocks: gr.Blocks) -> Dict[str, gr.components.Component]:
    """Create the Settings & Tools tab and return components requiring campaign updates."""

    with gr.Tab("Settings & Tools"):
        gr.Markdown(
            """
            # Settings & Tools

            Inspect diagnostics, review recent logs, and test LLM connectivity.
            """
        )

        diagnostics_md = gr.Markdown(
            value=StatusMessages.info(
                "Diagnostics",
                "Run a session for the active campaign to see status tracker updates here."
            )
        )

        chat_md = gr.Markdown(
            value=StatusMessages.info(
                "LLM Chat",
                "Load a campaign to initialise chat context for that campaign."
            )
        )

    return {
        "diagnostics": diagnostics_md,
        "chat": chat_md,
    }
