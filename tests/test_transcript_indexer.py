"""
Tests for TranscriptIndexer.

Tests the indexing functionality for session transcripts including:
- Index building
- Session parsing
- Caching
- Error handling

Author: Claude (Sonnet 4.5)
Date: 2025-11-17
"""
import json
import pytest
from pathlib import Path

from src.transcript_indexer import (
    TranscriptIndexer,
    TranscriptIndex,
    TranscriptSegment,
)


def test_indexer_initialization(tmp_path):
    """Test indexer initializes correctly."""
    indexer = TranscriptIndexer(tmp_path)
    assert indexer.output_dir == tmp_path
    assert indexer.cache_dir.exists()
    assert indexer.cache_file == indexer.cache_dir / "transcript_index.pkl"


def test_build_empty_index(tmp_path):
    """Test building index with no sessions."""
    indexer = TranscriptIndexer(tmp_path)
    index = indexer.build_index()

    assert isinstance(index, TranscriptIndex)
    assert index.get_total_segments() == 0
    assert index.get_session_count() == 0
    assert len(index.speakers) == 0


def test_index_single_session(tmp_path):
    """Test indexing a single session."""
    # Create mock session directory with JSON data
    session_dir = tmp_path / "20251117_143000_test_session"
    session_dir.mkdir()

    data_file = session_dir / "test_session_data.json"
    data_file.write_text(
        json.dumps(
            {
                "segments": [
                    {
                        "start": 0.0,
                        "timestamp": "00:00:00",
                        "speaker": "Alice",
                        "text": "Hello world",
                        "classification": "IC",
                    },
                    {
                        "start": 5.0,
                        "timestamp": "00:00:05",
                        "speaker": "Bob",
                        "text": "Hi there",
                        "classification": "IC",
                    },
                ],
                "num_speakers": 2,
                "total_duration": 10.0,
            }
        )
    )

    indexer = TranscriptIndexer(tmp_path)
    index = indexer.build_index()

    assert index.get_total_segments() == 2
    assert index.get_session_count() == 1
    assert len(index.speakers) == 2
    assert "Alice" in index.speakers
    assert "Bob" in index.speakers

    # Check first segment
    seg = index.segments[0]
    assert seg.session_id == "test_session"
    assert seg.speaker == "Alice"
    assert seg.text == "Hello world"
    assert seg.ic_ooc == "IC"


def test_index_multiple_sessions(tmp_path):
    """Test indexing multiple sessions."""
    # Create two sessions
    for i in range(2):
        session_dir = tmp_path / f"20251117_14300{i}_session_{i}"
        session_dir.mkdir()

        data_file = session_dir / f"session_{i}_data.json"
        data_file.write_text(
            json.dumps(
                {
                    "segments": [
                        {
                            "start": 0.0,
                            "timestamp": "00:00:00",
                            "speaker": f"Speaker{i}",
                            "text": f"Session {i} text",
                            "classification": "IC",
                        }
                    ]
                }
            )
        )

    indexer = TranscriptIndexer(tmp_path)
    index = indexer.build_index()

    assert index.get_total_segments() == 2
    assert index.get_session_count() == 2
    assert "Speaker0" in index.speakers
    assert "Speaker1" in index.speakers


def test_cache_persistence(tmp_path):
    """Test index caching works."""
    # Create mock session
    session_dir = tmp_path / "20251117_143000_test"
    session_dir.mkdir()

    data_file = session_dir / "test_data.json"
    data_file.write_text(
        json.dumps(
            {
                "segments": [
                    {
                        "start": 0.0,
                        "timestamp": "00:00:00",
                        "speaker": "Alice",
                        "text": "Test",
                        "classification": "IC",
                    }
                ]
            }
        )
    )

    indexer = TranscriptIndexer(tmp_path)

    # Build index (creates cache)
    index1 = indexer.build_index()
    assert index1.get_total_segments() == 1

    # Check cache file exists
    assert indexer.cache_file.exists()

    # Create new indexer, should load from cache
    indexer2 = TranscriptIndexer(tmp_path)
    index2 = indexer2.build_index(force_rebuild=False)

    assert index2.get_total_segments() == 1


def test_force_rebuild(tmp_path):
    """Test force rebuild bypasses cache."""
    session_dir = tmp_path / "20251117_143000_test"
    session_dir.mkdir()

    data_file = session_dir / "test_data.json"
    data_file.write_text(
        json.dumps({"segments": [{"start": 0.0, "timestamp": "00:00:00", "speaker": "Alice", "text": "Test", "classification": "IC"}]})
    )

    indexer = TranscriptIndexer(tmp_path)

    # Build and cache
    index1 = indexer.build_index()
    cache_time1 = indexer.cache_file.stat().st_mtime

    # Force rebuild (should create new cache)
    import time

    time.sleep(0.1)  # Ensure different timestamp
    index2 = indexer.build_index(force_rebuild=True)

    cache_time2 = indexer.cache_file.stat().st_mtime
    assert cache_time2 > cache_time1


def test_invalid_directory_name(tmp_path):
    """Test handling of invalid directory names."""
    # Create directory with invalid format
    invalid_dir = tmp_path / "invalid_format"
    invalid_dir.mkdir()

    (invalid_dir / "data.json").write_text(json.dumps({"segments": []}))

    indexer = TranscriptIndexer(tmp_path)
    index = indexer.build_index()

    # Should skip invalid directory
    assert index.get_session_count() == 0


def test_missing_json_file(tmp_path):
    """Test handling of missing JSON data file."""
    session_dir = tmp_path / "20251117_143000_test"
    session_dir.mkdir()
    # No JSON file created

    indexer = TranscriptIndexer(tmp_path)
    index = indexer.build_index()

    # Should skip session without JSON
    assert index.get_session_count() == 0


def test_invalidate_cache(tmp_path):
    """Test cache invalidation."""
    session_dir = tmp_path / "20251117_143000_test"
    session_dir.mkdir()

    data_file = session_dir / "test_data.json"
    data_file.write_text(json.dumps({"segments": []}))

    indexer = TranscriptIndexer(tmp_path)
    indexer.build_index()

    assert indexer.cache_file.exists()

    # Invalidate cache
    indexer.invalidate_cache()

    assert not indexer.cache_file.exists()
    assert indexer.index is None


def test_segment_metadata(tmp_path):
    """Test segment metadata is correctly extracted."""
    session_dir = tmp_path / "20251117_143000_test_session"
    session_dir.mkdir()

    data_file = session_dir / "test_session_data.json"
    data_file.write_text(
        json.dumps(
            {
                "segments": [
                    {
                        "start": 12.5,
                        "timestamp": "00:00:12",
                        "speaker": "Alice",
                        "text": "Test text",
                        "classification": "OOC",
                    }
                ]
            }
        )
    )

    indexer = TranscriptIndexer(tmp_path)
    index = indexer.build_index()

    seg = index.segments[0]
    assert seg.session_id == "test_session"
    assert seg.timestamp == 12.5
    assert seg.timestamp_str == "00:00:12"
    assert seg.speaker == "Alice"
    assert seg.text == "Test text"
    assert seg.ic_ooc == "OOC"
    assert seg.session_date == "20251117_143000"


def test_session_metadata_extraction(tmp_path):
    """Test session metadata is correctly stored."""
    session_dir = tmp_path / "20251117_143000_test"
    session_dir.mkdir()

    data_file = session_dir / "test_data.json"
    data_file.write_text(
        json.dumps(
            {
                "segments": [],
                "num_speakers": 3,
                "total_duration": 120.5,
                "ic_percentage": 75.2,
                "ooc_percentage": 24.8,
            }
        )
    )

    indexer = TranscriptIndexer(tmp_path)
    index = indexer.build_index()

    metadata = index.sessions["test"]
    assert metadata["num_speakers"] == 3
    assert metadata["total_duration"] == 120.5
    assert metadata["ic_percentage"] == 75.2
    assert metadata["ooc_percentage"] == 24.8
