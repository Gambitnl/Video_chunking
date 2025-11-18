"""
Analyzes transcripts for topics, keywords, and other insights.

This module provides comprehensive text analysis capabilities for OOC (Out-of-Character)
transcripts, including TF-IDF keyword extraction, topic modeling, and insight generation.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import logging

# Import for TF-IDF and topic modeling
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.decomposition import LatentDirichletAllocation
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

# Import for better tokenization and stop words
try:
    import nltk
    from nltk.corpus import stopwords
    from nltk.tokenize import word_tokenize
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False

import re
import math

logger = logging.getLogger(__name__)

# Basic Dutch stop words (fallback if NLTK not available)
DUTCH_STOP_WORDS = set([
    "de", "en", "van", "ik", "te", "dat", "die", "in", "een", "hij", "het", "niet", "zijn",
    "is", "was", "op", "aan", "met", "als", "voor", "had", "er", "maar", "om", "hem",
    "dan", "zou", "of", "wat", "mijn", "men", "dit", "zo", "door", "over", "ze", "zich",
    "bij", "ook", "tot", "je", "mij", "uit", "der", "daar", "haar", "naar", "heb",
    "hoe", "heeft", "hem", "na", "want", "nog", "zal", "u", "nu", "ga", "iets", "doen",
    "al", "ja", "nee", "dan", "dus", "wel", "kan", "worden", "hebben", "worden", "veel",
    "meer", "geen", "moet", "kunnen", "waar", "alleen", "komen", "gaan", "maken", "zien",
    "weten", "geven", "worden", "gebruikt", "tussen", "staat", "zonder", "onder", "terug",
    "hier", "laatste", "jaar", "twee", "grote", "nieuwe", "eigen", "bijvoorbeeld"
])

# English stop words (for bilingual support)
ENGLISH_STOP_WORDS = set([
    "the", "be", "to", "of", "and", "a", "in", "that", "have", "i", "it", "for", "not",
    "on", "with", "he", "as", "you", "do", "at", "this", "but", "his", "by", "from",
    "they", "we", "say", "her", "she", "or", "an", "will", "my", "one", "all", "would",
    "there", "their", "what", "so", "up", "out", "if", "about", "who", "get", "which",
    "go", "me", "when", "make", "can", "like", "time", "no", "just", "him", "know",
    "take", "people", "into", "year", "your", "good", "some", "could", "them", "see",
    "other", "than", "then", "now", "look", "only", "come", "its", "over", "think",
    "also", "back", "after", "use", "two", "how", "our", "work", "first", "well",
    "way", "even", "new", "want", "because", "any", "these", "give", "day", "most", "us"
])

# Combined stop words
DEFAULT_STOP_WORDS = DUTCH_STOP_WORDS | ENGLISH_STOP_WORDS


@dataclass
class Keyword:
    """Represents a keyword with associated metrics."""
    term: str
    score: float  # TF-IDF score or frequency score
    frequency: int  # Raw count in document
    document_frequency: int = 1  # Number of documents containing term (for TF-IDF)

    def __repr__(self) -> str:
        return f"Keyword(term='{self.term}', score={self.score:.4f}, freq={self.frequency})"


@dataclass
class Topic:
    """Represents a discovered topic with keywords and metadata."""
    id: int
    label: str  # Generated from top keywords
    keywords: List[Tuple[str, float]]  # (term, weight) pairs
    coherence_score: float = 0.0  # Quality metric for topic
    document_proportion: float = 0.0  # Percentage of documents with this topic

    def __repr__(self) -> str:
        top_3 = ", ".join([kw[0] for kw in self.keywords[:3]])
        return f"Topic(id={self.id}, label='{self.label}', top_keywords=[{top_3}])"


@dataclass
class SessionInsights:
    """Comprehensive insights from OOC transcript analysis."""
    session_id: str
    keywords: List[Keyword] = field(default_factory=list)
    topics: List[Topic] = field(default_factory=list)
    inside_jokes: List[str] = field(default_factory=list)  # High-frequency unique terms
    discussion_patterns: Dict[str, any] = field(default_factory=dict)  # Topic metadata
    diversity_metrics: Dict[str, float] = field(default_factory=dict)  # Shannon entropy, etc.

    def __repr__(self) -> str:
        return (
            f"SessionInsights(session='{self.session_id}', "
            f"keywords={len(self.keywords)}, topics={len(self.topics)})"
        )


class OOCAnalyzer:
    """
    Analyzes Out-of-Character transcripts for keywords and topics.

    Supports both simple frequency analysis and advanced TF-IDF-based
    keyword extraction with topic modeling capabilities.
    """

    def __init__(
        self,
        transcript_path: Path,
        stop_words: Optional[set] = None,
        min_word_length: int = 3,
    ):
        """
        Initialize the analyzer with a transcript file.

        Args:
            transcript_path: Path to the OOC transcript file
            stop_words: Custom set of stop words (uses default if None)
            min_word_length: Minimum word length to consider (default: 3)

        Raises:
            FileNotFoundError: If transcript file doesn't exist
        """
        if not transcript_path.exists():
            raise FileNotFoundError(f"Transcript file not found: {transcript_path}")

        self.transcript_path = transcript_path
        self.text = self.transcript_path.read_text(encoding="utf-8")
        self.stop_words = stop_words if stop_words is not None else DEFAULT_STOP_WORDS
        self.min_word_length = min_word_length

        # Cache for processed data
        self._tokens: Optional[List[str]] = None
        self._tfidf_vectorizer: Optional[TfidfVectorizer] = None
        self._tfidf_matrix: Optional[any] = None

    def _tokenize(self) -> List[str]:
        """
        Tokenize and clean the transcript text.

        Returns:
            List of cleaned tokens
        """
        if self._tokens is not None:
            return self._tokens

        # Use NLTK tokenizer if available, otherwise simple split
        if NLTK_AVAILABLE:
            try:
                tokens = word_tokenize(self.text.lower(), language='dutch')
            except LookupError:
                # Fallback if Dutch tokenizer not available
                logger.warning("NLTK Dutch tokenizer not available, using simple tokenization")
                tokens = self.text.lower().split()
        else:
            tokens = self.text.lower().split()

        # Clean tokens
        cleaned_tokens = []
        for token in tokens:
            # Remove punctuation
            token = re.sub(r'[^\w\s]', '', token)
            # Filter by length and stop words
            if (
                len(token) >= self.min_word_length
                and token not in self.stop_words
                and token.isalpha()  # Only alphabetic characters
            ):
                cleaned_tokens.append(token)

        self._tokens = cleaned_tokens
        return self._tokens

    def get_keywords_by_frequency(self, top_n: int = 20) -> List[Tuple[str, int]]:
        """
        Extract keywords using simple frequency counting (legacy method).

        Args:
            top_n: Number of top keywords to return

        Returns:
            List of (keyword, frequency) tuples ordered by frequency
        """
        tokens = self._tokenize()

        if not tokens:
            return []

        word_counts = Counter(tokens)
        return word_counts.most_common(top_n)

    def get_keywords(
        self,
        top_n: int = 20,
        use_tfidf: bool = True,
    ) -> List[Keyword]:
        """
        Extract keywords from the transcript using TF-IDF or frequency.

        Args:
            top_n: Number of top keywords to return
            use_tfidf: Use TF-IDF scoring (True) or simple frequency (False)

        Returns:
            List of Keyword objects ordered by score
        """
        if not use_tfidf or not SKLEARN_AVAILABLE:
            # Fall back to frequency-based extraction
            freq_keywords = self.get_keywords_by_frequency(top_n)
            return [
                Keyword(term=term, score=float(freq), frequency=freq, document_frequency=1)
                for term, freq in freq_keywords
            ]

        # TF-IDF-based extraction
        tokens = self._tokenize()

        if not tokens:
            return []

        # Create TF-IDF vectorizer
        # Note: For single document, TF-IDF == TF (no IDF component)
        # This is still useful as it normalizes by document length
        vectorizer = TfidfVectorizer(
            max_features=min(1000, len(set(tokens))),
            stop_words=None,  # We already filtered stop words
            lowercase=False,  # Already lowercased
            token_pattern=r'\b\w+\b',
        )

        # Reconstruct text from tokens for vectorizer
        text_for_tfidf = " ".join(tokens)

        try:
            tfidf_matrix = vectorizer.fit_transform([text_for_tfidf])
            feature_names = vectorizer.get_feature_names_out()

            # Get TF-IDF scores
            tfidf_scores = tfidf_matrix.toarray()[0]

            # Create keyword objects
            keywords = []
            word_counts = Counter(tokens)

            for term, score in zip(feature_names, tfidf_scores):
                if score > 0:  # Only non-zero scores
                    keywords.append(
                        Keyword(
                            term=term,
                            score=score,
                            frequency=word_counts[term],
                            document_frequency=1
                        )
                    )

            # Sort by score and return top N
            keywords.sort(key=lambda k: k.score, reverse=True)
            return keywords[:top_n]

        except Exception as e:
            logger.error(f"TF-IDF extraction failed: {e}. Falling back to frequency.")
            # Fall back to frequency-based
            freq_keywords = self.get_keywords_by_frequency(top_n)
            return [
                Keyword(term=term, score=float(freq), frequency=freq, document_frequency=1)
                for term, freq in freq_keywords
            ]

    def get_topics(
        self,
        num_topics: int = 5,
        words_per_topic: int = 10,
        min_words: int = 100,
    ) -> List[Topic]:
        """
        Extract topics from the transcript using LDA topic modeling.

        Args:
            num_topics: Number of topics to extract
            words_per_topic: Number of keywords per topic
            min_words: Minimum word count required for topic modeling

        Returns:
            List of Topic objects

        Raises:
            ValueError: If transcript is too short for topic modeling
        """
        if not SKLEARN_AVAILABLE:
            logger.warning("scikit-learn not available. Topic modeling disabled.")
            return []

        tokens = self._tokenize()

        if len(tokens) < min_words:
            logger.warning(
                f"Transcript too short for topic modeling "
                f"({len(tokens)} words < {min_words} required)"
            )
            return []

        # Reconstruct text from tokens
        text_for_lda = " ".join(tokens)

        try:
            # Create TF-IDF vectorizer for LDA input
            vectorizer = TfidfVectorizer(
                max_features=500,
                stop_words=None,
                lowercase=False,
                token_pattern=r'\b\w+\b',
            )

            tfidf_matrix = vectorizer.fit_transform([text_for_lda])
            feature_names = vectorizer.get_feature_names_out()

            # Calculate optimal number of components
            # Ensure at least 1 topic, max num_topics requested
            optimal_components = max(1, min(num_topics, len(feature_names) // 10))

            # Guard against edge case: not enough features for topic modeling
            if optimal_components < 1 or len(feature_names) < 5:
                logger.warning(
                    f"Insufficient features for topic modeling "
                    f"(features={len(feature_names)}, min=5)"
                )
                return []

            # Fit LDA model
            lda = LatentDirichletAllocation(
                n_components=optimal_components,
                max_iter=50,  # Increased from 10 for better topic quality
                learning_method='online',
                random_state=42,
                n_jobs=-1,  # Use all CPUs
            )

            lda.fit(tfidf_matrix)

            # Extract topics
            topics = []
            for topic_idx, topic_dist in enumerate(lda.components_):
                # Get top words for this topic
                top_indices = topic_dist.argsort()[-words_per_topic:][::-1]
                top_keywords = [
                    (feature_names[i], float(topic_dist[i]))
                    for i in top_indices
                ]

                # Generate label from top 3 keywords
                label = ", ".join([kw[0] for kw in top_keywords[:3]])

                # Calculate approximate coherence (simplified)
                # Real coherence would require external reference corpus
                coherence = self._calculate_simple_coherence(top_keywords)

                topics.append(
                    Topic(
                        id=topic_idx,
                        label=label,
                        keywords=top_keywords,
                        coherence_score=coherence,
                        document_proportion=1.0 / num_topics,  # Simplified assumption
                    )
                )

            return topics

        except Exception as e:
            logger.error(f"Topic modeling failed: {e}")
            return []

    def _calculate_simple_coherence(self, keywords: List[Tuple[str, float]]) -> float:
        """
        Calculate a simplified coherence score for a topic.

        **IMPORTANT**: This is a custom heuristic, not a standard coherence metric.
        It does NOT align with academic metrics like C_v, NPMI, or UCI coherence.

        This simplified implementation measures keyword co-occurrence within
        sliding windows. For production use or research, consider using
        gensim.models.coherencemodel for standard metrics.

        Algorithm:
        - Counts windows (10 tokens) where 2+ topic keywords co-occur
        - Normalizes by total number of windows
        - Scaled and capped at 1.0

        Args:
            keywords: List of (word, weight) tuples

        Returns:
            Coherence score between 0 and 1 (higher = more coherent)
            Note: Scores are NOT comparable to standard coherence metrics
        """
        if not keywords:
            return 0.0

        # Extract just the words
        words = [kw[0] for kw in keywords]

        # Count co-occurrences in windows
        window_size = 10
        tokens = self._tokenize()

        co_occurrence_count = 0
        total_windows = len(tokens) - window_size + 1

        if total_windows <= 0:
            return 0.0

        for i in range(total_windows):
            window = tokens[i:i + window_size]
            # Count how many topic words appear in this window
            matches = sum(1 for word in words if word in window)
            if matches >= 2:  # At least 2 topic words co-occur
                co_occurrence_count += 1

        # Normalize by total windows
        coherence = co_occurrence_count / total_windows
        return min(coherence * 2, 1.0)  # Scale up and cap at 1.0

    def get_insights(self, session_id: str = "unknown") -> SessionInsights:
        """
        Generate comprehensive insights from the OOC transcript.

        Args:
            session_id: Identifier for the session (for tracking)

        Returns:
            SessionInsights object with keywords, topics, and patterns
        """
        insights = SessionInsights(session_id=session_id)

        # Extract keywords
        insights.keywords = self.get_keywords(top_n=30, use_tfidf=True)

        # Extract topics (if enough content)
        insights.topics = self.get_topics(num_topics=5, words_per_topic=10)

        # Detect potential inside jokes
        # Inside jokes are high-frequency unique terms (low IDF, high TF)
        insights.inside_jokes = self._detect_inside_jokes()

        # Calculate diversity metrics
        insights.diversity_metrics = self._calculate_diversity_metrics()

        # Discussion patterns
        insights.discussion_patterns = {
            "total_words": len(self._tokenize()),
            "unique_words": len(set(self._tokenize())),
            "lexical_diversity": (
                len(set(self._tokenize())) / len(self._tokenize())
                if len(self._tokenize()) > 0
                else 0.0
            ),
            "num_topics": len(insights.topics),
        }

        return insights

    def _detect_inside_jokes(self, threshold: int = 5) -> List[str]:
        """
        Detect potential inside jokes based on repetition patterns.

        Inside jokes are characterized by:
        - High frequency within the session
        - Unusual or uncommon words

        Args:
            threshold: Minimum frequency to consider as inside joke

        Returns:
            List of potential inside joke terms
        """
        word_counts = Counter(self._tokenize())

        # Filter for high-frequency terms
        candidates = [
            word for word, count in word_counts.items()
            if count >= threshold
        ]

        # Further filter for "unusual" words (longer length, less common patterns)
        inside_jokes = []
        for word in candidates:
            # Heuristic: longer words (>6 chars) or repeated many times
            if len(word) > 6 or word_counts[word] > 10:
                inside_jokes.append(word)

        return inside_jokes[:10]  # Limit to top 10

    def _calculate_diversity_metrics(self) -> Dict[str, float]:
        """
        Calculate text diversity metrics.

        Returns:
            Dictionary of diversity metrics
        """
        tokens = self._tokenize()

        if not tokens:
            return {
                "shannon_entropy": 0.0,
                "lexical_diversity": 0.0,
                "vocabulary_richness": 0.0,
            }

        word_counts = Counter(tokens)
        total_words = len(tokens)
        unique_words = len(word_counts)

        # Shannon entropy
        shannon_entropy = 0.0
        for count in word_counts.values():
            probability = count / total_words
            shannon_entropy -= probability * math.log2(probability)

        # Lexical diversity (type-token ratio)
        lexical_diversity = unique_words / total_words if total_words > 0 else 0.0

        # Vocabulary richness (log-adjusted TTR)
        vocab_richness = (
            math.log(unique_words) / math.log(total_words)
            if total_words > 1
            else 0.0
        )

        return {
            "shannon_entropy": shannon_entropy,
            "lexical_diversity": lexical_diversity,
            "vocabulary_richness": vocab_richness,
        }


class MultiSessionAnalyzer:
    """
    Analyzes patterns across multiple OOC transcripts.

    Provides comparative analysis, topic tracking, and theme identification
    across multiple sessions.
    """

    def __init__(self, transcript_paths: List[Path], session_ids: Optional[List[str]] = None):
        """
        Initialize multi-session analyzer.

        Args:
            transcript_paths: List of paths to OOC transcript files
            session_ids: Optional list of session identifiers (uses filenames if None)

        Raises:
            ValueError: If transcript_paths is empty
        """
        if not transcript_paths:
            raise ValueError("Must provide at least one transcript path")

        self.transcript_paths = transcript_paths
        self.session_ids = session_ids or [
            path.stem for path in transcript_paths
        ]

        # Create analyzers for each session
        self.analyzers = [
            OOCAnalyzer(path) for path in transcript_paths
        ]

        # Cache for aggregated data
        self._all_texts: Optional[List[str]] = None
        self._tfidf_vectorizer: Optional[TfidfVectorizer] = None
        self._tfidf_matrix: Optional[any] = None

    def compare_sessions(self) -> Dict[str, any]:
        """
        Compare keywords and topics across all sessions.

        Returns:
            Dictionary with comparative analysis results
        """
        # Extract insights from each session
        all_insights = [
            analyzer.get_insights(session_id)
            for analyzer, session_id in zip(self.analyzers, self.session_ids)
        ]

        # Compare keyword overlap
        keyword_sets = [
            set(kw.term for kw in insights.keywords)
            for insights in all_insights
        ]

        # Find common and unique keywords
        if len(keyword_sets) > 1:
            common_keywords = set.intersection(*keyword_sets)
            all_keywords = set.union(*keyword_sets)
            unique_keywords_per_session = [
                keywords - common_keywords
                for keywords in keyword_sets
            ]
        else:
            common_keywords = keyword_sets[0] if keyword_sets else set()
            all_keywords = keyword_sets[0] if keyword_sets else set()
            unique_keywords_per_session = [set()]

        return {
            "sessions": self.session_ids,
            "insights": all_insights,
            "common_keywords": list(common_keywords),
            "total_unique_keywords": len(all_keywords),
            "unique_keywords_per_session": [
                list(unique_set) for unique_set in unique_keywords_per_session
            ],
            "avg_lexical_diversity": sum(
                insights.discussion_patterns.get("lexical_diversity", 0.0)
                for insights in all_insights
            ) / len(all_insights) if all_insights else 0.0,
        }

    def track_evolution(self) -> Dict[str, List[float]]:
        """
        Track how discussion metrics evolve across sessions.

        Returns:
            Dictionary mapping metric names to time-series values
        """
        evolution = {
            "lexical_diversity": [],
            "shannon_entropy": [],
            "total_words": [],
            "unique_words": [],
        }

        for analyzer in self.analyzers:
            insights = analyzer.get_insights()

            evolution["lexical_diversity"].append(
                insights.discussion_patterns.get("lexical_diversity", 0.0)
            )
            evolution["shannon_entropy"].append(
                insights.diversity_metrics.get("shannon_entropy", 0.0)
            )
            evolution["total_words"].append(
                insights.discussion_patterns.get("total_words", 0)
            )
            evolution["unique_words"].append(
                insights.discussion_patterns.get("unique_words", 0)
            )

        return evolution

    def identify_recurring_themes(self, min_sessions: int = 2) -> List[str]:
        """
        Identify themes that recur across multiple sessions.

        Args:
            min_sessions: Minimum number of sessions a keyword must appear in

        Returns:
            List of recurring theme keywords
        """
        # Extract keywords from each session
        all_keywords = []
        for analyzer in self.analyzers:
            keywords = analyzer.get_keywords(top_n=20, use_tfidf=True)
            all_keywords.append(set(kw.term for kw in keywords))

        # Count how many sessions each keyword appears in
        keyword_frequency = Counter()
        for keyword_set in all_keywords:
            for keyword in keyword_set:
                keyword_frequency[keyword] += 1

        # Filter for recurring themes
        recurring = [
            keyword for keyword, count in keyword_frequency.items()
            if count >= min_sessions
        ]

        # Sort by frequency
        recurring.sort(key=lambda k: keyword_frequency[k], reverse=True)

        return recurring
