"""Modern Stories & Output tab - campaign-filtered session outputs."""
from typing import Dict

import gradio as gr
import pandas as pd

from src.config import Config
from src.session_search import SessionSearcher
from src.ui.helpers import StatusMessages


def create_stories_output_tab_modern(blocks: gr.Blocks) -> Dict[str, gr.components.Component]:
    """Create the Stories & Output tab and return updateable components."""

    with gr.Tab("📖 Stories & Output"):
        gr.Markdown(
            """
            # Campaign Stories & Outputs

            Browse processed sessions, transcripts, and generated narratives.
            """
        )

        with gr.Accordion("🔎 Session Search", open=False):
            search_query = gr.Textbox(label="Search Query", placeholder="Enter text to search for in all session transcripts...")
            search_button = gr.Button("Search", variant="primary")
            search_results_df = gr.DataFrame(label="Search Results", headers=["Session ID", "Line Number", "Line Content"], visible=False)
            search_no_results_md = gr.Markdown(visible=False)

        # UX-13: session library helper now returns list-of-lists (DataFrame data).
        # We must use gr.DataFrame to display it correctly.
        session_list_md = gr.DataFrame(
            headers=["Date", "Session ID", "Duration", "Speakers", "Status"],
            datatype=["str", "str", "str", "number", "str"],
            interactive=False,
            wrap=True,
            value=[],
            label="Session Library"
        )

        narrative_hint_md = gr.HTML(
            value=StatusMessages.empty_state_cta(
                icon="📝",
                title="No Narratives Generated",
                message="Run the session processing pipeline for this campaign to generate transcripts and story narratives.",
                cta_html='<span class="info-badge">→ Use the Process Session tab to get started</span>'
            )
        )

    def handle_search(query: str):
        if not query:
            return {search_results_df: gr.DataFrame(visible=False), search_no_results_md: gr.Markdown(visible=False)}
        
        config = Config.from_env()
        searcher = SessionSearcher(config.output_dir)
        results = searcher.search(query)

        if not results:
            return {search_results_df: gr.DataFrame(visible=False), search_no_results_md: gr.Markdown(StatusMessages.warning("No results found."), visible=True)}

        df = pd.DataFrame(results)
        # Select and reorder columns for display
        display_df = df[["session_id", "line_number", "line_content"]]
        return {search_results_df: gr.DataFrame(value=display_df, visible=True), search_no_results_md: gr.Markdown(visible=False)}

    search_button.click(
        fn=handle_search,
        inputs=[search_query],
        outputs=[search_results_df, search_no_results_md]
    )

    return {
        "session_list": session_list_md,
        "narrative_hint": narrative_hint_md,
    }
