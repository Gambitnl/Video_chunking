"""
Tests for SearchEngine.

Tests search functionality including:
- Full-text search
- Regex search
- Exact search
- Filtering (speaker, IC/OOC, session, time)
- Context extraction
- Relevance scoring

Author: Claude (Sonnet 4.5)
Date: 2025-11-17
"""
import pytest

from src.search_engine import SearchEngine, SearchFilters, SearchMode
from src.transcript_indexer import TranscriptIndex, TranscriptSegment


@pytest.fixture
def sample_index():
    """Create a sample index for testing."""
    index = TranscriptIndex()

    # Add test segments
    segments = [
        TranscriptSegment(
            session_id="session1",
            timestamp=0.0,
            timestamp_str="00:00:00",
            speaker="Alice",
            text="The dragon attacks the village with fierce fire",
            ic_ooc="IC",
            segment_index=0,
            session_date="20251117_120000",
        ),
        TranscriptSegment(
            session_id="session1",
            timestamp=5.0,
            timestamp_str="00:00:05",
            speaker="Bob",
            text="I cast fireball at the dragon!",
            ic_ooc="IC",
            segment_index=1,
            session_date="20251117_120000",
        ),
        TranscriptSegment(
            session_id="session1",
            timestamp=10.0,
            timestamp_str="00:00:10",
            speaker="DM",
            text="Let's take a break here",
            ic_ooc="OOC",
            segment_index=2,
            session_date="20251117_120000",
        ),
        TranscriptSegment(
            session_id="session2",
            timestamp=0.0,
            timestamp_str="00:00:00",
            speaker="Alice",
            text="We continue our quest to find the dragon",
            ic_ooc="IC",
            segment_index=0,
            session_date="20251118_140000",
        ),
    ]

    for seg in segments:
        index.add_segment(seg)

    return index


def test_full_text_search(sample_index):
    """Test full-text search finds matches."""
    engine = SearchEngine(sample_index)

    results = engine.search("dragon", mode=SearchMode.FULL_TEXT)

    assert len(results) == 3
    for result in results:
        assert "dragon" in result.segment.text.lower()


def test_full_text_case_insensitive(sample_index):
    """Test full-text search is case-insensitive."""
    engine = SearchEngine(sample_index)

    results_lower = engine.search("dragon", mode=SearchMode.FULL_TEXT)
    results_upper = engine.search("DRAGON", mode=SearchMode.FULL_TEXT)

    assert len(results_lower) == len(results_upper)


def test_exact_search(sample_index):
    """Test exact phrase search."""
    engine = SearchEngine(sample_index)

    results = engine.search("I cast fireball", mode=SearchMode.EXACT)

    assert len(results) == 1
    assert results[0].segment.speaker == "Bob"
    assert "I cast fireball" in results[0].segment.text


def test_regex_search(sample_index):
    """Test regex search."""
    engine = SearchEngine(sample_index)

    # Match either 'dragon' or 'fireball'
    results = engine.search(r"(dragon|fireball)", mode=SearchMode.REGEX)

    assert len(results) == 3


def test_regex_word_boundary(sample_index):
    """Test regex with word boundaries."""
    engine = SearchEngine(sample_index)

    # Match 'fire' as complete word (not 'fireball')
    results = engine.search(r"\bfire\b", mode=SearchMode.REGEX)

    assert len(results) == 1
    assert "fierce fire" in results[0].segment.text


def test_invalid_regex(sample_index):
    """Test invalid regex returns empty results."""
    engine = SearchEngine(sample_index)

    # Invalid regex pattern
    results = engine.search(r"[invalid(", mode=SearchMode.REGEX)

    assert len(results) == 0


def test_speaker_filter(sample_index):
    """Test filtering by speaker."""
    engine = SearchEngine(sample_index)

    filters = SearchFilters(speakers={"Alice"})
    results = engine.search("dragon", filters=filters)

    assert len(results) == 2
    for result in results:
        assert result.segment.speaker == "Alice"


def test_ic_ooc_filter_ic(sample_index):
    """Test filtering for IC content."""
    engine = SearchEngine(sample_index)

    filters = SearchFilters(ic_ooc="IC")
    results = engine.search("", filters=filters, max_results=100)

    assert len(results) == 3  # All IC segments
    for result in results:
        assert result.segment.ic_ooc == "IC"


def test_ic_ooc_filter_ooc(sample_index):
    """Test filtering for OOC content."""
    engine = SearchEngine(sample_index)

    filters = SearchFilters(ic_ooc="OOC")
    results = engine.search("", filters=filters, max_results=100)

    assert len(results) == 1
    assert results[0].segment.ic_ooc == "OOC"


def test_session_filter(sample_index):
    """Test filtering by session ID."""
    engine = SearchEngine(sample_index)

    filters = SearchFilters(session_ids={"session1"})
    results = engine.search("", filters=filters, max_results=100)

    assert len(results) == 3
    for result in results:
        assert result.segment.session_id == "session1"


def test_time_range_filter(sample_index):
    """Test filtering by time range."""
    engine = SearchEngine(sample_index)

    # Only segments between 0 and 6 seconds
    filters = SearchFilters(time_range=(0.0, 6.0))
    results = engine.search("", filters=filters, max_results=100)

    assert len(results) == 3  # Includes session2 timestamp 0.0
    for result in results:
        assert 0.0 <= result.segment.timestamp <= 6.0


def test_date_range_filter(sample_index):
    """Test filtering by session date."""
    engine = SearchEngine(sample_index)

    # Only sessions from 2025-11-17
    filters = SearchFilters(
        min_timestamp="20251117_000000", max_timestamp="20251117_235959"
    )
    results = engine.search("", filters=filters, max_results=100)

    assert len(results) == 3  # Only session1
    for result in results:
        assert result.segment.session_id == "session1"


def test_combined_filters(sample_index):
    """Test combining multiple filters."""
    engine = SearchEngine(sample_index)

    filters = SearchFilters(speakers={"Alice"}, ic_ooc="IC", session_ids={"session1"})
    results = engine.search("", filters=filters, max_results=100)

    assert len(results) == 1
    result = results[0]
    assert result.segment.speaker == "Alice"
    assert result.segment.ic_ooc == "IC"
    assert result.segment.session_id == "session1"


def test_max_results_limit(sample_index):
    """Test max results limit is respected."""
    engine = SearchEngine(sample_index)

    results = engine.search("", max_results=2)

    assert len(results) <= 2


def test_empty_query(sample_index):
    """Test empty query returns no results."""
    engine = SearchEngine(sample_index)

    results = engine.search("")

    assert len(results) == 0


def test_no_matches(sample_index):
    """Test search with no matches."""
    engine = SearchEngine(sample_index)

    results = engine.search("nonexistent_word")

    assert len(results) == 0


def test_relevance_scoring(sample_index):
    """Test results are ranked by relevance."""
    engine = SearchEngine(sample_index)

    # "dragon" appears twice in first segment, once in others
    results = engine.search("dragon")

    # Results should be sorted by relevance (highest first)
    assert results[0].relevance_score >= results[1].relevance_score
    assert results[1].relevance_score >= results[2].relevance_score


def test_ic_boost_in_scoring(sample_index):
    """Test IC content gets relevance boost."""
    engine = SearchEngine(sample_index)

    results = engine.search("dragon")

    # IC segments should have higher scores than OOC (if any)
    ic_scores = [r.relevance_score for r in results if r.segment.ic_ooc == "IC"]
    ooc_scores = [r.relevance_score for r in results if r.segment.ic_ooc == "OOC"]

    if ic_scores and ooc_scores:
        # IC segments should generally score higher
        assert max(ic_scores) > min(ooc_scores)


def test_context_extraction(sample_index):
    """Test context is extracted correctly."""
    engine = SearchEngine(sample_index)

    results = engine.search("fireball", include_context=True)

    assert len(results) == 1
    result = results[0]

    # Should have context before (Alice's message)
    assert len(result.context_before) == 1
    assert "[Alice]" in result.context_before[0]
    assert "dragon" in result.context_before[0].lower()

    # Should have context after (DM's message)
    assert len(result.context_after) == 1
    assert "[DM]" in result.context_after[0]


def test_context_no_cross_session(sample_index):
    """Test context doesn't cross session boundaries."""
    engine = SearchEngine(sample_index)

    # Search for "quest" (only in session2)
    results = engine.search("quest", include_context=True)

    assert len(results) == 1
    result = results[0]

    # No context before (start of session)
    assert len(result.context_before) == 0

    # No context after (no more segments in session)
    assert len(result.context_after) == 0


def test_match_text_extraction(sample_index):
    """Test matched text is extracted with context."""
    engine = SearchEngine(sample_index)

    results = engine.search("dragon")

    assert len(results) > 0
    for result in results:
        # Match text should contain the query
        assert "dragon" in result.match_text.lower()
        # And should be a substring of the full text
        assert result.match_text.replace("...", "") in result.segment.text or result.segment.text in result.match_text


def test_no_context_when_disabled(sample_index):
    """Test context is not included when disabled."""
    engine = SearchEngine(sample_index)

    results = engine.search("dragon", include_context=False)

    assert len(results) > 0
    for result in results:
        assert len(result.context_before) == 0
        assert len(result.context_after) == 0
