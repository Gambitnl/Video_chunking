"""
Comprehensive tests for OOC transcript analyzer.

Tests TF-IDF keyword extraction, topic modeling, insights generation,
and multi-session analysis capabilities.
"""
import pytest
from pathlib import Path
from src.analyzer import (
    OOCAnalyzer,
    MultiSessionAnalyzer,
    Keyword,
    Topic,
    SessionInsights,
    DUTCH_STOP_WORDS,
    ENGLISH_STOP_WORDS,
)


@pytest.fixture
def dummy_transcript_file(tmp_path):
    """Create a dummy transcript file for testing."""
    content = """
    Dit is een test. Ja, een hele leuke test. Wat gaan we doen?
    Nog een test, en nog een keer het woord test. De regels, de regels!
    """
    file_path = tmp_path / "transcript.txt"
    file_path.write_text(content, encoding="utf-8")
    return file_path


@pytest.fixture
def empty_transcript_file(tmp_path):
    """Create an empty dummy transcript file."""
    file_path = tmp_path / "empty_transcript.txt"
    file_path.touch()
    return file_path


@pytest.fixture
def long_transcript_file(tmp_path):
    """
    Create a longer transcript for topic modeling.

    Contains multiple themes: gaming, food, travel.
    """
    content = """
    Yesterday we played amazing video game. The graphics were stunning.
    We spent hours exploring virtual worlds and fighting dragons.
    Gaming is really fun hobby for our group.

    Later we went out for pizza. The restaurant had great Italian food.
    Everyone loved the margherita pizza and pasta carbonara.
    Food brings people together in wonderful ways.

    Next month we plan vacation to Spain. Barcelona looks beautiful.
    The beaches and architecture are incredible. Travel expands horizons.
    We should visit museums and try local cuisine during trip.

    Back to gaming topic - new expansion pack releases soon.
    More levels and characters to explore in game world.
    Cannot wait to play together again next weekend.

    Pizza discussion continues - should we order takeout tonight?
    Maybe try different toppings this time. Food choices are important.

    Travel planning is exciting but requires careful preparation.
    Need to book hotels and flights for Barcelona adventure.
    """
    file_path = tmp_path / "long_transcript.txt"
    file_path.write_text(content, encoding="utf-8")
    return file_path


@pytest.fixture
def multiple_transcripts(tmp_path):
    """Create multiple transcript files for multi-session analysis."""
    transcripts = []

    # Session 1: Gaming focus
    session1 = tmp_path / "session1.txt"
    session1.write_text("""
    Playing video games together is amazing fun.
    Graphics and gameplay mechanics are really impressive.
    Spent hours exploring dungeons and fighting monsters.
    """, encoding="utf-8")
    transcripts.append(session1)

    # Session 2: Food focus
    session2 = tmp_path / "session2.txt"
    session2.write_text("""
    Ordered pizza for group tonight. Delicious Italian food.
    Everyone loved margherita and carbonara choices.
    Food brings people together wonderfully.
    """, encoding="utf-8")
    transcripts.append(session2)

    # Session 3: Mixed themes
    session3 = tmp_path / "session3.txt"
    session3.write_text("""
    After gaming session we ordered takeout food.
    Pizza and video games make perfect combination.
    Planning vacation trip soon - maybe Italy for food?
    """, encoding="utf-8")
    transcripts.append(session3)

    return transcripts


class TestOOCAnalyzer:
    """Test suite for OOCAnalyzer class."""

    def test_init_success(self, dummy_transcript_file):
        """Test that the analyzer initializes correctly with a valid file."""
        analyzer = OOCAnalyzer(dummy_transcript_file)
        assert analyzer.text is not None
        assert analyzer.transcript_path == dummy_transcript_file
        assert analyzer.stop_words == (DUTCH_STOP_WORDS | ENGLISH_STOP_WORDS)
        assert analyzer.min_word_length == 3

    def test_init_with_custom_stop_words(self, dummy_transcript_file):
        """Test initialization with custom stop words."""
        custom_stops = {"custom", "stop"}
        analyzer = OOCAnalyzer(dummy_transcript_file, stop_words=custom_stops)
        assert analyzer.stop_words == custom_stops

    def test_init_file_not_found(self):
        """Test that FileNotFoundError is raised for non-existent file."""
        non_existent_path = Path("/non/existent/file.txt")
        with pytest.raises(FileNotFoundError):
            OOCAnalyzer(non_existent_path)

    def test_tokenize_caching(self, dummy_transcript_file):
        """Test that tokenization results are cached."""
        analyzer = OOCAnalyzer(dummy_transcript_file)
        tokens1 = analyzer._tokenize()
        tokens2 = analyzer._tokenize()
        assert tokens1 is tokens2  # Same object reference (cached)

    def test_tokenize_filters_stop_words(self, dummy_transcript_file):
        """Test that stop words are properly filtered."""
        analyzer = OOCAnalyzer(dummy_transcript_file)
        tokens = analyzer._tokenize()

        # Common Dutch stop words should be filtered
        for token in tokens:
            assert token not in DUTCH_STOP_WORDS
            assert token not in ENGLISH_STOP_WORDS

    def test_tokenize_filters_short_words(self, dummy_transcript_file):
        """Test that short words are filtered."""
        analyzer = OOCAnalyzer(dummy_transcript_file, min_word_length=4)
        tokens = analyzer._tokenize()

        # All tokens should be >= 4 characters
        for token in tokens:
            assert len(token) >= 4

    def test_get_keywords_by_frequency(self, dummy_transcript_file):
        """Test basic keyword extraction by frequency."""
        analyzer = OOCAnalyzer(dummy_transcript_file)
        keywords = analyzer.get_keywords_by_frequency(top_n=10)

        # Should return tuples of (word, count)
        assert all(isinstance(kw, tuple) and len(kw) == 2 for kw in keywords)
        assert all(isinstance(kw[0], str) and isinstance(kw[1], int) for kw in keywords)

        # Check expected word
        keywords_dict = dict(keywords)
        assert "test" in keywords_dict
        assert keywords_dict["test"] == 4

    def test_get_keywords_with_different_top_n(self, dummy_transcript_file):
        """Test that top_n parameter works correctly."""
        analyzer = OOCAnalyzer(dummy_transcript_file)

        keywords_top_1 = analyzer.get_keywords_by_frequency(top_n=1)
        assert len(keywords_top_1) == 1
        assert keywords_top_1[0] == ("test", 4)

        keywords_all = analyzer.get_keywords_by_frequency(top_n=10)
        assert len(keywords_all) == 6  # Total unique non-stop words > 2 chars

    def test_get_keywords_from_empty_file(self, empty_transcript_file):
        """Test that keyword extraction handles empty file gracefully."""
        analyzer = OOCAnalyzer(empty_transcript_file)
        keywords = analyzer.get_keywords_by_frequency()
        assert keywords == []

    def test_get_keywords_tfidf(self, dummy_transcript_file):
        """Test TF-IDF keyword extraction."""
        analyzer = OOCAnalyzer(dummy_transcript_file)
        keywords = analyzer.get_keywords(top_n=10, use_tfidf=True)

        # Should return Keyword objects
        assert all(isinstance(kw, Keyword) for kw in keywords)

        # Check that keywords have expected attributes
        if keywords:  # If sklearn available
            kw = keywords[0]
            assert hasattr(kw, 'term')
            assert hasattr(kw, 'score')
            assert hasattr(kw, 'frequency')
            assert hasattr(kw, 'document_frequency')
            assert kw.score > 0
            assert kw.frequency > 0

    def test_get_keywords_tfidf_fallback(self, dummy_transcript_file):
        """Test that TF-IDF falls back gracefully without sklearn."""
        analyzer = OOCAnalyzer(dummy_transcript_file)
        # Force fallback by using use_tfidf=False
        keywords = analyzer.get_keywords(top_n=10, use_tfidf=False)

        # Should still return Keyword objects (from frequency method)
        assert all(isinstance(kw, Keyword) for kw in keywords)

        # Scores should be frequency values
        if keywords:
            assert keywords[0].term == "test"
            assert keywords[0].score == 4.0
            assert keywords[0].frequency == 4

    def test_get_keywords_empty_file(self, empty_transcript_file):
        """Test keyword extraction from empty file."""
        analyzer = OOCAnalyzer(empty_transcript_file)
        keywords = analyzer.get_keywords(top_n=10)
        assert keywords == []

    def test_get_topics_short_transcript(self, dummy_transcript_file):
        """Test that topic modeling is skipped for short transcripts."""
        analyzer = OOCAnalyzer(dummy_transcript_file)
        topics = analyzer.get_topics(num_topics=3, min_words=100)

        # Should return empty list for short transcripts
        assert topics == []

    def test_get_topics_long_transcript(self, long_transcript_file):
        """Test topic extraction from longer transcript."""
        analyzer = OOCAnalyzer(long_transcript_file)
        topics = analyzer.get_topics(num_topics=3, min_words=50)

        # Should extract topics (if sklearn available)
        if topics:  # If sklearn available
            assert len(topics) <= 3
            assert all(isinstance(topic, Topic) for topic in topics)

            # Check topic structure
            topic = topics[0]
            assert hasattr(topic, 'id')
            assert hasattr(topic, 'label')
            assert hasattr(topic, 'keywords')
            assert hasattr(topic, 'coherence_score')
            assert len(topic.keywords) > 0

    def test_get_insights(self, long_transcript_file):
        """Test comprehensive insights generation."""
        analyzer = OOCAnalyzer(long_transcript_file)
        insights = analyzer.get_insights(session_id="test_session")

        # Check insights structure
        assert isinstance(insights, SessionInsights)
        assert insights.session_id == "test_session"
        assert len(insights.keywords) > 0
        assert isinstance(insights.discussion_patterns, dict)
        assert isinstance(insights.diversity_metrics, dict)

        # Check discussion patterns
        patterns = insights.discussion_patterns
        assert "total_words" in patterns
        assert "unique_words" in patterns
        assert "lexical_diversity" in patterns
        assert "num_topics" in patterns
        assert patterns["total_words"] > 0
        assert patterns["unique_words"] > 0
        assert 0 <= patterns["lexical_diversity"] <= 1

        # Check diversity metrics
        metrics = insights.diversity_metrics
        assert "shannon_entropy" in metrics
        assert "lexical_diversity" in metrics
        assert "vocabulary_richness" in metrics
        assert metrics["shannon_entropy"] >= 0
        assert 0 <= metrics["lexical_diversity"] <= 1

    def test_detect_inside_jokes(self, long_transcript_file):
        """Test inside joke detection."""
        analyzer = OOCAnalyzer(long_transcript_file)
        inside_jokes = analyzer._detect_inside_jokes(threshold=3)

        # Should detect some repeated terms
        assert isinstance(inside_jokes, list)
        assert len(inside_jokes) <= 10  # Limited to top 10

    def test_calculate_diversity_metrics(self, long_transcript_file):
        """Test diversity metrics calculation."""
        analyzer = OOCAnalyzer(long_transcript_file)
        metrics = analyzer._calculate_diversity_metrics()

        # Check metric ranges
        assert "shannon_entropy" in metrics
        assert "lexical_diversity" in metrics
        assert "vocabulary_richness" in metrics

        assert metrics["shannon_entropy"] > 0  # Should have some entropy
        assert 0 <= metrics["lexical_diversity"] <= 1
        assert 0 <= metrics["vocabulary_richness"] <= 1

    def test_calculate_diversity_metrics_empty(self, empty_transcript_file):
        """Test diversity metrics with empty file."""
        analyzer = OOCAnalyzer(empty_transcript_file)
        metrics = analyzer._calculate_diversity_metrics()

        # Should return zero metrics
        assert metrics["shannon_entropy"] == 0.0
        assert metrics["lexical_diversity"] == 0.0
        assert metrics["vocabulary_richness"] == 0.0

    def test_calculate_simple_coherence(self, long_transcript_file):
        """Test simplified coherence calculation."""
        analyzer = OOCAnalyzer(long_transcript_file)

        # Create dummy topic keywords
        keywords = [("gaming", 1.0), ("video", 0.8), ("play", 0.6)]
        coherence = analyzer._calculate_simple_coherence(keywords)

        # Should return a score between 0 and 1
        assert 0 <= coherence <= 1

    def test_calculate_simple_coherence_empty(self, dummy_transcript_file):
        """Test coherence with empty keywords."""
        analyzer = OOCAnalyzer(dummy_transcript_file)
        coherence = analyzer._calculate_simple_coherence([])
        assert coherence == 0.0


class TestMultiSessionAnalyzer:
    """Test suite for MultiSessionAnalyzer class."""

    def test_init_success(self, multiple_transcripts):
        """Test successful initialization."""
        analyzer = MultiSessionAnalyzer(
            multiple_transcripts,
            session_ids=["s1", "s2", "s3"]
        )

        assert len(analyzer.analyzers) == 3
        assert analyzer.session_ids == ["s1", "s2", "s3"]

    def test_init_without_session_ids(self, multiple_transcripts):
        """Test initialization without explicit session IDs."""
        analyzer = MultiSessionAnalyzer(multiple_transcripts)

        # Should use file stems as session IDs
        assert len(analyzer.session_ids) == 3
        assert all(isinstance(sid, str) for sid in analyzer.session_ids)

    def test_init_empty_paths(self):
        """Test that ValueError is raised for empty path list."""
        with pytest.raises(ValueError, match="Must provide at least one transcript path"):
            MultiSessionAnalyzer([])

    def test_compare_sessions(self, multiple_transcripts):
        """Test session comparison."""
        analyzer = MultiSessionAnalyzer(
            multiple_transcripts,
            session_ids=["gaming", "food", "mixed"]
        )

        comparison = analyzer.compare_sessions()

        # Check comparison structure
        assert "sessions" in comparison
        assert "insights" in comparison
        assert "common_keywords" in comparison
        assert "total_unique_keywords" in comparison
        assert "unique_keywords_per_session" in comparison
        assert "avg_lexical_diversity" in comparison

        # Check data types
        assert comparison["sessions"] == ["gaming", "food", "mixed"]
        assert len(comparison["insights"]) == 3
        assert isinstance(comparison["common_keywords"], list)
        assert isinstance(comparison["total_unique_keywords"], int)
        assert isinstance(comparison["avg_lexical_diversity"], float)

    def test_track_evolution(self, multiple_transcripts):
        """Test metric evolution tracking."""
        analyzer = MultiSessionAnalyzer(multiple_transcripts)
        evolution = analyzer.track_evolution()

        # Check evolution metrics
        assert "lexical_diversity" in evolution
        assert "shannon_entropy" in evolution
        assert "total_words" in evolution
        assert "unique_words" in evolution

        # Each metric should have 3 values (one per session)
        assert len(evolution["lexical_diversity"]) == 3
        assert len(evolution["shannon_entropy"]) == 3
        assert len(evolution["total_words"]) == 3
        assert len(evolution["unique_words"]) == 3

        # Check value types
        assert all(isinstance(v, float) for v in evolution["lexical_diversity"])
        assert all(isinstance(v, float) for v in evolution["shannon_entropy"])
        assert all(isinstance(v, int) for v in evolution["total_words"])
        assert all(isinstance(v, int) for v in evolution["unique_words"])

    def test_identify_recurring_themes(self, multiple_transcripts):
        """Test recurring theme identification."""
        analyzer = MultiSessionAnalyzer(multiple_transcripts)

        # Find themes appearing in at least 2 sessions
        recurring = analyzer.identify_recurring_themes(min_sessions=2)

        # Should return a list of keywords
        assert isinstance(recurring, list)

        # Keywords should be strings
        assert all(isinstance(kw, str) for kw in recurring)

    def test_identify_recurring_themes_single_session(self, multiple_transcripts):
        """Test recurring themes with threshold = 1 (all themes)."""
        analyzer = MultiSessionAnalyzer(multiple_transcripts)

        # Find themes appearing in at least 1 session (all keywords)
        all_themes = analyzer.identify_recurring_themes(min_sessions=1)

        # Should return many keywords
        assert len(all_themes) > 0


class TestDataClasses:
    """Test data class structures and representations."""

    def test_keyword_dataclass(self):
        """Test Keyword dataclass."""
        kw = Keyword(term="test", score=0.5, frequency=10, document_frequency=2)

        assert kw.term == "test"
        assert kw.score == 0.5
        assert kw.frequency == 10
        assert kw.document_frequency == 2
        assert "test" in repr(kw)
        assert "0.5000" in repr(kw)

    def test_keyword_default_doc_frequency(self):
        """Test Keyword with default document frequency."""
        kw = Keyword(term="test", score=0.5, frequency=10)
        assert kw.document_frequency == 1

    def test_topic_dataclass(self):
        """Test Topic dataclass."""
        topic = Topic(
            id=0,
            label="gaming, video, play",
            keywords=[("gaming", 1.0), ("video", 0.8)],
            coherence_score=0.6,
            document_proportion=0.33
        )

        assert topic.id == 0
        assert topic.label == "gaming, video, play"
        assert len(topic.keywords) == 2
        assert topic.coherence_score == 0.6
        assert "gaming" in repr(topic)

    def test_topic_default_values(self):
        """Test Topic with default values."""
        topic = Topic(
            id=1,
            label="test",
            keywords=[("word", 1.0)]
        )

        assert topic.coherence_score == 0.0
        assert topic.document_proportion == 0.0

    def test_session_insights_dataclass(self):
        """Test SessionInsights dataclass."""
        insights = SessionInsights(
            session_id="test_session",
            keywords=[Keyword("word", 1.0, 5)],
            topics=[Topic(0, "label", [("word", 1.0)])],
            inside_jokes=["joke1", "joke2"],
            discussion_patterns={"total_words": 100},
            diversity_metrics={"shannon_entropy": 3.5}
        )

        assert insights.session_id == "test_session"
        assert len(insights.keywords) == 1
        assert len(insights.topics) == 1
        assert len(insights.inside_jokes) == 2
        assert insights.discussion_patterns["total_words"] == 100
        assert "test_session" in repr(insights)

    def test_session_insights_default_values(self):
        """Test SessionInsights with default values."""
        insights = SessionInsights(session_id="empty")

        assert insights.keywords == []
        assert insights.topics == []
        assert insights.inside_jokes == []
        assert insights.discussion_patterns == {}
        assert insights.diversity_metrics == {}


class TestStopWords:
    """Test stop word sets."""

    def test_dutch_stop_words_contains_common_words(self):
        """Test that Dutch stop words include common words."""
        assert "de" in DUTCH_STOP_WORDS
        assert "het" in DUTCH_STOP_WORDS
        assert "een" in DUTCH_STOP_WORDS
        assert "van" in DUTCH_STOP_WORDS

    def test_english_stop_words_contains_common_words(self):
        """Test that English stop words include common words."""
        assert "the" in ENGLISH_STOP_WORDS
        assert "is" in ENGLISH_STOP_WORDS
        assert "and" in ENGLISH_STOP_WORDS
        assert "of" in ENGLISH_STOP_WORDS

    def test_stop_words_are_sets(self):
        """Test that stop word collections are sets."""
        assert isinstance(DUTCH_STOP_WORDS, set)
        assert isinstance(ENGLISH_STOP_WORDS, set)
