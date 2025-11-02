"""Modern Stories & Output tab - campaign-filtered session outputs."""
from typing import Dict

import gradio as gr

from src.ui.helpers import StatusMessages


def create_stories_output_tab_modern(blocks: gr.Blocks) -> Dict[str, gr.components.Component]:
    """Create the Stories & Output tab and return updateable components."""

    with gr.Tab("Stories & Output"):
        gr.Markdown(
            """
            # Campaign Stories & Outputs

            Browse processed sessions, transcripts, and generated narratives.
            """
        )

        session_list_md = gr.Markdown(
            value=StatusMessages.info(
                "Session Library",
                "Processed sessions for the active campaign will be listed here."
            )
        )

        narrative_hint_md = gr.Markdown(
            value=StatusMessages.info(
                "Narrative Guidance",
                "Run the pipeline for this campaign and generate narratives to populate this section."
            )
        )

    return {
        "session_list": session_list_md,
        "narrative_hint": narrative_hint_md,
    }
