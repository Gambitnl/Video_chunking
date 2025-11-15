"""
Unit tests for IntermediateOutputManager.

Tests the save/load functionality for intermediate stage outputs.
"""

import json
import pytest
from pathlib import Path
from typing import List

from src.intermediate_output import IntermediateOutputManager
from src.transcriber import TranscriptionSegment


@pytest.fixture
def temp_session_dir(tmp_path):
    """Create a temporary session directory for testing."""
    session_dir = tmp_path / "20251115_120000_test_session"
    session_dir.mkdir()
    return session_dir


@pytest.fixture
def manager(temp_session_dir):
    """Create an IntermediateOutputManager instance for testing."""
    return IntermediateOutputManager(temp_session_dir)


@pytest.fixture
def sample_merged_segments():
    """Create sample merged transcript segments for testing."""
    return [
        TranscriptionSegment(
            text="Welcome to the adventure!",
            start_time=0.0,
            end_time=2.5,
            confidence=0.95,
            words=[
                {"word": "Welcome", "start": 0.0, "end": 0.5},
                {"word": "to", "start": 0.5, "end": 0.7},
                {"word": "the", "start": 0.7, "end": 0.9},
                {"word": "adventure", "start": 0.9, "end": 2.0},
            ],
        ),
        TranscriptionSegment(
            text="Let's begin our journey.",
            start_time=2.5,
            end_time=5.0,
            confidence=0.92,
            words=None,
        ),
    ]


@pytest.fixture
def sample_diarization_segments():
    """Create sample diarization segments for testing."""
    return [
        {
            "text": "Welcome to the adventure!",
            "start_time": 0.0,
            "end_time": 2.5,
            "speaker": "SPEAKER_00",
            "confidence": 0.88,
            "words": [
                {"word": "Welcome", "start": 0.0, "end": 0.5},
            ],
        },
        {
            "text": "Let's begin our journey.",
            "start_time": 2.5,
            "end_time": 5.0,
            "speaker": "SPEAKER_01",
            "confidence": 0.85,
            "words": [],
        },
    ]


@pytest.fixture
def sample_classification_data():
    """Create sample classification data for testing."""
    segments = [
        {
            "text": "Welcome to the adventure!",
            "start_time": 0.0,
            "end_time": 2.5,
            "speaker": "SPEAKER_00",
        },
        {
            "text": "Should we order pizza?",
            "start_time": 2.5,
            "end_time": 5.0,
            "speaker": "SPEAKER_01",
        },
    ]
    classifications = [
        {
            "classification": "IC",
            "confidence": 0.95,
            "reasoning": "Dungeon Master opening the session",
            "character": None,
        },
        {
            "classification": "OOC",
            "confidence": 0.92,
            "reasoning": "Discussing real-world food",
            "character": None,
        },
    ]
    return segments, classifications


class TestIntermediateOutputManager:
    """Test suite for IntermediateOutputManager."""

    def test_initialization(self, temp_session_dir):
        """Test manager initialization."""
        manager = IntermediateOutputManager(temp_session_dir)
        assert manager.session_output_dir == temp_session_dir
        assert manager.intermediates_dir == temp_session_dir / "intermediates"
        assert manager.session_id == "20251115_120000_test_session"

    def test_ensure_intermediates_dir(self, manager):
        """Test that intermediates directory is created."""
        intermediates_dir = manager.ensure_intermediates_dir()
        assert intermediates_dir.exists()
        assert intermediates_dir.is_dir()
        assert intermediates_dir == manager.intermediates_dir

    def test_get_stage_filename(self, manager):
        """Test stage filename generation."""
        assert manager.get_stage_filename(4) == "stage_4_merged_transcript.json"
        assert manager.get_stage_filename(5) == "stage_5_diarization.json"
        assert manager.get_stage_filename(6) == "stage_6_classification.json"

        with pytest.raises(ValueError, match="Invalid stage number"):
            manager.get_stage_filename(7)

    def test_get_stage_path(self, manager):
        """Test stage path generation."""
        path = manager.get_stage_path(4)
        assert path == manager.intermediates_dir / "stage_4_merged_transcript.json"

    def test_stage_output_exists(self, manager):
        """Test checking if stage output exists."""
        assert not manager.stage_output_exists(4)

        # Create a dummy file
        manager.ensure_intermediates_dir()
        stage_path = manager.get_stage_path(4)
        stage_path.write_text("{}")

        assert manager.stage_output_exists(4)

    def test_save_merged_transcript(self, manager, sample_merged_segments):
        """Test saving merged transcript output."""
        output_path = manager.save_merged_transcript(
            sample_merged_segments,
            input_file="test_input.mp4",
        )

        assert output_path.exists()
        assert output_path.name == "stage_4_merged_transcript.json"

        # Verify file contents
        with open(output_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "metadata" in data
        assert "segments" in data
        assert "statistics" in data

        # Check metadata
        metadata = data["metadata"]
        assert metadata["session_id"] == "20251115_120000_test_session"
        assert metadata["stage"] == "merged_transcript"
        assert metadata["stage_number"] == 4
        assert metadata["input_file"] == "test_input.mp4"
        assert metadata["version"] == "1.0"

        # Check segments
        assert len(data["segments"]) == 2
        assert data["segments"][0]["text"] == "Welcome to the adventure!"
        assert data["segments"][0]["start_time"] == 0.0
        assert data["segments"][0]["end_time"] == 2.5
        assert data["segments"][0]["confidence"] == 0.95
        assert len(data["segments"][0]["words"]) == 4

        # Check statistics
        assert data["statistics"]["total_segments"] == 2
        assert data["statistics"]["total_duration"] == 5.0

    def test_load_merged_transcript(self, manager, sample_merged_segments):
        """Test loading merged transcript output."""
        # Save first
        manager.save_merged_transcript(sample_merged_segments)

        # Load
        loaded_segments = manager.load_merged_transcript()

        assert len(loaded_segments) == 2
        assert isinstance(loaded_segments[0], TranscriptionSegment)
        assert loaded_segments[0].text == "Welcome to the adventure!"
        assert loaded_segments[0].start_time == 0.0
        assert loaded_segments[0].end_time == 2.5
        assert loaded_segments[0].confidence == 0.95
        assert loaded_segments[0].words is not None
        assert len(loaded_segments[0].words) == 4

    def test_save_diarization(self, manager, sample_diarization_segments):
        """Test saving diarization output."""
        output_path = manager.save_diarization(
            sample_diarization_segments,
            input_file="test_input.mp4",
        )

        assert output_path.exists()
        assert output_path.name == "stage_5_diarization.json"

        # Verify file contents
        with open(output_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "metadata" in data
        assert "segments" in data
        assert "statistics" in data

        # Check statistics
        stats = data["statistics"]
        assert stats["unique_speakers"] == 2
        assert stats["total_segments"] == 2
        assert "SPEAKER_00" in stats["speaker_time"]
        assert "SPEAKER_01" in stats["speaker_time"]

    def test_load_diarization(self, manager, sample_diarization_segments):
        """Test loading diarization output."""
        # Save first
        manager.save_diarization(sample_diarization_segments)

        # Load
        loaded_segments = manager.load_diarization()

        assert len(loaded_segments) == 2
        assert loaded_segments[0]["text"] == "Welcome to the adventure!"
        assert loaded_segments[0]["speaker"] == "SPEAKER_00"
        assert loaded_segments[0]["confidence"] == 0.88

    def test_save_classification(self, manager, sample_classification_data):
        """Test saving classification output."""
        segments, classifications = sample_classification_data

        output_path = manager.save_classification(
            segments,
            classifications,
            input_file="test_input.mp4",
        )

        assert output_path.exists()
        assert output_path.name == "stage_6_classification.json"

        # Verify file contents
        with open(output_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "metadata" in data
        assert "segments" in data
        assert "statistics" in data

        # Check merged segments
        assert len(data["segments"]) == 2
        assert data["segments"][0]["text"] == "Welcome to the adventure!"
        assert data["segments"][0]["classification"] == "IC"
        assert data["segments"][0]["confidence"] == 0.95
        assert data["segments"][1]["classification"] == "OOC"

        # Check statistics
        stats = data["statistics"]
        assert stats["total_segments"] == 2
        assert stats["ic_count"] == 1
        assert stats["ooc_count"] == 1
        assert stats["mixed_count"] == 0
        assert stats["ic_percentage"] == 50.0

    def test_load_classification(self, manager, sample_classification_data):
        """Test loading classification output."""
        segments, classifications = sample_classification_data

        # Save first
        manager.save_classification(segments, classifications)

        # Load
        loaded_segments, loaded_classifications = manager.load_classification()

        assert len(loaded_segments) == 2
        assert len(loaded_classifications) == 2

        # Check segments
        assert loaded_segments[0]["text"] == "Welcome to the adventure!"
        assert loaded_segments[0]["speaker"] == "SPEAKER_00"

        # Check classifications
        assert loaded_classifications[0]["classification"] == "IC"
        assert loaded_classifications[0]["confidence"] == 0.95
        assert loaded_classifications[1]["classification"] == "OOC"

    def test_load_nonexistent_stage(self, manager):
        """Test loading from a nonexistent stage file."""
        with pytest.raises(FileNotFoundError, match="Stage 4 output not found"):
            manager.load_merged_transcript()

    def test_save_stage_output_invalid_stage(self, manager):
        """Test saving with an invalid stage number."""
        with pytest.raises(ValueError, match="Invalid stage number"):
            manager.save_stage_output(99, [], {})

    def test_roundtrip_merged_transcript(self, manager, sample_merged_segments):
        """Test save/load roundtrip for merged transcript."""
        # Save
        manager.save_merged_transcript(sample_merged_segments)

        # Load
        loaded = manager.load_merged_transcript()

        # Compare
        assert len(loaded) == len(sample_merged_segments)
        for original, loaded_seg in zip(sample_merged_segments, loaded):
            assert loaded_seg.text == original.text
            assert loaded_seg.start_time == original.start_time
            assert loaded_seg.end_time == original.end_time
            assert loaded_seg.confidence == original.confidence

    def test_roundtrip_diarization(self, manager, sample_diarization_segments):
        """Test save/load roundtrip for diarization."""
        # Save
        manager.save_diarization(sample_diarization_segments)

        # Load
        loaded = manager.load_diarization()

        # Compare
        assert len(loaded) == len(sample_diarization_segments)
        for original, loaded_seg in zip(sample_diarization_segments, loaded):
            assert loaded_seg["text"] == original["text"]
            assert loaded_seg["speaker"] == original["speaker"]
            assert loaded_seg["start_time"] == original["start_time"]

    def test_roundtrip_classification(self, manager, sample_classification_data):
        """Test save/load roundtrip for classification."""
        segments, classifications = sample_classification_data

        # Save
        manager.save_classification(segments, classifications)

        # Load
        loaded_segments, loaded_classifications = manager.load_classification()

        # Compare
        assert len(loaded_segments) == len(segments)
        assert len(loaded_classifications) == len(classifications)

        for orig_seg, loaded_seg in zip(segments, loaded_segments):
            assert loaded_seg["text"] == orig_seg["text"]
            assert loaded_seg["speaker"] == orig_seg["speaker"]

        for orig_class, loaded_class in zip(classifications, loaded_classifications):
            assert loaded_class["classification"] == orig_class["classification"]
            assert loaded_class["confidence"] == orig_class["confidence"]
