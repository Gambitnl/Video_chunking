
import pytest
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
import json

from src.diarizer import SpeakerDiarizer, SpeakerProfileManager, SpeakerSegment
from src.transcriber import TranscriptionSegment

@pytest.fixture
def diarizer():
    """Provides a SpeakerDiarizer instance."""
    return SpeakerDiarizer(num_speakers=2)

class TestSpeakerDiarizer:

    @pytest.mark.parametrize("start_a, end_a, start_b, end_b, expected_overlap", [
        (0, 10, 5, 15, 5),      # Partial overlap at the end
        (5, 15, 0, 10, 5),      # Partial overlap at the beginning
        (0, 10, 2, 8, 6),       # B is inside A
        (2, 8, 0, 10, 6),       # A is inside B
        (0, 10, 10, 20, 0),     # Adjacent, no overlap
        (0, 5, 10, 15, 0),      # No overlap
        (0, 10, 0, 10, 10),     # Exact same segment
    ])
    def test_calculate_overlap(self, diarizer, start_a, end_a, start_b, end_b, expected_overlap):
        overlap = diarizer._calculate_overlap(start_a, end_a, start_b, end_b)
        assert overlap == pytest.approx(expected_overlap)

    def test_assign_speakers_to_transcription(self, diarizer):
        trans_segments = [
            TranscriptionSegment(text="Hello", start_time=0.5, end_time=1.5),
            TranscriptionSegment(text="world", start_time=2.0, end_time=3.0),
            TranscriptionSegment(text="no speaker", start_time=10.0, end_time=11.0),
        ]
        speaker_segments = [
            SpeakerSegment(speaker_id="SPEAKER_00", start_time=0.0, end_time=1.8),
            SpeakerSegment(speaker_id="SPEAKER_01", start_time=1.9, end_time=5.0),
        ]

        enriched = diarizer.assign_speakers_to_transcription(trans_segments, speaker_segments)

        assert len(enriched) == 3
        assert enriched[0]['speaker'] == "SPEAKER_00"
        assert enriched[1]['speaker'] == "SPEAKER_01"
        assert enriched[2]['speaker'] == "UNKNOWN"

    @patch('pyannote.audio.Pipeline')
    def test_diarize_successful_pipeline(self, MockPipeline, diarizer, tmp_path):
        # Arrange
        mock_pipeline_instance = MockPipeline.from_pretrained.return_value
        mock_diarization_result = MagicMock()
        # Mock the iterable result of itertracks
        mock_diarization_result.itertracks.return_value = [
            (MagicMock(start=1.0, end=3.0), None, "SPEAKER_00"),
            (MagicMock(start=3.5, end=5.0), None, "SPEAKER_01"),
        ]
        mock_pipeline_instance.return_value = mock_diarization_result
        diarizer.pipeline = mock_pipeline_instance # Pre-load to avoid thread lock issues in test

        dummy_audio_path = tmp_path / "audio.wav"
        dummy_audio_path.touch()

        # Act
        result = diarizer.diarize(dummy_audio_path)

        # Assert
        mock_pipeline_instance.assert_called_once_with(str(dummy_audio_path), num_speakers=2)
        assert len(result) == 2
        assert result[0].speaker_id == "SPEAKER_00"
        assert result[0].start_time == 1.0
        assert result[1].speaker_id == "SPEAKER_01"

    @patch('pyannote.audio.Pipeline.from_pretrained', side_effect=Exception("Model loading failed"))
    @patch('pydub.AudioSegment.from_file')
    def test_diarize_fallback_on_pipeline_failure(self, MockAudioSegment, MockFromPretrained, diarizer, tmp_path):
        # Arrange
        mock_audio = MagicMock()
        mock_audio.duration_seconds = 120.0
        # pydub uses len() for duration in ms
        type(mock_audio).duration_seconds = property(fget=lambda s: len(s) / 1000.0)
        mock_audio.__len__.return_value = 120000
        MockAudioSegment.return_value = mock_audio
        
        diarizer.pipeline = None # Ensure pipeline is not loaded

        dummy_audio_path = tmp_path / "audio.wav"
        dummy_audio_path.touch()

        # Act
        result = diarizer.diarize(dummy_audio_path)

        # Assert
        MockFromPretrained.assert_called_once()
        assert len(result) == 1
        assert result[0].speaker_id == "SPEAKER_00"
        assert result[0].start_time == 0.0
        assert result[0].end_time == 120.0

class TestSpeakerProfileManager:

    @pytest.fixture
    def profile_file(self, tmp_path):
        return tmp_path / "profiles.json"

    def test_init_no_file(self, profile_file):
        manager = SpeakerProfileManager(profile_file=profile_file)
        assert manager.profiles == {}

    def test_map_and_save_profile(self, profile_file):
        manager = SpeakerProfileManager(profile_file=profile_file)
        manager.map_speaker("session1", "SPEAKER_00", "Alice")
        manager.map_speaker("session1", "SPEAKER_01", "Bob")
        manager.map_speaker("session2", "SPEAKER_00", "Charlie")

        # Verify in-memory representation
        assert manager.profiles["session1"]["SPEAKER_00"] == "Alice"
        assert manager.profiles["session2"]["SPEAKER_00"] == "Charlie"

        # Verify file content
        with open(profile_file, 'r') as f:
            data = json.load(f)
        assert data["session1"]["SPEAKER_00"] == "Alice"

    def test_load_existing_profiles(self, profile_file):
        # Arrange: Create a profile file first
        initial_data = {"session1": {"SPEAKER_00": "Alice"}}
        with open(profile_file, 'w') as f:
            json.dump(initial_data, f)

        # Act: Create a new manager that loads the file
        manager = SpeakerProfileManager(profile_file=profile_file)

        # Assert
        assert manager.profiles == initial_data
        name = manager.get_person_name("session1", "SPEAKER_00")
        assert name == "Alice"

    def test_get_person_name(self, profile_file):
        manager = SpeakerProfileManager(profile_file=profile_file)
        manager.map_speaker("session1", "SPEAKER_00", "Alice")

        # Test successful retrieval
        assert manager.get_person_name("session1", "SPEAKER_00") == "Alice"

        # Test unsuccessful retrievals
        assert manager.get_person_name("session1", "SPEAKER_01") is None
        assert manager.get_person_name("session2", "SPEAKER_00") is None
