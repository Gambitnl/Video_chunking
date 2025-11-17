"""
Tests for SearchResultExporter.

Tests export functionality for search results including:
- JSON export
- CSV export
- TXT export
- Markdown export
- Error handling

Author: Claude (Sonnet 4.5)
Date: 2025-11-17
"""
import csv
import json
import pytest
from pathlib import Path

from src.search_engine import SearchResult
from src.search_exporter import SearchResultExporter
from src.transcript_indexer import TranscriptSegment


@pytest.fixture
def sample_results():
    """Create sample search results."""
    segment1 = TranscriptSegment(
        session_id="test_session",
        timestamp=10.5,
        timestamp_str="00:00:10",
        speaker="Alice",
        text="This is a test segment with dragon",
        ic_ooc="IC",
        segment_index=0,
        session_date="20251117_120000",
    )

    segment2 = TranscriptSegment(
        session_id="test_session",
        timestamp=20.0,
        timestamp_str="00:00:20",
        speaker="Bob",
        text="Another test about dragons",
        ic_ooc="OOC",
        segment_index=1,
        session_date="20251117_120000",
    )

    result1 = SearchResult(
        segment=segment1,
        match_text="test segment with dragon",
        context_before=["[DM] Previous context"],
        context_after=["[Bob] Following context"],
        relevance_score=0.95,
    )

    result2 = SearchResult(
        segment=segment2, match_text="test about dragons", relevance_score=0.80
    )

    return [result1, result2]


def test_export_to_json(tmp_path, sample_results):
    """Test JSON export."""
    output_file = tmp_path / "results.json"

    success = SearchResultExporter.export_to_json(sample_results, output_file)

    assert success
    assert output_file.exists()

    with open(output_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "exported_at" in data
    assert data["result_count"] == 2
    assert len(data["results"]) == 2

    # Check first result
    result = data["results"][0]
    assert result["speaker"] == "Alice"
    assert result["session_id"] == "test_session"
    assert result["text"] == "This is a test segment with dragon"
    assert result["relevance_score"] == 0.95
    assert len(result["context_before"]) == 1
    assert len(result["context_after"]) == 1


def test_export_to_json_unicode(tmp_path, sample_results):
    """Test JSON export handles unicode correctly."""
    # Add unicode characters
    sample_results[0].segment.text = "Test with unicode: \u2764\ufe0f"

    output_file = tmp_path / "results.json"
    success = SearchResultExporter.export_to_json(sample_results, output_file)

    assert success

    with open(output_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "\u2764\ufe0f" in data["results"][0]["text"]


def test_export_to_csv(tmp_path, sample_results):
    """Test CSV export."""
    output_file = tmp_path / "results.csv"

    success = SearchResultExporter.export_to_csv(sample_results, output_file)

    assert success
    assert output_file.exists()

    with open(output_file, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    # Header + 2 results
    assert len(rows) == 3

    # Check header
    assert rows[0][0] == "Session ID"
    assert "Speaker" in rows[0]
    assert "IC/OOC" in rows[0]

    # Check first result
    assert rows[1][0] == "test_session"
    assert rows[1][3] == "Alice"
    assert rows[1][4] == "IC"


def test_export_to_csv_special_characters(tmp_path, sample_results):
    """Test CSV export handles special characters (commas, quotes)."""
    # Add text with commas and quotes
    sample_results[0].segment.text = 'Text with "quotes" and, commas'

    output_file = tmp_path / "results.csv"
    success = SearchResultExporter.export_to_csv(sample_results, output_file)

    assert success

    with open(output_file, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    # CSV should properly escape quotes and commas
    assert rows[1][5] == 'Text with "quotes" and, commas'


def test_export_to_txt(tmp_path, sample_results):
    """Test TXT export."""
    output_file = tmp_path / "results.txt"

    success = SearchResultExporter.export_to_txt(
        sample_results, output_file, query="dragon"
    )

    assert success
    assert output_file.exists()

    content = output_file.read_text(encoding="utf-8")

    # Check header
    assert "Search Results for: dragon" in content
    assert "Total Results: 2" in content

    # Check first result
    assert "Result 1:" in content
    assert "Session: test_session" in content
    assert "Speaker: Alice" in content
    assert "Relevance: 0.95" in content
    assert "This is a test segment with dragon" in content


def test_export_to_markdown(tmp_path, sample_results):
    """Test Markdown export."""
    output_file = tmp_path / "results.md"

    success = SearchResultExporter.export_to_markdown(
        sample_results, output_file, query="dragon"
    )

    assert success
    assert output_file.exists()

    content = output_file.read_text(encoding="utf-8")

    # Check markdown header
    assert "# Search Results: dragon" in content
    assert "**Total Results:** 2" in content

    # Check markdown formatting
    assert "## Result 1:" in content
    assert "**Speaker:** Alice" in content
    assert "**Type:** IC" in content
    assert "**Score:** 0.95" in content

    # Check context formatting (blockquotes)
    assert "> [DM] Previous context" in content
    assert "> [Bob] Following context" in content


def test_export_empty_results(tmp_path):
    """Test exporting empty results list."""
    output_file = tmp_path / "results.json"

    success = SearchResultExporter.export_to_json([], output_file)

    assert success

    with open(output_file, "r") as f:
        data = json.load(f)

    assert data["result_count"] == 0
    assert len(data["results"]) == 0


def test_export_to_invalid_path(sample_results):
    """Test export fails gracefully with invalid path."""
    # Non-existent directory
    invalid_path = Path("/nonexistent/directory/results.json")

    success = SearchResultExporter.export_to_json(sample_results, invalid_path)

    assert not success


def test_export_all_formats(tmp_path, sample_results):
    """Test all export formats work correctly."""
    exporter = SearchResultExporter()

    # Test all formats
    formats = {
        "json": exporter.export_to_json,
        "csv": exporter.export_to_csv,
        "txt": lambda r, p: exporter.export_to_txt(r, p, "test"),
        "md": lambda r, p: exporter.export_to_markdown(r, p, "test"),
    }

    for ext, export_fn in formats.items():
        output_file = tmp_path / f"results.{ext}"
        success = export_fn(sample_results, output_file)

        assert success, f"Export to {ext} failed"
        assert output_file.exists(), f"{ext} file not created"
        assert output_file.stat().st_size > 0, f"{ext} file is empty"
