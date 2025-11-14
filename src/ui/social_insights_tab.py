from __future__ import annotations

from typing import Callable, Dict, Optional
import gradio as gr
from src.ui.helpers import StatusMessages
from src.ui.constants import StatusIndicators as SI
from src.story_notebook import StoryNotebookManager


def create_social_insights_tab(
    story_manager: StoryNotebookManager,
    refresh_campaign_names: Callable[[], Dict[str, str]],
    *,
    initial_campaign_id: Optional[str] = None,
) -> Dict[str, gr.components.Component]:
    def analyze_ooc_ui(session_id):
        """
        Analyze OOC transcript with progress feedback.
        Yields intermediate status updates during processing.
        """
        try:
            # Clear previous results and show starting status
            yield (
                None,
                None,
                StatusMessages.loading("Starting analysis")
            )

            from src.analyzer import OOCAnalyzer
            from src.config import Config

            # Check WordCloud dependency first
            try:
                from wordcloud import WordCloud
            except ImportError:
                error_msg = StatusMessages.error(
                    "Missing Dependency",
                    "The 'wordcloud' package is required for social insights analysis.",
                    "Install it with: pip install wordcloud"
                )
                yield (error_msg, None, error_msg)
                return

            if not session_id:
                warning_msg = StatusMessages.warning("Input Required", "Please select a session ID.")
                yield (warning_msg, None, warning_msg)
                return

            from src.formatter import sanitize_filename

            sanitized_session_id = sanitize_filename(session_id)
            ooc_file = Config.OUTPUT_DIR / f"{sanitized_session_id}_ooc_only.txt"

            # Progress: Checking for transcript
            yield (
                gr.update(),
                gr.update(),
                StatusMessages.loading("Locating OOC transcript")
            )

            if not ooc_file.exists():
                error_msg = StatusMessages.error(
                    "File Not Found",
                    f"OOC transcript not found for session: {session_id}",
                    "Run the main pipeline first to generate OOC transcripts."
                )
                yield (error_msg, None, error_msg)
                return

            # Progress: Loading transcript
            yield (
                gr.update(),
                gr.update(),
                StatusMessages.loading("Loading OOC transcript and extracting keywords")
            )

            analyzer = OOCAnalyzer(ooc_file)
            keywords = analyzer.get_keywords(top_n=30)

            if not keywords:
                info_msg = StatusMessages.info(
                    "No Keywords",
                    "No significant keywords found in the OOC transcript.",
                    "This session may have limited out-of-character content."
                )
                yield (info_msg, None, info_msg)
                return

            # Progress: Generating word cloud
            yield (
                gr.update(),
                gr.update(),
                StatusMessages.loading("Generating Topic Nebula word cloud")
            )

            wc = WordCloud(
                width=800,
                height=400,
                background_color="#0C111F",
                colormap="cool",
                max_words=100,
                contour_width=3,
                contour_color="#89DDF5",
            )
            wc.generate_from_frequencies(dict(keywords))

            temp_path = Config.TEMP_DIR / f"{sanitized_session_id}_nebula.png"
            wc.to_file(str(temp_path))

            # Build keyword table
            keyword_md_header = "### Top Keywords\n\n| Rank | Keyword | Frequency |\n|---|---|---|"
            keyword_rows = [f"| {idx} | {word} | {count} |" for idx, (word, count) in enumerate(keywords, 1)]
            keyword_md = "\n".join([keyword_md_header] + keyword_rows)

            # Success
            success_msg = StatusMessages.success(
                "Analysis Complete",
                f"Successfully analyzed {len(keywords)} keywords and generated Topic Nebula."
            )
            yield (keyword_md, temp_path, success_msg)

        except Exception as exc:
            error_msg = StatusMessages.error(
                "Analysis Failed",
                "Unable to complete social insights analysis.",
                f"Error: {type(exc).__name__}: {str(exc)}"
            )
            yield (error_msg, None, error_msg)

    campaign_names = refresh_campaign_names()
    campaign_choices = ["All Campaigns"] + list(campaign_names.values())
    initial_campaign_name = "All Campaigns"
    if initial_campaign_id:
        initial_campaign_name = campaign_names.get(initial_campaign_id, "All Campaigns")

    if initial_campaign_name != "All Campaigns":
        initial_sessions = story_manager.list_sessions(campaign_id=initial_campaign_id)
    else:
        initial_sessions = story_manager.list_sessions()

    def refresh_sessions_ui(campaign_name: str = "All Campaigns"):
        campaign_id = None
        if campaign_name != "All Campaigns":
            campaign_names_map = refresh_campaign_names()
            campaign_id = next(
                (cid for cid, cname in campaign_names_map.items() if cname == campaign_name),
                None
            )
        sessions = story_manager.list_sessions(campaign_id=campaign_id)
        return gr.update(choices=sessions, value=sessions[0] if sessions else None)

    with gr.Tab("Social Insights"):
        gr.Markdown("""
        ### OOC Keyword Analysis (Topic Nebula)

        Analyze the out-of-character banter to find the most common topics and keywords.

        **Workflow**
        - Select a campaign and session from the dropdowns below.
        - Click **Analyze Banter** to compute TF-IDF keywords from the saved OOC transcript and render the nebula word cloud.
        - If no OOC transcript exists yet, run the main pipeline first or verify the session ID matches the generated files.

        **Interpreting results**
        - The markdown table highlights the top terms with raw counts so you can skim popular jokes and topics.
        - The nebula graphic saves to `temp/` for reuse in retrospectives or recap decks.
        - Rerun the analysis after updating speaker mappings or classifications to compare topic shifts between sessions.
        """)
        with gr.Row():
            with gr.Column():
                campaign_selector = gr.Dropdown(
                    choices=campaign_choices,
                    value=initial_campaign_name,
                    label="Filter by Campaign",
                    info="Show only sessions from the selected campaign",
                )
                insight_session_id = gr.Dropdown(
                    label="Session ID",
                    choices=initial_sessions,
                    value=initial_sessions[0] if initial_sessions else None,
                    interactive=True,
                )
                insight_btn = gr.Button(f"{SI.ACTION_PROCESS} Analyze Banter", variant="primary")
                # Status output for progress feedback
                status_output = gr.Markdown(
                    label="Status",
                    value=StatusMessages.info(
                        "Ready",
                        "Select a session and click Analyze Banter to begin."
                    ),
                )
            with gr.Column():
                keyword_output = gr.Markdown(
                    label="Top Keywords",
                    value=StatusMessages.info(
                        "Social Insights",
                        "Select a campaign and session, then click Analyze Banter."
                    ),
                )
        with gr.Row():
            nebula_output = gr.Image(label="Topic Nebula")

        campaign_selector.change(
            fn=refresh_sessions_ui,
            inputs=[campaign_selector],
            outputs=[insight_session_id],
        )

        insight_btn.click(
            fn=analyze_ooc_ui,
            inputs=[insight_session_id],
            outputs=[keyword_output, nebula_output, status_output],
        )

    return {
        "campaign_selector": campaign_selector,
        "session_dropdown": insight_session_id,
        "keyword_output": keyword_output,
        "nebula_output": nebula_output,
        "status_output": status_output,
    }
