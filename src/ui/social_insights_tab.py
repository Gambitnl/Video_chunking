"""
Social Insights Tab for analyzing OOC transcripts.

Provides TF-IDF keyword extraction, topic modeling, and discussion insights
for Out-of-Character (OOC) session content.
"""
from __future__ import annotations

from typing import Callable, Dict, Optional, Tuple
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
    """
    Create the Social Insights tab for OOC transcript analysis.

    Args:
        story_manager: Story notebook manager for session management
        refresh_campaign_names: Callback to refresh campaign names
        initial_campaign_id: Initial campaign ID to display

    Returns:
        Dictionary of Gradio components
    """

    def analyze_ooc_ui(session_id: str) -> Tuple[str, str, Optional[str], str, str]:
        """
        Analyze OOC transcript with comprehensive insights.

        Yields intermediate status updates during processing.

        Args:
            session_id: Session identifier to analyze

        Yields:
            Tuple of (keywords_md, topics_md, nebula_path, insights_md, status_msg)
        """
        try:
            # Clear previous results and show starting status
            yield (
                None,
                None,
                None,
                None,
                StatusMessages.loading("Starting comprehensive OOC analysis")
            )

            from src.analyzer import OOCAnalyzer
            from src.config import Config

            # Check dependencies
            try:
                from wordcloud import WordCloud
            except ImportError:
                error_msg = StatusMessages.error(
                    "Missing Dependency",
                    "The 'wordcloud' package is required for social insights analysis.",
                    "Install it with: pip install wordcloud"
                )
                yield (error_msg, None, None, None, error_msg)
                return

            if not session_id:
                warning_msg = StatusMessages.warning("Input Required", "Please select a session ID.")
                yield (warning_msg, None, None, None, warning_msg)
                return

            from src.formatter import sanitize_filename

            sanitized_session_id = sanitize_filename(session_id)
            ooc_file = Config.OUTPUT_DIR / f"{sanitized_session_id}_ooc_only.txt"

            # Progress: Checking for transcript
            yield (
                gr.update(),
                gr.update(),
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
                yield (error_msg, None, None, None, error_msg)
                return

            # Progress: Loading transcript and extracting insights
            yield (
                gr.update(),
                gr.update(),
                gr.update(),
                gr.update(),
                StatusMessages.loading("Analyzing transcript: extracting keywords, topics, and insights")
            )

            # Create analyzer and extract comprehensive insights
            analyzer = OOCAnalyzer(ooc_file)
            insights = analyzer.get_insights(session_id=session_id)

            if not insights.keywords:
                info_msg = StatusMessages.info(
                    "No Keywords",
                    "No significant keywords found in the OOC transcript.",
                    "This session may have limited out-of-character content."
                )
                yield (info_msg, None, None, None, info_msg)
                return

            # Build Keywords Table (TF-IDF scores)
            keyword_md_header = (
                "### Top Keywords (TF-IDF)\n\n"
                "| Rank | Keyword | TF-IDF Score | Frequency |\n"
                "|------|---------|--------------|-----------|"
            )
            keyword_rows = [
                f"| {idx} | {kw.term} | {kw.score:.4f} | {kw.frequency} |"
                for idx, kw in enumerate(insights.keywords, 1)
            ]
            keyword_md = "\n".join([keyword_md_header] + keyword_rows)

            # Build Topics Table (LDA)
            if insights.topics:
                topic_md_header = (
                    "### Discovered Topics (LDA)\n\n"
                    "| Topic | Label | Top Keywords | Coherence |\n"
                    "|-------|-------|--------------|-----------|"
                )
                topic_rows = []
                for topic in insights.topics:
                    # Format top 5 keywords with weights
                    top_keywords = ", ".join([
                        f"{kw[0]} ({kw[1]:.2f})"
                        for kw in topic.keywords[:5]
                    ])
                    topic_rows.append(
                        f"| {topic.id + 1} | {topic.label} | {top_keywords} | {topic.coherence_score:.2f} |"
                    )
                topic_md = "\n".join([topic_md_header] + topic_rows)
            else:
                topic_md = StatusMessages.info(
                    "Topic Modeling Skipped",
                    "Transcript too short for topic modeling (< 100 words).",
                    "Longer sessions will reveal discussion topics."
                )

            # Build Insights Summary
            patterns = insights.discussion_patterns
            metrics = insights.diversity_metrics

            insights_md_parts = ["### Session Insights\n"]

            # Discussion Patterns
            insights_md_parts.append("**Discussion Patterns:**\n")
            insights_md_parts.append(f"- Total Words: {patterns.get('total_words', 0)}")
            insights_md_parts.append(f"- Unique Words: {patterns.get('unique_words', 0)}")
            insights_md_parts.append(
                f"- Lexical Diversity: {patterns.get('lexical_diversity', 0.0):.2%}"
            )
            insights_md_parts.append(f"- Topics Identified: {patterns.get('num_topics', 0)}\n")

            # Diversity Metrics
            insights_md_parts.append("**Text Diversity Metrics:**\n")
            insights_md_parts.append(
                f"- Shannon Entropy: {metrics.get('shannon_entropy', 0.0):.2f}"
            )
            insights_md_parts.append(
                f"- Vocabulary Richness: {metrics.get('vocabulary_richness', 0.0):.2f}\n"
            )

            # Inside Jokes
            if insights.inside_jokes:
                insights_md_parts.append("**Potential Inside Jokes:**\n")
                inside_jokes_list = ", ".join(insights.inside_jokes)
                insights_md_parts.append(f"_{inside_jokes_list}_\n")
            else:
                insights_md_parts.append("**Potential Inside Jokes:** None detected\n")

            insights_md = "\n".join(insights_md_parts)

            # Progress: Generating word cloud
            yield (
                gr.update(),
                gr.update(),
                gr.update(),
                gr.update(),
                StatusMessages.loading("Generating Topic Nebula word cloud")
            )

            # Generate word cloud from keyword frequencies
            keyword_freq = {kw.term: kw.frequency for kw in insights.keywords}

            wc = WordCloud(
                width=800,
                height=400,
                background_color="#0C111F",
                colormap="cool",
                max_words=100,
                contour_width=3,
                contour_color="#89DDF5",
            )
            wc.generate_from_frequencies(keyword_freq)

            temp_path = Config.TEMP_DIR / f"{sanitized_session_id}_nebula.png"
            wc.to_file(str(temp_path))

            # Success
            success_msg = StatusMessages.success(
                "Analysis Complete",
                f"Successfully analyzed {len(insights.keywords)} keywords, "
                f"{len(insights.topics)} topics, and generated insights."
            )
            yield (keyword_md, topic_md, str(temp_path), insights_md, success_msg)

        except Exception as exc:
            import traceback
            error_msg = StatusMessages.error(
                "Analysis Failed",
                "Unable to complete social insights analysis.",
                f"Error: {type(exc).__name__}: {str(exc)}\n\n{traceback.format_exc()}"
            )
            yield (error_msg, None, None, None, error_msg)

    # Campaign and session selection setup
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
        """Refresh session list when campaign changes."""
        campaign_id = None
        if campaign_name != "All Campaigns":
            campaign_names_map = refresh_campaign_names()
            campaign_id = next(
                (cid for cid, cname in campaign_names_map.items() if cname == campaign_name),
                None
            )
        sessions = story_manager.list_sessions(campaign_id=campaign_id)
        return gr.update(choices=sessions, value=sessions[0] if sessions else None)

    # UI Layout
    with gr.Tab("Social Insights"):
        gr.Markdown("""
        ### OOC Keyword & Topic Analysis

        Analyze out-of-character banter to discover discussion topics, recurring themes, and social patterns.

        **Features:**
        - **TF-IDF Keywords**: Important terms ranked by relevance (not just frequency)
        - **Topic Modeling (LDA)**: Automatically discover discussion themes
        - **Inside Jokes**: Detect potential recurring group-specific terms
        - **Diversity Metrics**: Measure conversational richness and variety

        **Workflow:**
        1. Select a campaign and session from the dropdowns below
        2. Click **Analyze Banter** to extract insights from the OOC transcript
        3. Review keywords, topics, and insights
        4. Word cloud visualization highlights the most prominent terms

        **Note**: Topic modeling requires at least 100 words in the OOC transcript.
        """)

        with gr.Row():
            # Left column: Controls and status
            with gr.Column(scale=1):
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
                insight_btn = gr.Button(
                    f"{SI.ACTION_PROCESS} Analyze Banter",
                    variant="primary",
                    size="lg"
                )

                # Status output
                status_output = gr.Markdown(
                    label="Status",
                    value=StatusMessages.info(
                        "Ready",
                        "Select a session and click Analyze Banter to begin."
                    ),
                )

                # Session insights
                insights_output = gr.Markdown(
                    label="Session Insights",
                    value="",
                )

            # Right column: Results
            with gr.Column(scale=2):
                # Keywords table
                keyword_output = gr.Markdown(
                    label="Top Keywords (TF-IDF)",
                    value=StatusMessages.info(
                        "Keywords",
                        "Run analysis to see TF-IDF ranked keywords."
                    ),
                )

                # Topics table
                topics_output = gr.Markdown(
                    label="Discovered Topics",
                    value=StatusMessages.info(
                        "Topics",
                        "Run analysis to discover discussion topics."
                    ),
                )

        # Word cloud visualization (full width)
        with gr.Row():
            nebula_output = gr.Image(
                label="Topic Nebula (Word Cloud)",
                show_label=True,
                height=400,
            )

        # Event handlers
        campaign_selector.change(
            fn=refresh_sessions_ui,
            inputs=[campaign_selector],
            outputs=[insight_session_id],
        )

        insight_btn.click(
            fn=analyze_ooc_ui,
            inputs=[insight_session_id],
            outputs=[keyword_output, topics_output, nebula_output, insights_output, status_output],
        )

    return {
        "campaign_selector": campaign_selector,
        "session_dropdown": insight_session_id,
        "keyword_output": keyword_output,
        "topics_output": topics_output,
        "nebula_output": nebula_output,
        "insights_output": insights_output,
        "status_output": status_output,
    }
