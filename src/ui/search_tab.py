"""
Search Tab - UI for searching transcripts.

Provides a comprehensive search interface for D&D session transcripts with
advanced filters, context display, and export functionality.

Author: Claude (Sonnet 4.5)
Date: 2025-11-17
"""
from __future__ import annotations

import logging
import re  # FIX: Move import to top of file (PEP 8)
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import gradio as gr

from src.search_engine import SearchEngine, SearchFilters, SearchMode, SearchResult
from src.search_exporter import SearchResultExporter
from src.transcript_indexer import TranscriptIndexer
from src.ui.constants import StatusIndicators as SI
from src.ui.helpers import StatusMessages

logger = logging.getLogger("DDSessionProcessor.search_tab")


def create_search_tab(project_root: Path, ui_container: Optional[gr.Blocks] = None) -> None:
    """
    Create the Search tab for transcript search.

    Args:
        project_root: Path to project root directory
        ui_container: Optional Blocks instance used to register load callbacks
    """

    output_dir = project_root / "output"

    # Initialize indexer and engine (will be lazy-loaded)
    indexer = TranscriptIndexer(output_dir)
    index = None
    engine = None

    # Store last search results for export
    last_results: List[SearchResult] = []
    last_query: str = ""

    def initialize_index():
        """
        Initialize or rebuild the search index.

        Returns:
            Tuple of (status_message, speaker_dropdown_update)
        """
        nonlocal index, engine

        try:
            index = indexer.build_index(force_rebuild=False)
            engine = SearchEngine(index)

            # IMPROVEMENT 3: Check if index is stale and warn users
            staleness_warning = ""
            if indexer.is_index_stale():
                staleness_warning = (
                    f"\n\n{SI.WARNING} **Index may be stale!** "
                    "New sessions detected. Click 'Rebuild Index' to include them in search."
                )

            stats_msg = (
                f"{SI.SUCCESS} Index ready: "
                f"{index.get_total_segments()} segments from "
                f"{index.get_session_count()} sessions"
                f"{staleness_warning}"
            )

            # Get speaker list for dropdown
            speakers = sorted(list(index.speakers))

            return stats_msg, gr.update(choices=speakers)

        except Exception as e:
            logger.error(f"Failed to initialize index: {e}", exc_info=True)
            error_msg = StatusMessages.error(
                "Indexing Failed", "Unable to build search index.", str(e)
            )
            return error_msg, gr.update()

    def rebuild_index():
        """
        Force rebuild of search index.

        Returns:
            Tuple of (status_message, speaker_dropdown_update)
        """
        nonlocal index, engine

        try:
            index = indexer.build_index(force_rebuild=True)
            engine = SearchEngine(index)

            success_msg = (
                f"{SI.SUCCESS} Index rebuilt: "
                f"{index.get_total_segments()} segments from "
                f"{index.get_session_count()} sessions"
            )

            speakers = sorted(list(index.speakers))

            return success_msg, gr.update(choices=speakers)

        except Exception as e:
            logger.error(f"Failed to rebuild index: {e}", exc_info=True)
            error_msg = StatusMessages.error(
                "Rebuild Failed", "Unable to rebuild search index.", str(e)
            )
            return error_msg, gr.update()

    def perform_search(
        query: str,
        search_mode: str,
        speaker_filter: List[str],
        ic_ooc_filter: str,
        max_results: int,
    ) -> str:
        """
        Perform search and return formatted results.

        Args:
            query: Search query string
            search_mode: "Full Text", "Regex", or "Exact"
            speaker_filter: List of speakers to filter by
            ic_ooc_filter: "All", "IC", or "OOC"
            max_results: Maximum results to return

        Returns:
            Formatted search results as markdown
        """
        nonlocal last_results, last_query

        if not engine:
            return StatusMessages.error(
                "Index Not Ready",
                "Please wait for index to initialize or click Rebuild Index.",
            )

        if not query or not query.strip():
            return f"{SI.INFO} Enter a search query to begin"

        try:
            # Convert UI mode to SearchMode enum
            mode_map = {
                "Full Text": SearchMode.FULL_TEXT,
                "Regex": SearchMode.REGEX,
                "Exact": SearchMode.EXACT,
            }
            mode = mode_map.get(search_mode, SearchMode.FULL_TEXT)

            # Build filters
            filters = SearchFilters()

            if speaker_filter:
                filters.speakers = set(speaker_filter)

            if ic_ooc_filter != "All":
                filters.ic_ooc = ic_ooc_filter

            # Perform search
            results = engine.search(
                query=query,
                mode=mode,
                filters=filters,
                max_results=max_results,
                include_context=True,
            )

            # Store results for export
            last_results = results
            last_query = query

            # Format results
            if not results:
                return f"{SI.INFO} No results found for '{query}'"

            return format_search_results(results, query)

        except Exception as e:
            logger.error(f"Search error: {e}", exc_info=True)
            return StatusMessages.error(
                "Search Failed", f"Error searching for '{query}'", str(e)
            )

    def format_search_results(results: List[SearchResult], query: str) -> str:
        """
        Format search results as markdown.

        Args:
            results: List of search results
            query: Original query

        Returns:
            Formatted markdown string
        """
        md = f"### {SI.SUCCESS} Search Results for '{query}'\n\n"
        md += f"Found **{len(results)}** matches\n\n"
        md += "---\n\n"

        for i, result in enumerate(results, 1):
            seg = result.segment

            # Result header
            md += f"#### Result {i}: [{seg.session_id}] {seg.timestamp_str}\n\n"
            md += f"**Speaker:** {seg.speaker} | **Type:** {seg.ic_ooc} | **Score:** {result.relevance_score:.2f}\n\n"

            # Context before
            if result.context_before:
                md += "**Context:**\n"
                for ctx in result.context_before:
                    md += f"> {ctx}\n"
                md += "\n"

            # IMPROVEMENT 2: Highlight the matched text within the full segment
            # This makes it easier for users to spot the relevant portion
            highlighted_text = seg.text
            # Simple case-insensitive highlighting (works for full-text search)
            # Escape special regex characters in query for highlighting
            escaped_query = re.escape(query)
            highlighted_text = re.sub(
                f"({escaped_query})",
                r"**\1**",
                seg.text,
                flags=re.IGNORECASE
            )

            # Main result (with match context)
            md += f"**Match:** _{result.match_text}_\n\n"
            md += f"**Full Text:** {highlighted_text}\n\n"

            # Context after
            if result.context_after:
                for ctx in result.context_after:
                    md += f"> {ctx}\n"
                md += "\n"

            md += "---\n\n"

        return md

    def export_results(format_type: str) -> str:
        """
        Export search results to specified format.

        Args:
            format_type: "json", "csv", "txt", or "md"

        Returns:
            Status message
        """
        nonlocal last_results, last_query

        if not last_results:
            return f"{SI.WARNING} No results to export. Run a search first."

        try:
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"search_results_{timestamp}.{format_type}"
            output_path = output_dir / filename

            exporter = SearchResultExporter()

            success = False
            if format_type == "json":
                success = exporter.export_to_json(last_results, output_path)
            elif format_type == "csv":
                success = exporter.export_to_csv(last_results, output_path)
            elif format_type == "txt":
                success = exporter.export_to_txt(last_results, output_path, last_query)
            elif format_type == "md":
                success = exporter.export_to_markdown(
                    last_results, output_path, last_query
                )
            else:
                return f"{SI.ERROR} Unknown format: {format_type}"

            if success:
                return f"{SI.SUCCESS} Exported {len(last_results)} results to {filename}"
            else:
                return StatusMessages.error(
                    "Export Failed", f"Unable to export to {format_type}"
                )

        except Exception as e:
            logger.error(f"Export error: {e}", exc_info=True)
            return StatusMessages.error(
                "Export Failed",
                f"Error exporting to {format_type}",
                "See logs for details.",
            )

    # Create UI
    with gr.Tab("Search"):
        gr.Markdown(
            """
        ### [SEARCH] Transcript Search

        Search across all processed session transcripts with advanced filters.

        **Features:**
        - Full-text search (case-insensitive substring matching)
        - Regular expression support (advanced pattern matching)
        - Exact phrase matching
        - Filter by speaker, IC/OOC, session
        - Export results to JSON/CSV/TXT/Markdown

        **Tips:**
        - Use regex for variations: `(dragon|wyrm|beast)` finds any of those terms
        - Combine filters: Search "attack" + Speaker "DM" + IC to find DM combat descriptions
        - Export to Markdown for session recaps and documentation
        """
        )

        with gr.Row():
            index_status = gr.Markdown(f"{SI.LOADING} Initializing search index...")
            rebuild_btn = gr.Button(
                f"{SI.ACTION_REFRESH} Rebuild Index", size="sm", variant="secondary"
            )

        with gr.Row():
            with gr.Column(scale=3):
                search_query = gr.Textbox(
                    label="Search Query",
                    placeholder="Enter search term, phrase, or regex pattern...",
                    lines=2,
                    info="Type your search query and press Enter or click Search",
                )

            with gr.Column(scale=1):
                search_mode = gr.Radio(
                    label="Search Mode",
                    choices=["Full Text", "Regex", "Exact"],
                    value="Full Text",
                    info="Full Text: substring match | Regex: pattern match | Exact: phrase match",
                )

        with gr.Row():
            speaker_filter = gr.Dropdown(
                label="Filter by Speaker",
                choices=[],
                multiselect=True,
                info="Leave empty to search all speakers",
            )

            ic_ooc_filter = gr.Radio(
                label="Filter by Type",
                choices=["All", "IC", "OOC"],
                value="All",
                info="IC: In-character | OOC: Out-of-character",
            )

            max_results = gr.Slider(
                label="Max Results",
                minimum=10,
                maximum=500,
                value=100,
                step=10,
                info="Limit number of results to display",
            )

        search_btn = gr.Button(
            f"{SI.ACTION_SEARCH} Search", variant="primary", size="lg"
        )

        results_display = gr.Markdown(
            f"{SI.INFO} Enter a query above and click Search to begin"
        )

        # Export buttons
        with gr.Row():
            gr.Markdown("**Export Results:**")

        with gr.Row():
            export_json_btn = gr.Button(
                f"{SI.ACTION_DOWNLOAD} JSON",
                size="sm",
                variant="secondary",
            )
            export_csv_btn = gr.Button(
                f"{SI.ACTION_DOWNLOAD} CSV",
                size="sm",
                variant="secondary",
            )
            export_txt_btn = gr.Button(
                f"{SI.ACTION_DOWNLOAD} TXT",
                size="sm",
                variant="secondary",
            )
            export_md_btn = gr.Button(
                f"{SI.ACTION_DOWNLOAD} Markdown",
                size="sm",
                variant="secondary",
            )

        export_status = gr.Markdown("")

        # Event handlers
        search_btn.click(
            fn=perform_search,
            inputs=[
                search_query,
                search_mode,
                speaker_filter,
                ic_ooc_filter,
                max_results,
            ],
            outputs=[results_display],
        )

        search_query.submit(
            fn=perform_search,
            inputs=[
                search_query,
                search_mode,
                speaker_filter,
                ic_ooc_filter,
                max_results,
            ],
            outputs=[results_display],
        )

        rebuild_btn.click(
            fn=rebuild_index, outputs=[index_status, speaker_filter]
        )

        # Export handlers
        export_json_btn.click(
            fn=lambda: export_results("json"), outputs=[export_status]
        )

        export_csv_btn.click(
            fn=lambda: export_results("csv"), outputs=[export_status]
        )

        export_txt_btn.click(
            fn=lambda: export_results("txt"), outputs=[export_status]
        )

        export_md_btn.click(
            fn=lambda: export_results("md"), outputs=[export_status]
        )

    # IMPROVEMENT 1: Auto-initialize index on tab load
    # This provides better UX by automatically preparing the search index
    # when the user navigates to the Search tab
    def on_tab_load():
        """Initialize index when tab loads."""
        return initialize_index()

    # Trigger initialization when the hosting Blocks finishes loading (if provided).
    if ui_container is not None:
        ui_container.load(fn=on_tab_load, outputs=[index_status, speaker_filter])
