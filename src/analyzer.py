"""Analyzes transcripts for topics, keywords, and other insights."""
from collections import Counter
from pathlib import Path
from typing import List, Dict

# A basic list of Dutch stop words. A more comprehensive list would be better.
STOP_WORDS = set([
    "de", "en", "van", "ik", "te", "dat", "die", "in", "een", "hij", "het", "niet", "zijn",
    "is", "was", "op", "aan", "met", "als", "voor", "had", "er", "maar", "om", "hem",
    "dan", "zou", "of", "wat", "mijn", "men", "dit", "zo", "door", "over", "ze", "zich",
    "bij", "ook", "tot", "je", "mij", "uit", "der", "daar", "haar", "naar", "heb",
    "hoe", "heeft", "hem", "na", "want", "nog", "zal", "u", "nu", "ga", "iets", "doen",
    "al", "ja", "nee", "dan", "dus", "wel"
])

class OOCAnalyzer:
    """Analyzes Out-of-Character transcripts for keywords and topics."""

    def __init__(self, transcript_path: Path):
        """Initializes the analyzer with the path to an OOC transcript file."""
        if not transcript_path.exists():
            raise FileNotFoundError(f"Transcript file not found: {transcript_path}")
        self.transcript_path = transcript_path
        self.text = self.transcript_path.read_text(encoding="utf-8")

    def get_keywords(self, top_n: int = 20) -> List[tuple[str, int]]:
        """
        Extracts the most common keywords from the OOC transcript.

        This is a simple implementation that counts word frequency after removing
        common stop words.

        Args:
            top_n: The number of top keywords to return.

        Returns:
            A list of tuples, where each tuple contains a keyword and its frequency.
        """
        # Simple tokenization and cleaning
        words = self.text.lower().split()
        cleaned_words = [word.strip(".,!?()[]") for word in words]

        # Filter out stop words and short words
        filtered_words = [
            word for word in cleaned_words if word not in STOP_WORDS and len(word) > 2
        ]

        # Count word frequencies
        word_counts = Counter(filtered_words)

        return word_counts.most_common(top_n)
