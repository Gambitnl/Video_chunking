import pytest
from pathlib import Path
from src.session_search import SessionSearcher

@pytest.fixture
def mock_output_dir(tmp_path: Path) -> Path:
    session1_dir = tmp_path / "20251106_120000_session1"
    session1_dir.mkdir()
    (session1_dir / "session1_full.txt").write_text("Hello world\nThis is a test\nAnother line with hello")

    session2_dir = tmp_path / "20251106_130000_session2"
    session2_dir.mkdir()
    (session2_dir / "session2_full.txt").write_text("This is session two\nNo matches here")

    session3_dir = tmp_path / "20251106_140000_session3"
    session3_dir.mkdir()
    (session3_dir / "session3_full.txt").write_text("A third session with a HELLO in caps")

    return tmp_path


def test_search_no_matches(mock_output_dir: Path):
    searcher = SessionSearcher(str(mock_output_dir))
    results = searcher.search("goodbye")
    assert len(results) == 0

def test_search_single_match(mock_output_dir: Path):
    searcher = SessionSearcher(str(mock_output_dir))
    results = searcher.search("world")
    assert len(results) == 1
    assert results[0]["session_id"] == "session1"
    assert results[0]["line_number"] == 1
    assert "Hello world" in results[0]["line_content"]

def test_search_multiple_matches_in_one_file(mock_output_dir: Path):
    searcher = SessionSearcher(str(mock_output_dir))
    results = searcher.search("hello")
    assert len(results) == 3 # Two in session1, one in session3
    session1_matches = [r for r in results if r["session_id"] == "session1"]
    assert len(session1_matches) == 2

def test_search_case_insensitive(mock_output_dir: Path):
    searcher = SessionSearcher(str(mock_output_dir))
    results = searcher.search("HELLO")
    assert len(results) == 3
    assert results[0]["line_content"] == "Hello world"
    assert results[1]["line_content"] == "Another line with hello"
    assert results[2]["line_content"] == "A third session with a HELLO in caps"

def test_search_across_multiple_files(mock_output_dir: Path):
    searcher = SessionSearcher(str(mock_output_dir))
    results = searcher.search("session")
    assert len(results) == 2
    session_ids = {r["session_id"] for r in results}
    assert session_ids == {"session2", "session3"}
