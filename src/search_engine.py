"""
Search Engine - Full-text search across transcript index.

This module provides comprehensive search functionality for D&D session transcripts,
including full-text search, regex matching, and advanced filtering capabilities.

Author: Claude (Sonnet 4.5)
Date: 2025-11-17
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Set, Tuple

from src.transcript_indexer import TranscriptIndex, TranscriptSegment

logger = logging.getLogger("DDSessionProcessor.search_engine")


class SearchMode(Enum):
    """Search mode options."""

    FULL_TEXT = "fulltext"  # Case-insensitive substring match
    REGEX = "regex"  # Regular expression
    EXACT = "exact"  # Exact phrase match


@dataclass
class SearchFilters:
    """
    Filters for narrowing search results.

    All filters are optional and can be combined to narrow the search space.
    """

    speakers: Optional[Set[str]] = None  # Filter by speaker names
    ic_ooc: Optional[str] = None  # "IC", "OOC", or None for both
    session_ids: Optional[Set[str]] = None  # Filter by session IDs
    time_range: Optional[Tuple[float, float]] = None  # (min_seconds, max_seconds) within each session
    min_timestamp: Optional[str] = None  # Minimum timestamp across all sessions (session_date)
    max_timestamp: Optional[str] = None  # Maximum timestamp across all sessions


@dataclass
class SearchResult:
    """
    A single search result with context.

    Represents one matching segment from the transcript index,
    including surrounding context for better understanding.
    """

    segment: TranscriptSegment  # The matching segment
    match_text: str  # The matched portion (with surrounding context)
    context_before: List[str] = field(default_factory=list)  # 2 segments before
    context_after: List[str] = field(default_factory=list)  # 2 segments after
    relevance_score: float = 1.0  # For ranking (higher is better)


class SearchEngine:
    """
    Full-text search engine for transcript data.

    Features:
    - Full-text search (case-insensitive)
    - Regular expression support
    - Exact phrase matching
    - Speaker filtering
    - IC/OOC filtering
    - Time range filtering
    - Session filtering
    - Context display (surrounding segments)
    - Result ranking by relevance

    Example usage:
        engine = SearchEngine(index)
        results = engine.search(
            query="dragon",
            mode=SearchMode.FULL_TEXT,
            filters=SearchFilters(speakers={"DM"}),
            max_results=50
        )
    """

    def __init__(self, index: TranscriptIndex):
        """
        Initialize search engine with an index.

        Args:
            index: TranscriptIndex to search
        """
        self.index = index

    def search(
        self,
        query: str,
        mode: SearchMode = SearchMode.FULL_TEXT,
        filters: Optional[SearchFilters] = None,
        max_results: int = 100,
        include_context: bool = True,
    ) -> List[SearchResult]:
        """
        Search the transcript index.

        Args:
            query: Search query string
            mode: Search mode (fulltext, regex, exact)
            filters: Optional filters to narrow results
            max_results: Maximum number of results to return
            include_context: Whether to include surrounding segments

        Returns:
            List of SearchResult objects, sorted by relevance (highest first)

        Raises:
            No exceptions - returns empty list on error after logging
        """
        # Allow empty queries for filter-only searches
        # If no query and no filters, return empty results
        if not query or not query.strip():
            if not filters:
                logger.warning("Empty query and no filters provided")
                return []
            # Filter-only search (no text matching)
            query = ""
        else:
            query = query.strip()

        results: List[SearchResult] = []

        # Compile regex pattern if needed
        pattern = None
        if mode == SearchMode.REGEX:
            try:
                pattern = re.compile(query, re.IGNORECASE)
            except re.error as e:
                logger.error(f"Invalid regex pattern: {query} - {e}")
                return []
        elif mode == SearchMode.EXACT:
            # Exact match uses escaped regex
            pattern = re.compile(re.escape(query), re.IGNORECASE)

        # FIX: Use enumerate to track index for efficient context extraction
        # Search through segments
        for idx, segment in enumerate(self.index.segments):
            # Apply filters first (cheap operation)
            if not self._passes_filters(segment, filters):
                continue

            # Check if segment matches query
            match = False
            match_text = ""

            # If query is empty, match all (filter-only search)
            if not query:
                match = True
                match_text = segment.text[:100]  # Show first 100 chars
            elif mode == SearchMode.FULL_TEXT:
                # Case-insensitive substring search
                if query.lower() in segment.text.lower():
                    match = True
                    match_text = self._extract_match(segment.text, query)
            else:
                # Regex or exact match
                if pattern and pattern.search(segment.text):
                    match = True
                    match_obj = pattern.search(segment.text)
                    match_text = match_obj.group(0) if match_obj else query

            if match:
                result = SearchResult(
                    segment=segment,
                    match_text=match_text,
                    relevance_score=self._calculate_relevance(segment, query),
                )

                if include_context:
                    # Pass index directly instead of searching for it (O(1) vs O(n))
                    result.context_before, result.context_after = self._get_context(
                        idx, segment
                    )

                results.append(result)

                # Stop if we hit max results (optimization)
                if len(results) >= max_results:
                    break

        # Sort by relevance (highest score first)
        results.sort(key=lambda r: r.relevance_score, reverse=True)

        logger.info(f"Search '{query}' returned {len(results)} results")
        return results

    def _passes_filters(
        self, segment: TranscriptSegment, filters: Optional[SearchFilters]
    ) -> bool:
        """
        Check if segment passes all filters.

        Args:
            segment: Segment to check
            filters: Search filters to apply

        Returns:
            True if segment passes all filters (or if no filters provided)
        """
        if not filters:
            return True

        # Speaker filter
        if filters.speakers and segment.speaker not in filters.speakers:
            return False

        # IC/OOC filter
        if filters.ic_ooc and segment.ic_ooc != filters.ic_ooc:
            return False

        # Session ID filter
        if filters.session_ids and segment.session_id not in filters.session_ids:
            return False

        # Time range filter (within session, in seconds)
        if filters.time_range:
            min_time, max_time = filters.time_range
            if not (min_time <= segment.timestamp <= max_time):
                return False

        # Date range filter (across sessions, by session_date string)
        if filters.min_timestamp and segment.session_date:
            if segment.session_date < filters.min_timestamp:
                return False

        if filters.max_timestamp and segment.session_date:
            if segment.session_date > filters.max_timestamp:
                return False

        return True

    def _extract_match(
        self, text: str, query: str, context_chars: int = 50
    ) -> str:
        """
        Extract the matched portion with surrounding context.

        Args:
            text: Full text of the segment
            query: Search query
            context_chars: Characters of context on each side

        Returns:
            Matched text with surrounding context (with ellipses if truncated)
        """
        # Find match position (case-insensitive)
        match_pos = text.lower().find(query.lower())
        if match_pos == -1:
            # Fallback if match not found (shouldn't happen)
            return text[:100]

        # Extract with context
        start = max(0, match_pos - context_chars)
        end = min(len(text), match_pos + len(query) + context_chars)

        excerpt = text[start:end]

        # Add ellipsis if truncated
        if start > 0:
            excerpt = "..." + excerpt
        if end < len(text):
            excerpt = excerpt + "..."

        return excerpt

    def _calculate_relevance(self, segment: TranscriptSegment, query: str) -> float:
        """
        Calculate relevance score for ranking.

        Scoring factors:
        - Query frequency in text (more matches = higher score)
        - IC content boost (story content is often more relevant)
        - Match position (earlier matches may be more important)

        Args:
            segment: Segment to score
            query: Search query (can be empty for filter-only searches)

        Returns:
            Relevance score (higher is better, typically 1.0-5.0)
        """
        score = 1.0

        # For filter-only searches (empty query), use timestamp as score
        if not query:
            # More recent segments get slightly higher scores
            score += segment.timestamp * 0.0001
            if segment.ic_ooc == "IC":
                score += 0.2
            return score

        # Boost score if query appears multiple times
        count = segment.text.lower().count(query.lower())
        score += count * 0.5

        # Boost IC segments slightly (assuming IC content more important)
        if segment.ic_ooc == "IC":
            score += 0.2

        # Boost if match is closer to start of text (title/topic match)
        # FIX: Check for empty text to avoid ZeroDivisionError
        match_pos = segment.text.lower().find(query.lower())
        if match_pos != -1 and len(segment.text) > 0:
            # Position score: 1.0 at start, 0.0 at end
            position_score = 1.0 - (match_pos / len(segment.text))
            score += position_score * 0.3

        return score

    def _get_context(
        self, idx: int, segment: TranscriptSegment
    ) -> Tuple[List[str], List[str]]:
        """
        Get context segments (before and after).

        Retrieves up to 2 segments before and 2 segments after the target segment,
        but only from the same session (stops at session boundaries).

        FIX: Accept index directly instead of searching for it (O(1) vs O(n)).

        Args:
            idx: Index of segment in self.index.segments
            segment: Target segment

        Returns:
            Tuple of (context_before, context_after) as lists of formatted text
        """
        context_before = []
        context_after = []

        # Get 2 segments before (same session only)
        for i in range(max(0, idx - 2), idx):
            prev_segment = self.index.segments[i]
            if prev_segment.session_id == segment.session_id:
                context_before.append(
                    f"[{prev_segment.speaker}] {prev_segment.text}"
                )
            else:
                # Different session, stop looking back
                break

        # Get 2 segments after (same session only)
        for i in range(idx + 1, min(len(self.index.segments), idx + 3)):
            next_segment = self.index.segments[i]
            if next_segment.session_id == segment.session_id:
                context_after.append(f"[{next_segment.speaker}] {next_segment.text}")
            else:
                # Different session, stop looking forward
                break

        return context_before, context_after
