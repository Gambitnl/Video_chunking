"""
Search Result Exporter - Export search results to various formats.

This module provides functionality to export search results to multiple formats
for different use cases: JSON for programmatic access, CSV for spreadsheets,
TXT for simple reading, and Markdown for documentation.

Author: Claude (Sonnet 4.5)
Date: 2025-11-17
"""
from __future__ import annotations

import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List

from src.search_engine import SearchResult

logger = logging.getLogger("DDSessionProcessor.search_exporter")


class SearchResultExporter:
    """
    Export search results to various formats.

    Supported formats:
    - JSON (structured data for programmatic access)
    - CSV (spreadsheet-friendly tabular format)
    - TXT (plain text for simple reading)
    - Markdown (formatted text for wikis/documentation)

    All exports include metadata (session ID, timestamp, speaker, IC/OOC)
    and the matched text with optional context.
    """

    @staticmethod
    def export_to_json(results: List[SearchResult], output_path: Path) -> bool:
        """
        Export results to JSON format.

        Creates a structured JSON file with all result metadata and context.
        Suitable for programmatic access or further processing.

        Args:
            results: Search results to export
            output_path: Path to output file

        Returns:
            True if successful, False if export failed
        """
        try:
            data = {
                "exported_at": datetime.now().isoformat(),
                "result_count": len(results),
                "results": [],
            }

            for result in results:
                seg = result.segment
                data["results"].append(
                    {
                        "session_id": seg.session_id,
                        "session_date": seg.session_date,
                        "timestamp": seg.timestamp,
                        "timestamp_str": seg.timestamp_str,
                        "speaker": seg.speaker,
                        "text": seg.text,
                        "ic_ooc": seg.ic_ooc,
                        "match_text": result.match_text,
                        "relevance_score": result.relevance_score,
                        "context_before": result.context_before,
                        "context_after": result.context_after,
                    }
                )

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info(f"Exported {len(results)} results to JSON: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export to JSON: {e}", exc_info=True)
            return False

    @staticmethod
    def export_to_csv(results: List[SearchResult], output_path: Path) -> bool:
        """
        Export results to CSV format.

        Creates a spreadsheet-compatible CSV file with key metadata.
        Context segments are not included to keep the CSV compact.

        Args:
            results: Search results to export
            output_path: Path to output file

        Returns:
            True if successful, False if export failed
        """
        try:
            with open(output_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)

                # Header row
                writer.writerow(
                    [
                        "Session ID",
                        "Session Date",
                        "Timestamp",
                        "Speaker",
                        "IC/OOC",
                        "Text",
                        "Match Text",
                        "Relevance Score",
                    ]
                )

                # Data rows
                for result in results:
                    seg = result.segment
                    writer.writerow(
                        [
                            seg.session_id,
                            seg.session_date or "",
                            seg.timestamp_str,
                            seg.speaker,
                            seg.ic_ooc,
                            seg.text,
                            result.match_text,
                            f"{result.relevance_score:.2f}",
                        ]
                    )

            logger.info(f"Exported {len(results)} results to CSV: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export to CSV: {e}", exc_info=True)
            return False

    @staticmethod
    def export_to_txt(
        results: List[SearchResult], output_path: Path, query: str = ""
    ) -> bool:
        """
        Export results to plain text format.

        Creates a human-readable text file with formatted results.
        Includes context segments and all metadata.

        Args:
            results: Search results to export
            output_path: Path to output file
            query: Original search query (for header)

        Returns:
            True if successful, False if export failed
        """
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                # Header
                f.write(f"Search Results for: {query}\n")
                f.write(f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total Results: {len(results)}\n")
                f.write("=" * 80 + "\n\n")

                # Results
                for i, result in enumerate(results, 1):
                    seg = result.segment

                    f.write(f"Result {i}:\n")
                    f.write(f"  Session: {seg.session_id}")
                    if seg.session_date:
                        f.write(f" ({seg.session_date})")
                    f.write("\n")
                    f.write(f"  Timestamp: {seg.timestamp_str}\n")
                    f.write(f"  Speaker: {seg.speaker} ({seg.ic_ooc})\n")
                    f.write(f"  Relevance: {result.relevance_score:.2f}\n")
                    f.write(f"\n  Text: {seg.text}\n")
                    f.write(f"\n  Match: {result.match_text}\n")

                    # Add context if available
                    if result.context_before:
                        f.write("\n  Context Before:\n")
                        for ctx in result.context_before:
                            f.write(f"    {ctx}\n")

                    if result.context_after:
                        f.write("\n  Context After:\n")
                        for ctx in result.context_after:
                            f.write(f"    {ctx}\n")

                    f.write("-" * 80 + "\n\n")

            logger.info(f"Exported {len(results)} results to TXT: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export to TXT: {e}", exc_info=True)
            return False

    @staticmethod
    def export_to_markdown(
        results: List[SearchResult], output_path: Path, query: str = ""
    ) -> bool:
        """
        Export results to Markdown format.

        Creates a formatted Markdown file suitable for wikis or documentation.
        Includes all metadata and context with proper formatting.

        Args:
            results: Search results to export
            output_path: Path to output file
            query: Original search query (for header)

        Returns:
            True if successful, False if export failed
        """
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                # Header
                f.write(f"# Search Results: {query}\n\n")
                f.write(
                    f"**Exported:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                )
                f.write(f"**Total Results:** {len(results)}\n\n")
                f.write("---\n\n")

                # Results
                for i, result in enumerate(results, 1):
                    seg = result.segment

                    # Result header
                    f.write(
                        f"## Result {i}: [{seg.session_id}] {seg.timestamp_str}\n\n"
                    )

                    # Metadata
                    f.write(
                        f"**Speaker:** {seg.speaker} | **Type:** {seg.ic_ooc} | "
                    )
                    f.write(f"**Score:** {result.relevance_score:.2f}\n\n")

                    # Context before
                    if result.context_before:
                        f.write("**Context:**\n")
                        for ctx in result.context_before:
                            f.write(f"> {ctx}\n")
                        f.write("\n")

                    # Main result (highlighted with emphasis)
                    f.write(f"**Match:** _{result.match_text}_\n\n")
                    f.write(f"**Full Text:** {seg.text}\n\n")

                    # Context after
                    if result.context_after:
                        for ctx in result.context_after:
                            f.write(f"> {ctx}\n")
                        f.write("\n")

                    f.write("---\n\n")

            logger.info(f"Exported {len(results)} results to Markdown: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export to Markdown: {e}", exc_info=True)
            return False
