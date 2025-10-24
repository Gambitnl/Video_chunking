
import pytest
from pathlib import Path
from src.analyzer import OOCAnalyzer

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

class TestOOCAnalyzer:

    def test_init_success(self, dummy_transcript_file):
        """Test that the analyzer initializes correctly with a valid file."""
        try:
            analyzer = OOCAnalyzer(dummy_transcript_file)
            assert analyzer.text is not None
        except FileNotFoundError:
            pytest.fail("OOCAnalyzer raised FileNotFoundError unexpectedly.")

    def test_init_file_not_found(self):
        """Test that a FileNotFoundError is raised for a non-existent file."""
        non_existent_path = Path("/non/existent/file.txt")
        with pytest.raises(FileNotFoundError):
            OOCAnalyzer(non_existent_path)

    def test_get_keywords(self, dummy_transcript_file):
        """Test the basic keyword extraction functionality."""
        analyzer = OOCAnalyzer(dummy_transcript_file)
        # Get all keywords to avoid issues with tie-breaking order
        all_keywords = analyzer.get_keywords(top_n=10)
        keywords_dict = dict(all_keywords)

        # Assert the counts of specific words regardless of their order
        assert keywords_dict["test"] == 4
        assert keywords_dict["regels"] == 2
        assert keywords_dict["leuke"] == 1
        assert keywords_dict["hele"] == 1

    def test_get_keywords_with_different_top_n(self, dummy_transcript_file):
        """Test that the top_n parameter works correctly."""
        analyzer = OOCAnalyzer(dummy_transcript_file)
        
        keywords_top_1 = analyzer.get_keywords(top_n=1)
        assert len(keywords_top_1) == 1
        assert keywords_top_1[0] == ("test", 4)

        keywords_all = analyzer.get_keywords(top_n=10) # More than available keywords
        assert len(keywords_all) == 7 # Total unique non-stop words > 2 chars

    def test_get_keywords_from_empty_file(self, empty_transcript_file):
        """Test that keyword extraction handles an empty file gracefully."""
        analyzer = OOCAnalyzer(empty_transcript_file)
        keywords = analyzer.get_keywords()
        assert keywords == []
